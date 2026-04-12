"use client";
/**
 * app/lifestyle/tax-residency/page.tsx — Sprint 45
 * Interactive tax residency comparison table across 10 jurisdictions.
 */
import { useState, useMemo } from "react";
import Link from "next/link";
import { ArrowLeft, AlertTriangle } from "lucide-react";

interface Country {
    name: string; flag: string;
    income_tax: string;     // top rate
    capital_gains: string;
    wealth_tax: string;
    crypto: string;         // treatment
    days_required: number;  // min days for residency
    fatca: boolean;         // FATCA exposure (US persons)
    system: "territorial" | "worldwide" | "remittance";
    crypto_friendly: boolean;
    no_wealth_tax: boolean;
}

const COUNTRIES: Country[] = [
    { name: "UAE (Dubai)", flag: "🇦🇪", income_tax: "0%", capital_gains: "0%", wealth_tax: "None", crypto: "0% — no CGT", days_required: 90, fatca: false, system: "territorial", crypto_friendly: true, no_wealth_tax: true },
    { name: "Portugal (NHR)", flag: "🇵🇹", income_tax: "20% flat", capital_gains: "28%", wealth_tax: "None", crypto: "0% (>365 days)", days_required: 183, fatca: false, system: "territorial", crypto_friendly: true, no_wealth_tax: true },
    { name: "Malta", flag: "🇲🇹", income_tax: "15–35%", capital_gains: "0%*", wealth_tax: "None", crypto: "Taxed as income", days_required: 183, fatca: false, system: "remittance", crypto_friendly: false, no_wealth_tax: true },
    { name: "Cyprus", flag: "🇨🇾", income_tax: "0–35%", capital_gains: "0%*", wealth_tax: "None", crypto: "Variable", days_required: 60, fatca: false, system: "territorial", crypto_friendly: false, no_wealth_tax: true },
    { name: "Georgia", flag: "🇬🇪", income_tax: "20%", capital_gains: "0%*", wealth_tax: "None", crypto: "0% (foreign-source)", days_required: 183, fatca: false, system: "territorial", crypto_friendly: true, no_wealth_tax: true },
    { name: "Germany", flag: "🇩🇪", income_tax: "45%", capital_gains: "25%", wealth_tax: "None", crypto: "0% (>1yr hold)", days_required: 183, fatca: false, system: "worldwide", crypto_friendly: true, no_wealth_tax: true },
    { name: "Spain", flag: "🇪🇸", income_tax: "47%", capital_gains: "26%", wealth_tax: "0.2–2.5%", crypto: "Taxed as savings", days_required: 183, fatca: false, system: "worldwide", crypto_friendly: false, no_wealth_tax: false },
    { name: "Switzerland", flag: "🇨🇭", income_tax: "11–22%", capital_gains: "0%*", wealth_tax: "0.1–0.9%", crypto: "0% (private investor)", days_required: 183, fatca: false, system: "worldwide", crypto_friendly: true, no_wealth_tax: false },
    { name: "Singapore", flag: "🇸🇬", income_tax: "22%", capital_gains: "0%", wealth_tax: "None", crypto: "Variable (trading=income)", days_required: 183, fatca: false, system: "territorial", crypto_friendly: false, no_wealth_tax: true },
    { name: "USA", flag: "🇺🇸", income_tax: "37%", capital_gains: "20%", wealth_tax: "None", crypto: "Capital gains tax", days_required: 0, fatca: true, system: "worldwide", crypto_friendly: false, no_wealth_tax: true },
];

type SortKey = "name" | "days_required" | "income_tax_raw";
type Filter = "all" | "no_wealth_tax" | "territorial" | "crypto_friendly";

const FILTER_OPTS: { key: Filter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "no_wealth_tax", label: "No wealth tax" },
    { key: "territorial", label: "Territorial system" },
    { key: "crypto_friendly", label: "Crypto-friendly" },
];

function parseRate(s: string): number {
    const m = s.match(/(\d+)/);
    return m ? parseInt(m[1]) : 999;
}

