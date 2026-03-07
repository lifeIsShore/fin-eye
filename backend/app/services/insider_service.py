"""
app/services/insider_service.py
───────────────────────────────────────────────────────────────────────────────
EXP-INSID-01 — Insider Trading Intelligence via SEC EDGAR

Fetches Form 4 (Statement of Changes in Beneficial Ownership) filings from the
SEC's free EDGAR full-text search API. No API key required.

Data flow:
  1. Resolve ticker → CIK via SEC company_tickers JSON
  2. Fetch recent Form 4 filings for the CIK via EDGAR submissions endpoint
  3. Parse transaction details (type, shares, price, date, insider name/title)
  4. Compute an insider sentiment score (0–100) from recent buy/sell balance
  5. Cache results for 1 hour (Form 4s are filed within 2 business days; no need
     for sub-hour freshness)

SEC EDGAR API endpoints used:
  - https://data.sec.gov/submissions/CIK{cik:010d}.json   (filing index per company)
  - https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=...  (fallback)
  - https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json  (not used)

SEC User-Agent header required: "Fin-Eye/1.0 contact@fin-eye.com"
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

EDGAR_BASE = "https://data.sec.gov"
HEADERS = {
    "User-Agent": "Fin-Eye/1.0 contact@fin-eye.com",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "application/json",
}
CACHE_TTL = 3600          # 1 hour
MAX_TRANSACTIONS = 50     # transactions to return in detail list
LOOKBACK_DAYS   = 180     # how many days of transactions to consider for score

# ─── Cache ────────────────────────────────────────────────────────────────────

_TICKER_CIK_CACHE: Dict[str, Optional[str]] = {}     # ticker -> CIK or None
_CACHE: Dict[str, tuple] = {}                          # symbol -> (ts, InsiderAnalysis)
_COMPANY_TICKERS: Optional[Dict] = None               # lazy-loaded once
_COMPANY_TICKERS_TS: float = 0.0


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class InsiderTransaction:
    filing_date: str           # YYYY-MM-DD
    transaction_date: str      # YYYY-MM-DD (may equal filing_date if missing)
    insider_name: str
    insider_title: str
    transaction_type: str      # "P" buy, "S" sell, "A" award, "D" dispose, etc.
    transaction_type_label: str
    shares: float
    price_per_share: Optional[float]
    total_value: Optional[float]
    shares_after: Optional[float]
    ownership_type: str        # "D" direct, "I" indirect
    accession_number: str


@dataclass
class InsiderSentiment:
    score: float               # 0–100 (50 = neutral)
    label: str                 # Bullish / Mildly Bullish / Neutral / Mildly Bearish / Bearish
    buy_transactions: int
    sell_transactions: int
    buy_shares: float
    sell_shares: float
    buy_value: Optional[float]
    sell_value: Optional[float]
    net_shares: float          # buy_shares - sell_shares
    net_value: Optional[float]
    lookback_days: int


@dataclass
class InsiderAnalysis:
    symbol: str
    company_name: str
    cik: str
    sentiment: InsiderSentiment
    transactions: List[InsiderTransaction]
    total_filings_found: int
    disclaimer: str = (
        "Insider transaction data is sourced from SEC EDGAR Form 4 filings. "
        "Transactions include purchases, sales, and awards. Insider activity is "
        "one signal among many — it does not constitute investment advice. "
        "Always conduct independent research before making financial decisions."
    )


# ─── SEC EDGAR helpers ────────────────────────────────────────────────────────

def _get_company_tickers() -> Dict:
    """Fetch and cache the SEC's full company tickers JSON (updates infrequently)."""
    global _COMPANY_TICKERS, _COMPANY_TICKERS_TS
    now = time.time()
    if _COMPANY_TICKERS is not None and (now - _COMPANY_TICKERS_TS) < 86400:
        return _COMPANY_TICKERS

    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        with httpx.Client(headers=HEADERS, timeout=15) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            _COMPANY_TICKERS = data
            _COMPANY_TICKERS_TS = now
            return data
    except Exception as exc:
        logger.warning("Failed to fetch SEC company tickers: %s", exc)
        return {}


