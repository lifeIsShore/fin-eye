"use client";

import { useAuth } from "@/components/AuthProvider";
import { Check, Construction, CreditCard, Zap, Building2 } from "lucide-react";

function ComingSoonBadge() {
    return (
        <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-950/40 px-2 py-0.5 text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
            <Construction className="h-2.5 w-2.5" />
            Coming Soon
        </span>
    );
}

const PLANS = [
    {
        id: "free",
        name: "Free",
        price: "$0",
        period: "forever",
        description: "Explore the platform with core features.",
        features: [
            "Dashboard with GAS & Market Weather",
            "Macro indicator panel",
            "News & Sentiment (limited)",
            "5 backtests / month",
            "Educational blog",
        ],
        cta: "Current Plan",
        highlight: false,
    },
    {
        id: "pro",
        name: "Pro",
        price: "$29",
        period: "/ month",
        description: "Full access for active retail traders.",
        features: [
            "Everything in Free",
            "Unlimited backtests & strategies",
            "Reddit retail sentiment",
            "Portfolio watchlist (up to 10 stocks)",
            "GAS threshold & regime alerts",
            "Priority data refresh",
        ],
        cta: "Upgrade to Pro",
        highlight: true,
    },
    {
        id: "institutional",
        name: "Institutional",
        price: "Custom",
        period: "",
        description: "For professional desks and advisory firms.",
        features: [
            "Everything in Pro",
            "Public API access",
            "Bulk ticker analysis (50+)",
            "White-label dashboard",
            "PDF / Excel report generation",
            "Dedicated support",
        ],
        cta: "Contact Sales",
        highlight: false,
    },
];

export default function BillingPage() {
    const { user } = useAuth();
    const currentPlan = user?.is_pro ? "pro" : "free";

    return (
        <div className="mx-auto max-w-4xl space-y-8">
            <div>
                <h2 className="text-xl font-semibold tracking-tight">Billing &amp; Plans</h2>
                <p className="mt-1 text-sm text-slate-400">
                    Choose the plan that fits your workflow. Payments are not yet live.
                </p>
            </div>

            {/* Current plan banner */}
            <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/50 px-5 py-4">
                <div className="flex items-center gap-3">
                    <CreditCard className="h-5 w-5 text-slate-400" />
                    <div>
                        <p className="text-sm font-medium text-slate-200">
                            Current plan: <span className="text-blue-400 capitalize">{currentPlan}</span>
                        </p>
                        <p className="text-xs text-slate-500">
                            {currentPlan === "pro"
                                ? "Your Pro plan renews monthly."
                                : "Upgrade to unlock all features."}
                        </p>
                    </div>
                </div>
                <ComingSoonBadge />
            </div>

            {/* Plan cards */}
            <div className="grid gap-5 md:grid-cols-3">
                {PLANS.map((plan) => {
                    const isCurrent = plan.id === currentPlan;
                    return (
                        <div
                            key={plan.id}
                            className={`relative flex flex-col rounded-xl border p-6 ${
                                plan.highlight
                                    ? "border-blue-500/50 bg-blue-950/20"
                                    : "border-slate-800 bg-slate-900/50"
                            }`}
                        >
                            {plan.highlight && (
                                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                                    <span className="flex items-center gap-1 rounded-full border border-blue-500/50 bg-blue-600 px-3 py-0.5 text-xs font-semibold text-white">
                                        <Zap className="h-3 w-3" />
                                        Most Popular
                                    </span>
                                </div>
                            )}

                            {plan.id === "institutional" && (
                                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                                    <span className="flex items-center gap-1 rounded-full border border-slate-600 bg-slate-800 px-3 py-0.5 text-xs font-semibold text-slate-300">
                                        <Building2 className="h-3 w-3" />
                                        Enterprise
                                    </span>
                                </div>
                            )}

                            <div className="mb-4">
                                <p className="text-base font-semibold text-slate-100">{plan.name}</p>
                                <div className="mt-1 flex items-baseline gap-1">
                                    <span className="text-3xl font-bold text-slate-50">{plan.price}</span>
                                    {plan.period && (
                                        <span className="text-sm text-slate-500">{plan.period}</span>
                                    )}
                                </div>
                                <p className="mt-2 text-xs text-slate-400">{plan.description}</p>
                            </div>

                            <ul className="mb-6 flex-1 space-y-2">
                                {plan.features.map((f) => (
                                    <li key={f} className="flex items-start gap-2 text-xs text-slate-300">
                                        <Check className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-400" />
                                        {f}
                                    </li>
                                ))}
                            </ul>

                            <button
                                disabled
                                className={`w-full rounded-lg py-2.5 text-sm font-semibold transition-colors cursor-not-allowed opacity-60 ${
                                    isCurrent
                                        ? "border border-slate-700 bg-slate-800 text-slate-400"
                                        : plan.highlight
                                        ? "bg-blue-600 text-white"
                                        : "border border-slate-700 bg-slate-800 text-slate-300"
                                }`}
                            >
                                {isCurrent ? "✓ Current Plan" : plan.cta}
                            </button>

                            <p className="mt-2 text-center text-[10px] text-slate-600">
                                {isCurrent ? "You are on this plan" : "Payments coming soon"}
                            </p>
                        </div>
                    );
                })}
            </div>

            {/* FAQ stub */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
                <h3 className="mb-4 text-sm font-semibold text-slate-200">Frequently Asked Questions</h3>
                <div className="space-y-4 text-sm text-slate-400">
                    {[
                        ["Can I cancel anytime?", "Yes — you can cancel your subscription at any time. You'll retain Pro access until the end of your billing period."],
                        ["Is my payment data safe?", "Payments will be processed via Stripe. Fin-Eye never stores card details."],
                        ["What happens to my data if I cancel?", "Your saved portfolios and watchlists remain accessible on the Free plan, within Free tier limits."],
                    ].map(([q, a]) => (
                        <div key={q}>
                            <p className="font-medium text-slate-300">{q}</p>
                            <p className="mt-1 text-slate-500">{a}</p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
