/**
 * lib/signalUtils.ts — Sprint 33
 *
 * Shared signal interpretation utilities used across TimeframeGrid,
 * LLMInsightCard, and any other component that renders direction / confidence.
 *
 * Previously these were duplicated as inline helpers inside TimeframeGrid.tsx.
 * Extracting here ensures both components stay in sync on labels and colours.
 */

// ── Confidence interpretation ─────────────────────────────────────────────────

export interface ConfidenceInfo {
  /** Human-readable label shown in the UI */
  label: "Strong signal" | "Moderate signal" | "Weak signal" | "Uncertain" | "No clear signal";
  /** Plain-English description of what this confidence level means */
  description: string;
  /** Tailwind text colour class */
  color: string;
}

/**
 * Map a raw confidence percentage (50–100) to a labelled, colour-coded object.
 *
 * Thresholds:
 *   ≥ 75% → Strong signal    (emerald)
 *   65–74% → Moderate signal (sky)
 *   55–64% → Weak signal     (amber)
 *   50–54% → Uncertain       (amber / muted)
 *   < 50%  → No clear signal (slate)
 */
export function interpretConfidence(conf: number): ConfidenceInfo {
  if (conf >= 75) return {
    label: "Strong signal",
    description: "The model is strongly leaning in this direction. All key features are aligned.",
    color: "text-emerald-400",
  };
  if (conf >= 65) return {
    label: "Moderate signal",
    description: "Most features agree on this direction. A reliable signal but not exceptional.",
    color: "text-sky-400",
  };
  if (conf >= 55) return {
    label: "Weak signal",
    description: "Slight majority of features point this way. Treat with caution — confirm with other layers.",
    color: "text-amber-400",
  };
  if (conf >= 50) return {
    label: "Uncertain",
    description: "Features are close to split. The model has a marginal lean but this is near-random.",
    color: "text-amber-500",
  };
  return {
    label: "No clear signal",
    description: "Features are mixed or conflicting. Wait for a clearer setup before acting.",
    color: "text-slate-400",
  };
}

// ── Direction configuration ───────────────────────────────────────────────────

export interface DirectionConfig {
  /** Lucide icon name (consumers import the icon themselves) */
  iconName: "TrendingUp" | "TrendingDown" | "Minus";
  /** Tile background + border classes */
  tile: string;
  /** Primary text colour class */
  text: string;
  /** Badge background / border / text classes */
  badge: string;
  /** Progress bar colour class */
  bar: string;
  /** Panel background / border classes */
  panelBg: string;
  /** Short direction label */
  label: "Bullish" | "Bearish" | "Neutral";
  /** Plain-English one-sentence description for the detail panel */
  plain: string;
}

/**
 * Return colour, style, and label configuration for a direction string.
 * Accepts "Bullish", "Bearish", or anything else (treated as Neutral).
 */
export function directionConfig(direction: string): DirectionConfig {
  if (direction === "Bullish") return {
    iconName: "TrendingUp",
    tile:    "bg-emerald-950/40 border-emerald-800/50 hover:border-emerald-600/60",
    text:    "text-emerald-400",
    badge:   "bg-emerald-900/50 text-emerald-300 border-emerald-700/40",
    bar:     "bg-emerald-500",
    panelBg: "bg-emerald-950/20 border-emerald-800/40",
    label:   "Bullish",
    plain:   "The model predicts this asset will move UP over the forecast horizon.",
  };
  if (direction === "Bearish") return {
    iconName: "TrendingDown",
    tile:    "bg-rose-950/40 border-rose-800/50 hover:border-rose-600/60",
    text:    "text-rose-400",
    badge:   "bg-rose-900/50 text-rose-300 border-rose-700/40",
    bar:     "bg-rose-500",
    panelBg: "bg-rose-950/20 border-rose-800/40",
    label:   "Bearish",
    plain:   "The model predicts this asset will move DOWN over the forecast horizon.",
  };
  return {
    iconName: "Minus",
    tile:    "bg-amber-950/30 border-amber-800/40 hover:border-amber-600/50",
    text:    "text-amber-400",
    badge:   "bg-amber-900/50 text-amber-300 border-amber-700/40",
    bar:     "bg-amber-500",
    panelBg: "bg-amber-950/20 border-amber-800/40",
    label:   "Neutral",
    plain:   "The model sees roughly equal probability of up and down movement.",
  };
}

// ── Multi-timeframe agreement summary ────────────────────────────────────────

export interface AgreementSummary {
  bullish: number;
  bearish: number;
  neutral: number;
  total: number;
  dominant: "Bullish" | "Bearish" | "Mixed";
  dominantCount: number;
  agreementPct: number;
  avgConfidence: number;
  /** Short banner message, e.g. "4/5 timeframes agree: Bullish" */
  message: string;
  /** Supporting sub-text for the banner */
  subText: string;
  /** Banner colour scheme */
  scheme: "emerald-strong" | "emerald-mild" | "rose-strong" | "rose-mild" | "amber";
}

export function buildAgreementSummary(
  signals: { direction: string; confidence: number }[],
): AgreementSummary {
  const bullish = signals.filter((s) => s.direction === "Bullish").length;
  const bearish = signals.filter((s) => s.direction === "Bearish").length;
  const neutral = signals.length - bullish - bearish;
  const total   = signals.length;

  const dominantCount = Math.max(bullish, bearish);
  const dominant: "Bullish" | "Bearish" | "Mixed" =
    bullish > bearish ? "Bullish" : bearish > bullish ? "Bearish" : "Mixed";
  const agreementPct = total > 0 ? Math.round((dominantCount / total) * 100) : 0;
  const avgConfidence =
    total > 0 ? signals.reduce((s, x) => s + x.confidence, 0) / total : 0;

  let message = "";
  let subText  = "";
  let scheme: AgreementSummary["scheme"] = "amber";

  if (dominant === "Mixed") {
    message = "Timeframes are split — no clear direction";
    subText  = "Timeframes conflict. Wait for confirmation before acting.";
    scheme   = "amber";
  } else if (agreementPct >= 80) {
    message = `${dominantCount}/${total} timeframes agree: ${dominant}`;
    subText  = "Strong cross-timeframe consensus — higher-conviction signal.";
    scheme   = dominant === "Bullish" ? "emerald-strong" : "rose-strong";
  } else if (agreementPct >= 60) {
    message = `${dominantCount}/${total} timeframes lean ${dominant}`;
    subText  = "Moderate consensus — use with normal risk controls.";
    scheme   = dominant === "Bullish" ? "emerald-mild" : "rose-mild";
  } else {
    message = `${dominantCount}/${total} timeframes lean ${dominant} — low conviction`;
    subText  = "Timeframes conflict. Wait for confirmation before acting.";
    scheme   = "amber";
  }

  return { bullish, bearish, neutral, total, dominant, dominantCount, agreementPct, avgConfidence, message, subText, scheme };
}