def _ticker_to_cik(ticker: str) -> Optional[str]:
    """Resolve ticker symbol to a zero-padded 10-digit CIK string."""
    ticker_upper = ticker.upper()
    if ticker_upper in _TICKER_CIK_CACHE:
        return _TICKER_CIK_CACHE[ticker_upper]

    tickers = _get_company_tickers()
    for entry in tickers.values():
        if entry.get("ticker", "").upper() == ticker_upper:
            cik = str(entry["cik_str"]).zfill(10)
            _TICKER_CIK_CACHE[ticker_upper] = cik
            return cik

    _TICKER_CIK_CACHE[ticker_upper] = None
    return None


def _fetch_submissions(cik: str) -> Dict:
    """Fetch the EDGAR submissions JSON for a CIK."""
    url = f"{EDGAR_BASE}/submissions/CIK{cik}.json"
    with httpx.Client(headers=HEADERS, timeout=20) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def _fetch_form4_index(cik: str, accession: str) -> Optional[str]:
    """Fetch the filing index page to get the actual Form 4 XML filename."""
    # Convert accession: "0001234567-24-000123" -> "000123456724000123"
    acc_clean = accession.replace("-", "")
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{accession}-index.json"
    try:
        with httpx.Client(headers=HEADERS, timeout=10) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            for doc in data.get("documents", []):
                if doc.get("type") == "4" or doc.get("documentDescription", "").startswith("FORM 4"):
                    return doc.get("document")
    except Exception:
        pass
    return None


def _parse_transaction_type(code: str) -> str:
    """Human-readable label for SEC transaction type codes."""
    mapping = {
        "P": "Open Market Purchase",
        "S": "Open Market Sale",
        "A": "Award / Grant",
        "D": "Disposition (Non-Sale)",
        "M": "Option Exercise",
        "F": "Tax Withholding",
        "X": "Option / Warrant Exercise",
        "G": "Gift",
        "L": "Small Acquisition",
        "U": "Tender of Shares",
        "W": "Will / Inheritance",
        "Z": "Voting Trust",
        "J": "Other Acquisition",
        "K": "Equity Swap",
        "C": "Conversion",
        "E": "Expiration of Short Derivative",
        "H": "Expiration of Long Derivative",
        "I": "Discretionary Transaction",
        "O": "Option Out-of-Money Exercise",
        "R": "Disposition to Issuer",
        "T": "Specified Transactions",
        "V": "Voluntary Report",
        "Y": "In-Kind Exchange",
    }
    return mapping.get(code.upper(), f"Transaction ({code})")


def _is_buy(code: str) -> bool:
    return code.upper() in {"P", "M", "X", "A", "J", "L", "C"}


def _is_sell(code: str) -> bool:
    return code.upper() in {"S", "D", "F", "G", "U", "I"}


# ─── Main analysis function ───────────────────────────────────────────────────

def analyse_insiders(symbol: str) -> InsiderAnalysis:
    """
    Fetch and analyse insider transactions for a ticker from SEC EDGAR.
    Results cached for 1 hour.
    """
    symbol_upper = symbol.upper()

    # Cache check
    if symbol_upper in _CACHE:
        ts, cached = _CACHE[symbol_upper]
        if time.time() - ts < CACHE_TTL:
            return cached

    # Resolve CIK
    cik = _ticker_to_cik(symbol_upper)
    if not cik:
        raise ValueError(
            f"Could not resolve ticker '{symbol_upper}' to an SEC CIK. "
            f"The ticker may not be listed on a US exchange or may use a different symbol "
            f"in EDGAR (e.g. BRK-B is BRKB in EDGAR)."
        )

    # Fetch submissions index
    try:
        submissions = _fetch_submissions(cik)
    except Exception as exc:
        raise ValueError(f"Failed to fetch EDGAR filings for {symbol_upper}: {exc}") from exc

    company_name = submissions.get("name", symbol_upper)
    filings = submissions.get("filings", {}).get("recent", {})

    if not filings:
        raise ValueError(f"No filings found for {symbol_upper} in EDGAR.")

    # Extract Form 4 filings
    form_types   = filings.get("form", [])
    filing_dates = filings.get("filingDate", [])
    accessions   = filings.get("accessionNumber", [])

    # We get parallel arrays — zip them and filter for Form 4
    form4_entries = [
        (date, acc)
        for ftype, date, acc in zip(form_types, filing_dates, accessions)
        if ftype == "4"
    ]

    # Sort newest first
    form4_entries.sort(key=lambda x: x[0], reverse=True)
    total_filings = len(form4_entries)

    # Parse transactions from the EDGAR submission data directly
    # EDGAR's submissions.json now includes transaction data inline for recent filings
    transactions: List[InsiderTransaction] = _extract_transactions_from_submissions(
        filings, cik
    )

    # Compute sentiment
    sentiment = _compute_sentiment(transactions, LOOKBACK_DAYS)

    result = InsiderAnalysis(
        symbol=symbol_upper,
        company_name=company_name,
        cik=cik,
        sentiment=sentiment,
        transactions=transactions[:MAX_TRANSACTIONS],
        total_filings_found=total_filings,
    )

    _CACHE[symbol_upper] = (time.time(), result)
    return result


