"use client";
/**
 * frontend/components/NpsSurvey.tsx — Sprint 49
 * Slide-up NPS survey. Fires on 7th session or after user is logged in 30+ days.
 * Submits score + comment to PostHog. Shows once per user (localStorage flag).
 */
import { useState, useEffect } from "react";
import { X } from "lucide-react";
import { trackEvent } from "@/lib/posthog";
import { useAuth } from "@/components/AuthProvider";

const STORAGE_KEY    = "fin_eye_nps_submitted";
const SESSION_KEY    = "fin_eye_session_count";
const TRIGGER_AFTER  = 7;   // sessions

export function NpsSurvey() {
    const { user } = useAuth();
    const [visible, setVisible]   = useState(false);
    const [score, setScore]       = useState<number | null>(null);
    const [comment, setComment]   = useState("");
    const [submitted, setSubmitted] = useState(false);

    useEffect(() => {
        if (!user) return;
        if (localStorage.getItem(STORAGE_KEY)) return;

        // Increment session counter
        const count = parseInt(localStorage.getItem(SESSION_KEY) ?? "0", 10) + 1;
        localStorage.setItem(SESSION_KEY, String(count));

        // Trigger on 7th session or if account is ≥30 days old
        const daysSinceSignup = user.created_at
            ? Math.floor((Date.now() - new Date(user.created_at as any).getTime()) / 86_400_000)
            : 0;

        if (count >= TRIGGER_AFTER || daysSinceSignup >= 30) {
            // Delay slightly so it doesn't pop up on page load
            const t = setTimeout(() => setVisible(true), 3000);
            return () => clearTimeout(t);
        }
    }, [user]);

    const dismiss = () => {
        setVisible(false);
        localStorage.setItem(STORAGE_KEY, "dismissed");
    };

    const submit = () => {
        if (score === null) return;
        const daysSinceSignup = user?.created_at
            ? Math.floor((Date.now() - new Date(user.created_at as any).getTime()) / 86_400_000)
            : 0;
        trackEvent("nps_submitted", { score, comment: comment.trim(), days_since_signup: daysSinceSignup });
        localStorage.setItem(STORAGE_KEY, "true");
        setSubmitted(true);
        setTimeout(() => setVisible(false), 2500);
    };

    if (!visible) return null;

    return (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-sm px-4">
            <div className="rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl shadow-black/50 overflow-hidden">

                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                    <p className="text-sm font-semibold text-slate-200">
                        {submitted ? "Thanks for your feedback! 🙏" : "Quick question"}
                    </p>
                    <button onClick={dismiss} className="text-slate-500 hover:text-slate-300 transition-colors">
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {submitted ? (
                    <div className="px-4 py-5 text-sm text-slate-400 text-center">
                        Your feedback helps us improve Fin-Eye.
                    </div>
                ) : (
                    <div className="px-4 py-4 space-y-4">
                        <p className="text-sm text-slate-300">
                            How likely are you to recommend Fin-Eye to a friend?
                        </p>

                        {/* 0–10 score row */}
                        <div className="flex gap-1 justify-between">
                            {Array.from({ length: 11 }, (_, i) => (
                                <button
                                    key={i}
                                    onClick={() => setScore(i)}
                                    className={`flex-1 rounded-md py-1.5 text-xs font-bold transition-colors ${
                                        score === i
                                            ? "bg-sky-600 text-white"
                                            : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                                    }`}
                                >
                                    {i}
                                </button>
                            ))}
                        </div>

                        <div className="flex justify-between text-[10px] text-slate-600">
                            <span>Not likely</span><span>Very likely</span>
                        </div>

                        {/* Optional comment */}
                        <textarea
                            value={comment}
                            onChange={(e) => setComment(e.target.value)}
                            placeholder="What's the main reason for your score? (optional)"
                            rows={2}
                            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-300 placeholder-slate-600 focus:border-sky-500 focus:outline-none resize-none"
                        />

                        <div className="flex gap-2">
                            <button onClick={dismiss}
                                className="flex-1 rounded-lg border border-slate-700 bg-slate-800 py-2 text-xs text-slate-400 hover:bg-slate-700 transition-colors">
                                Not now
                            </button>
                            <button onClick={submit} disabled={score === null}
                                className="flex-1 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-40 py-2 text-xs font-semibold text-white transition-colors">
                                Submit
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
