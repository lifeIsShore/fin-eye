"use client";
/**
 * app/verify-email/page.tsx
 * SEC-07 — Email verification landing page.
 * Reads ?token= from the URL and calls POST /api/v1/auth/verify-email.
 */

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function VerifyEmailPage() {
    const params = useSearchParams();
    const token = params.get("token") ?? "";

    const [status, setStatus] = useState<"pending" | "success" | "error" | "expired">("pending");
    const [message, setMessage] = useState("");

    useEffect(() => {
        if (!token) {
            setStatus("error");
            setMessage("No verification token found in URL.");
            return;
        }

        fetch(`${API_BASE}/api/v1/auth/verify-email?token=${encodeURIComponent(token)}`, {
            method: "POST",
        })
            .then(async (res) => {
                if (res.status === 204) {
                    setStatus("success");
                } else if (res.status === 410) {
                    setStatus("expired");
                    setMessage("This link has expired. Please request a new one from Settings.");
                } else if (res.status === 404) {
                    setStatus("error");
                    setMessage("Invalid or already-used verification link.");
                } else {
                    const data = await res.json().catch(() => ({}));
                    setStatus("error");
                    setMessage(data.detail ?? "Verification failed. Please try again.");
                }
            })
            .catch(() => {
                setStatus("error");
                setMessage("Network error. Please try again.");
            });
    }, [token]);

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center space-y-6">
                {/* Icon */}
                <div className="flex justify-center">
                    {status === "pending" && (
                        <Loader2 className="h-12 w-12 text-sky-400 animate-spin" />
                    )}
                    {status === "success" && (
                        <CheckCircle2 className="h-12 w-12 text-emerald-400" />
                    )}
                    {(status === "error" || status === "expired") && (
                        <XCircle className="h-12 w-12 text-rose-400" />
                    )}
                </div>

                {/* Heading */}
                <div className="space-y-2">
                    {status === "pending" && (
                        <>
                            <h1 className="text-xl font-bold text-slate-100">Verifying your email…</h1>
                            <p className="text-sm text-slate-400">This will only take a moment.</p>
                        </>
                    )}
                    {status === "success" && (
                        <>
                            <h1 className="text-xl font-bold text-emerald-300">Email verified!</h1>
                            <p className="text-sm text-slate-400">
                                Your email has been confirmed. You now have full access to Fin-Eye.
                            </p>
                        </>
                    )}
                    {status === "expired" && (
                        <>
                            <h1 className="text-xl font-bold text-amber-300">Link expired</h1>
                            <p className="text-sm text-slate-400">{message}</p>
                        </>
                    )}
                    {status === "error" && (
                        <>
                            <h1 className="text-xl font-bold text-rose-300">Verification failed</h1>
                            <p className="text-sm text-slate-400">{message}</p>
                        </>
                    )}
                </div>

                {/* CTA */}
                {status === "success" && (
                    <Link
                        href="/"
                        className="inline-block rounded-xl bg-emerald-600 hover:bg-emerald-500 px-6 py-2.5 text-sm font-semibold text-white transition-colors"
                    >
                        Go to Dashboard →
                    </Link>
                )}
                {(status === "expired" || status === "error") && (
                    <Link
                        href="/settings"
                        className="inline-block rounded-xl border border-slate-700 bg-slate-800 hover:bg-slate-700 px-6 py-2.5 text-sm font-semibold text-slate-300 transition-colors"
                    >
                        Go to Settings →
                    </Link>
                )}
            </div>
        </div>
    );
}
