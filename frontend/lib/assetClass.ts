/**
 * lib/assetClass.ts
 * Sprint 41 — Client-side asset class detection.
 *
 * Mirrors backend app/config.py asset_class() helper so the frontend
 * can show Crypto / Commodity / Forex / Equity badges without an API call.
 *
 * Lists must stay in sync with backend config.py CRYPTO_SYMBOLS /
 * COMMODITY_SYMBOLS / FX_SYMBOLS. Add new symbols here as they land.
 */

// ── Symbol sets (uppercase) ──────────────────────────────────────────────────

const CRYPTO_SYMBOLS = new Set([
  "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
  "ADA-USD", "DOGE-USD", "AVAX-USD", "MATIC-USD", "DOT-USD",
]);

const COMMODITY_SYMBOLS = new Set([
  "GC=F",   // Gold futures
  "CL=F",   // Crude Oil WTI
  "NG=F",   // Natural Gas
  "ZC=F",   // Corn futures
  "ZS=F",   // Soybean futures
  "SI=F",   // Silver futures
  "HG=F",   // Copper futures
]);

const FX_SYMBOLS = new Set([
  "EURUSD=X", "GBPUSD=X", "USDJPY=X",
  "AUDUSD=X", "USDCHF=X", "USDCAD=X",
  "NZDUSD=X", "EURGBP=X", "EURJPY=X",
]);

// ── Types ───────────────────────────────────────────────────────────────────

export type AssetClass = "crypto" | "commodity" | "fx" | "equity";

export interface AssetClassMeta {
  label: string;
  /** Tailwind bg colour class */
  bgClass: string;
  /** Tailwind text colour class */
  textClass: string;
  /** Tailwind ring colour class */
  ringClass: string;
  /** Emoji icon */
  icon: string;
  /** Whether to show the badge at all (equity = false by default) */
  showBadge: boolean;
}

// ── Metadata map ─────────────────────────────────────────────────────────────

export const ASSET_CLASS_META: Record<AssetClass, AssetClassMeta> = {
  crypto: {
    label:     "Crypto",
    bgClass:   "bg-amber-500/15",
    textClass: "text-amber-400",
    ringClass: "ring-amber-500/30",
    icon:      "₿",
    showBadge: true,
  },
  commodity: {
    label:     "Commodity",
    bgClass:   "bg-orange-500/15",
    textClass: "text-orange-400",
    ringClass: "ring-orange-500/30",
    icon:      "🪙",
    showBadge: true,
  },
  fx: {
    label:     "Forex",
    bgClass:   "bg-sky-500/15",
    textClass: "text-sky-400",
    ringClass: "ring-sky-500/30",
    icon:      "💱",
    showBadge: true,
  },
  equity: {
    label:     "Equity",
    bgClass:   "bg-slate-700/40",
    textClass: "text-slate-400",
    ringClass: "ring-slate-600/30",
    icon:      "📈",
    showBadge: false,
  },
};

// ── Main helper ──────────────────────────────────────────────────────────────

/**
 * Return the asset class for a given ticker symbol.
 * Matching is case-insensitive.
 */
export function getAssetClass(symbol: string): AssetClass {
  const upper = symbol.toUpperCase().trim();

  if (CRYPTO_SYMBOLS.has(upper))    return "crypto";
  if (COMMODITY_SYMBOLS.has(upper)) return "commodity";
  if (FX_SYMBOLS.has(upper))        return "fx";

  // Heuristic fallback: yfinance FX pairs all end in =X
  if (upper.endsWith("=X")) return "fx";
  // Futures: end in =F
  if (upper.endsWith("=F")) return "commodity";
  // Crypto: yfinance crypto pairs end in -USD / -USDT / -BTC / -ETH
  if (/-(USD|USDT|USDC|BTC|ETH)$/.test(upper)) return "crypto";

  return "equity";
}

/** Convenience boolean helpers */
export const isCrypto    = (s: string) => getAssetClass(s) === "crypto";
export const isCommodity = (s: string) => getAssetClass(s) === "commodity";
export const isFx        = (s: string) => getAssetClass(s) === "fx";
export const isEquity    = (s: string) => getAssetClass(s) === "equity";
