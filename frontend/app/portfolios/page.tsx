"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import { useAuth } from "../../components/AuthProvider";

const fetcher = async (url: string) => {
    const token = localStorage.getItem("access_token") || "";
    const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Failed to load");
    return res.json();
};

export default function PortfoliosOverview() {
    const { user } = useAuth();
    const [newPortName, setNewPortName] = useState("");
    const [isCreating, setIsCreating] = useState(false);

    const { data: portfolios, error, mutate } = useSWR(
        user ? "http://localhost:8000/api/v1/portfolios/" : null,
        fetcher
    );

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newPortName.trim()) return;
        setIsCreating(true);

        try {
            const token = localStorage.getItem("access_token") || "";
            const res = await fetch("http://localhost:8000/api/v1/portfolios/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ name: newPortName, description: "My custom portfolio" }),
            });

            if (res.ok) {
                setNewPortName("");
                mutate(); // Re-fetch the list
            }
        } catch (err) {
            console.error(err);
        } finally {
            setIsCreating(false);
        }
    };

    if (error) return <div className="text-red-400 p-4">Error loading portfolios. Please ensure you are logged in.</div>;
    if (!portfolios) return <div className="p-4 text-slate-400">Loading portfolios...</div>;

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-slate-50 tracking-tight">Your Portfolios</h2>
                    <p className="text-sm text-slate-400">Track aggregate exposure and algorithmic risk across your custom baskets.</p>
                </div>

                <form onSubmit={handleCreate} className="flex gap-2 w-full sm:w-auto">
                    <input
                        type="text"
                        placeholder="Portfolio Name..."
                        value={newPortName}
                        onChange={(e) => setNewPortName(e.target.value)}
                        className="rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                    <button
                        type="submit"
                        disabled={isCreating || !newPortName.trim()}
                        className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
                    >
                        {isCreating ? "Creating..." : "Create"}
                    </button>
                </form>
            </div>

            {portfolios.length === 0 ? (
                <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-12 text-center text-slate-400">
                    <p>You haven't created any portfolios yet.</p>
                    <p className="text-sm mt-1">Create your first basket above to track weighted market signals.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {portfolios.map((portfolio: any) => (
                        <Link
                            key={portfolio.id}
                            href={`/portfolios/${portfolio.id}`}
                            className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 hover:border-blue-500/50 hover:bg-slate-800/50 transition-all block group"
                        >
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-lg font-semibold text-slate-100 group-hover:text-blue-400 transition-colors">{portfolio.name}</h3>
                                <span className="text-xs font-mono bg-slate-800 text-slate-400 px-2 py-1 rounded-full">{portfolio.items?.length || 0} Assets</span>
                            </div>
                            <p className="text-sm text-slate-500 mb-6">{portfolio.description}</p>

                            <div className="flex items-center text-sm font-medium text-blue-400">
                                Manage Allocations
                                <svg className="ml-1 h-4 w-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
