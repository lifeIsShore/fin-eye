"use client";
/**
 * app/admin/gas-weights/page.tsx — Sprint 45
 * Custom GAS component weight editor for B2B advisor tenants.
 */
import { useState } from "react";
import { Sliders, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const PRESETS = [
    { label: "Balanced",         t: 0.40, m: 0.30, s: 0.30 },
    { label: "Technical Focus",  t: 0.60, m: 0.20, s: 0.20 },
    { label: "Macro-Heavy",      t: 0.25, m: 0.50, s: 0.25 },
    { label: "Sentiment-Driven", t: 0.25, m: 0.25, s: 0.50 },
];

function pct(v: number) { return `${Math.round(v * 100)}%`; }

export default function GasWeightsPage() {
    const [slug, setSlug] = useState("");
    const [tech, setTech] = useState(0.40);
    const [macro, setMacro] = useState(0.30);
    const [sent, setSent] = useState(0.30);
    const [saving, setSaving] = useState(false);
    const [msg, setMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

    const total = Math.round((tech + macro + sent) * 100) / 100;
    const valid = Math.abs(total - 1.0) < 0.001 && slug.trim().length >= 3;

    const applyPreset = (p: typeof PRESETS[0]) => { setTech(p.t); setMacro(p.m); setSent(p.s); };

    const save = async () => {
        setSaving(true); setMsg(null);
        try {
            const token = localStorage.getItem("access_token") ?? "";
            const res = await fetch(`${API_BASE}/api/v1/tenants/${slug.trim()}/gas-weights`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({ weight_technical: tech, weight_macro: macro, weight_sentiment: sent }),
            });
            if (!res.ok) { const e = await res.json(); throw new Error(e.detail ?? "Save failed"); }
            setMsg({ type: "ok", text: "Weights saved successfully." });
        } catch (e: any) {
            setMsg({ type: "err", text: e.message });
        } finally { setSaving(false); }
    };

    return (
        <div className="mx-auto max-w-xl space-y-6">
            <div className="flex items-center gap-3">
                <Sliders className="h-5 w-5 text-sky-400" />
                <div>
                    <h1 className="text-xl font-semibold">Custom GAS Weights</h1>
                    <p className="text-sm text-slate-400 mt-0.5">Override component weights for your advisor tenant.</p>
                </div>
            </div>

            {/* Tenant slug */}
            <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Tenant Slug</label>
                <input value={slug} onChange={(e) => setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                    placeholder="my-advisor-firm"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-mono text-slate-200 placeholder-slate-600 focus:border-sky-500 focus:outline-none" />
            </div>

            {/* Presets */}
            <div>
                <p className="text-xs text-slate-500 mb-2">Quick presets</p>
                <div className="flex flex-wrap gap-2">
                    {PRESETS.map((p) => (
                        <button key={p.label} onClick={() => applyPreset(p)}
                            className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-sky-600 hover:text-sky-300 transition-colors">
                            {p.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Sliders */}
            {(["Technical", "Macro", "Sentiment"] as const).map((label) => {
                const val = label === "Technical" ? tech : label === "Macro" ? macro : sent;
                const set = label === "Technical" ? setTech : label === "Macro" ? setMacro : setSent;
                const color = label === "Technical" ? "sky" : label === "Macro" ? "emerald" : "violet";
                return (
                    <div key={label} className="space-y-2">
                        <div className="flex justify-between text-xs">
                            <span className="text-slate-300 font-medium">{label}</span>
                            <span className={`font-bold text-${color}-400 tabular-nums`}>{pct(val)}</span>
                        </div>
                        <input type="range" min={0} max={1} step={0.05} value={val}
                            onChange={(e) => set(parseFloat(e.target.value))}
                            className="w-full accent-sky-500" />
                    </div>
                );
            })}

            {/* Total indicator */}
            <div className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${
                valid ? "border border-emerald-800/40 bg-emerald-950/20 text-emerald-400"
                      : "border border-amber-800/40 bg-amber-950/20 text-amber-400"
            }`}>
                {valid
                    ? <><CheckCircle2 className="h-3.5 w-3.5" /> Weights sum to 100% ✓</>
                    : <><AlertTriangle className="h-3.5 w-3.5" /> Total: {pct(total)} — must equal 100%</>
                }
            </div>

            {/* Save */}
            <button onClick={save} disabled={!valid || saving}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 disabled:cursor-not-allowed px-4 py-2.5 text-sm font-semibold text-white transition-colors">
                {saving ? <><Loader2 className="h-4 w-4 animate-spin" /> Saving…</> : "Save Weights"}
            </button>

            {msg && (
                <div className={`text-xs rounded-lg px-3 py-2 ${msg.type === "ok" ? "text-emerald-400 bg-emerald-950/20 border border-emerald-800/30" : "text-red-400 bg-red-950/20 border border-red-800/30"}`}>
                    {msg.text}
                </div>
            )}

            <p className="text-xs text-slate-600">
                Weights apply to GAS score computation for all symbols viewed under this tenant.
                Changes take effect on the next GAS precompute cycle.
            </p>
        </div>
    );
}
