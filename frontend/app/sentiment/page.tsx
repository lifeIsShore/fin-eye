"use client";

import { useState } from "react";
import useSWR from "swr";
import { getRetailSentiment } from "@/lib/api";
import { Search } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import CommentList from "@/components/sentiment/CommentList";

export default function RetailSentimentPage() {
    const [searchInput, setSearchInput] = useState("");
    const [activeTicker, setActiveTicker] = useState("AAPL");

    // Fetch sentiment data
    const { data, error, isLoading } = useSWR(
        activeTicker ? `/api/v1/sentiment/retail/${activeTicker}` : null,
        () => getRetailSentiment(activeTicker),
        {
            revalidateOnFocus: false,
        }
    );

    const handleSearch = (e: React.FormEvent) => {
        e.preventDefault();
        if (searchInput.trim()) {
            setActiveTicker(searchInput.trim().toUpperCase());
        }
    };

    const chartData = data ? [
        { name: "Positive", value: data.summary.percent_positive, color: "#16a34a" }, // green-600
        { name: "Neutral", value: data.summary.percent_neutral, color: "#94a3b8" },   // slate-400
        { name: "Negative", value: data.summary.percent_negative, color: "#dc2626" }, // red-600
    ] : [];

    return (
        <div className="container mx-auto p-4 md:p-8 space-y-8 animate-in fade-in zoom-in-95 duration-500">
            <header className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">Retail Sentiment</h1>
                <p className="text-muted-foreground w-full md:w-2/3">
                    Gauge the crowd. We analyze mentions across popular subreddits to
                    understand if retail traders are bullish, bearish, or neutral.
                </p>
            </header>

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="flex max-w-md gap-2">
                <input
                    type="text"
                    placeholder="Search ticker (e.g. TSLA, NVDA)..."
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    className="flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                />
                <button
                    type="submit"
                    disabled={!searchInput.trim() || isLoading}
                    className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-4 py-2"
                >
                    <Search className="w-4 h-4 mr-2" />
                    Analyze
                </button>
            </form>

            {/* Loading / Error States */}
            {isLoading && (
                <div className="flex justify-center items-center py-12">
                    <div className="w-8 h-8 rounded-full border-4 border-primary border-t-transparent animate-spin" />
                </div>
            )}

            {error && !isLoading && (
                <div className="p-4 bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 rounded-lg">
                    <p className="font-semibold">Failed to fetch sentiment data.</p>
                    <p className="text-sm mt-1">{error.message}</p>
                </div>
            )}

            {/* Data View */}
            {data && !isLoading && !error && (
                <div className="space-y-8">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div className="p-6 bg-card text-card-foreground shadow-sm rounded-xl border flex flex-col items-center justify-center">
                            <h3 className="text-sm font-medium text-muted-foreground mb-1">Retail Sentiment Score</h3>
                            <div className="text-5xl font-black bg-clip-text text-transparent bg-gradient-to-br from-primary to-primary/60">
                                {data.summary.retail_sentiment_score}
                            </div>
                            <p className="text-xs text-muted-foreground mt-2">0 (Bearish) - 100 (Bullish)</p>
                        </div>

                        <div className="p-6 bg-card text-card-foreground shadow-sm rounded-xl border flex flex-col items-center justify-center">
                            <h3 className="text-sm font-medium text-muted-foreground mb-1">Total Mentions (30d)</h3>
                            <div className="text-4xl font-bold">
                                {data.summary.total_mentions}
                            </div>
                        </div>

                        <div className="p-6 bg-card text-card-foreground shadow-sm rounded-xl border flex flex-col lg:row-span-2">
                            <h3 className="text-sm font-medium text-muted-foreground mb-4 text-center">Sentiment Breakdown</h3>
                            <div className="flex-1 w-full min-h-[250px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={chartData}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={60}
                                            outerRadius={80}
                                            paddingAngle={5}
                                            dataKey="value"
                                        >
                                            {chartData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            formatter={(value: number) => `${value.toFixed(1)}%`}
                                            contentStyle={{ borderRadius: '8px', border: '1px solid hsl(var(--border))', backgroundColor: 'hsl(var(--card))' }}
                                        />
                                        <Legend verticalAlign="bottom" height={36} />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>

                    {/* Comments Section */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 pt-4">
                        <div className="space-y-4">
                            <div className="flex items-center gap-2 border-b pb-2">
                                <div className="w-3 h-3 rounded-full bg-green-500" />
                                <h2 className="text-xl font-semibold">Top Bullish Vibes</h2>
                            </div>
                            <CommentList comments={data.top_bullish} type="bullish" />
                        </div>

                        <div className="space-y-4">
                            <div className="flex items-center gap-2 border-b pb-2">
                                <div className="w-3 h-3 rounded-full bg-red-500" />
                                <h2 className="text-xl font-semibold">Top Bearish Vibes</h2>
                            </div>
                            <CommentList comments={data.top_bearish} type="bearish" />
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