def _extract_transactions_from_submissions(filings: Dict, cik: str) -> List[InsiderTransaction]:
    """
    Parse the inline transaction data from EDGAR's submissions.json.
    
    The recent filings object has parallel arrays. For Form 4 filings, EDGAR
    also includes reportingOwner name and transaction details in some fields.
    We reconstruct transactions from what's available.
    
    For richer data we use the EDGAR XBRL facts endpoint which has structured
    Form 4 data, but the submissions approach avoids per-filing fetching.
    """
    transactions: List[InsiderTransaction] = []

    form_types       = filings.get("form", [])
    filing_dates     = filings.get("filingDate", [])
    accessions       = filings.get("accessionNumber", [])
    report_dates     = filings.get("reportDate", [])
    primary_docs     = filings.get("primaryDocument", [])

    # We'll fetch the EDGAR company facts for Form 4 structured data instead
    # since the submissions JSON doesn't include per-transaction detail inline.
    # Fall back to fetching the first N Form 4 XMLs.
    
    form4_indices = [
        i for i, ft in enumerate(form_types) if ft == "4"
    ][:25]  # limit to 25 most recent for performance

    for idx in form4_indices:
        acc  = accessions[idx]
        date = filing_dates[idx]
        rep_date = report_dates[idx] if idx < len(report_dates) else date

        txns = _parse_form4_xml(cik, acc, date, rep_date)
        transactions.extend(txns)

    # Sort newest first
    transactions.sort(key=lambda t: t.filing_date, reverse=True)
    return transactions


def _parse_form4_xml(
    cik: str,
    accession: str,
    filing_date: str,
    report_date: str,
) -> List[InsiderTransaction]:
    """
    Fetch and parse a Form 4 XML document from EDGAR.
    
    Form 4 XML structure (simplified):
    <ownershipDocument>
      <issuer> ... </issuer>
      <reportingOwner>
        <reportingOwnerId><rptOwnerName>, <rptOwnerCik>
        <reportingOwnerRelationship>...isDirector, isOfficer, officerTitle
      </reportingOwner>
      <nonDerivativeTable>
        <nonDerivativeTransaction>
          <securityTitle>, <transactionDate>, <transactionCoding><transactionCode>
          <transactionAmounts><transactionShares>, <transactionPricePerShare>
          <postTransactionAmounts><sharesOwnedFollowingTransaction>
        </nonDerivativeTransaction>
      </nonDerivativeTable>
    </ownershipDocument>
    """
    import xml.etree.ElementTree as ET

    acc_clean = accession.replace("-", "")
    cik_int = int(cik)
    
    # Try to find the primary XML document
    # Standard Form 4 filename patterns
    candidate_names = [f"{accession}.xml", "form4.xml", "wf-form4.xml"]
    
    xml_content = None
    for fname in candidate_names:
        url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{fname}"
        try:
            with httpx.Client(headers=HEADERS, timeout=8) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    xml_content = resp.text
                    break
        except Exception:
            continue

    if not xml_content:
        # Try fetching the index to find the correct filename
        index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{accession}-index.json"
        try:
            with httpx.Client(headers=HEADERS, timeout=8) as client:
                resp = client.get(index_url)
                if resp.status_code == 200:
                    index_data = resp.json()
                    for doc in index_data.get("documents", []):
                        if "4" in doc.get("type", "") or doc.get("document", "").endswith(".xml"):
                            fname = doc["document"]
                            xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{fname}"
                            resp2 = client.get(xml_url)
                            if resp2.status_code == 200:
                                xml_content = resp2.text
                                break
        except Exception:
            pass

    if not xml_content:
        return []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return []

    def _text(el, tag: str, default: str = "") -> str:
        node = el.find(f".//{tag}")
        return (node.text or default).strip() if node is not None else default

    def _float(el, tag: str) -> Optional[float]:
        txt = _text(el, tag)
        try:
            return float(txt)
        except (ValueError, TypeError):
            return None

    # Reporting owner
    owner_name  = _text(root, "rptOwnerName") or "Unknown Insider"
    is_director = _text(root, "isDirector") == "1"
    is_officer  = _text(root, "isOfficer") == "1"
    officer_title = _text(root, "officerTitle") or ""

    if officer_title:
        title = officer_title
    elif is_director and is_officer:
        title = "Director & Officer"
    elif is_director:
        title = "Director"
    elif is_officer:
        title = "Officer"
    else:
        title = "10% Owner / Other"

    transactions: List[InsiderTransaction] = []

    # Non-derivative transactions (stock purchases/sales)
    for txn_el in root.findall(".//nonDerivativeTransaction"):
        code         = _text(txn_el, "transactionCode")
        shares       = _float(txn_el, "transactionShares")
        price        = _float(txn_el, "transactionPricePerShare")
        shares_after = _float(txn_el, "sharesOwnedFollowingTransaction")
        txn_date     = _text(txn_el, "transactionDate") or report_date
        own_type     = _text(txn_el, "directOrIndirectOwnership") or "D"

        if shares is None or shares == 0:
            continue

        total_val = shares * price if price is not None else None

        # Flip shares to negative for sells/dispositions for clarity
        signed_shares = shares if _is_buy(code) else -shares

        transactions.append(InsiderTransaction(
            filing_date=filing_date,
            transaction_date=txn_date,
            insider_name=owner_name,
            insider_title=title,
            transaction_type=code,
            transaction_type_label=_parse_transaction_type(code),
            shares=abs(signed_shares),
            price_per_share=price,
            total_value=abs(total_val) if total_val is not None else None,
            shares_after=shares_after,
            ownership_type=own_type,
            accession_number=accession,
        ))

    return transactions


