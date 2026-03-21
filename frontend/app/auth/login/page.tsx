"use client";

/**
 * /auth/login — Login page with 2FA support (CORE-SEC-01)
 *
 * Sprint 7 (SEC-04): now passes refresh_token through to AuthProvider.login()
 * so it can be stored and later used by the /auth/logout JTI blacklist call.
 */

import { useState, useRef } from "react";
import Link from "next/link";
import { useAuth } from "../../../components/AuthProvider";
import { loginWithTotp, verify2faLogin } from "@/lib/api";
import { Loader2, ShieldCheck } from "lucide-react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function LoginPage() {
    const [email, setEmail]       = useState("");
    const [password, setPassword] = useState("");
    const [error, setError]       = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const { login } = useAuth();

    // ── 2FA state ─────────────────────────────────────────────────────────────
    const [totpRequired, setTotpRequired] = useState(false);
    const [pendingToken, setPendingToken] = useState("");
    const [totpCode, setTotpCode]         = useState("");
    const totpInputRef = useRef<HTMLInputElement>(null);

    // ── Step 1: email + password ──────────────────────────────────────────────
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError("");

        try {
            const data = await loginWithTotp(email, password);

            if (data.totp_required) {
                setPendingToken(data.pending_token);
                setTotpRequired(true);
                setTimeout(() => totpInputRef.current?.focus(), 100);
                return;
            }

            // No 2FA — complete login with both tokens
            await _completeLogin(data.access_token, data.refresh_token);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "An unexpected error occurred");
        } finally {
            setIsLoading(false);
        }
    };

    // ── Step 2: TOTP code ─────────────────────────────────────────────────────
    const handleTotpSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (totpCode.length !== 6) return;
        setIsLoading(true);
        setError("");

        try {
            const tokens = await verify2faLogin(pendingToken, totpCode);
            await _completeLogin(tokens.access_token, tokens.refresh_token);
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : "Invalid code. Try again.");
            setTotpCode("");
            totpInputRef.current?.focus();
        } finally {
            setIsLoading(false);
        }
    };

    // ── Shared: fetch /me, hydrate auth context ───────────────────────────────
    const _completeLogin = async (accessToken: string, refreshToken: string) => {
        const meRes = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!meRes.ok) throw new Error("Failed to fetch user profile");
        const userData = await meRes.json();
        // Pass refreshToken so AuthProvider stores it for logout JTI blacklist (SEC-04)
        login(accessToken, userData, refreshToken);
    };

    // ── TOTP auto-advance on 6 digits ─────────────────────────────────────────
    const handleTotpChange = (val: string) => {
        const digits = val.replace(/\D/g, "").slice(0, 6);
        setTotpCode(digits);
        if (digits.length === 6) {
            setTimeout(() => document.getElementById("totp-submit")?.click(), 80);
        }
    };

    // ─────────────────────────────────────────────────────────────────────────

    return (
        <div className="flex flex-col flex-1 items-center justify-center p-4">
            <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/50 p-8 shadow-2xl backdrop-blur-sm">

                {totpRequired ? (
                    <>
                        <div className="mb-8 text-center">
                            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-indigo-900/40 border border-indigo-700/40">
                                <ShieldCheck className="h-7 w-7 text-indigo-400" />
                            </div>
                            <h1 className="text-2xl font-bold tracking-tight text-slate-50">Two-Factor Authentication</h1>
                            <p className="mt-2 text-sm text-slate-400">Open your authenticator app and enter the 6-digit code.</p>
                        </div>

                        {error && (
                            <div className="mb-6 rounded-md bg-red-500/10 p-4 text-sm text-red-400 border border-red-500/20">{error}</div>
                        )}

                        <form onSubmit={handleTotpSubmit} className="space-y-6">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2 text-center">Verification Code</label>
                                <input
                                    ref={totpInputRef}
                                    type="text"
                                    inputMode="numeric"
                                    autoComplete="one-time-code"
                                    maxLength={6}
                                    value={totpCode}
                                    onChange={(e) => handleTotpChange(e.target.value)}
                                    placeholder="000000"
                                    className="block w-full rounded-md border border-slate-700 bg-slate-950 px-4 py-3 text-center text-2xl font-mono tracking-[0.4em] text-slate-50 placeholder-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                                />
                            </div>
                            <button
                                id="totp-submit"
                                type="submit"
                                disabled={isLoading || totpCode.length !== 6}
                                className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition-all flex items-center justify-center gap-2"
                            >
                                {isLoading ? <><Loader2 className="h-4 w-4 animate-spin" /> Verifying…</> : "Verify Code"}
                            </button>
                            <p className="text-center text-xs text-slate-500">
                                Code expires in 5 minutes.{" "}
                                <button type="button" onClick={() => { setTotpRequired(false); setPendingToken(""); setTotpCode(""); setError(""); }}
                                    className="text-slate-400 hover:text-slate-200 underline">
                                    Back to login
                                </button>
                            </p>
                        </form>
                    </>
                ) : (
                    <>
                        <div className="mb-8 text-center">
                            <h1 className="text-3xl font-bold tracking-tight text-slate-50">Welcome back</h1>
                            <p className="mt-2 text-sm text-slate-400">Log in to view your market consensus</p>
                        </div>

                        {error && (
                            <div className="mb-6 rounded-md bg-red-500/10 p-4 text-sm text-red-400 border border-red-500/20">{error}</div>
                        )}

                        <form onSubmit={handleSubmit} className="space-y-6">
                            <div>
                                <label className="block text-sm font-medium text-slate-300">Email Address</label>
                                <input type="email" required
                                    className="mt-2 block w-full rounded-md border border-slate-700 bg-slate-950 px-4 py-2 placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 sm:text-sm text-slate-50 transition-colors"
                                    placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300">Password</label>
                                <input type="password" required
                                    className="mt-2 block w-full rounded-md border border-slate-700 bg-slate-950 px-4 py-2 placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 sm:text-sm text-slate-50 transition-colors"
                                    placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
                            </div>
                            <button type="submit" disabled={isLoading}
                                className="w-full rounded-md bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm hover:bg-slate-200 disabled:opacity-50 transition-all">
                                {isLoading
                                    ? <span className="flex items-center justify-center gap-2"><Loader2 className="h-4 w-4 animate-spin" /> Authenticating…</span>
                                    : "Sign In"}
                            </button>
                        </form>

                        <p className="mt-8 text-center text-sm text-slate-400">
                            Don&apos;t have an account?{" "}
                            <Link href="/auth/signup" className="font-semibold text-white hover:text-blue-400 transition-colors">Sign up</Link>
                        </p>
                    </>
                )}
            </div>
        </div>
    );
}
