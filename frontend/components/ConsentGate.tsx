"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { ShieldAlert, Loader2, CheckCircle2 } from "lucide-react";
import { fetchConsentStatus, recordConsent } from "@/lib/api";

/**
 * ConsentGate — renders a full-screen modal that blocks the app until the user
 * accepts the current version of the ToS + Privacy Policy.
 *
 * Logic:
 *  1. On mount, hit GET /api/v1/legal/consent/status
 *  2. If has_accepted === true, render nothing (gate is open)
 *  3. If has_accepted === false, show the consent modal
 *  4. On "I Agree", POST /api/v1/legal/consent, then open the gate
 *
 * In dev-bypass mode (NEXT_PUBLIC_REQUIRE_AUTH !== "true") the gate skips the
 * API call and stays open — dev user id 9999 has no DB row, so we don't want
 * a perpetual consent loop during development.
 */
export function ConsentGate({ children }: { children: React.ReactNode }) {
    const [status, setStatus] = useState<"loading" | "needed" | "accepted">("loading");
    const [checked, setChecked] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const REQUIRE_AUTH = process.env.NEXT_PUBLIC_REQUIRE_AUTH === "true";

    useEffect(() => {
        // Skip consent gate entirely in dev bypass mode
        if (!REQUIRE_AUTH) {
            setStatus("accepted");
            return;
        }

        fetchConsentStatus()
            .then((data) => setStatus(data.has_accepted ? "accepted" : "needed"))
            .catch(() => {
                // If the check fails (network, auth), fail open — don't block the app
                setStatus("accepted");
            });
    }, [REQUIRE_AUTH]);

    const handleAccept = async () => {
        if (!checked) return;
        setSubmitting(true);
        setError(null);
        try {
            await recordConsent();
            setStatus("accepted");
        } catch {
            setError("Could not record your consent. Please try again.");
        } finally {
            setSubmitting(false);
        }
    };

    // Still checking
    if (status === "loading") {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
        );
    }

    // Gate is open
    if (status === "accepted") {
        return <>{children}</>;
    }

    // Gate is closed — show consent modal
    return (
        <>
            {/* Blurred background — render children so layout doesn't flicker */}
            <div className="pointer-events-none select-none blur-sm brightness-50 overflow-hidden max-h-screen">
                {children}
            </div>

            {/* Modal overlay */}
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm px-4">
                <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">

                    {/* Header */}
                    <div className="flex items-center gap-3 border-b border-slate-800 px-6 py-5">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-500/10 border border-amber-500/20">
                            <ShieldAlert className="h-5 w-5 text-amber-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-slate-50">Before you continue</h2>
                            <p className="text-xs text-slate-400">Fin-Eye requires your acknowledgement</p>
                        </div>
                    </div>

                    {/* Body */}
                    <div className="px-6 py-5 space-y-4">
                        <div className="rounded-lg border border-amber-500/20 bg-amber-950/10 p-4 text-sm text-amber-200/90 leading-relaxed">
                            Fin-Eye is an <strong>educational analytics platform</strong>. It does not provide
                            investment advice. All signals, scores, and backtest results are for informational
                            purposes only. Past performance does not guarantee future results.{" "}
                            <strong>You are solely responsible for your financial decisions.</strong>
                        </div>

                        <ul className="space-y-2 text-sm text-slate-400">
                            <li className="flex items-start gap-2">
                                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-500" />
                                Model outputs may be incorrect, especially during unusual market conditions.
                            </li>
                            <li className="flex items-start gap-2">
                                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-500" />
                                Backtest results are simulations — live performance is typically 40–60% lower.
                            </li>
                            <li className="flex items-start gap-2">
                                <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0 text-slate-500" />
                                Always consult a licensed financial adviser before making any trading decisions.
                            </li>
                        </ul>

                        {/* Checkbox */}
                        <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-slate-700 bg-slate-800/50 p-4 hover:border-slate-600 transition-colors">
                            <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => setChecked(e.target.checked)}
                                className="mt-0.5 h-4 w-4 flex-shrink-0 accent-blue-500 cursor-pointer"
                            />
                            <span className="text-sm text-slate-300 leading-relaxed">
                                I have read and agree to the{" "}
                                <Link
                                    href="/legal/terms"
                                    target="_blank"
                                    className="text-blue-400 underline hover:text-blue-300"
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    Terms of Service
                                </Link>{" "}
                                and{" "}
                                <Link
                                    href="/legal/privacy"
                                    target="_blank"
                                    className="text-blue-400 underline hover:text-blue-300"
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    Privacy Policy
                                </Link>
                                . I understand that Fin-Eye does not provide investment advice and I am solely
                                responsible for any financial decisions I make.
                            </span>
                        </label>

                        {error && (
                            <p className="text-sm text-red-400">{error}</p>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="border-t border-slate-800 px-6 py-4 flex items-center justify-between gap-4">
                        <Link
                            href="/legal/disclaimer"
                            target="_blank"
                            className="text-xs text-slate-500 hover:text-slate-400 underline"
                        >
                            Full Risk Disclaimer
                        </Link>
                        <button
                            onClick={handleAccept}
                            disabled={!checked || submitting}
                            className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
                        >
                            {submitting ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Saving…
                                </>
                            ) : (
                                "I Agree — Enter Fin-Eye"
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}
