"""
app/services/llm_service.py

LLM service for Fin-Eye — Investment Manager Insight Engine.

BACKEND PRIORITY (all free, no paid APIs required):
  1. Ollama  — local, zero cost, zero rate limits, fully private.
               Requires: `ollama serve` running + a model pulled.
               Recommended models (pull one):
                 ollama pull llama3:8b          ← best quality/speed balance
                 ollama pull mistral:7b         ← good alternative
                 ollama pull phi3:mini          ← fastest, lower quality
               Config: OLLAMA_BASE_URL, OLLAMA_MODEL in backend/.env

  2. Groq    — free tier, extremely fast, but has monthly token limits.
               Use as a fallback if Ollama is unavailable (e.g. on a server
               without a GPU). Will fail gracefully when limits are hit.
               Config: GROQ_API_KEY in backend/.env
               Free tier: ~30 req/min, ~6000 req/day (as of 2026)

ADDING PAID APIS LATER:
  The _generate() method checks backends in order. To add Anthropic or OpenAI
  later, insert a new _try_anthropic() / _try_openai() call before Groq.
  No other code needs to change — the InsightInput/InsightOutput contract is stable.

ARCHITECTURE:
  - InsightInput  — structured data passed to the LLM (ML signals, macro, sentiment, price)
  - InsightOutput — structured 6-section output parsed from the LLM response
  - generate_investment_insight() — the single public function called by endpoints
  - OllamaBackend / GroqBackend   — interchangeable backends, same interface
  - get_llm_service() / close_llm_service() — singleton lifecycle helpers

SYSTEM PROMPT DESIGN (investment manager persona):
  The LLM is prompted to act as a senior quant portfolio manager.
  Output is constrained to exactly 6 labelled sections so the frontend
  can parse and render each section independently with its own icon/style.
  Temperature is set low (0.3) for consistency — we want repeatability,
  not creativity, in financial analysis.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── Output token budget ───────────────────────────────────────────────────────
# Keep this reasonable — Groq free tier counts tokens, and long responses
# from Ollama are slow on CPU. 600 tokens ≈ ~450 words = plenty for 6 sections.
MAX_TOKENS = 600

# Low temperature: we want consistent, structured output, not creative writing.
TEMPERATURE = 0.3

# ── System prompt: investment manager persona ─────────────────────────────────
SYSTEM_PROMPT = """You are a senior quantitative portfolio manager at a hedge fund.
You are direct, data-driven, and always quantify uncertainty.
You never make recommendations without conditions.
You always distinguish short-term (days) from medium-term (weeks) views.
You always include a risk note. You never promise returns.

Respond ONLY in this exact format with these exact section headers.
Do not add any text before [PRIMARY SIGNAL] or after [CAUTION].
Keep each section to 2-3 sentences maximum.

[PRIMARY SIGNAL]
One sentence summarising direction, timeframe, and confidence level.

[ENTRY]
Specific condition or price level for entry. What to wait for if signal is weak.

[TARGETS]
Short-term exit target and expected return range. What counts as a good outcome vs an exceptional one.

[RISK MANAGEMENT]
Stop-loss condition. Whether to add on a dip and at what threshold. Maximum position adjustment.

[TIMEFRAME SPLIT]
Short-term view (1-3 days). Medium-term view (1-2 weeks). Whether they agree or conflict.

