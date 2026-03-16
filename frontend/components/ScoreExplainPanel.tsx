"use client";

import React, { useEffect, useRef } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

export type ExplainTarget = "gas" | "technical" | "sentiment" | "macro";

export interface SubComponent {
  label: string;
  value: number;     // 0–100 normalised
  rawLabel: string;  // e.g. "+0.42", "VIX 18.2", "7 of 9 bullish"
  color: "emerald" | "teal" | "amber" | "orange" | "rose" | "sky" | "slate";
  description: string;
}

export interface ExplainPayload {
  target: ExplainTarget;
  title: string;
  score: number;
  scoreLabel: string;
  summary: string;
  weight?: string;   // e.g. "40% of GAS"
  subComponents: SubComponent[];
  methodology: string;
}

interface ScoreExplainPanelProps {
  payload: ExplainPayload | null;
  onClose: () => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const COLOR_MAP: Record<SubComponent["color"], { bar: string; text: string; bg: string }> = {
  emerald: { bar: "bg-emerald-500", text: "text-emerald-400", bg: "bg-emerald-950/30" },
  teal:    { bar: "bg-teal-500",    text: "text-teal-400",    bg: "bg-teal-950/30"    },
  amber:   { bar: "bg-amber-500",   text: "text-amber-400",   bg: "bg-amber-950/30"   },
  orange:  { bar: "bg-orange-500",  text: "text-orange-400",  bg: "bg-orange-950/30"  },
  rose:    { bar: "bg-rose-500",    text: "text-rose-400",    bg: "bg-rose-950/30"    },
  sky:     { bar: "bg-sky-500",     text: "text-sky-400",     bg: "bg-sky-950/30"     },
  slate:   { bar: "bg-slate-500",   text: "text-slate-400",   bg: "bg-slate-800/30"   },
};

function scoreToColor(score: number): SubComponent["color"] {
  if (score >= 65) return "emerald";
  if (score >= 55) return "teal";
  if (score >= 45) return "amber";
  if (score >= 35) return "orange";
  return "rose";
}

// ── Score interpretation ──────────────────────────────────────────────────────
// Describes market CONDITIONS — never recommends actions.
// Framing is always "the signal environment is X", never "you should do Y".

interface ScoreInterpretation {
  label: string;
  labelColor: string;
  labelBg: string;
  guidanceText: string;
  guidanceColor: string;
}

function interpretScore(
  score: number,
  target: ExplainTarget,
): ScoreInterpretation {
  // GAS-specific labels
  if (target === "gas") {
    if (score >= 80) return {
      label: "Strong Tailwind",
      labelColor: "text-emerald-400",
      labelBg: "bg-emerald-950/40 border-emerald-700/50",
      guidanceText: "All three layers — technical, sentiment, and macro — are broadly aligned in a bullish direction. Historically, this combination has been associated with continued near-term momentum. Conditions can shift — always verify with your own research.",
      guidanceColor: "text-emerald-300",
    };
    if (score >= 60) return {
      label: "Mild Support",
      labelColor: "text-sky-400",
      labelBg: "bg-sky-950/40 border-sky-700/50",
      guidanceText: "Most signals lean positive, though some disagreement exists between layers. The data environment is moderately supportive. Mixed signals across components warrant some caution.",
      guidanceColor: "text-sky-300",
    };
    if (score >= 40) return {
      label: "Mixed Signals",
      labelColor: "text-amber-400",
      labelBg: "bg-amber-950/40 border-amber-700/50",
      guidanceText: "Technical, sentiment, and macro signals are not in agreement. The picture is unclear. Historically, mixed-signal environments have been associated with elevated uncertainty and choppy price action.",
      guidanceColor: "text-amber-300",
    };
    if (score >= 20) return {
      label: "Headwind",
      labelColor: "text-orange-400",
      labelBg: "bg-orange-950/40 border-orange-700/50",
      guidanceText: "Signals lean bearish across multiple layers. The data environment is not broadly supportive at this time. Historically, sub-40 GAS readings have coincided with continued downward pressure rather than recoveries.",
      guidanceColor: "text-orange-300",
    };
    return {
      label: "High Instability",
      labelColor: "text-rose-400",
      labelBg: "bg-rose-950/40 border-rose-700/50",
      guidanceText: "Strong bearish alignment across all layers simultaneously. This combination is historically associated with elevated volatility and unfavourable conditions. Patience is typically rewarded over activity in low-GAS environments like this.",
      guidanceColor: "text-rose-300",
    };
  }

  // Technical-specific labels
  if (target === "technical") {
    if (score >= 80) return {
      label: "Strong Bullish Momentum", labelColor: "text-emerald-400", labelBg: "bg-emerald-950/40 border-emerald-700/50",
      guidanceText: "Most timeframes agree — models see upward pressure across the board. Cross-timeframe agreement is the strongest form of technical signal.",
      guidanceColor: "text-emerald-300",
    };
    if (score >= 60) return {
      label: "Bullish Lean", labelColor: "text-sky-400", labelBg: "bg-sky-950/40 border-sky-700/50",
      guidanceText: "Majority of timeframes lean bullish with some disagreement. Signals are positive but not exceptional — shorter timeframes may diverge from the broader trend.",
      guidanceColor: "text-sky-300",
    };
    if (score >= 40) return {
      label: "No Clear Direction", labelColor: "text-amber-400", labelBg: "bg-amber-950/40 border-amber-700/50",
      guidanceText: "Timeframes are split with no dominant direction. Models see no strong edge in either direction. Historically, low-consensus periods are associated with range-bound or choppy price action.",
      guidanceColor: "text-amber-300",
    };
    if (score >= 20) return {
      label: "Bearish Lean", labelColor: "text-orange-400", labelBg: "bg-orange-950/40 border-orange-700/50",
      guidanceText: "Majority of timeframes lean bearish. Signals are negative but not at an extreme — some timeframes may still offer divergence.",
      guidanceColor: "text-orange-300",
    };
    return {
      label: "Strong Bearish Momentum", labelColor: "text-rose-400", labelBg: "bg-rose-950/40 border-rose-700/50",
      guidanceText: "Most timeframes agree — models see downward pressure across the board. High cross-timeframe agreement on the bearish side is historically a strong signal.",
      guidanceColor: "text-rose-300",
    };
  }

  // Sentiment-specific labels
  if (target === "sentiment") {
    if (score >= 70) return {
      label: "Very Positive Coverage", labelColor: "text-emerald-400", labelBg: "bg-emerald-950/40 border-emerald-700/50",
      guidanceText: "News coverage over the past 30 days has been predominantly positive. Strong sentiment has historically preceded or accompanied upward momentum — though news narratives can reverse sharply.",
      guidanceColor: "text-emerald-300",
    };
    if (score >= 55) return {
      label: "Mildly Positive", labelColor: "text-sky-400", labelBg: "bg-sky-950/40 border-sky-700/50",
      guidanceText: "More positive than negative coverage over the past 30 days. Sentiment is constructive but not extreme.",
      guidanceColor: "text-sky-300",
    };
    if (score >= 45) return {
      label: "Neutral Coverage", labelColor: "text-amber-400", labelBg: "bg-amber-950/40 border-amber-700/50",
      guidanceText: "Coverage is broadly balanced with no strong directional lean. Neutral sentiment provides no additional tailwind or headwind from the news cycle.",
      guidanceColor: "text-amber-300",
    };
    if (score >= 30) return {
      label: "Mildly Negative", labelColor: "text-orange-400", labelBg: "bg-orange-950/40 border-orange-700/50",
      guidanceText: "News coverage leans negative over the past 30 days. Negative sentiment can persist and reinforce price weakness, though it can also represent a contrarian signal near extremes.",
      guidanceColor: "text-orange-300",
    };
    return {
      label: "Strongly Negative", labelColor: "text-rose-400", labelBg: "bg-rose-950/40 border-rose-700/50",
      guidanceText: "News coverage has been predominantly negative. Extreme negative sentiment historically marks both continued downtrends and eventual contrarian reversals — context matters.",
      guidanceColor: "text-rose-300",
    };
  }

  // Macro / Volatility
  if (score >= 70) return {
    label: "Supportive", labelColor: "text-emerald-400", labelBg: "bg-emerald-950/40 border-emerald-700/50",
    guidanceText: "Macro environment is broadly favourable for risk assets. Low volatility, accommodative conditions, and stable indicators historically support equity momentum.",
    guidanceColor: "text-emerald-300",
  };
  if (score >= 40) return {
    label: "Neutral", labelColor: "text-amber-400", labelBg: "bg-amber-950/40 border-amber-700/50",
    guidanceText: "Mixed macro signals — neither clearly supportive nor restrictive. The macro environment adds neither tailwind nor headwind to risk assets at this time.",
    guidanceColor: "text-amber-300",
  };
  return {
    label: "Stressed", labelColor: "text-rose-400", labelBg: "bg-rose-950/40 border-rose-700/50",
    guidanceText: "Macro indicators are unfavourable. Historically, stressed macro environments have added headwinds to equity risk-taking. Elevated caution is typically warranted.",
    guidanceColor: "text-rose-300",
  };
}

function ScoreBar({ value, color }: { value: number; color: SubComponent["color"] }) {
  const { bar } = COLOR_MAP[color];
  const clamped = Math.min(100, Math.max(0, value));
  return (
    <div className="relative h-2 rounded-full bg-slate-800 overflow-hidden">
      <div
        className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${bar}`}
        style={{ width: `${clamped}%` }}
      />
      {/* Midline marker */}
      <div className="absolute inset-y-0 left-1/2 w-px bg-slate-600/60" />
    </div>
  );
}

// ─── Main Panel ───────────────────────────────────────────────────────────────

export default function ScoreExplainPanel({ payload, onClose }: ScoreExplainPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  // Prevent scroll bleed on body while open
  useEffect(() => {
    if (payload) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [payload]);

  const isOpen = payload !== null;

  return (
    <>
      {/* Backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity duration-300 ${
          isOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Slide-over panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={payload?.title ?? "Score Explanation"}
        className={`fixed top-0 right-0 z-50 h-full w-full sm:max-w-lg lg:max-w-2xl bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {payload && (
          <>
            {/* Header */}
            <div className="flex items-start justify-between p-6 lg:p-8 border-b border-slate-800">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1">
                  Score Breakdown
                </p>
                <h2 className="text-2xl lg:text-3xl font-black text-slate-100">{payload.title}</h2>
                {payload.weight && (
                  <p className="text-sm text-slate-500 mt-1">{payload.weight}</p>
                )}
              </div>
              <button
                onClick={onClose}
                aria-label="Close explanation panel"
                className="ml-4 mt-1 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Scrollable body */}
            <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-6">

              {/* Headline score */}
              {(() => {
                const interp = interpretScore(payload.score, payload.target);
                return (
                  <div className={`rounded-2xl p-6 lg:p-7 border ${COLOR_MAP[scoreToColor(payload.score)].bg} border-slate-800`}>
                    {/* Score number + label badge */}
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-baseline gap-3">
                        <span className={`text-6xl lg:text-7xl font-black tracking-tighter ${COLOR_MAP[scoreToColor(payload.score)].text}`}>
                          {payload.score.toFixed(0)}
                        </span>
                        <span className="text-xl font-bold text-slate-400">{payload.scoreLabel}</span>
                      </div>
                      {/* Condition label badge */}
                      <span className={`flex-shrink-0 mt-2 inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold ${interp.labelBg} ${interp.labelColor}`}>
                        {interp.label}
                      </span>
                    </div>

                    <ScoreBar value={payload.score} color={scoreToColor(payload.score)} />

                    {/* Technical description */}
                    <p className="mt-4 text-sm lg:text-base text-slate-300 leading-relaxed">{payload.summary}</p>

                    {/* Condition guidance — environment description */}
                    <div className={`mt-4 rounded-xl border px-4 py-3 ${interp.labelBg}`}>
                      <p className={`text-xs font-semibold uppercase tracking-wider mb-1.5 ${interp.labelColor}`}>
                        Signal Environment
                      </p>
                      <p className={`text-sm leading-relaxed ${interp.guidanceColor}`}>
                        {interp.guidanceText}
                      </p>
                      <p className="mt-2 text-[10px] text-slate-600 italic">
                        This describes market conditions based on data signals — not personalised investment advice.
                      </p>
                    </div>
                  </div>
                );
              })()}

              {/* Sub-component breakdown */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
                  Signal Breakdown
                </h3>
                <div className="space-y-4">
                  {payload.subComponents.map((sub) => {
                    const c = COLOR_MAP[sub.color];
                    return (
                      <div key={sub.label} className="rounded-xl bg-slate-900/60 border border-slate-800 p-5">
                        <div className="flex justify-between items-baseline mb-3">
                          <span className="text-base font-semibold text-slate-200">{sub.label}</span>
                          <span className={`text-sm font-mono font-bold ${c.text}`}>{sub.rawLabel}</span>
                        </div>
                        <ScoreBar value={sub.value} color={sub.color} />
                        <div className="flex justify-between mt-1.5 text-xs text-slate-600">
                          <span>Bearish</span>
                          <span className={`font-semibold ${c.text}`}>{sub.value.toFixed(0)} / 100</span>
                          <span>Bullish</span>
                        </div>
                        <p className="mt-3 text-sm text-slate-400 leading-relaxed">{sub.description}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Methodology */}
              <div className="rounded-xl bg-slate-900/40 border border-slate-800 p-5">
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
                  Methodology
                </h3>
                <p className="text-sm text-slate-400 leading-relaxed">{payload.methodology}</p>
              </div>

              {/* Disclaimer */}
              <p className="text-xs text-slate-600 leading-relaxed italic pb-6">
                All scores are model outputs and should not be treated as investment advice. Always conduct independent research before making financial decisions.
              </p>
            </div>
          </>
        )}
      </div>
    </>
  );
}

// ─── ℹ Info Button ────────────────────────────────────────────────────────────

interface InfoButtonProps {
  onClick: () => void;
  label: string;
}

export function InfoButton({ onClick, label }: InfoButtonProps) {
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      aria-label={`Explain ${label}`}
      title={`Explain ${label}`}
      className="inline-flex items-center justify-center w-5 h-5 rounded-full text-slate-500 hover:text-sky-400 hover:bg-sky-950/40 border border-slate-700 hover:border-sky-800 transition-all duration-150 ml-1.5 flex-shrink-0"
    >
      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
      </svg>
    </button>
  );
}
