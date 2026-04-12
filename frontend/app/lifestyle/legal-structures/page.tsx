"use client";
/**
 * app/lifestyle/legal-structures/page.tsx — Sprint 45
 * 9 entity types with interactive "Which fits me?" quiz.
 */
import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ChevronRight, RotateCcw } from "lucide-react";

interface Entity {
    name: string; region: string;
    asset_protection: "High" | "Medium" | "Low";
    tax_efficiency: "High" | "Medium" | "Low";
    privacy: "High" | "Medium" | "Low";
    setup_cost: "Low" | "Medium" | "High";
    complexity: "Simple" | "Medium" | "Complex";
    best_for: string;
    tags: string[];
    scores: { residency: string[]; asset: string[]; privacy_need: string[]; tax_goal: string[] };
}

const ENTITIES: Entity[] = [
    { name: "Sole Trader", region: "Universal", asset_protection: "Low", tax_efficiency: "Low", privacy: "Low", setup_cost: "Low", complexity: "Simple", best_for: "Freelancers / early-stage", tags: ["Simple", "No separation"], scores: { residency: ["any"], asset: ["services"], privacy_need: ["low"], tax_goal: ["simplicity"] } },
    { name: "UK LTD", region: "UK", asset_protection: "High", tax_efficiency: "Medium", privacy: "Low", setup_cost: "Low", complexity: "Simple", best_for: "UK-based businesses", tags: ["19% corp tax", "Dividends"], scores: { residency: ["uk"], asset: ["equity", "services"], privacy_need: ["low"], tax_goal: ["dividends"] } },
    { name: "GmbH", region: "Germany / Austria", asset_protection: "High", tax_efficiency: "Medium", privacy: "Medium", setup_cost: "Medium", complexity: "Complex", best_for: "German-market companies", tags: ["25k€ share capital", "~30% tax"], scores: { residency: ["de", "at"], asset: ["equity", "services"], privacy_need: ["medium"], tax_goal: ["reinvestment"] } },
    { name: "US LLC", region: "USA", asset_protection: "High", tax_efficiency: "High", privacy: "Medium", setup_cost: "Low", complexity: "Simple", best_for: "Non-US founders (pass-through)", tags: ["Pass-through", "Wyoming/Delaware"], scores: { residency: ["non-us"], asset: ["equity", "digital"], privacy_need: ["medium"], tax_goal: ["pass-through"] } },
    { name: "Holding Company", region: "Universal", asset_protection: "High", tax_efficiency: "High", privacy: "High", setup_cost: "Medium", complexity: "Complex", best_for: "Multi-entity structures", tags: ["Participation exemption", "Dividend shield"], scores: { residency: ["any"], asset: ["equity", "real-estate"], privacy_need: ["high"], tax_goal: ["dividends", "reinvestment"] } },
    { name: "Trust", region: "UK / Channel Islands", asset_protection: "High", tax_efficiency: "Medium", privacy: "High", setup_cost: "High", complexity: "Complex", best_for: "Succession planning", tags: ["Estate planning", "Discretionary"], scores: { residency: ["uk"], asset: ["real-estate", "equity"], privacy_need: ["high"], tax_goal: ["succession"] } },
    { name: "Foundation", region: "Liechtenstein / Panama", asset_protection: "High", tax_efficiency: "High", privacy: "High", setup_cost: "High", complexity: "Complex", best_for: "Asset protection & privacy", tags: ["No beneficial owner registry", "Offshore"], scores: { residency: ["any"], asset: ["real-estate", "equity"], privacy_need: ["high"], tax_goal: ["protection"] } },
    { name: "BV (Netherlands)", region: "Netherlands", asset_protection: "High", tax_efficiency: "High", privacy: "Medium", setup_cost: "Medium", complexity: "Medium", best_for: "EU holding, low corp tax", tags: ["15–25.8% corp tax", "EU access"], scores: { residency: ["eu"], asset: ["equity", "services"], privacy_need: ["medium"], tax_goal: ["dividends", "reinvestment"] } },
    { name: "S.A.", region: "Spain / France / Switzerland", asset_protection: "High", tax_efficiency: "Medium", privacy: "Low", setup_cost: "High", complexity: "Complex", best_for: "Public-ready companies", tags: ["Listed eligible", "High capital"], scores: { residency: ["eu"], asset: ["equity"], privacy_need: ["low"], tax_goal: ["growth"] } },
];

