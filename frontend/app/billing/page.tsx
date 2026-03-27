"use client";

/**
 * /billing — Sprint 29 redesign
 *
 * - Monthly / Annual toggle with "Save €48/year" incentive
 * - Full feature comparison table (Free vs Pro vs Institutional)
 * - "Most Popular" badge on Pro
 * - Clear CTA states (current plan, upgrade, contact sales)
 * - Payments not yet live — Coming Soon badge preserved
 */

import { useState, useEffect } from "react";
import { useAuth } from "@/components/AuthProvider";
import Link from "next/link";
import {
  Check, X, Zap, Building2, CreditCard, Shield,
  TrendingUp, BarChart2, Bell, Users, Globe,
  Lock, Star, Receipt, PauseCircle,
} from "lucide-react";

// ── Plan data ─────────────────────────────────────────────────────────────────

interface Plan {
  id: "free" | "pro" | "institutional";
  name: string;
  monthlyPrice: number | null;  // null = custom
  annualPrice: number | null;
  annualSaving?: number;
  description: string;
  badge?: string;
  badgeColor?: string;
  cta: string;
  ctaStyle: "current" | "primary" | "secondary";
  highlight: boolean;
}

const PLANS: Plan[] = [
  {
    id: "free",
    name: "Free",
    monthlyPrice: 0,
    annualPrice: 0,
    description: "Core market intelligence to get started.",
    cta: "Current Plan",
    ctaStyle: "current",
    highlight: false,
  },
  {
    id: "pro",
    name: "Pro",
    monthlyPrice: 14.99,
    annualPrice: 119.99,
    annualSaving: 59.89,
    description: "Full access for active retail traders.",
    badge: "Most Popular",
    badgeColor: "bg-blue-600 text-white border-blue-500/50",
    cta: "Upgrade to Pro",
    ctaStyle: "primary",
    highlight: true,
  },
  {
    id: "institutional",
    name: "Institutional",
    monthlyPrice: null,
    annualPrice: null,
    description: "For professional desks and advisory firms.",
    badge: "Enterprise",
    badgeColor: "bg-slate-800 text-slate-300 border-slate-600",
    cta: "Contact Sales",
    ctaStyle: "secondary",
    highlight: false,
  },
];

// ── Feature matrix ────────────────────────────────────────────────────────────

interface Feature {
  category: string;
  name: string;
  free: boolean | string;
  pro: boolean | string;
  institutional: boolean | string;
  tooltip?: string;
}

const FEATURES: Feature[] = [
  // Dashboard
  { category: "Dashboard", name: "GAS Score & Market Weather", free: true, pro: true, institutional: true },
  { category: "Dashboard", name: "Multi-timeframe agreement banner", free: true, pro: true, institutional: true },
  { category: "Dashboard", name: "7-day GAS sparkline", free: true, pro: true, institutional: true },
  { category: "Dashboard", name: "Regime change notifications", free: true, pro: true, institutional: true },
  { category: "Dashboard", name: "LLM investment manager insight", free: "3/day", pro: "Unlimited", institutional: "Unlimited" },
  // Signals
  { category: "Signals", name: "Technical ML consensus (all timeframes)", free: true, pro: true, institutional: true },
  { category: "Signals", name: "Signal grade (A+→F) with explanation", free: true, pro: true, institutional: true },
  { category: "Signals", name: "SHAP feature importance panel", free: true, pro: true, institutional: true },
  { category: "Signals", name: "Model drift alerts", free: false, pro: true, institutional: true },
  // Macro
  { category: "Macro", name: "Core macro indicators (FRED)", free: true, pro: true, institutional: true },
  { category: "Macro", name: "Advanced macro dashboard", free: false, pro: true, institutional: true },
  { category: "Macro", name: "Yield curve inversion alert", free: true, pro: true, institutional: true },
  { category: "Macro", name: "Economic calendar (2-week)", free: true, pro: true, institutional: true },
  // Sentiment
  { category: "Sentiment", name: "FinBERT news sentiment", free: "30 articles", pro: "Unlimited", institutional: "Unlimited" },
  { category: "Sentiment", name: "Source tier breakdown", free: false, pro: true, institutional: true },
  { category: "Sentiment", name: "Keyword cloud & topic clusters", free: false, pro: true, institutional: true },
  { category: "Sentiment", name: "Retail mood (StockTwits)", free: false, pro: true, institutional: true },
  // Portfolio & Watchlist
  { category: "Portfolio & Watchlist", name: "Watchlist symbols", free: "5", pro: "50", institutional: "Unlimited" },
  { category: "Portfolio & Watchlist", name: "Watchlist grade filter", free: true, pro: true, institutional: true },
  { category: "Portfolio & Watchlist", name: "Portfolio tracking", free: "1 portfolio", pro: "10 portfolios", institutional: "Unlimited" },
  { category: "Portfolio & Watchlist", name: "AI portfolio allocator", free: false, pro: true, institutional: true },
  { category: "Portfolio & Watchlist", name: "Correlation heatmap", free: false, pro: true, institutional: true },
  // Backtesting
  { category: "Backtesting", name: "Backtests per month", free: "5", pro: "Unlimited", institutional: "Unlimited" },
  { category: "Backtesting", name: "Strategy templates", free: "1", pro: "All 3", institutional: "All 3 + custom" },
  { category: "Backtesting", name: "Walk-forward validation", free: false, pro: true, institutional: true },
  { category: "Backtesting", name: "Trade log export (CSV)", free: false, pro: true, institutional: true },
  // Alerts
  { category: "Alerts", name: "GAS threshold alerts", free: "2", pro: "Unlimited", institutional: "Unlimited" },
  { category: "Alerts", name: "Email alert delivery", free: true, pro: true, institutional: true },
  { category: "Alerts", name: "Grade rebalancing alerts", free: false, pro: true, institutional: true },
  // Enterprise
  { category: "Enterprise", name: "Public API access", free: false, pro: false, institutional: true },
  { category: "Enterprise", name: "Bulk ticker analysis (50+)", free: false, pro: false, institutional: true },
  { category: "Enterprise", name: "White-label dashboard", free: false, pro: false, institutional: true },
  { category: "Enterprise", name: "Dedicated support", free: false, pro: false, institutional: true },
];

