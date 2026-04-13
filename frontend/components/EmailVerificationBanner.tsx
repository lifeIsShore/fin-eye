"use client";
/**
 * components/EmailVerificationBanner.tsx
 * SEC-07 — Shows a dismissable banner when the user's email is unverified.
 * Includes a "Resend verification email" button with cooldown feedback.
 */

import { useState } from "react";
import { useAuth } from "./AuthProvider";
import { Mail, X, CheckCircle2, RefreshCw } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function EmailVerificationBanner() {
    const { user } = useAuth();
    const [dismissed, setDismissed] = useState(false);
    const [sending, setSending] = useState(false);
    const [sent, setSent] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Don't show if: not logged in, already verified, or dismissed
    if (!user || user.is_verified || dismissed) return null;

    const handleResend = async () => {
        setSending(true);
        setError(null);
        try {
            const token = localStorage.getItem("access_token") ?? "";
            const res = await fetch(`${API_BASE}/api/v1/auth/resend-verification`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.status === 204 || res.ok) {
                setSent(true);
            } else {
                const data = await res.json().catch(() => ({}));
                setError(data.detail ?? "Failed to send. Try again later.");
            }
        } catch {
            setError("Network error. Please try again.");
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="w-full bg-amber-950/40 border-b border-amber-700/50">
            <div className="mx-auto max-w-6xl px-4 py-2.5 flex items-center gap-3">
                <Mail className="h-4 w-4 flex-shrink-0 text-amber-400" />
                <p className="flex-1 text-sm text-amber-300">
                    <strong>Please verify your email address</strong> to unlock full platform access.
                    {" "}Check your inbox for a link from Fin-Eye.
                </p>

                {sent ? (
                    <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 flex-shrink-0">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Email sent!
                    </span>
                ) : (
                    <button
                        onClick={handleResend}
                        disabled={sending}
                        className="flex-shrink-0 flex items-center gap-1.5 rounded-lg border border-amber-700/60 bg-amber-900/40 px-3 py-1 text-xs font-semibold text-amber-300 hover:bg-amber-800/40 disabled:opacity-50 transition-colors"
                    >
                        <RefreshCw className={`h-3 w-3 ${sending ? "animate-spin" : ""}`} />
                        {sending ? "Sending…" : "Resend email"}
                    </button>
                )}

                {error && (
                    <span className="text-xs text-rose-400 flex-shrink-0">{error}</span>
                )}

                <button
                    onClick={() => setDismissed(true)}
                    className="flex-shrink-0 text-amber-500 hover:text-amber-300 transition-colors"
                    aria-label="Dismiss"
                >
                    <X className="h-4 w-4" />
                </button>
            </div>
        </div>
    );
}