const QUIZ_STEPS = [
    { q: "Where are you tax-resident (or planning to be)?", key: "residency", opts: [{ label: "UK", val: "uk" }, { label: "Germany / Austria", val: "de" }, { label: "EU (other)", val: "eu" }, { label: "Non-US, non-EU", val: "non-us" }, { label: "Not sure / flexible", val: "any" }] },
    { q: "What type of assets will the entity hold?", key: "asset", opts: [{ label: "Equity investments / shares", val: "equity" }, { label: "Real estate", val: "real-estate" }, { label: "Services / consulting income", val: "services" }, { label: "Digital products / SaaS", val: "digital" }] },
    { q: "How important is privacy?", key: "privacy_need", opts: [{ label: "Not important", val: "low" }, { label: "Somewhat important", val: "medium" }, { label: "Very important", val: "high" }] },
    { q: "Primary tax goal?", key: "tax_goal", opts: [{ label: "Simplicity", val: "simplicity" }, { label: "Tax-efficient dividends", val: "dividends" }, { label: "Reinvest profits", val: "reinvestment" }, { label: "Asset protection", val: "protection" }, { label: "Succession planning", val: "succession" }, { label: "Pass-through income", val: "pass-through" }] },
];

type Answers = Record<string, string>;

function scoreEntities(answers: Answers): Entity[] {
    return [...ENTITIES]
        .map((e) => {
            let score = 0;
            for (const key of Object.keys(answers) as (keyof Entity["scores"])[]) {
                const val = answers[key];
                const allowed = e.scores[key];
                if (allowed.includes(val) || allowed.includes("any")) score += 2;
                else if (allowed.includes("any")) score += 1;
            }
            return { entity: e, score };
        })
        .sort((a, b) => b.score - a.score)
        .map((x) => x.entity);
}

const LEVEL_COLOR: Record<string, string> = {
    High: "text-emerald-400", Medium: "text-amber-400", Low: "text-rose-400",
    Simple: "text-emerald-400", Complex: "text-rose-400",
};