const CATEGORIES = [...new Set(FEATURES.map((f) => f.category))];

// ── Sub-components ────────────────────────────────────────────────────────────

function FeatureCell({ value }: { value: boolean | string }) {
  if (value === true)  return <Check className="h-4 w-4 text-emerald-400 mx-auto" />;
  if (value === false) return <X className="h-3.5 w-3.5 text-slate-700 mx-auto" />;
  return <span className="text-xs text-sky-400 font-medium">{value}</span>;
}

function PriceDisplay({
  plan,
  annual,
}: {
  plan: Plan;
  annual: boolean;
}) {
  if (plan.monthlyPrice === null) {
    return (
      <div className="mt-2">
        <span className="text-3xl font-bold text-slate-50">Custom</span>
      </div>
    );
  }

  const displayPrice = annual ? (plan.annualPrice! / 12) : plan.monthlyPrice;

  return (
    <div className="mt-2">
      <div className="flex items-baseline gap-1">
        <span className="text-3xl font-bold text-slate-50">
          €{displayPrice === 0 ? "0" : displayPrice.toFixed(2)}
        </span>
        <span className="text-sm text-slate-500">/ month</span>
      </div>
      {annual && plan.annualPrice !== null && plan.annualPrice > 0 && (
        <p className="text-[11px] text-slate-500 mt-0.5">
          Billed annually · €{plan.annualPrice.toFixed(2)}/yr
        </p>
      )}
      {!annual && plan.monthlyPrice === 0 && (
        <p className="text-[11px] text-slate-500 mt-0.5">No credit card required</p>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const { user } = useAuth();
  const [annual, setAnnual] = useState(false);
  const [trialLoading, setTrialLoading] = useState(false);
  const [trialMessage, setTrialMessage] = useState<string | null>(null);

  const currentPlanId: "free" | "pro" | "institutional" = user?.is_pro ? "pro" : "free";

  // Compute trial state
  const trialEnd = user?.trial_ends_at ? new Date(user.trial_ends_at) : null;
  const trialActive = trialEnd && trialEnd > new Date();
  const trialDaysLeft = trialActive
    ? Math.ceil((trialEnd!.getTime() - Date.now()) / 86_400_000)
    : 0;
  const neverTrialed = !user?.trial_ends_at;

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  const startTrial = async () => {
    setTrialLoading(true);
    setTrialMessage(null);
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch(`${API_BASE}/api/v1/billing/start-trial`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      const data = await res.json();
      setTrialMessage(data.message ?? "Trial started!");
    } catch {
      setTrialMessage("Something went wrong. Please try again.");
    } finally {
      setTrialLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-10">

      {/* Trial banner */}
      {trialActive && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-700/40 bg-amber-950/20 px-5 py-4">
          <Zap className="h-4 w-4 text-amber-400 flex-shrink-0" />
          <p className="text-sm text-amber-300">
            <strong>Free trial active</strong> — {trialDaysLeft} day{trialDaysLeft !== 1 ? "s" : ""} remaining.
            {" "}
            <Link href="#plans" className="underline hover:text-amber-200">Upgrade to keep Pro access.</Link>
          </p>
        </div>
      )}

      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold text-slate-100">Plans & Pricing</h1>
        <p className="text-sm text-slate-400">
          Choose the plan that fits your workflow. Payments are not yet live.
        </p>
      </div>

      {/* Billing toggle */}
      <div className="flex items-center justify-center gap-3">
        <span className={`text-sm font-medium ${!annual ? "text-slate-200" : "text-slate-500"}`}>
          Monthly
        </span>
        <button
          onClick={() => setAnnual((v) => !v)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            annual ? "bg-blue-600" : "bg-slate-700"
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              annual ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
        <span className={`text-sm font-medium ${annual ? "text-slate-200" : "text-slate-500"}`}>
          Annual
        </span>
        {annual && (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-700/50 bg-emerald-950/40 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
            <Star className="h-3 w-3" />
            Save €59.89/year
          </span>
        )}
      </div>

      {/* Plan cards */}
      <div className="grid gap-5 md:grid-cols-3">
        {PLANS.map((plan) => {
          const isCurrent = plan.id === currentPlanId;

          return (
            <div
              key={plan.id}
              className={`relative flex flex-col rounded-2xl border p-6 ${
                plan.highlight
                  ? "border-blue-500/50 bg-blue-950/15 shadow-lg shadow-blue-950/20"
                  : "border-slate-800 bg-slate-900/50"
              }`}
            >
              {/* Badge */}
              {plan.badge && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className={`flex items-center gap-1.5 rounded-full border px-3 py-0.5 text-xs font-semibold ${plan.badgeColor}`}>
                    {plan.id === "pro" ? <Zap className="h-3 w-3" /> : <Building2 className="h-3 w-3" />}
                    {plan.badge}
                  </span>
                </div>
              )}

              {/* Plan name + price */}
              <div className="mb-5">
                <p className="text-base font-semibold text-slate-100">{plan.name}</p>
                <PriceDisplay plan={plan} annual={annual} />
                <p className="mt-2 text-xs text-slate-500">{plan.description}</p>
              </div>

              {/* Key features (top 6) */}
              <ul className="mb-6 flex-1 space-y-2.5">
                {FEATURES.filter((f) => {
                  const val = f[plan.id];
                  return val !== false;
                }).slice(0, 7).map((f) => (
                  <li key={f.name} className="flex items-start gap-2 text-xs text-slate-300">
                    <Check className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-400" />
                    <span>
                      {f.name}
                      {typeof f[plan.id] === "string" && f[plan.id] !== "true" && (
                        <span className="ml-1 text-sky-400 font-medium">({f[plan.id]})</span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <div className="space-y-2">
                {isCurrent ? (
                  <>
                    <button
                      disabled
                      className="w-full rounded-xl border border-slate-700 bg-slate-800 py-2.5 text-sm font-semibold text-slate-400 opacity-70 cursor-not-allowed"
                    >
                      ✓ Current Plan
                    </button>
                    <p className="text-center text-[10px] text-slate-600">You are on this plan</p>
                  </>
                ) : plan.id === "pro" && !user?.is_pro && neverTrialed ? (
                  <>
                    <button
                      onClick={startTrial}
                      disabled={trialLoading}
                      className="w-full rounded-xl bg-blue-600 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
                    >
                      {trialLoading ? "Starting trial…" : "Start free 7-day trial"}
                    </button>
                    {trialMessage && (
                      <p className="text-center text-[11px] text-emerald-400">{trialMessage}</p>
                    )}
                    {!trialMessage && (
                      <p className="text-center text-[10px] text-slate-600">No credit card required</p>
                    )}
                  </>
                ) : (
                  <>
                    <button
                      disabled
                      className={`w-full rounded-xl py-2.5 text-sm font-semibold cursor-not-allowed ${
                        plan.ctaStyle === "primary"
                          ? "bg-blue-600 text-white opacity-60"
                          : "border border-slate-700 bg-slate-800 text-slate-300 opacity-60"
                      }`}
                    >
                      {plan.cta}
                    </button>
                    <p className="text-center text-[10px] text-slate-600">Payments coming soon</p>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Annual savings callout */}
      {!annual && (
        <div
          className="flex items-center justify-between rounded-xl border border-emerald-800/30 bg-emerald-950/15 px-5 py-4 cursor-pointer hover:border-emerald-700/50 transition-colors"
          onClick={() => setAnnual(true)}
        >
          <div className="flex items-center gap-3">
            <Star className="h-5 w-5 text-emerald-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-emerald-300">Switch to annual and save €59.89/year</p>
              <p className="text-xs text-slate-500">Pro plan: €14.99/mo → €9.99/mo billed annually</p>
            </div>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); setAnnual(true); }}
            className="flex-shrink-0 rounded-lg border border-emerald-700/50 bg-emerald-900/30 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-900/50 transition-colors"
          >
            Switch to annual
          </button>
        </div>
      )}

      {/* Feature comparison table */}
      <div className="rounded-2xl border border-slate-800 overflow-hidden">
        <div className="bg-slate-900/60 px-6 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-slate-200">Full feature comparison</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/40">
                <th className="px-6 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider w-1/2">
                  Feature
                </th>
                {PLANS.map((p) => (
                  <th
                    key={p.id}
                    className={`px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider w-[16.6%] ${
                      p.highlight ? "text-blue-400" : "text-slate-500"
                    }`}
                  >
                    {p.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {CATEGORIES.map((cat) => {
                const catFeatures = FEATURES.filter((f) => f.category === cat);
                return [
                  // Category header row
                  <tr key={`cat-${cat}`} className="bg-slate-900/30">
                    <td
                      colSpan={4}
                      className="px-6 py-2 text-[10px] font-bold uppercase tracking-widest text-slate-600"
                    >
                      {cat}
                    </td>
                  </tr>,
                  // Feature rows
                  ...catFeatures.map((f) => (
                    <tr key={f.name} className="hover:bg-slate-900/20 transition-colors">
                      <td className="px-6 py-2.5 text-xs text-slate-400">{f.name}</td>
                      <td className="px-4 py-2.5 text-center">
                        <FeatureCell value={f.free} />
                      </td>
                      <td className={`px-4 py-2.5 text-center ${currentPlanId === "pro" ? "bg-blue-950/10" : ""}`}>
                        <FeatureCell value={f.pro} />
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <FeatureCell value={f.institutional} />
                      </td>
                    </tr>
                  )),
                ];
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trust signals */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { icon: Shield, title: "Stripe-powered payments", body: "Card details never touch our servers. All transactions via Stripe." },
          { icon: TrendingUp, title: "Cancel anytime", body: "No lock-in. Cancel at any time and keep access until period end." },
          { icon: Lock, title: "Your data, your control", body: "Full GDPR data export and account deletion available in Settings." },
        ].map(({ icon: Icon, title, body }) => (
          <div key={title} className="flex gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
            <Icon className="h-5 w-5 text-sky-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-semibold text-slate-200">{title}</p>
              <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{body}</p>
            </div>
          </div>
        ))}
      </div>

      {/* FAQ */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
        <h3 className="text-sm font-semibold text-slate-200">Frequently Asked Questions</h3>
        <div className="divide-y divide-slate-800/60">
          {[
            ["Can I cancel anytime?", "Yes — cancel at any time. You retain Pro access until the end of your billing period with no partial refunds on annual plans."],
            ["Is there a free trial?", "A 7-day free trial for Pro is coming soon. You'll be able to try all Pro features with no credit card required."],
            ["What happens to my data if I downgrade?", "Your portfolios, watchlists, and backtests remain saved. Access reverts to Free tier limits — nothing is deleted."],
            ["What payment methods are accepted?", "All major credit and debit cards via Stripe. EU invoices available for business accounts on the Institutional plan."],
            ["Is this GDPR compliant?", "Yes — Fin-Eye is built with EU users in mind. Full data export and account deletion are available in Settings at any time."],
          ].map(([q, a]) => (
            <div key={q as string} className="py-3 first:pt-0 last:pb-0">
              <p className="text-xs font-semibold text-slate-300">{q}</p>
              <p className="mt-1 text-xs text-slate-500 leading-relaxed">{a}</p>
            </div>
          ))}
        </div>
      </div>
      {/* Invoices */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Receipt className="h-4 w-4 text-slate-500" />
          <h3 className="text-sm font-semibold text-slate-200">Invoices</h3>
        </div>
        <p className="text-xs text-slate-500">
          No invoices yet — invoices will appear here after your first payment.
        </p>
      </div>

      {/* Cancel subscription */}
      {(user?.is_pro || trialActive) && (
        <div className="text-center">
          <Link
            href="/billing/cancel"
            className="text-xs text-slate-600 hover:text-rose-400 transition-colors underline"
          >
            Cancel or pause subscription
          </Link>
        </div>
      )}

    </div>
  );
}
