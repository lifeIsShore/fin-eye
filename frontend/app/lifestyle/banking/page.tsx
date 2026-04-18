"use client";
/**
 * app/lifestyle/banking/page.tsx — Sprint 48
 * International Banking & Investing guide for location-independent investors.
 * Accordion sections — collapsed by default, no backend required.
 */
import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ChevronDown, ChevronRight, AlertTriangle, CheckCircle2 } from "lucide-react";

interface Section {
    title: string;
    summary: string;
    content: React.ReactNode;
}

function Accordion({ section }: { section: Section }) {
    const [open, setOpen] = useState(false);
    return (
        <div className="rounded-xl border border-slate-800 overflow-hidden">
            <button
                onClick={() => setOpen((v) => !v)}
                className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-slate-800/30 transition-colors"
            >
                <div>
                    <p className="text-sm font-semibold text-slate-200">{section.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{section.summary}</p>
                </div>
                {open
                    ? <ChevronDown className="h-4 w-4 text-slate-400 flex-shrink-0" />
                    : <ChevronRight className="h-4 w-4 text-slate-400 flex-shrink-0" />}
            </button>
            {open && (
                <div className="border-t border-slate-800 px-5 py-4 space-y-3 text-sm text-slate-400 leading-relaxed">
                    {section.content}
                </div>
            )}
        </div>
    );
}

function Check({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0 mt-0.5" />
            <span>{children}</span>
        </div>
    );
}

function Warn({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <span className="text-amber-300/80">{children}</span>
        </div>
    );
}

function Tag({ children }: { children: React.ReactNode }) {
    return <span className="inline-block text-[11px] bg-slate-800 text-slate-400 rounded-full px-2 py-0.5 mr-1">{children}</span>;
}

const SECTIONS: Section[] = [
    {
        title: "Multi-Currency Accounts",
        summary: "Best accounts for moving money across currencies with minimal fees",
        content: (
            <div className="space-y-4">
                <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4 space-y-2">
                    <div className="flex items-center justify-between">
                        <p className="font-semibold text-slate-200">Wise (TransferWise)</p>
                        <Tag>Best for FX</Tag>
                    </div>
                    <p>Uses the real mid-market exchange rate with a small transparent fee (0.3–1.5%). Holds EUR, USD, GBP, CHF, and 50+ more. Debit card included. <strong className="text-slate-300">No hidden spread.</strong></p>
                    <Check>Best for regular EUR↔USD↔GBP movement</Check>
                    <Check>IBAN in DE, UK, US — works for SEPA and ACH</Check>
                </div>
                <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4 space-y-2">
                    <div className="flex items-center justify-between">
                        <p className="font-semibold text-slate-200">Revolut</p>
                        <Tag>All-in-one</Tag>
                    </div>
                    <p>Multi-currency account + stock trading + crypto in one app. Good FX rates within limits (unlimited on Metal plan). Full EU banking licence (Lithuanian).</p>
                    <Check>Convenient for retail spending abroad</Check>
                    <Warn>FX rate degrades on weekends — exchange Mon–Fri</Warn>
                </div>
                <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4 space-y-2">
                    <div className="flex items-center justify-between">
                        <p className="font-semibold text-slate-200">Interactive Brokers</p>
                        <Tag>Best for investing</Tag>
                    </div>
                    <p>Cheapest FX conversion for large amounts ($2 flat or 0.002%). Full EU banking licence. Holds 20+ currencies. Best option if you also invest through them.</p>
                    <Check>SIPC + FSCS protected (US + UK assets)</Check>
                    <Check>Ideal if you move €10k+ at a time</Check>
                </div>
            </div>
        ),
    },
    {
        title: "SEPA vs SWIFT",
        summary: "When to use each — practical decision guide for international transfers",
        content: (
            <div className="space-y-4">
                <div className="grid sm:grid-cols-2 gap-4">
                    <div className="rounded-lg border border-emerald-800/30 bg-emerald-950/10 p-4 space-y-2">
                        <p className="font-semibold text-emerald-300">SEPA</p>
                        <p className="text-xs text-slate-400">Euro transfers within EU/EEA. Usually same-day or next business day. Cost: near-zero (banks must offer it free under EU rules).</p>
                        <Check>Sending EUR to any EU/EEA bank</Check>
                        <Check>Salary payments, rent, recurring bills</Check>
                        <Check>Instant SEPA available at most major banks</Check>
                    </div>
                    <div className="rounded-lg border border-sky-800/30 bg-sky-950/10 p-4 space-y-2">
                        <p className="font-semibold text-sky-300">SWIFT</p>
                        <p className="text-xs text-slate-400">International wire. 1–5 business days. Cost: $15–50 per transfer + possible intermediary bank fees.</p>
                        <Check>Sending to non-EU countries (US, UAE, CH)</Check>
                        <Check>Sending non-EUR currencies internationally</Check>
                        <Warn>Correspondent bank may deduct fees in transit</Warn>
                    </div>
                </div>
                <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Decision tree</p>
                    <div className="space-y-1 text-sm">
                        <p>Sending EUR → EU/EEA bank? <span className="text-emerald-400 font-medium">→ Use SEPA</span></p>
                        <p>Sending EUR → non-EU (e.g. UAE)? <span className="text-sky-400 font-medium">→ Use Wise (SWIFT at better rate)</span></p>
                        <p>Sending USD/GBP internationally? <span className="text-sky-400 font-medium">→ Use Wise or IBKR</span></p>
                        <p>Large amount ({'>'}€20k) any currency? <span className="text-violet-400 font-medium">→ Use IBKR for lowest cost</span></p>
                    </div>
                </div>
            </div>
        ),
    },
    {
        title: "FATCA Exposure for US Persons",
        summary: "Critical: US citizens and green card holders face unique reporting obligations abroad",
        content: (
            <div className="space-y-4">
                <div className="flex items-start gap-3 rounded-lg border border-rose-800/30 bg-rose-950/10 p-4">
                    <AlertTriangle className="h-5 w-5 text-rose-400 flex-shrink-0 mt-0.5" />
                    <p className="text-rose-300/90 text-sm">The US taxes citizens on <strong>worldwide income regardless of residency</strong>. This applies to US citizens and green card holders living anywhere.</p>
                </div>
                <div className="space-y-3">
                    <div>
                        <p className="font-semibold text-slate-200 mb-1">FBAR (FinCEN 114)</p>
                        <p>Report all foreign accounts with combined value exceeding $10,000 at any point in the year. Filed separately from tax return. Penalty for non-compliance: up to $10,000/year per account.</p>
                    </div>
                    <div>
                        <p className="font-semibold text-slate-200 mb-1">FATCA Form 8938</p>
                        <p>Report foreign financial assets exceeding $50,000 (single) or $100,000 (married). Filed with your 1040. Overlaps with but is not the same as FBAR.</p>
                    </div>
                    <div>
                        <p className="font-semibold text-slate-200 mb-1">European banks that still accept US persons</p>
                        <p>Many EU banks refuse US persons due to FATCA compliance cost. Banks generally still accepting: <strong className="text-slate-300">Interactive Brokers, Wise, Swissquote, PostFinance (CH), Revolut</strong> (with limitations).</p>
                    </div>
                </div>
                <Warn>Consult a US-licensed international tax attorney before relocating or opening foreign accounts. Renunciation of US citizenship is a one-way, irreversible process with an exit tax.</Warn>
            </div>
        ),
    },
    {
        title: "Non-Resident Account Opening",
        summary: "Which countries and banks accept non-residents — documents required",
        content: (
            <div className="space-y-4">
                <div className="grid sm:grid-cols-2 gap-3">
                    {[
                        { country: "🇬🇪 Georgia", notes: "TBC Bank, Bank of Georgia — easy non-resident opening, low requirements, English service. Territorial tax system." },
                        { country: "🇦🇪 UAE (Dubai)", notes: "Emirates NBD, ADCB — requires UAE residency visa. Non-residents can open with introduction." },
                        { country: "🇨🇭 Switzerland", notes: "Swissquote, PostFinance — accept non-residents for brokerage. Some cantonal banks require meeting in person." },
                        { country: "🇸🇬 Singapore", notes: "DBS, OCBC — non-resident personal accounts possible but require visit to branch." },
                    ].map((b) => (
                        <div key={b.country} className="rounded-lg border border-slate-700 bg-slate-900/40 p-3">
                            <p className="font-semibold text-slate-200 text-sm mb-1">{b.country}</p>
                            <p className="text-xs text-slate-400">{b.notes}</p>
                        </div>
                    ))}
                </div>
                <div>
                    <p className="font-semibold text-slate-200 mb-2">Digital-first banks accepting non-residents</p>
                    <div className="space-y-1">
                        <Check><strong className="text-slate-300">Wise</strong> — accepts almost all nationalities, fully online</Check>
                        <Check><strong className="text-slate-300">Revolut</strong> — available in 40+ countries, minimal KYC</Check>
                        <Check><strong className="text-slate-300">IBKR</strong> — brokerage account open to non-residents of most countries</Check>
                    </div>
                </div>
                <div>
                    <p className="font-semibold text-slate-200 mb-1">Typical documents required</p>
                    <div className="space-y-1 text-sm">
                        <Check>Valid passport (not expiring within 6 months)</Check>
                        <Check>Proof of address (utility bill or bank statement, {'<'}3 months old)</Check>
                        <Check>Source of funds declaration (for amounts {'>'}€10k)</Check>
                        <Check>Tax identification number (TIN) from your home country</Check>
                    </div>
                </div>
            </div>
        ),
    },
    {
        title: "Brokerage for Non-Residents",
        summary: "Best EU-accessible brokers — restrictions for US citizens explained",
        content: (
            <div className="space-y-4">
                <div className="space-y-3">
                    {[
                        {
                            name: "Interactive Brokers",
                            tags: ["Best overall", "Stocks", "ETFs", "Options", "Forex"],
                            desc: "Globally the most accessible broker. Accepts investors from 200+ countries. Cheapest commissions. Access to stocks, ETFs, options, futures, forex, bonds. Full EU licence (IBCE based in Hungary).",
                            ok: ["Non-residents of most countries", "US citizens (full FATCA compliance)", "Large portfolios"],
                            warn: null,
                        },
                        {
                            name: "Trade Republic",
                            tags: ["EU only", "German licence", "Commission-free"],
                            desc: "German-regulated, €1 flat commission per trade. Available in 17 EU countries. 4% interest on uninvested cash. Best for EU residents who want simple stock + ETF investing.",
                            ok: ["EU residents", "Simple buy-and-hold", "Fractional shares"],
                            warn: "Not available to US citizens or non-EU residents",
                        },
                        {
                            name: "Degiro",
                            tags: ["Netherlands", "Low cost", "EU focused"],
                            desc: "Dutch-regulated, flat fee of €1–3 per trade. 30+ exchanges. No crypto. Good for frequent ETF buyers.",
                            ok: ["EU residents", "Frequent traders", "Index fund investing"],
                            warn: "Not available to US persons",
                        },
                    ].map((b) => (
                        <div key={b.name} className="rounded-lg border border-slate-700 bg-slate-900/40 p-4 space-y-2">
                            <div className="flex flex-wrap items-center gap-2">
                                <p className="font-semibold text-slate-200">{b.name}</p>
                                {b.tags.map((t) => <Tag key={t}>{t}</Tag>)}
                            </div>
                            <p className="text-sm">{b.desc}</p>
                            <div className="space-y-1">
                                {b.ok.map((o) => <Check key={o}>{o}</Check>)}
                                {b.warn && <Warn>{b.warn}</Warn>}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        ),
    },
];

export default function BankingPage() {
    return (
        <div className="mx-auto max-w-3xl space-y-6">
            <div className="flex items-center gap-3">
                <Link href="/lifestyle" className="text-slate-500 hover:text-slate-300 transition-colors">
                    <ArrowLeft className="h-4 w-4" />
                </Link>
                <div>
                    <h1 className="text-xl font-semibold">International Banking & Investing</h1>
                    <p className="text-sm text-slate-400 mt-0.5">Multi-currency accounts · SEPA vs SWIFT · FATCA · Non-resident accounts · Brokerages</p>
                </div>
            </div>

            <div className="space-y-3">
                {SECTIONS.map((s) => <Accordion key={s.title} section={s} />)}
            </div>

            <p className="text-xs text-slate-600 border-t border-slate-800 pt-4">
                Information is for educational purposes only and may be outdated. Banking rules and availability change frequently.
                Not financial or legal advice. Always verify with official sources before opening accounts.
            </p>
        </div>
    );
}