[CAUTION]
One specific risk visible in the data. A historical upper bound on expected return. One-sentence disclaimer."""

# ── Structured input ──────────────────────────────────────────────────────────

@dataclass
class MLSignal:
    timeframe: str          # "1h", "4h", "1d", "1wk", "1mo"
    direction: str          # "Bullish" | "Bearish"
    confidence: float       # 50.0–100.0
    sharpe: float
    horizon_periods: int
    model_used: str


@dataclass
class InsightInput:
    """All structured data fed to the LLM before it generates the insight."""
    symbol: str
    current_price: float

    # ML signals per timeframe
    signals: list[MLSignal] = field(default_factory=list)

    # Consensus
    agreement_count: int = 0        # how many timeframes agree on direction
    total_timeframes: int = 0
    dominant_direction: str = "Mixed"

    # Technical indicators (current values)
    rsi_14: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_pb: Optional[float] = None   # Bollinger Band %B (0=lower, 1=upper)
    atr_pct: Optional[float] = None # ATR as % of price
    volume_ratio: Optional[float] = None

    # Macro
    macro_score: Optional[float] = None
    vix: Optional[float] = None
    yield_spread: Optional[float] = None
    macro_regime: Optional[str] = None

    # Sentiment
    news_sentiment_1d: Optional[float] = None
    news_sentiment_7d: Optional[float] = None
    news_sentiment_30d: Optional[float] = None

    # GAS score
    gas_score: Optional[float] = None

    # Probabilistic price targets (pre-computed from ATR + model return)
    expected_price: Optional[float] = None
    upside_target: Optional[float] = None
    downside_stop: Optional[float] = None
    expected_return_pct: Optional[float] = None
    atr_absolute: Optional[float] = None


@dataclass
class InsightOutput:
    """Parsed 6-section output from the LLM."""
    primary_signal: str = ""
    entry: str = ""
    targets: str = ""
    risk_management: str = ""
    timeframe_split: str = ""
    caution: str = ""
    raw_response: str = ""
    backend_used: str = ""          # "ollama" | "groq" | "fallback"
    model_used: str = ""
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """True if at least the primary signal and one other section were parsed."""
        return bool(self.primary_signal and (self.entry or self.targets))

    def to_dict(self) -> dict:
        return {
            "primary_signal":   self.primary_signal,
            "entry":            self.entry,
            "targets":          self.targets,
            "risk_management":  self.risk_management,
            "timeframe_split":  self.timeframe_split,
            "caution":          self.caution,
            "backend_used":     self.backend_used,
            "model_used":       self.model_used,
            "error":            self.error,
        }


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_user_prompt(inp: InsightInput) -> str:
    """
    Converts InsightInput into a dense but readable prompt.
    Sections are clearly labelled so the LLM can follow the structure.
    """
    lines: list[str] = [f"SYMBOL: {inp.symbol}  |  PRICE: ${inp.current_price:.2f}"]

    # ML signals
    if inp.signals:
        lines.append("\nML MODEL SIGNALS:")
        for s in inp.signals:
            horizon_label = {
                "1h": "~3 hours", "4h": "~12 hours", "1d": "~3 days",
                "1wk": "~2 weeks", "1mo": "~1 month",
            }.get(s.timeframe, f"{s.horizon_periods} periods")
            lines.append(
                f"  {s.timeframe:>4}  {s.direction:<8}  conf={s.confidence:.0f}%  "
                f"Sharpe={s.sharpe:.2f}  horizon={horizon_label}  model={s.model_used}"
            )

        agree_pct = (inp.agreement_count / inp.total_timeframes * 100) if inp.total_timeframes else 0
        lines.append(
            f"  Consensus: {inp.dominant_direction}  "
            f"({inp.agreement_count}/{inp.total_timeframes} timeframes agree, {agree_pct:.0f}%)"
        )

    # Technical indicators
    tech_parts = []
    if inp.rsi_14 is not None:
        rsi_note = "oversold" if inp.rsi_14 < 30 else "overbought" if inp.rsi_14 > 70 else "neutral"
        tech_parts.append(f"RSI={inp.rsi_14:.1f} ({rsi_note})")
    if inp.macd_hist is not None:
        tech_parts.append(f"MACD_hist={inp.macd_hist:+.4f} ({'bullish' if inp.macd_hist > 0 else 'bearish'})")
    if inp.bb_pb is not None:
        bb_note = "near upper band" if inp.bb_pb > 0.8 else "near lower band" if inp.bb_pb < 0.2 else "mid-band"
        tech_parts.append(f"BB%B={inp.bb_pb:.2f} ({bb_note})")
    if inp.atr_pct is not None:
        tech_parts.append(f"ATR={inp.atr_pct*100:.2f}% of price")
    if inp.volume_ratio is not None:
        vol_note = "above avg" if inp.volume_ratio > 1.2 else "below avg" if inp.volume_ratio < 0.8 else "avg"
        tech_parts.append(f"Volume={inp.volume_ratio:.2f}x ({vol_note})")
    if tech_parts:
        lines.append("\nTECHNICAL INDICATORS: " + "  |  ".join(tech_parts))

    # Macro
    macro_parts = []
    if inp.macro_score is not None:
        macro_parts.append(f"Macro score={inp.macro_score:.0f}/100")
    if inp.vix is not None:
        vix_note = "low fear" if inp.vix < 15 else "high fear" if inp.vix > 25 else "moderate"
        macro_parts.append(f"VIX={inp.vix:.1f} ({vix_note})")
    if inp.yield_spread is not None:
        spread_note = "inverted (recession signal)" if inp.yield_spread < 0 else "normal"
        macro_parts.append(f"10Y-2Y spread={inp.yield_spread:+.2f}% ({spread_note})")
    if inp.macro_regime:
        macro_parts.append(f"Regime={inp.macro_regime}")
    if macro_parts:
        lines.append("MACRO: " + "  |  ".join(macro_parts))

    # Sentiment
    sent_parts = []
    if inp.news_sentiment_1d is not None:
        sent_parts.append(f"1d={inp.news_sentiment_1d:+.2f}")
    if inp.news_sentiment_7d is not None:
        sent_parts.append(f"7d={inp.news_sentiment_7d:+.2f}")
    if inp.news_sentiment_30d is not None:
        sent_parts.append(f"30d={inp.news_sentiment_30d:+.2f}")
    if sent_parts:
        lines.append("NEWS SENTIMENT (range -1 to +1): " + "  ".join(sent_parts))

    if inp.gas_score is not None:
        lines.append(f"GAS COMPOSITE SCORE: {inp.gas_score:.0f}/100")

    # Price targets
    if inp.expected_price is not None:
        lines.append(
            f"\nPROBABILISTIC PRICE TARGETS (pre-computed, use these in your response):"
            f"\n  Expected price in ~3 days: ${inp.expected_price:.2f}"
            + (f"  (+{inp.expected_return_pct:.1f}%)" if inp.expected_return_pct else "")
        )
        if inp.upside_target:
            lines.append(f"  Upside target (expected + 1 ATR): ${inp.upside_target:.2f}")
        if inp.downside_stop:
            lines.append(f"  Stop-loss level (current - 1 ATR): ${inp.downside_stop:.2f}")
        if inp.atr_absolute:
            lines.append(f"  ATR (absolute): ${inp.atr_absolute:.2f}")

    lines.append(
        "\nGenerate the investment manager analysis now. "
        "Use the exact 6-section format from your instructions. "
        "Reference the specific numbers above. Be concise and direct."
    )

    return "\n".join(lines)


# ── Response parser ───────────────────────────────────────────────────────────

_SECTION_PATTERN = re.compile(
    r"\[(?P<header>PRIMARY SIGNAL|ENTRY|TARGETS|RISK MANAGEMENT|TIMEFRAME SPLIT|CAUTION)\]"
    r"(?P<body>.*?)(?=\[(?:PRIMARY SIGNAL|ENTRY|TARGETS|RISK MANAGEMENT|TIMEFRAME SPLIT|CAUTION)\]|$)",
    re.DOTALL | re.IGNORECASE,
)

_HEADER_MAP = {
    "PRIMARY SIGNAL":  "primary_signal",
    "ENTRY":           "entry",
    "TARGETS":         "targets",
    "RISK MANAGEMENT": "risk_management",
    "TIMEFRAME SPLIT": "timeframe_split",
    "CAUTION":         "caution",
}


def parse_llm_response(raw: str, backend: str, model: str) -> InsightOutput:
    """
    Parse the 6-section LLM response into an InsightOutput.
    Tolerates minor deviations (extra whitespace, lowercase headers).
    """
    out = InsightOutput(raw_response=raw, backend_used=backend, model_used=model)

    for match in _SECTION_PATTERN.finditer(raw):
        header = match.group("header").upper().strip()
        body   = match.group("body").strip()
        attr   = _HEADER_MAP.get(header)
        if attr:
            setattr(out, attr, body)

    if not out.is_valid:
        # Fallback: if parsing failed, put everything in primary_signal
        # so the frontend always has something to show.
        out.primary_signal = raw.strip()[:500]
        logger.warning("LLM response did not match expected 6-section format. Raw:\n%s", raw[:200])

    return out


# ── Fallback static response ──────────────────────────────────────────────────

def _static_fallback(inp: InsightInput) -> InsightOutput:
    """
    Returned when all LLM backends are unavailable.
    Uses the pre-computed price targets to generate a minimal useful response
    without any LLM call.
    """
    direction = inp.dominant_direction if inp.dominant_direction != "Mixed" else "uncertain"
    agreement = f"{inp.agreement_count}/{inp.total_timeframes}" if inp.total_timeframes else "?"

    primary = (
        f"{inp.symbol} shows a {direction} lean with {agreement} timeframes in agreement. "
        f"LLM insight service is currently unavailable — analysis is based on model signals only."
    )
    entry = (
        f"Wait for Ollama to be available for full analysis. "
        f"Ensure `ollama serve` is running and a model is pulled (e.g. `ollama pull llama3:8b`)."
    )
    targets = ""
    if inp.expected_price and inp.expected_return_pct is not None:
        targets = (
            f"Pre-computed target: ${inp.expected_price:.2f} "
            f"({inp.expected_return_pct:+.1f}% expected over ~3 days). "
        )
    if inp.upside_target:
        targets += f"Upside: ${inp.upside_target:.2f}. "
    if inp.downside_stop:
        targets += f"Stop: ${inp.downside_stop:.2f}."

    return InsightOutput(
        primary_signal=primary,
        entry=entry,
        targets=targets or "Price targets unavailable — insufficient model data.",
        risk_management=f"Use ATR-based stops. Stop loss: ${inp.downside_stop:.2f}." if inp.downside_stop else "Apply standard risk management.",
        timeframe_split="LLM unavailable — check Ollama service.",
        caution="This is a static fallback — no LLM analysis was performed. This is not investment advice.",
        backend_used="fallback",
        model_used="none",
        error="All LLM backends unavailable.",
    )


# ── Ollama backend ────────────────────────────────────────────────────────────

class OllamaBackend:
    """
    Async client for a local Ollama instance.

    The /api/chat endpoint (messages format) is preferred over /api/generate
    because it handles the system prompt more reliably across model families.

    Lazy client creation — startup never blocks on Ollama being available.
    """

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model    = model
        self._client: Optional[httpx.AsyncClient] = None
        self._lock    = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            async with self._lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        base_url=self.base_url,
                        timeout=httpx.Timeout(connect=5.0, read=180.0, write=10.0, pool=5.0),
                    )
        return self._client

    async def generate(self, system: str, user: str) -> Optional[str]:
        """
        Call Ollama /api/chat with system + user messages.
        Returns the assistant content string, or None on failure.
        """
        payload = {
            "model":  self.model,
            "stream": False,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS,
            },
            "messages": [
                {"role": "system",    "content": system},
                {"role": "user",      "content": user},
            ],
        }
        try:
            client   = await self._get_client()
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            # /api/chat returns: { "message": { "role": "assistant", "content": "..." } }
            return data.get("message", {}).get("content", "").strip() or None
        except httpx.ConnectError:
            logger.warning(
                "Ollama not reachable at %s. Is `ollama serve` running? "
                "Pull a model first: `ollama pull %s`",
                self.base_url, self.model,
            )
            return None
        except httpx.TimeoutException:
            logger.warning("Ollama request timed out (model may be loading — retry in a moment).")
            return None
        except Exception as exc:
            logger.error("Ollama backend error: %s", exc)
            return None

    async def generate_stream(self, system: str, user: str):
        """
        Stream tokens from Ollama /api/chat using server-sent events.
        Yields raw text chunks as they arrive from the model.
        Falls back to None generator if Ollama is unavailable.
        """
        payload = {
            "model":  self.model,
            "stream": True,
            "options": {
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS,
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }
        try:
            client = await self._get_client()
            import json as _json
            async with client.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = _json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except Exception:
                        continue
        except httpx.ConnectError:
            logger.warning("Ollama not reachable for streaming — is `ollama serve` running?")
            return
        except Exception as exc:
            logger.error("Ollama stream error: %s", exc)
            return

    async def is_available(self) -> bool:
        """Quick health check — does Ollama respond at all?"""
        try:
            client   = await self._get_client()
            response = await client.get("/api/tags", timeout=3.0)
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# ── Groq backend (free tier fallback) ────────────────────────────────────────

class GroqBackend:
    """
    Free Groq API — extremely fast inference, but has monthly token limits.
    Used as fallback when Ollama is unavailable (e.g. on a remote server).

    Free tier limits (as of 2026):
      - 30 requests / minute
      - 6,000 requests / day
      - 500,000 tokens / day per model

    When limits are hit, Groq returns HTTP 429. This backend catches that
    and returns None so the service falls back to the static response.

    Recommended models (fast + free):
      - llama-3.1-8b-instant   ← fastest
      - llama-3.3-70b-versatile ← best quality on free tier
      - mixtral-8x7b-32768     ← good balance
    """

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.1-8b-instant"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model   = model
        self._client: Optional[httpx.AsyncClient] = None
        self._lock   = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            async with self._lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type":  "application/json",
                        },
                        timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
                    )
        return self._client

    async def generate(self, system: str, user: str) -> Optional[str]:
        """
        Call Groq OpenAI-compatible chat completion endpoint.
        Returns assistant content string, or None on failure / rate limit.
        """
        if not self.api_key:
            return None
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            "temperature": TEMPERATURE,
            "max_tokens":  MAX_TOKENS,
        }
        try:
            client   = await self._get_client()
            response = await client.post(self.GROQ_API_URL, json=payload)
            if response.status_code == 429:
                logger.warning(
                    "Groq rate limit hit. Daily or per-minute token budget exhausted. "
                    "Falling back to static response. Consider starting Ollama locally."
                )
                return None
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip() or None
        except httpx.ConnectError:
            logger.warning("Could not connect to Groq API.")
            return None
        except Exception as exc:
            logger.error("Groq backend error: %s", exc)
            return None

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# ── LLM service (orchestrator) ────────────────────────────────────────────────

class LLMService:
    """
    Orchestrates multiple LLM backends with automatic fallback.

    Priority order:
      1. Ollama (local, free, no limits)   ← always tried first
      2. Groq   (free tier, rate-limited)  ← only if GROQ_API_KEY is set
      3. Static fallback                   ← always available, no LLM call

    The old get_explanation() method is preserved for backwards compatibility
    with any callers that haven't been updated yet.
    """

    def __init__(self) -> None:
        self._ollama = OllamaBackend(
            base_url=getattr(settings, "ollama_base_url", "http://localhost:11434"),
            model=getattr(settings, "ollama_model", "llama3:8b"),
        )
        groq_key = getattr(settings, "groq_api_key", "")
        self._groq = GroqBackend(api_key=groq_key) if groq_key else None

    # ── Core: structured investment insight ───────────────────────────────────

    async def generate_investment_insight(self, inp: InsightInput) -> InsightOutput:
        """
        Main public method. Builds the prompt, tries each backend in order,
        parses the structured response, and returns an InsightOutput.

        Always returns something — falls back to static if all LLMs fail.
        """
        system_prompt = SYSTEM_PROMPT
        user_prompt   = build_user_prompt(inp)

        # 1. Try Ollama first
        raw = await self._ollama.generate(system_prompt, user_prompt)
        if raw:
            logger.info("LLM insight generated via Ollama (%s)", self._ollama.model)
            return parse_llm_response(raw, backend="ollama", model=self._ollama.model)

        # 2. Try Groq if available
        if self._groq and self._groq.api_key:
            raw = await self._groq.generate(system_prompt, user_prompt)
            if raw:
                logger.info("LLM insight generated via Groq (%s)", self._groq.model)
                return parse_llm_response(raw, backend="groq", model=self._groq.model)
            logger.warning("Groq also unavailable — using static fallback.")

        # 3. Static fallback
        logger.warning("All LLM backends unavailable for %s — returning static fallback.", inp.symbol)
        return _static_fallback(inp)

    # ── Price target computation (called before building InsightInput) ─────────

    @staticmethod
    def compute_price_targets(
        current_price: float,
        expected_return: float,     # model's expected return (e.g. 0.018 = +1.8%)
        atr_absolute: float,        # ATR in price units (e.g. $3.20)
        confidence: float,          # model confidence 0–1
    ) -> dict:
        """
        Pre-compute probabilistic price targets from ATR and model expected return.
        These are fed into InsightInput and referenced explicitly in the LLM prompt.

        All values are probabilistic estimates, not guarantees.
        """
        mid_target   = current_price * (1.0 + expected_return)
        upper_target = mid_target + atr_absolute
        lower_stop   = current_price - atr_absolute

        return {
            "expected_price":      round(mid_target, 2),
            "upside_target":       round(upper_target, 2),
            "downside_stop":       round(max(lower_stop, 0.01), 2),
            "expected_return_pct": round(expected_return * 100, 2),
            "atr_absolute":        round(atr_absolute, 2),
            "confidence":          round(confidence * 100, 1),
        }

    # ── Backwards compatibility: old get_explanation() interface ──────────────

    async def get_explanation(
        self,
        symbol: str,
        tech_score: float,
        sent_score: Optional[float],
        macro_score: float,
        gas_score: float,
        ml_output: Optional[str] = None,
    ) -> Optional[str]:
        """
        Preserved for backwards compatibility with existing callers.
        Wraps the old flat interface into an InsightInput and returns raw text.

        New code should call generate_investment_insight() directly.
        """
        inp = InsightInput(
            symbol=symbol,
            current_price=0.0,
            gas_score=gas_score,
            macro_score=macro_score,
            news_sentiment_7d=sent_score,
            dominant_direction="Bullish" if tech_score >= 60 else "Bearish" if tech_score <= 40 else "Mixed",
        )
        out = await self.generate_investment_insight(inp)

        if out.error and not out.is_valid:
            return None

        # Stitch sections back into a plain string for old callers
        parts = []
        if out.primary_signal: parts.append(out.primary_signal)
        if out.entry:          parts.append(out.entry)
        if out.caution:        parts.append(out.caution)
        return " ".join(parts) if parts else None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def close(self) -> None:
        await self._ollama.close()
        if self._groq:
            await self._groq.close()


# ── Module-level singleton ────────────────────────────────────────────────────

_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Return (or create) the module-level singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


async def close_llm_service() -> None:
    """Cleanly shut down — call from FastAPI lifespan shutdown."""
    global _llm_service
    if _llm_service is not None:
        await _llm_service.close()
        _llm_service = None


# ── Backwards-compatibility aliases ──────────────────────────────────────────
# Old code that calls get_ollama_service() / close_ollama_service() will still
# work — they just return the new unified service.

def get_ollama_service() -> LLMService:
    """Deprecated alias — use get_llm_service() in new code."""
    return get_llm_service()


async def close_ollama_service() -> None:
    """Deprecated alias — use close_llm_service() in new code."""
    await close_llm_service()