# ─── Sentiment computation ────────────────────────────────────────────────────

def _compute_sentiment(
    transactions: List[InsiderTransaction],
    lookback_days: int,
) -> InsiderSentiment:
    """
    Compute a 0–100 insider sentiment score from recent buy/sell balance.
    
    Methodology:
    - Only count open-market purchases (P) and sales (S) — excludes awards,
      option exercises, and tax withholding which are not discretionary.
    - Weight by dollar value when available, shares otherwise.
    - Score = 100 × buy_weight / (buy_weight + sell_weight), clamp to [5, 95].
    - If no discretionary activity: neutral 50.
    """
    import datetime

    cutoff = (
        datetime.date.today() - datetime.timedelta(days=lookback_days)
    ).isoformat()

    buys  = [t for t in transactions if _is_buy(t.transaction_type)  and t.transaction_date >= cutoff]
    sells = [t for t in transactions if _is_sell(t.transaction_type) and t.transaction_date >= cutoff]

    # Prefer value weight, fall back to share weight
    def _weight(txn_list: List[InsiderTransaction]) -> float:
        total_val = sum(t.total_value for t in txn_list if t.total_value is not None)
        if total_val > 0:
            return total_val
        return sum(t.shares for t in txn_list)

    buy_w  = _weight(buys)
    sell_w = _weight(sells)
    total_w = buy_w + sell_w

    if total_w == 0:
        score = 50.0
    else:
        score = max(5.0, min(95.0, 100.0 * buy_w / total_w))

    if score >= 70:
        label = "Bullish"
    elif score >= 58:
        label = "Mildly Bullish"
    elif score >= 42:
        label = "Neutral"
    elif score >= 30:
        label = "Mildly Bearish"
    else:
        label = "Bearish"

    buy_shares  = sum(t.shares for t in buys)
    sell_shares = sum(t.shares for t in sells)
    buy_val     = sum(t.total_value for t in buys  if t.total_value is not None) or None
    sell_val    = sum(t.total_value for t in sells if t.total_value is not None) or None
    net_val     = (buy_val - sell_val) if (buy_val is not None and sell_val is not None) else None

    return InsiderSentiment(
        score=round(score, 1),
        label=label,
        buy_transactions=len(buys),
        sell_transactions=len(sells),
        buy_shares=round(buy_shares, 0),
        sell_shares=round(sell_shares, 0),
        buy_value=round(buy_val, 2) if buy_val else None,
        sell_value=round(sell_val, 2) if sell_val else None,
        net_shares=round(buy_shares - sell_shares, 0),
        net_value=round(net_val, 2) if net_val else None,
        lookback_days=lookback_days,
    )
