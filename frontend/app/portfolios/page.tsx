"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { useAuth } from "../../components/AuthProvider";
import { PageBanner } from "../../components/ui/PageBanner";
import { Briefcase, Trash2, ChevronRight, Plus, Loader2, AlertCircle } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const fetcher = async (url: string) => {
    const token = localStorage.getItem("access_token") || "";
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error("Failed to load");
    return res.json();
};

export default function PortfoliosOverview() {
    const { user } = useAuth();
    const [newPortName, setNewPortName]   = useState("");
    const [isCreating, setIsCreating]     = useState(false);
    const [createError, setCreateError]   = useState<string | null>(null);
    const [deletingId, setDeletingId]     = useState<number | null>(null);
    const [confirmId, setConfirmId]       = useState<number | null>(null);

    const { data: portfolios, error, isLoading, mutate } = useSWR(
        user ? `${API}/api/v1/portfolios/` : null,
        fetcher,
    );

    // ── Create ────────────────────────────────────────────────────────────────
    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        const name = newPortName.trim();
        if (!name) return;

        // Client-side duplicate check before hitting the API
        if (portfolios?.some((p: any) => p.name.toLowerCase() === name.toLowerCase())) {
            setCreateError(`A portfolio named "${name}" already exists.`);
            return;
        }

        setIsCreating(true);
        setCreateError(null);
        try {
            const token = localStorage.getItem("access_token") || "";
            const res = await fetch(`${API}/api/v1/portfolios/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ name, description: "" }),
            });

            if (res.ok) {
                setNewPortName("");
                mutate();
            } else {
                const data = await res.json().catch(() => ({}));
                // 409 = duplicate name caught by backend
                setCreateError(data.detail ?? "Failed to create portfolio.");
            }
        } catch {
            setCreateError("Network error — please try again.");
        } finally {
            setIsCreating(false);
        }
    };

    // ── Delete ────────────────────────────────────────────────────────────────
    const handleDelete = async (id: number) => {
        setDeletingId(id);
        try {
            const token = localStorage.getItem("access_token") || "";
            await fetch(`${API}/api/v1/portfolios/${id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });
            setConfirmId(null);
            mutate();
        } catch {
            // silently retry on next interaction
        } finally {
            setDeletingId(null);
        }
    };

    // ── Loading / error states ────────────────────────────────────────────────
    if (error) return (
        <div className="rounded-xl border border-rose-800/50 bg-rose-950/20 p-6 text-rose-400 text-sm">
            Failed to load portfolios. Make sure you are logged in and the backend is running.
        </div>
    );

    if (isLoading || !portfolios) return (
        <div className="flex items-center justify-center py-24">
            <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
    );

    return (
        <div className="space-y-6">
            <PageBanner
                icon={<Briefcase className="h-5 w-5" />}
                title="Portfolio Builder"
                description="Create custom baskets, track weighted GAS scores, and manage grade-based allocations."
                badge="Grade-Based"
                badgeColor="emerald"
            />

            {/* ── Create form ───────────────────────────────────────────────── */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <p className="text-sm text-slate-500">
                    {portfolios.length === 0
                        ? "No portfolios yet — create your first one."
                        : `${portfolios.length} portfolio${portfolios.length !== 1 ? "s" : ""}`}
                </p>

                <div className="space-y-1.5 w-full sm:w-auto">
                    <form onSubmit={handleCreate} className="flex gap-2">
                        <input
                            type="text"
                            placeholder="Portfolio name…"
                            value={newPortName}
                            onChange={(e) => { setNewPortName(e.target.value); setCreateError(null); }}
                            maxLength={64}
                            className={`flex-1 sm:w-56 rounded-lg border bg-slate-900 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:ring-1 ${
                                createError
                                    ? "border-rose-500 focus:border-rose-500 focus:ring-rose-500/30"
                                    : "border-slate-700 focus:border-sky-500 focus:ring-sky-500/20"
                            }`}
                        />
                        <button
                            type="submit"
                            disabled={isCreating || !newPortName.trim()}
                            className="flex items-center gap-1.5 rounded-lg bg-sky-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50 transition-colors"
                        >
                            {isCreating
                                ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                : <Plus className="h-3.5 w-3.5" />}
                            Create
                        </button>
                    </form>

                    {/* Inline error */}
                    {createError && (
                        <p className="flex items-center gap-1.5 text-xs text-rose-400">
                            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" />
                            {createError}
                        </p>
                    )}
                </div>
            </div>

            {/* ── Grid ──────────────────────────────────────────────────────── */}
            {portfolios.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/30 p-16 text-center">
                    <Briefcase className="mx-auto h-8 w-8 text-slate-600 mb-3" />
                    <p className="text-slate-400 font-medium">No portfolios yet</p>
                    <p className="text-sm text-slate-600 mt-1">
                        Create your first basket above to track weighted market signals.
                    </p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {portfolios.map((portfolio: any) => (
                        <div
                            key={portfolio.id}
                            className="group relative flex flex-col rounded-xl border border-slate-800 bg-slate-900/50 hover:border-slate-700 transition-colors"
                        >
                            {/* Delete button — top right corner */}
                            <div className="absolute top-3 right-3">
                                {confirmId === portfolio.id ? (
                                    // Confirm row
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-xs text-slate-400">Delete?</span>
                                        <button
                                            onClick={() => handleDelete(portfolio.id)}
                                            disabled={deletingId === portfolio.id}
                                            className="rounded px-2 py-0.5 text-xs font-semibold bg-rose-600 text-white hover:bg-rose-500 disabled:opacity-50 transition-colors"
                                        >
                                            {deletingId === portfolio.id ? "…" : "Yes"}
                                        </button>
                                        <button
                                            onClick={() => setConfirmId(null)}
                                            className="rounded px-2 py-0.5 text-xs font-semibold bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
                                        >
                                            No
                                        </button>
                                    </div>
                                ) : (
                                    <button
                                        onClick={(e) => { e.preventDefault(); setConfirmId(portfolio.id); }}
                                        className="rounded-lg p-1.5 text-slate-600 hover:text-rose-400 hover:bg-rose-950/30 transition-colors opacity-0 group-hover:opacity-100"
                                        title="Delete portfolio"
                                        aria-label={`Delete ${portfolio.name}`}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </button>
                                )}
                            </div>

                            {/* Card content — links to detail page */}
                            <Link href={`/portfolios/${portfolio.id}`} className="flex flex-col flex-1 p-6 pr-20">
                                <div className="flex items-start justify-between mb-1 gap-2">
                                    <h3 className="text-base font-bold text-slate-100 group-hover:text-sky-400 transition-colors leading-snug">
                                        {portfolio.name}
                                    </h3>
                                    <span className="flex-shrink-0 text-xs font-mono bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full mt-0.5">
                                        {portfolio.items?.length ?? 0} assets
                                    </span>
                                </div>

                                {portfolio.description && (
                                    <p className="text-sm text-slate-500 mb-4 line-clamp-2">
                                        {portfolio.description}
                                    </p>
                                )}

                                <div className="mt-auto flex items-center gap-1 text-sm font-medium text-sky-400 pt-4">
                                    Manage Allocations
                                    <ChevronRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                                </div>
                            </Link>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
