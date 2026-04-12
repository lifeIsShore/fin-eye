"use client";
/**
 * app/lifestyle/page.tsx — Sprint 45
 * Lifestyle Finance hub: four content pillars for location-independent wealth management.
 */
import Link from "next/link";
import { Globe, Building2, CreditCard, ScrollText, ChevronRight } from "lucide-react";

const PILLARS = [
    {
        href: "/lifestyle/tax-residency",
        icon: <Globe className="h-6 w-6 text-sky-400" />,
        title: "Tax Residency",
        desc: "Compare income tax, capital gains, wealth tax, and crypto treatment across 10 jurisdictions. Find your optimal base.",
        tags: ["No-tax havens", "Territorial systems", "Crypto-friendly"],
        badge: "Interactive table",
    },
    {
        href: "/lifestyle/legal-structures",
        icon: <Building2 className="h-6 w-6 text-violet-400" />,
        title: "Legal Structures",
        desc: "Compare 9 entity types (LTD, GmbH, LLC, holding, trust…) with an interactive quiz to find the best fit for your situation.",
        tags: ["Asset protection", "Tax optimisation", "Privacy"],
        badge: "Quiz included",
    },
    {
        href: "/lifestyle/banking",
        icon: <CreditCard className="h-6 w-6 text-emerald-400" />,
        title: "International Banking",
        desc: "Multi-currency accounts, SEPA vs SWIFT, FATCA exposure, and which banks work best for non-residents.",
        tags: ["FATCA", "Multi-currency", "Non-resident"],
        badge: "Coming soon",
        disabled: true,
    },
    {
        href: "/lifestyle/estate",
        icon: <ScrollText className="h-6 w-6 text-amber-400" />,
        title: "Estate & Pension",
        desc: "Cross-border inheritance rules, pension portability (QROPS, SIPP), and succession planning for international investors.",
        tags: ["Inheritance", "QROPS", "Succession"],
        badge: "Coming soon",
        disabled: true,
    },
];

export default function LifestylePage() {
    return (
        <div className="mx-auto max-w-3xl space-y-8">
            <div>
                <h1 className="text-xl font-semibold tracking-tight">Lifestyle Finance</h1>
                <p className="mt-1 text-sm text-slate-400">
                    Tools and guides for location-independent wealth management — tax residency,
                    legal structures, international banking, and estate planning.
                </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
                {PILLARS.map((p) => (
                    <div key={p.href} className={p.disabled ? "opacity-50 cursor-not-allowed" : ""}>
                        <Link
                            href={p.disabled ? "#" : p.href}
                            onClick={p.disabled ? (e) => e.preventDefault() : undefined}
                            className="flex flex-col h-full rounded-xl border border-slate-800 bg-slate-900/50 p-5 hover:border-slate-600 hover:bg-slate-900 transition-all group"
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-800">
                                    {p.icon}
                                </div>
                                <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                                    p.disabled
                                        ? "bg-slate-800 text-slate-500"
                                        : "bg-sky-900/40 text-sky-400 border border-sky-700/30"
                                }`}>
                                    {p.badge}
                                </span>
                            </div>
                            <h2 className="text-sm font-semibold text-slate-100 mb-1.5">{p.title}</h2>
                            <p className="text-xs text-slate-400 leading-relaxed flex-1">{p.desc}</p>
                            <div className="flex flex-wrap gap-1.5 mt-3">
                                {p.tags.map((t) => (
                                    <span key={t} className="text-[10px] text-slate-500 bg-slate-800 rounded-full px-2 py-0.5">{t}</span>
                                ))}
                            </div>
                            {!p.disabled && (
                                <div className="flex items-center gap-1 mt-4 text-xs text-sky-400 group-hover:gap-2 transition-all">
                                    Explore <ChevronRight className="h-3.5 w-3.5" />
                                </div>
                            )}
                        </Link>
                    </div>
                ))}
            </div>

            <p className="text-xs text-slate-600 border-t border-slate-800 pt-4">
                This content is for educational purposes only and does not constitute legal, tax,
                or financial advice. Always consult qualified professionals for your specific situation.
            </p>
        </div>
    );
}
