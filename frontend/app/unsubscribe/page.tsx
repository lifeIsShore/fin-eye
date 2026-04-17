"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, X, Loader2, Mail } from "lucide-react";
import { unsubscribeByToken } from "@/lib/api";

/**
 * /unsubscribe?token=<token>
 *
 * One-click unsubscribe page. Linked from the footer of every marketing email.
 * No authentication required — the token is the credential.
 */
export default function UnsubscribePage() {
    const params = useSearchParams();
    const token = params.get("token");

    const [state, setState] = useState<"loading" | "success" | "error" | "no-token">(
        token ? "loading" : "no-token",
    );
    const [message, setMessage] = useState("");

    useEffect(() => {
        if (!token) {
            setState("no-token");
            return;
        }

        unsubscribeByToken(token)
            .then((res) => {
                setMessage(res.message);
                setState("success");
            })
            .catch((err) => {
                setMessage(err instanceof Error ? err.message : "Something went wrong.");
                setState("error");
            });
        // only run once on mount
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center shadow-2xl">
                {/* Logo */}
                <div className="mb-6 flex justify-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 shadow-lg">
                        <Mail className="h-7 w-7 text-white" />
                    </div>
                </div>

                {state === "loading" && (
                    <>
                        <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-slate-400" />
                        <h1 className="text-xl font-semibold text-slate-200">Unsubscribing…</h1>
                        <p className="mt-2 text-sm text-slate-500">Processing your request.</p>
                    </>
                )}

                {state === "success" && (
                    <>
                        <CheckCircle2 className="mx-auto mb-4 h-10 w-10 text-emerald-400" />
                        <h1 className="text-xl font-semibold text-slate-200">
                            {"You've been unsubscribed"}
                        </h1>
                        <p className="mt-3 text-sm text-slate-400 leading-relaxed">
                            {message || "You will no longer receive marketing emails from Yagmur Terminal."}
                        </p>
                        <p className="mt-4 text-xs text-slate-600">
                            {"You'll still receive important transactional emails related to your account security."}
                        </p>
                        <a
                            href="/settings"
                            className="mt-6 inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                        >
                            Manage email preferences
                        </a>
                    </>
                )}

                {state === "error" && (
                    <>
                        <X className="mx-auto mb-4 h-10 w-10 text-red-400" />
                        <h1 className="text-xl font-semibold text-red-300">Unsubscribe failed</h1>
                        <p className="mt-3 text-sm text-slate-400 leading-relaxed">{message}</p>
                        <p className="mt-4 text-xs text-slate-600">
                            The link may have already been used. Please{" "}
                            <a href="/settings" className="text-blue-400 hover:underline">
                                manage your email preferences
                            </a>{" "}
                            from Settings instead.
                        </p>
                    </>
                )}

                {state === "no-token" && (
                    <>
                        <X className="mx-auto mb-4 h-10 w-10 text-amber-400" />
                        <h1 className="text-xl font-semibold text-slate-200">Invalid unsubscribe link</h1>
                        <p className="mt-3 text-sm text-slate-400 leading-relaxed">
                            No token was found. Please use the link from your email, or manage your
                            preferences in Settings.
                        </p>
                        <a
                            href="/settings"
                            className="mt-6 inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
                        >
                            Go to Settings
                        </a>
                    </>
                )}

                <p className="mt-8 text-xs text-slate-700">
                    © {new Date().getFullYear()} Yagmur Terminal · Institutional Grade Intelligence
                </p>
            </div>
        </div>
    );
}