export default function TaxResidencyPage() {
    const [filter, setFilter] = useState<Filter>("all");
    const [sort, setSort] = useState<SortKey>("name");

    const rows = useMemo(() => {
        let list = [...COUNTRIES];
        if (filter === "no_wealth_tax") list = list.filter((c) => c.no_wealth_tax);
        if (filter === "territorial")  list = list.filter((c) => c.system === "territorial");
        if (filter === "crypto_friendly") list = list.filter((c) => c.crypto_friendly);
        if (sort === "name") list.sort((a, b) => a.name.localeCompare(b.name));
        if (sort === "days_required") list.sort((a, b) => a.days_required - b.days_required);
        if (sort === "income_tax_raw") list.sort((a, b) => parseRate(a.income_tax) - parseRate(b.income_tax));
        return list;
    }, [filter, sort]);

    return (
        <div className="mx-auto max-w-5xl space-y-6">
            <div className="flex items-center gap-3">
                <Link href="/lifestyle" className="text-slate-500 hover:text-slate-300 transition-colors">
                    <ArrowLeft className="h-4 w-4" />
                </Link>
                <div>
                    <h1 className="text-xl font-semibold">Tax Residency Comparison</h1>
                    <p className="text-sm text-slate-400 mt-0.5">10 jurisdictions · sortable · filterable</p>
                </div>
            </div>

            {/* US FATCA banner */}
            <div className="flex items-start gap-2.5 rounded-lg border border-amber-700/30 bg-amber-950/20 px-4 py-3 text-xs text-amber-300">
                <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>
                    <strong>US citizens & green card holders:</strong> The US taxes on worldwide income regardless of residency.
                    Renunciation or an exit tax may apply. Consult a US-licensed international tax attorney before relocating.
                </span>
            </div>

            {/* Filters + Sort */}
            <div className="flex flex-wrap items-center gap-3">
                <div className="flex rounded-lg border border-slate-700 overflow-hidden text-xs">
                    {FILTER_OPTS.map((f) => (
                        <button key={f.key} onClick={() => setFilter(f.key)}
                            className={`px-3 py-1.5 font-medium transition-colors ${filter === f.key ? "bg-slate-700 text-slate-100" : "text-slate-400 hover:text-slate-200"}`}>
                            {f.label}
                        </button>
                    ))}
                </div>
                <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)}
                    className="rounded-lg border border-slate-700 bg-slate-900 text-xs text-slate-300 px-3 py-1.5 focus:outline-none">
                    <option value="name">Sort: A–Z</option>
                    <option value="days_required">Sort: Fewest days</option>
                    <option value="income_tax_raw">Sort: Lowest income tax</option>
                </select>
            </div>

            {/* Table */}
            <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                            <th className="text-left px-4 py-3">Country</th>
                            <th className="text-left px-3 py-3">Income Tax</th>
                            <th className="text-left px-3 py-3">Capital Gains</th>
                            <th className="text-left px-3 py-3">Wealth Tax</th>
                            <th className="text-left px-3 py-3">Crypto</th>
                            <th className="text-right px-3 py-3">Days Req.</th>
                            <th className="text-left px-3 py-3">System</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {rows.map((c) => (
                            <tr key={c.name} className="hover:bg-slate-800/30 transition-colors">
                                <td className="px-4 py-3 font-medium text-slate-200 whitespace-nowrap">
                                    {c.flag} {c.name}
                                    {c.fatca && <span className="ml-2 text-[10px] text-rose-400 bg-rose-950/30 border border-rose-800/30 rounded-full px-1.5 py-0.5">FATCA</span>}
                                </td>
                                <td className="px-3 py-3 text-slate-300 tabular-nums">{c.income_tax}</td>
                                <td className="px-3 py-3 tabular-nums">
                                    <span className={c.capital_gains.startsWith("0") ? "text-emerald-400" : "text-slate-300"}>
                                        {c.capital_gains}
                                    </span>
                                </td>
                                <td className="px-3 py-3">
                                    <span className={c.no_wealth_tax ? "text-emerald-400" : "text-amber-400"}>
                                        {c.wealth_tax}
                                    </span>
                                </td>
                                <td className="px-3 py-3 text-slate-400 text-xs max-w-[160px]">{c.crypto}</td>
                                <td className="px-3 py-3 text-right tabular-nums text-slate-300">{c.days_required}</td>
                                <td className="px-3 py-3">
                                    <span className={`text-[11px] rounded-full px-2 py-0.5 font-medium ${
                                        c.system === "territorial" ? "bg-sky-900/40 text-sky-400"
                                        : c.system === "remittance" ? "bg-violet-900/40 text-violet-400"
                                        : "bg-slate-800 text-slate-400"
                                    }`}>
                                        {c.system}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <p className="text-xs text-slate-600">
                * Subject to conditions. Data is indicative — tax law changes frequently.
                Always verify with a qualified local tax advisor. Not legal advice.
            </p>
        </div>
    );
}
