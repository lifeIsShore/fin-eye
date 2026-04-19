"use client";
/**
 * WeeklyPoll.tsx — Sprint 52
 * Bull vs Bear weekly SPY sentiment poll.
 * Shows Mon–Fri (or whenever the user hasn't voted yet).
 * Place in dashboard sidebar above <EarningsCalendarStrip />.
 */
import { useState, useEffect } from "react";
import { fetchCurrentPoll, castPollVote, type PollDto } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

function DonutChart({ bullish, bearish, neutral, total }: {
  bullish: number; bearish: number; neutral: number; total: number;
}) {
  if (total === 0) return null;
  const r = 36, cx = 44, cy = 44, circumference = 2 * Math.PI * r;
  const pctBull = bullish / total;
  const pctBear = bearish / total;
  const pctNeut = neutral / total;

  const dashBull = circumference * pctBull;
  const dashBear = circumference * pctBear;
  const dashNeut = circumference * pctNeut;

  const offsetBull = 0;
  const offsetBear = circumference - dashBull;
  const offsetNeut = circumference - dashBull - dashBear;

  return (
    <svg width="88" height="88" viewBox="0 0 88 88">
      {/* Neutral */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f59e0b" strokeWidth="10"
        strokeDasharray={`${dashNeut} ${circumference - dashNeut}`}
        strokeDashoffset={-offsetNeut} transform="rotate(-90 44 44)" />
      {/* Bearish */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f43f5e" strokeWidth="10"
        strokeDasharray={`${dashBear} ${circumference - dashBear}`}
        strokeDashoffset={-offsetBear} transform="rotate(-90 44 44)" />
      {/* Bullish */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#10b981" strokeWidth="10"
        strokeDasharray={`${dashBull} ${circumference - dashBull}`}
        strokeDashoffset={-offsetBull} transform="rotate(-90 44 44)" />
      <text x={cx} y={cy + 5} textAnchor="middle" fontSize="11" fill="#e2e8f0" fontWeight="600">
        {total}
      </text>
    </svg>
  );
}

export default function WeeklyPoll() {
  const { user } = useAuth();
  const [poll, setPoll] = useState<PollDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [voting, setVoting] = useState(false);

  // Only show Mon–Fri
  const day = new Date().getDay();
  const isWeekday = day >= 1 && day <= 5;

  useEffect(() => {
    fetchCurrentPoll()
      .then(setPoll)
      .catch(() => setPoll(null))
      .finally(() => setLoading(false));
  }, []);

  // Hide on weekends if user has already voted
  if (!isWeekday && poll?.user_vote) return null;
  if (loading) return null;
  if (!poll) return null;

  const { results } = poll;
  const total = results.total;
  const pct = (n: number) => total > 0 ? Math.round((n / total) * 100) : 0;

  const handleVote = async (vote: "bullish" | "bearish" | "neutral") => {
    if (!user || voting) return;
    setVoting(true);
    try {
      const updated = await castPollVote(poll.poll_id, vote);
      setPoll(updated);
    } catch {
      /* silent */
    } finally {
      setVoting(false);
    }
  };

  const voted = !!poll.user_vote;

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-900/60 backdrop-blur-sm p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-base">🗳️</span>
        <p className="text-sm font-semibold text-slate-200">This week's poll</p>
      </div>
      <p className="text-xs text-slate-400">{poll.question}</p>

      {!voted ? (
        <div className="flex gap-2">
          <button
            onClick={() => handleVote("bullish")}
            disabled={voting}
            className="flex-1 rounded-lg bg-emerald-900/50 border border-emerald-700/50 py-2 text-xs font-semibold text-emerald-400 hover:bg-emerald-800/60 disabled:opacity-40 transition-colors"
          >
            🐂 Bullish
          </button>
          <button
            onClick={() => handleVote("bearish")}
            disabled={voting}
            className="flex-1 rounded-lg bg-rose-900/50 border border-rose-700/50 py-2 text-xs font-semibold text-rose-400 hover:bg-rose-800/60 disabled:opacity-40 transition-colors"
          >
            🐻 Bearish
          </button>
          <button
            onClick={() => handleVote("neutral")}
            disabled={voting}
            className="flex-1 rounded-lg bg-amber-900/50 border border-amber-700/50 py-2 text-xs font-semibold text-amber-400 hover:bg-amber-800/60 disabled:opacity-40 transition-colors"
          >
            😐 Neutral
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-4">
          <DonutChart {...results} />
          <div className="space-y-1 text-xs">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 inline-block" />
              <span className="text-slate-300">Bullish {pct(results.bullish)}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-500 inline-block" />
              <span className="text-slate-300">Bearish {pct(results.bearish)}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500 inline-block" />
              <span className="text-slate-300">Neutral {pct(results.neutral)}%</span>
            </div>
            <p className="text-slate-500 pt-0.5">{total.toLocaleString()} votes</p>
          </div>
        </div>
      )}

      {poll.user_vote && (
        <p className="text-xs text-slate-500">
          Your vote: <span className="capitalize text-slate-400">{poll.user_vote}</span>
          {" · "}
          <button
            onClick={() => handleVote(poll.user_vote!)}
            className="underline hover:text-slate-300"
          >
            Change
          </button>
        </p>
      )}

      {!user && (
        <p className="text-xs text-slate-500">Sign in to vote.</p>
      )}
    </div>
  );
}
