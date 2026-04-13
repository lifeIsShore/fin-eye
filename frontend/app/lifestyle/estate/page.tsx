"use client";
/**
 * app/lifestyle/estate/page.tsx — Sprint 48
 * Estate & Pension planning guide for cross-border investors.
 * Accordion sections — no backend required.
 */
import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ChevronDown, ChevronRight, AlertTriangle, CheckCircle2, Info } from "lucide-react";

function Accordion({ title, summary, children }: { title: string; summary: string; children: React.ReactNode }) {
    const [open, setOpen] = useState(false);
    return (
        <div className="rounded-xl border border-slate-800 overflow-hidden">
            <button onClick={() => setOpen((v) => !v)}
                className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-slate-800/30 transition-colors">
                <div>
                    <p className="text-sm font-semibold text-slate-200">{title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{summary}</p>
                </div>
                {open ? <ChevronDown className="h-4 w-4 text-slate-400 flex-shrink-0" />
                       : <ChevronRight className="h-4 w-4 text-slate-400 flex-shrink-0" />}
            </button>
            {open && <div className="border-t border-slate-800 px-5 py-4 space-y-3 text-sm text-slate-400 leading-relaxed">{children}</div>}
        </div>
    );
}

function Check({ children }: { children: React.ReactNode }) {
    return <div className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0 mt-0.5" /><span>{children}</span></div>;
}
function Warn({ children }: { children: React.ReactNode }) {
    return <div className="flex items-start gap-2"><AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" /><span className="text-amber-300/80">{children}</span></div>;
}
function Note({ children }: { children: React.ReactNode }) {
    return <div className="flex items-start gap-2"><Info className="h-4 w-4 text-sky-400 flex-shrink-0 mt-0.5" /><span className="text-sky-300/80">{children}</span></div>;
}

export default function EstatePage() {
    return (
        <div className="mx-auto max-w-3xl space-y-6">
            <div className="flex items-center gap-3">
                <Link href="/lifestyle" className="text-slate-500 hover:text-slate-300 transition-colors">
                    <ArrowLeft className="h-4 w-4" />
                </Link>
                <div>
                    <h1 className="text-xl font-semibold">Estate & Pension Planning</h1>
                    <p className="text-sm text-slate-400 mt-0.5">Cross-border inheritance · Pension portability · Succession planning · Tax-efficient wrappers</p>
                </div>
            </div>

            <div className="space-y-3">

                <Accordion title="Cross-Border Inheritance Rules" summary="How your assets are taxed and distributed when you live abroad">
                    <div className="space-y-4">
                        <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4 space-y-2">
                            <p className="font-semibold text-slate-200">EU Succession Regulation (EU 650/2012)</p>
                            <p>Since 2015, EU citizens can elect for their <strong className="text-slate-300">home country's succession law</strong> to apply to their entire EU estate — regardless of where they live. Without an election, the law of your country of habitual residence applies.</p>
                            <Check>File a will or declaration explicitly electing your home country law</Check>
                            <Check>Particularly useful for Germans/French living in Spain or Portugal</Check>
                            <Note>Does not apply to the UK (post-Brexit) or Denmark</Note>
                        </div>
                        <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4 space-y-2">
                            <p className="font-semibold text-slate-200">Germany — Global Inheritance Tax Reach</p>
                            <p>Germany taxes inheritance on <strong className="text-slate-300">all worldwide assets</strong> if either the deceased or the heir is a German tax resident — even if the assets are held abroad. Tax-free allowances: €400k (spouse), €200k (children) per inheritance event.</p>
                            <Warn>German citizens who recently emigrated may still be caught for up to 5 years after leaving</Warn>
                        </div>
                        <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4 space-y-2">
                            <p className="font-semibold text-slate-200">UK — Domicile Matters More Than Residency</p>
                            <p>UK Inheritance Tax (40% above £325k nil-rate band) applies to your <strong className="text-slate-300">worldwide estate if you are UK domiciled</strong> — a concept that can persist even after emigration. Non-UK assets held by non-UK domiciled individuals are generally outside scope.</p>
                            <Check>Establishing non-UK domicile takes time and deliberate action</Check>
                            <Warn>Spouses of UK domiciliaries have a reduced spouse exemption (£325k cap)</Warn>
                        </div>
                        <div className="rounded-lg border border-amber-800/20 bg-amber-950/10 p-3">
                            <p className="text-xs text-amber-300/80">Always hold a will in every country where you own real estate or significant assets. Many countries require local wills even if you have a home-country will.</p>
                        </div>
                    </div>
                </Accordion>

                <Accordion title="Pension Portability" summary="QROPS, SIPP, and EU pension rules when you move countries">
                    <div className="space-y-4">
                        <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4 space-y-2">
                            <p className="font-semibold text-slate-200">QROPS — Qualifying Recognised Overseas Pension Scheme</p>
                            <p>Allows UK pension funds to be transferred to a recognised overseas scheme. Since 2017, the <strong className="text-slate-300">Overseas Transfer Charge (OTC) is 25%</strong> unless you are tax resident in the same country as the receiving QROPS.</p>
                            <Check>Still useful if: moving to Australia, NZ, or Malta with a Malta QROPS</Check>
                            <Check>Avoids UK's Lifetime Allowance (now abolished, but was £1.07m)</Check>
                            <Warn>Always check with a pension transfer specialist — HMRC rules change frequently</Warn>
                        </div>
                        <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4 space-y-2">
                            <p className="font-semibold text-slate-200">SIPP — Self-Invested Personal Pension</p>
                            <p>UK personal pension with full investment control. You can keep contributing to a SIPP for up to <strong className="text-slate-300">5 years after leaving the UK</strong> (capped at £3,600/year gross after UK tax residency ends).</p>
                            <Check>Best option if you plan to return to the UK eventually</Check>
                            <Check>Grows tax-free; 25% tax-free lump sum on drawdown (UK rules)</Check>
                            <Note>Foreign employers cannot contribute to UK SIPPs</Note>
                        </div>
                        <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-4 space-y-2">
                            <p className="font-semibold text-slate-200">EU State Pensions</p>
                            <p>EU social security coordination means years worked in multiple EU countries <strong className="text-slate-300">all count toward your pension entitlement</strong> in each country. You can claim partial pensions from each country where you've contributed.</p>
                            <Check>Request a record of contributions (PD U1 form) when leaving an EU country</Check>
                            <Check>Claim from each country separately at retirement age</Check>
                            <Warn>UAE, Georgia, Singapore have no state pension — build private portfolio instead</Warn>
                        </div>
                    </div>
                </Accordion>

                <Accordion title="Succession Planning" summary="Trusts, beneficiary nominations, and Power of Attorney across borders">
                    <div className="space-y-4">
                        <div className="space-y-3">
                            <div>
                                <p className="font-semibold text-slate-200 mb-1">Beneficiary Nominations</p>
                                <p>Pensions and life insurance policies pass <strong className="text-slate-300">outside your will</strong> via beneficiary nominations. These must be updated each time you move countries — the old nomination may be invalid under new jurisdiction rules.</p>
                                <div className="mt-2 space-y-1">
                                    <Check>Update pension beneficiary nominations after every country move</Check>
                                    <Check>Name contingent beneficiaries in case primary predeceases you</Check>
                                    <Warn>A nomination made in the UK may not be enforceable in Germany</Warn>
                                </div>
                            </div>
                            <div>
                                <p className="font-semibold text-slate-200 mb-1">Power of Attorney</p>
                                <p>A Power of Attorney (POA) granted in one country is generally <strong className="text-slate-300">not automatically valid in another</strong>. You typically need a separate POA per country where you hold assets.</p>
                                <div className="mt-2 space-y-1">
                                    <Check>Apostille certification makes a POA usable in Hague Convention countries</Check>
                                    <Check>Lasting POA (UK) / Vorsorgevollmacht (DE) must be drawn up before incapacity</Check>
                                </div>
                            </div>
                            <div>
                                <p className="font-semibold text-slate-200 mb-1">Family Investment Company (FIC)</p>
                                <p>A UK private limited company used to hold family assets and pass them to children tax-efficiently. Shares gifted to children use up annual CGT exemption and IHT annual allowance.</p>
                                <div className="mt-2 space-y-1">
                                    <Check>Popular with UK-connected high-net-worth individuals</Check>
                                    <Note>Requires ongoing corporation tax filings — not suitable for every situation</Note>
                                </div>
                            </div>
                        </div>
                    </div>
                </Accordion>

                <Accordion title="Tax-Efficient Pension Wrappers by Country" summary="Best pension vehicles in Germany, UK, UAE, and Portugal NHR">
                    <div className="space-y-3">
                        {[
                            {
                                country: "🇩🇪 Germany",
                                wrapper: "Rürup-Rente (Basisrente)",
                                desc: "Contributions are up to 100% tax-deductible (2026 onwards). Designed for self-employed and high earners. Not transferable, cannot be pledged as collateral. Taxed on drawdown (income tax rate at retirement).",
                                best: "Freelancers, self-employed, high earners in Germany",
                                caution: "Cannot be accessed before age 62. Not suitable as the only savings vehicle.",
                            },
                            {
                                country: "🇬🇧 UK",
                                wrapper: "ISA + SIPP combination",
                                desc: "ISA (£20k/year, all growth and income tax-free forever). SIPP (pension, tax relief on contributions, 25% tax-free lump sum). The two together are arguably the best retail tax shelter in Europe.",
                                best: "UK tax residents and returning expats",
                                caution: "ISA allowance does not carry over — use it or lose it each tax year (April 5th deadline).",
                            },
                            {
                                country: "🇦🇪 UAE",
                                wrapper: "Private portfolio (no state pension)",
                                desc: "UAE has no state pension system and no income tax. Build a private pension equivalent via a globally diversified portfolio at IBKR or similar. End-of-service gratuity from UAE employer is not a pension substitute.",
                                best: "High earners who want to accumulate aggressively",
                                caution: "No safety net if markets fall. Build 12-month emergency fund before investing aggressively.",
                            },
                            {
                                country: "🇵🇹 Portugal (NHR)",
                                wrapper: "10-year flat tax regime",
                                desc: "Non-Habitual Resident status applies 20% flat tax on Portuguese-source income and potentially 0% on qualifying foreign pension income under certain DTA treaties. New NHR2 (IFICI) from 2024 still applies to specific professions.",
                                best: "Retirees drawing pension income from non-Portuguese sources",
                                caution: "Rules are complex and depend on the double tax treaty with your pension source country. Get Portuguese tax advice before relocating.",
                            },
                        ].map((item) => (
                            <div key={item.country} className="rounded-lg border border-slate-700 bg-slate-900/40 p-4 space-y-2">
                                <div className="flex items-center justify-between flex-wrap gap-2">
                                    <p className="font-semibold text-slate-200">{item.country}</p>
                                    <span className="text-[11px] text-sky-400 bg-sky-900/30 border border-sky-700/30 rounded-full px-2 py-0.5">{item.wrapper}</span>
                                </div>
                                <p>{item.desc}</p>
                                <Check><strong className="text-slate-300">Best for:</strong> {item.best}</Check>
                                <Warn>{item.caution}</Warn>
                            </div>
                        ))}
                    </div>
                </Accordion>

            </div>

            <p className="text-xs text-slate-600 border-t border-slate-800 pt-4">
                This content is for educational purposes only and may be outdated. Estate and pension law changes frequently across jurisdictions.
                Not legal, tax, or financial advice. Always consult a qualified cross-border specialist for your specific situation.
            </p>
        </div>
    );
}