export default function LegalStructuresPage() {
    const [step, setStep] = useState<number>(-1); // -1 = browse, 0+ = quiz
    const [answers, setAnswers] = useState<Answers>({});
    const [results, setResults] = useState<Entity[] | null>(null);

    const pick = (key: string, val: string) => {
        const next = { ...answers, [key]: val };
        setAnswers(next);
        if (step < QUIZ_STEPS.length - 1) { setStep(step + 1); }
        else { setResults(scoreEntities(next)); setStep(QUIZ_STEPS.length); }
    };

    const reset = () => { setStep(-1); setAnswers({}); setResults(null); };

    return (
        <div className="mx-auto max-w-3xl space-y-6">
            <div className="flex items-center gap-3">
                <Link href="/lifestyle" className="text-slate-500 hover:text-slate-300 transition-colors">
                    <ArrowLeft className="h-4 w-4" />
                </Link>
                <div>
                    <h1 className="text-xl font-semibold">Legal Entity Structures</h1>
                    <p className="text-sm text-slate-400 mt-0.5">Compare 9 structures · take the quiz to find your fit</p>
                </div>
            </div>

            {/* Quiz CTA / Quiz / Results */}
            {step === -1 && (
                <button onClick={() => setStep(0)}
                    className="w-full flex items-center justify-between rounded-xl border border-sky-700/40 bg-sky-950/20 px-5 py-4 hover:bg-sky-950/30 transition-colors">
                    <div className="text-left">
                        <p className="text-sm font-semibold text-sky-300">Which fits me?</p>
                        <p className="text-xs text-slate-400 mt-0.5">4 quick questions → ranked entity recommendations</p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-sky-400" />
                </button>
            )}

            {step >= 0 && step < QUIZ_STEPS.length && (
                <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-5 space-y-4">
                    <div className="flex items-center gap-2">
                        <div className="flex-1 h-1 rounded-full bg-slate-800 overflow-hidden">
                            <div className="h-full rounded-full bg-sky-500 transition-all" style={{ width: `${(step / QUIZ_STEPS.length) * 100}%` }} />
                        </div>
                        <span className="text-[11px] text-slate-500">{step + 1}/{QUIZ_STEPS.length}</span>
                    </div>
                    <p className="text-sm font-medium text-slate-200">{QUIZ_STEPS[step].q}</p>
                    <div className="grid gap-2">
                        {QUIZ_STEPS[step].opts.map((o) => (
                            <button key={o.val} onClick={() => pick(QUIZ_STEPS[step].key, o.val)}
                                className="text-left rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-slate-300 hover:border-sky-600 hover:bg-sky-950/20 hover:text-sky-300 transition-all">
                                {o.label}
                            </button>
                        ))}
                    </div>
                    <button onClick={reset} className="text-xs text-slate-600 hover:text-slate-400 transition-colors">Cancel</button>
                </div>
            )}

            {results && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-slate-200">Ranked recommendations</p>
                        <button onClick={reset} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300">
                            <RotateCcw className="h-3 w-3" /> Retake
                        </button>
                    </div>
                    {results.slice(0, 4).map((e, i) => (
                        <div key={e.name} className={`rounded-xl border p-4 space-y-2 ${i === 0 ? "border-sky-700/40 bg-sky-950/10" : "border-slate-800 bg-slate-900/30"}`}>
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    {i === 0 && <span className="text-xs font-bold text-sky-400 bg-sky-900/30 rounded-full px-2 py-0.5">Best match</span>}
                                    <span className="text-sm font-semibold text-slate-100">{e.name}</span>
                                    <span className="text-xs text-slate-500">{e.region}</span>
                                </div>
                            </div>
                            <p className="text-xs text-slate-400">{e.best_for}</p>
                            <div className="flex gap-4 text-xs">
                                <span>Protection: <span className={LEVEL_COLOR[e.asset_protection]}>{e.asset_protection}</span></span>
                                <span>Tax eff.: <span className={LEVEL_COLOR[e.tax_efficiency]}>{e.tax_efficiency}</span></span>
                                <span>Privacy: <span className={LEVEL_COLOR[e.privacy]}>{e.privacy}</span></span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Full comparison table */}
            <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-xs">
                    <thead>
                        <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                            <th className="text-left px-4 py-3">Entity</th>
                            <th className="text-left px-3 py-3">Region</th>
                            <th className="px-3 py-3">Protection</th>
                            <th className="px-3 py-3">Tax Eff.</th>
                            <th className="px-3 py-3">Privacy</th>
                            <th className="px-3 py-3">Complexity</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {ENTITIES.map((e) => (
                            <tr key={e.name} className="hover:bg-slate-800/20">
                                <td className="px-4 py-2.5 font-medium text-slate-200">{e.name}</td>
                                <td className="px-3 py-2.5 text-slate-500">{e.region}</td>
                                <td className={`px-3 py-2.5 text-center ${LEVEL_COLOR[e.asset_protection]}`}>{e.asset_protection}</td>
                                <td className={`px-3 py-2.5 text-center ${LEVEL_COLOR[e.tax_efficiency]}`}>{e.tax_efficiency}</td>
                                <td className={`px-3 py-2.5 text-center ${LEVEL_COLOR[e.privacy]}`}>{e.privacy}</td>
                                <td className={`px-3 py-2.5 text-center ${LEVEL_COLOR[e.complexity]}`}>{e.complexity}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <p className="text-xs text-slate-600">Not legal advice. Consult a qualified solicitor or tax attorney before establishing any entity.</p>
        </div>
    );
}
