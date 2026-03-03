"use client";

import { useState } from "react";
import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "../../../components/AuthProvider";

const fetcher = async (url: string) => {
    const token = localStorage.getItem("access_token") || "";
    const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error("Failed to load");
    return res.json();
};

export default function PortfolioDetailPage() {
    const params = useParams();
    const router = useRouter();
    const { user } = useAuth();
    const id = params.id;

    const [symbol, setSymbol] = useState("");
    const [weight, setWeight] = useState<number | "">("");
    const [isAdding, setIsAdding] = useState(false);

    // Fetch composition
    const { data: portfolio, mutate: mutatePort } = useSWR(
        user && id ? `http://localhost:8000/api/v1/portfolios/${id}` : null,
        fetcher
    );

    // Fetch analysis math
    const { data: analysis, error: analysisError, isLoading: isAnalysisLoading } = useSWR(
        user && id && portfolio?.items?.length > 0 ? `http://localhost:8000/api/v1/portfolios/${id}/analysis` : null,
        fetcher
    );


    const handleAddItem = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!symbol || !weight) return;
        setIsAdding(true);

        try {
            const token = localStorage.getItem("access_token") || "";
            const res = await fetch(`http://localhost:8000/api/v1/portfolios/${id}/items`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ symbol: symbol.toUpperCase(), weight: Number(weight) }),
            });

            if (res.ok) {
                setSymbol("");
                setWeight("");
                mutatePort();
            }
        } catch (err) {
            console.error(err);
        } finally {
            setIsAdding(false);
        }
    };

    const removeItem = async (sym: string) => {
        try {
            const token = localStorage.getItem("access_token") || "";
            await fetch(`http://localhost:8000/api/v1/portfolios/${id}/items/${sym}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` }
            });
            mutatePort();
        } catch (err) {
            console.error(err);
        }
    };


    if (!portfolio) return <div className="p-4 text-slate-400">Loading Portfolio context...</div>;

    const totalWeight = portfolio.items?.reduce((sum: number, item: any) => sum + item.weight, 0) || 0;

    return (
        <div className="space-y-6">
            {/* HEADER */}
            <div>
                <button onClick={() => router.push('/portfolios')} className="text-sm text-blue-400 hover:text-blue-300 mb-2 flex items-center">
                    &larr; Back to Portfolios
                </button>
                <h1 className="text-3xl font-bold tracking-tight text-slate-50">{portfolio.name}</h1>
                <p className="mt-1 text-sm text-slate-400">{portfolio.description}</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* LEFT COLUMN: COMPOSITION */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6">
                        <h2 className="text-lg font-semibold text-slate-100 mb-4">Allocation Mapping</h2>

                        <form onSubmit={handleAddItem} className="flex gap-2 mb-6">
                            <input
                                type="text"
                                placeholder="Ticker (e.g. AAPL)"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                className="w-1/3 rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                                required
                            />
                            <input
                                type="number"
                                step="0.01"
                                placeholder="Weight (e.g. 0.50)"
                                value={weight}
                                onChange={(e) => setWeight(e.target.valueAsNumber || "")}
                                className="w-1/3 rounded-md border border-slate-700 bg-slate-950 px-3 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                                required
                            />
                            <button
                                type="submit"
                                disabled={isAdding}
                                className="w-1/3 rounded-md bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
                            >
                                {isAdding ? "Saving..." : "Update Allocation"}
                            </button>
                        </form>

                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-slate-800">
                                <thead>
                                    <tr className="text-left text-xs font-medium text-slate-400 uppercase tracking-wider">
                                        <th className="px-4 py-3">Symbol</th>
                                        <th className="px-4 py-3">Raw Weight</th>
                                        <th className="px-4 py-3 text-right">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800">
                                    {portfolio.items?.map((item: any) => (
                                        <tr key={item.id} className="hover:bg-slate-800/20 transition-colors">
                                            <td className="px-4 py-3 text-sm font-bold text-slate-200">{item.symbol}</td>
                                            <td className="px-4 py-3 text-sm text-slate-300">{(item.weight * 100).toFixed(1)}%</td>
                                            <td className="px-4 py-3 text-right">
                                                <button onClick={() => removeItem(item.symbol)} className="text-red-400 hover:text-red-300 text-xs font-medium">
                                                    Remove
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                    {portfolio.items?.length === 0 && (
                                        <tr>
                                            <td colSpan={3} className="px-4 py-8 text-center text-sm text-slate-500 italic">No assets allocated yet.</td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>

                        <div className={`mt-4 text-xs font-medium ${totalWeight !== 1.0 ? 'text-amber-500' : 'text-emerald-400'}`}>
                            Total Raw Weight: {(totalWeight * 100).toFixed(1)}%
                            {totalWeight !== 1.0 && " (Note: Analytics auto-normalizes weights to 100%)"}
                        </div>
                    </div>
                </div>

                {/* RIGHT COLUMN: ALGORITHMIC METRICS */}
                <div className="space-y-6">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 flex flex-col h-full">
                        <h2 className="text-lg font-semibold text-slate-100 mb-6">Quantitative Analytics</h2>

                        {portfolio.items?.length === 0 ? (
                            <div className="flex-1 flex items-center justify-center text-sm text-slate-500 italic text-center">
                                Add assets to generate multi-dimensional risk metrics.
                            </div>
                        ) : isAnalysisLoading ? (
                            <div className="flex-1 flex items-center justify-center text-sm text-blue-400 animate-pulse">
                                Computing mathematical aggregation algorithms...
                            </div>
                        ) : analysisError ? (
                            <div className="flex-1 flex items-center justify-center text-sm text-red-400">
                                Failed to execute quantitative analysis.
                            </div>
                        ) : (
                            <div className="space-y-8">

                                {/* METRIC 1: WEIGHTED GAS */}
                                <div>
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-sm font-medium text-slate-300">Net Portfolio GAS</span>
                                        <span className={`text-xl font-bold ${analysis.weighted_gas > 60 ? 'text-emerald-400' : analysis.weighted_gas < 40 ? 'text-red-400' : 'text-amber-400'}`}>
                                            {analysis.weighted_gas} <span className="text-xs font-normal text-slate-500">/ 100</span>
                                        </span>
                                    </div>
                                    <div className="w-full bg-slate-800 rounded-full h-1.5">
                                        <div
                                            className={`h-1.5 rounded-full ${analysis.weighted_gas > 60 ? 'bg-emerald-400' : analysis.weighted_gas < 40 ? 'bg-red-400' : 'bg-amber-400'}`}
                                            style={{ width: `${analysis.weighted_gas}%` }}
                                        ></div>
                                    </div>
                                    <p className="mt-2 text-xs text-slate-500">Global Alignment Score aggregated dynamically across your weighted constituents.</p>
                                </div>

                                {/* METRIC 2: DIVERSIFICATION MATRIX */}
                                <div>
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-sm font-medium text-slate-300">Diversification Score</span>
                                        <span className={`text-xl font-bold ${analysis.diversification_score > 60 ? 'text-emerald-400' : analysis.diversification_score < 40 ? 'text-red-400' : 'text-amber-400'}`}>
                                            {analysis.diversification_score} <span className="text-xs font-normal text-slate-500">/ 100</span>
                                        </span>
                                    </div>
                                    <div className="w-full bg-slate-800 rounded-full h-1.5">
                                        <div
                                            className={`h-1.5 rounded-full ${analysis.diversification_score > 60 ? 'bg-emerald-400' : analysis.diversification_score < 40 ? 'bg-red-400' : 'bg-amber-400'}`}
                                            style={{ width: `${analysis.diversification_score}%` }}
                                        ></div>
                                    </div>
                                    <p className="mt-2 text-xs text-slate-500">A measure of inter-asset correlation. Higher scores represent statistically less systemic sector risk.</p>
                                </div>

                                {/* METRIC 3: SECTOR MAP */}
                                <div>
                                    <h3 className="text-sm font-medium text-slate-300 mb-3 border-b border-slate-800 pb-2">Sector Exposure Map</h3>
                                    <div className="space-y-3">
                                        {Object.entries(analysis.sector_breakdown).map(([sector, weightRaw]: any) => (
                                            <div key={sector}>
                                                <div className="flex justify-between text-xs mb-1">
                                                    <span className="text-slate-400 truncate w-32">{sector}</span>
                                                    <span className="text-slate-200 font-mono">{weightRaw.toFixed(1)}%</span>
                                                </div>
                                                <div className="w-full bg-slate-800 rounded-full h-1">
                                                    <div className="bg-blue-500 h-1 rounded-full" style={{ width: `${Math.min(weightRaw, 100)}%` }}></div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                            </div>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
}
