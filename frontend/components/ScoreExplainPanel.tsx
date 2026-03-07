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
        className={`fixed top-0 right-0 z-50 h-full w-full max-w-md bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {payload && (
          <>
            {/* Header */}
            <div className="flex items-start justify-between p-6 border-b border-slate-800">
              <div>
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-1">
                  Score Breakdown
                </p>
                <h2 className="text-xl font-black text-slate-100">{payload.title}</h2>
                {payload.weight && (
                  <p className="text-xs text-slate-500 mt-0.5">{payload.weight}</p>
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
            <div className="flex-1 overflow-y-auto p-6 space-y-6">

              {/* Headline score */}
              <div className={`rounded-2xl p-5 border ${COLOR_MAP[scoreToColor(payload.score)].bg} border-slate-800`}>
                <div className="flex items-baseline gap-3 mb-2">
                  <span className={`text-5xl font-black tracking-tighter ${COLOR_MAP[scoreToColor(payload.score)].text}`}>
                    {payload.score.toFixed(0)}
                  </span>
                  <span className="text-lg font-bold text-slate-400">{payload.scoreLabel}</span>
                </div>
                <ScoreBar value={payload.score} color={scoreToColor(payload.score)} />
                <p className="mt-3 text-sm text-slate-300 leading-relaxed">{payload.summary}</p>
              </div>

              {/* Sub-component breakdown */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">
                  Signal Breakdown
                </h3>
                <div className="space-y-4">
                  {payload.subComponents.map((sub) => {
                    const c = COLOR_MAP[sub.color];
                    return (
                      <div key={sub.label} className="rounded-xl bg-slate-900/60 border border-slate-800 p-4">
                        <div className="flex justify-between items-baseline mb-2">
                          <span className="text-sm font-semibold text-slate-200">{sub.label}</span>
                          <span className={`text-xs font-mono font-bold ${c.text}`}>{sub.rawLabel}</span>
                        </div>
                        <ScoreBar value={sub.value} color={sub.color} />
                        <div className="flex justify-between mt-1 text-xs text-slate-600">
                          <span>Bearish</span>
                          <span className={`font-semibold ${c.text}`}>{sub.value.toFixed(0)} / 100</span>
                          <span>Bullish</span>
                        </div>
                        <p className="mt-2 text-xs text-slate-400 leading-relaxed">{sub.description}</p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Methodology */}
              <div className="rounded-xl bg-slate-900/40 border border-slate-800 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-2">
                  Methodology
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">{payload.methodology}</p>
              </div>

              {/* Disclaimer */}
              <p className="text-xs text-slate-600 leading-relaxed italic pb-4">
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
