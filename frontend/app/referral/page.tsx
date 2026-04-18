"use client";

/**
 * /referral — Sprint 50
 * Referral Program: invite friends, earn free Pro months.
 */

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/components/AuthProvider";
import Link from "next/link";
import {
  Gift, Copy, Check, Twitter, Mail, Share2,
  Users, Trophy, ArrowRight, Zap, Star, ExternalLink,
} from "lucide-react";
import {
  fetchReferralStats,
  fetchReferralLeaderboard,
  type ReferralStatsDto,
  type ReferralLeaderEntry,
} from "@/lib/api";

// ── Whatsapp share helper ─────────────────────────────────────────────────────
function waUrl(link: string) {
  return `https://wa.me/?text=${encodeURIComponent(
    `I've been using Fin-Eye to track market signals — check it out! ${link}`
  )}`;
}

function xUrl(link: string) {
  return `https://twitter.com/intent/tweet?text=${encodeURIComponent(
    "I've been using Fin-Eye for institutional-grade market intelligence. Try it free:"
  )}&url=${encodeURIComponent(link)}`;
}

function mailUrl(link: string) {
  return `mailto:?subject=${encodeURIComponent(
    "You should try Fin-Eye"
  )}&body=${encodeURIComponent(
    `Hey,\n\nI've been using Fin-Eye to track GAS scores, macro signals, and ML-based market analysis.\n\nSign up with my link and we both benefit:\n${link}\n\nCheers`
  )}`;
}

// ── How it works steps ────────────────────────────────────────────────────────
const STEPS = [
  {
    icon: <Share2 className="h-5 w-5 text-sky-400" />,
    title: "Share your link",
    body: "Copy your unique referral link and share it with friends, colleagues, or on social media.",
  },
  {
    icon: <Users className="h-5 w-5 text-emerald-400" />,
    title: "Friend signs up",
    body: "When they register using your link, they're automatically linked to your referral.",
  },
  {
    icon: <Zap className="h-5 w-5 text-amber-400" />,
    title: "You earn a free month",
    body: "Each time a referred friend upgrades to Pro, you earn 1 free month — automatically applied.",
  },
];

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ReferralPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<ReferralStatsDto | null>(null);
  const [leaderboard, setLeaderboard] = useState<ReferralLeaderEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const [s, lb] = await Promise.all([
        fetchReferralStats(),
        fetchReferralLeaderboard(),
      ]);
      setStats(s);
      setLeaderboard(lb);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  const handleCopy = async () => {
    if (!stats?.link) return;
    await navigator.clipboard.writeText(stats.link);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Unauthenticated state ─────────────────────────────────────────────────

  if (!user) {
    return (
      <div className="mx-auto max-w-lg py-20 text-center space-y-4">
        <Gift className="mx-auto h-10 w-10 text-emerald-400" />
        <h1 className="text-xl font-bold text-slate-100">Invite friends, earn free Pro</h1>
        <p className="text-sm text-slate-400">
          Sign in to get your unique referral link and start earning free months.
        </p>
        <Link
          href="/login"
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 transition-colors"
        >
          Sign in <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-10">

      {/* Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center gap-2 rounded-full border border-emerald-700/50 bg-emerald-950/30 px-3 py-1 text-xs font-semibold text-emerald-400 mb-2">
          <Gift className="h-3.5 w-3.5" /> Referral Program
        </div>
        <h1 className="text-2xl font-bold text-slate-100">Invite friends, earn free Pro</h1>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          Share your unique link. Every time a friend upgrades to Pro, you get 1 month free — automatically.
        </p>
      </div>

      {/* How it works */}
      <div className="grid gap-4 sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <div key={i} className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 bg-slate-800">
              {step.icon}
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-100">{step.title}</p>
              <p className="mt-1 text-xs text-slate-400 leading-relaxed">{step.body}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Referral link box */}
      <div className="rounded-2xl border border-slate-700 bg-slate-900/60 p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200">Your referral link</h2>

        {loading ? (
          <div className="h-11 animate-pulse rounded-xl bg-slate-800" />
        ) : error ? (
          <p className="text-xs text-rose-400">{error}</p>
        ) : stats ? (
          <>
            {/* Link row */}
            <div className="flex items-center gap-2">
              <div className="flex-1 rounded-xl border border-slate-700 bg-slate-800 px-3 py-2.5">
                <p className="truncate text-sm text-slate-300 font-mono">{stats.link}</p>
              </div>
              <button
                onClick={handleCopy}
                className={`flex items-center gap-1.5 rounded-xl border px-4 py-2.5 text-sm font-semibold transition-colors flex-shrink-0 ${
                  copied
                    ? "border-emerald-600/50 bg-emerald-900/30 text-emerald-400"
                    : "border-slate-600 bg-slate-800 text-slate-200 hover:border-slate-500 hover:bg-slate-700"
                }`}
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? "Copied!" : "Copy"}
              </button>
            </div>

            {/* Share buttons */}
            <div className="flex flex-wrap gap-2">
              <a
                href={xUrl(stats.link)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-300 hover:border-slate-600 hover:text-slate-100 transition-colors"
              >
                <Twitter className="h-3.5 w-3.5" /> Share on X
              </a>
              <a
                href={waUrl(stats.link)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-300 hover:border-slate-600 hover:text-slate-100 transition-colors"
              >
                💬 WhatsApp
              </a>
              <a
                href={mailUrl(stats.link)}
                className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-300 hover:border-slate-600 hover:text-slate-100 transition-colors"
              >
                <Mail className="h-3.5 w-3.5" /> Email
              </a>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-3 pt-2 border-t border-slate-800">
              {[
                { label: "Friends signed up", value: stats.signups, icon: <Users className="h-4 w-4 text-sky-400" /> },
                { label: "Upgraded to Pro",   value: stats.upgrades, icon: <Zap className="h-4 w-4 text-amber-400" /> },
                { label: "Free months earned", value: stats.credits_earned, icon: <Star className="h-4 w-4 text-emerald-400" /> },
              ].map(({ label, value, icon }) => (
                <div key={label} className="flex flex-col items-center gap-1 py-2">
                  {icon}
                  <p className="text-xl font-bold text-slate-100">{value}</p>
                  <p className="text-[10px] text-slate-500 text-center leading-tight">{label}</p>
                </div>
              ))}
            </div>
          </>
        ) : null}
      </div>

      {/* Leaderboard */}
      {leaderboard.length > 0 && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 overflow-hidden">
          <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-900/60 px-5 py-4">
            <Trophy className="h-4 w-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-200">Top referrers</h2>
            <span className="text-xs text-slate-500">(anonymised)</span>
          </div>
          <ul className="divide-y divide-slate-800/40">
            {leaderboard.map((entry) => (
              <li key={entry.rank} className="flex items-center gap-4 px-5 py-3">
                <span className={`text-sm font-bold w-6 text-center ${
                  entry.rank === 1 ? "text-amber-400" :
                  entry.rank === 2 ? "text-slate-300" :
                  entry.rank === 3 ? "text-amber-700" :
                  "text-slate-600"
                }`}>
                  {entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : `#${entry.rank}`}
                </span>
                <span className="flex-1 text-sm text-slate-300 font-mono">{entry.display_name}</span>
                <span className="text-sm font-semibold text-sky-400">{entry.referrals} referral{entry.referrals !== 1 ? "s" : ""}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Upgrade nudge for free users */}
      {!user.is_pro && (
        <div className="flex items-center justify-between rounded-xl border border-blue-700/30 bg-blue-950/15 px-5 py-4">
          <div className="flex items-center gap-3">
            <Zap className="h-5 w-5 text-blue-400 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-blue-300">Want Pro now?</p>
              <p className="text-xs text-slate-500">Or keep referring — earn your way there for free.</p>
            </div>
          </div>
          <Link
            href="/billing"
            className="flex-shrink-0 flex items-center gap-1.5 rounded-lg border border-blue-600/50 bg-blue-900/30 px-3 py-1.5 text-xs font-semibold text-blue-300 hover:bg-blue-900/50 transition-colors"
          >
            View plans <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      )}

    </div>
  );
}
