"use client";

/**
 * /app/billing/cancel/page.tsx — todos-v3.md §10
 *
 * Cancellation flow with pause offer.
 * Survey → pause offer → confirm cancel or take pause.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, PauseCircle, HeartCrack } from "lucide-react";

const CANCEL_REASONS = [
    "It's too expensive",
    "I don't use it enough",
    "Missing features I need",
    "I found a better tool",
    "Just taking a break",
] as const;

type Step = "survey" | "pause_offer" | "done";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function CancelPage() {
    const router = useRouter();
    const [step, setStep] = useState<Step>("survey");
    const [reason, setReason] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<string | null>(null);

    const handleSurveySubmit = () => {
        if (!reason) return;
        setStep("pause_offer");
    };

    const handlePause = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem("access_token");
            const res = await fetch(`${API_BASE}/api/v1/billing/pause`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({ reason }),
            });
            if (res.ok) {
                const data = await res.json();
                setMessage(data.message);
                setStep("done");
            } else {
                setMessage("Something went wrong. Please try again.");
            }
        } catch {
            setMessage("Network error — please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleCancelAnyway = () => {
        // Placeholder — in production this would call Stripe's cancellation API
        setMessage("Cancellation recorded. You'll retain Pro access until your period ends.");
        setStep("done");
    };

    return (
        <div className="mx-auto max-w-lg space-y-6 py-6">
            {/* Back link */}
            <Link
                href="/billing"
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
                <ChevronLeft className="h-3.5 w-3.5" /> Back to Billing
            </Link>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-8 space-y-6">

                {/* ── Step 1: Survey ── */}
                {step === "survey" && (
                    <>
                        <div className="space-y-1">
                            <h1 className="text-lg font-bold text-slate-100">Before you go…</h1>
                            <p className="text-sm text-slate-400">Help us understand why you're leaving.</p>
                        </div>

                        <div className="space-y-2">
                            {CANCEL_REASONS.map((r) => (
                                <label
                                    key={r}
                                    className={`flex items-center gap-3 rounded-xl border px-4 py-3 cursor-pointer transition-colors ${
                                        reason === r
                                            ? "border-blue-500/50 bg-blue-950/20 text-slate-100"
                                            : "border-slate-700 bg-slate-900/40 text-slate-400 hover:border-slate-600 hover:text-slate-300"
                                    }`}
                                >
                                    <input
                                        type="radio"
                                        name="cancel_reason"
                                        value={r}
                                        checked={reason === r}
                                        onChange={() => setReason(r)}
                                        className="sr-only"
                                    />
                                    <span className={`h-4 w-4 flex-shrink-0 rounded-full border-2 flex items-center justify-center ${
                                        reason === r ? "border-blue-500" : "border-slate-600"
                                    }`}>
                                        {reason === r && <span className="h-2 w-2 rounded-full bg-blue-500" />}
                                    </span>
                                    <span className="text-sm">{r}</span>
                                </label>
                            ))}
                        </div>

                        <button
                            onClick={handleSurveySubmit}
                            disabled={!reason}
                            className="w-full rounded-xl bg-slate-700 py-2.5 text-sm font-semibold text-slate-200 hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                            Continue
                        </button>
                    </>
                )}

                {/* ── Step 2: Pause offer ── */}
                {step === "pause_offer" && (
                    <>
                        <div className="flex flex-col items-center text-center gap-4 py-2">
                            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-900/30 border border-amber-700/40">
                                <PauseCircle className="h-7 w-7 text-amber-400" />
                            </div>
                            <div className="space-y-1">
                                <h2 className="text-base font-bold text-slate-100">How about a pause instead?</h2>
                                <p className="text-sm text-slate-400 max-w-xs mx-auto">
                                    Pause your subscription for <strong className="text-slate-200">30 days free</strong> — pick up where you left off when you're ready.
                                </p>
                            </div>
                        </div>

                        <div className="space-y-2.5">
                            <button
                                onClick={handlePause}
                                disabled={loading}
                                className="w-full rounded-xl bg-amber-600 py-2.5 text-sm font-semibold text-white hover:bg-amber-500 disabled:opacity-50 transition-colors"
                            >
                                {loading ? "Pausing…" : "Pause for 30 days (free)"}
                            </button>
                            <button
                                onClick={handleCancelAnyway}
                                className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-slate-700 py-2.5 text-sm text-slate-500 hover:text-rose-400 hover:border-rose-900/50 transition-colors"
                            >
                                <HeartCrack className="h-3.5 w-3.5" />
                                Cancel anyway
                            </button>
                        </div>
                    </>
                )}

                {/* ── Step 3: Done ── */}
                {step === "done" && (
                    <div className="flex flex-col items-center text-center gap-4 py-4">
                        <p className="text-sm text-slate-300 leading-relaxed">{message}</p>
                        <Link
                            href="/"
                            className="rounded-xl bg-slate-800 px-6 py-2 text-sm text-slate-200 hover:bg-slate-700 transition-colors"
                        >
                            Back to Dashboard
                        </Link>
                    </div>
                )}
            </div>
        </div>
    );
}
