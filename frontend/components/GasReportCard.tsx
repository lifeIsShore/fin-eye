"use client";
/**
 * GasReportCard.tsx — Sprint 53
 * Hidden off-screen card (800×450px Twitter card ratio) that html2canvas
 * captures to produce a shareable PNG. Rendered in page.tsx with id="gas-report-card".
 */
import type { TechnicalSignalDto } from "@/lib/api";

interface Props {
  symbol: string;
  gasScore: number;
  grade: string | undefined;
  regime: string | null;
  techScore: number;
  sentScore: number;
  macroScore: number;
  signals: TechnicalSignalDto[];
  currentPrice: number;
}

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <div style={{ background: "#1e293b", borderRadius: 4, overflow: "hidden", height: 10, width: "100%" }}>
      <div style={{ width: `${Math.min(100, Math.max(0, value))}%`, height: "100%", background: color, borderRadius: 4 }} />
    </div>
  );
}

export default function GasReportCard({
  symbol, gasScore, grade, regime, techScore, sentScore, macroScore, signals, currentPrice,
}: Props) {
  const today = new Date().toISOString().slice(0, 10);
  const gasColor = gasScore >= 60 ? "#10b981" : gasScore >= 40 ? "#f59e0b" : "#f43f5e";
  const techDir = techScore >= 60 ? "↑ Bullish" : techScore >= 40 ? "→ Neutral" : "↓ Bearish";
  const sentDir = sentScore >= 60 ? "↑ Bullish" : sentScore >= 40 ? "→ Neutral" : "↓ Bearish";
  const macroDir = macroScore >= 60 ? "↑ Risk-On" : macroScore >= 40 ? "→ Neutral" : "↓ Risk-Off";

  // Dominant signal from timeframes
  const bullish = signals.filter(s => s.direction === "Bullish").length;
  const bearish = signals.filter(s => s.direction === "Bearish").length;
  const signalLabel = bullish > bearish ? "Bullish" : bearish > bullish ? "Bearish" : "Mixed";
  const signalColor = signalLabel === "Bullish" ? "#10b981" : signalLabel === "Bearish" ? "#f43f5e" : "#f59e0b";

  return (
    <div
      id="gas-report-card"
      style={{
        position: "fixed",
        left: -9999,
        top: 0,
        width: 800,
        height: 450,
        background: "#020617",
        color: "#e2e8f0",
        fontFamily: "'Inter', 'system-ui', sans-serif",
        padding: "36px 40px",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        border: "1px solid #1e293b",
        borderRadius: 16,
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <span style={{ fontSize: 18, fontWeight: 800, color: "#10b981", letterSpacing: -0.5 }}>fin-eye</span>
          <span style={{ fontSize: 11, color: "#475569", marginLeft: 8 }}>Market Intelligence</span>
        </div>
        <span style={{ fontSize: 12, color: "#475569" }}>{today}</span>
      </div>

      {/* Symbol + price */}
      <div style={{ marginTop: 4 }}>
        <span style={{ fontSize: 28, fontWeight: 900, letterSpacing: -1, color: "#f1f5f9" }}>{symbol}</span>
        {currentPrice > 0 && (
          <span style={{ fontSize: 14, color: "#64748b", marginLeft: 12 }}>${currentPrice.toFixed(2)}</span>
        )}
      </div>

      {/* GAS score block */}
      <div style={{ display: "flex", alignItems: "center", gap: 32, marginTop: 8 }}>
        <div>
          <div style={{ fontSize: 11, color: "#64748b", textTransform: "uppercase", letterSpacing: 1, marginBottom: 2 }}>GAS Score</div>
          <div style={{ fontSize: 52, fontWeight: 900, color: gasColor, lineHeight: 1 }}>{gasScore.toFixed(0)}</div>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>out of 100</div>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", gap: 16, marginBottom: 8 }}>
            {grade && (
              <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, padding: "6px 14px", textAlign: "center" }}>
                <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase" }}>Grade</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: gasColor }}>{grade}</div>
              </div>
            )}
            {regime && (
              <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, padding: "6px 14px", textAlign: "center" }}>
                <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase" }}>Regime</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: regime === "Risk-On" ? "#10b981" : "#f43f5e", marginTop: 2 }}>{regime}</div>
              </div>
            )}
            <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, padding: "6px 14px", textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase" }}>Consensus</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: signalColor, marginTop: 2 }}>{signalLabel}</div>
            </div>
          </div>
          <Bar value={gasScore} color={gasColor} />
        </div>
      </div>

      {/* Layer scores */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 8 }}>
        {[
          { label: "Technical", value: techScore, dir: techDir },
          { label: "Sentiment", value: sentScore, dir: sentDir },
          { label: "Macro", value: macroScore, dir: macroDir },
        ].map(({ label, value, dir }) => {
          const c = value >= 60 ? "#10b981" : value >= 40 ? "#f59e0b" : "#f43f5e";
          return (
            <div key={label} style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, padding: "10px 14px" }}>
              <div style={{ fontSize: 10, color: "#64748b", textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: c }}>{dir}</div>
              <div style={{ marginTop: 6 }}><Bar value={value} color={c} /></div>
              <div style={{ fontSize: 10, color: "#475569", marginTop: 3 }}>{value.toFixed(0)}/100</div>
            </div>
          );
        })}
      </div>

      {/* Footer disclaimer */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
        <span style={{ fontSize: 10, color: "#334155" }}>⚠ For educational purposes only. Not financial advice.</span>
        <span style={{ fontSize: 10, color: "#334155" }}>fin-eye.app</span>
      </div>
    </div>
  );
}
