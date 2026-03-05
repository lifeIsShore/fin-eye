"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { BlogCard } from "@/components/learn/BlogCard";
import { BookOpen, Loader2 } from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface Post {
    slug: string;
    title: string;
    summary: string;
    readTime: string;
    date: string;
    category: string;
}

// ─── Data fetching ────────────────────────────────────────────────────────────

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchPosts(): Promise<Post[]> {
    const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/published`, {
        cache: "no-store",
    });
    if (!res.ok) throw new Error("Failed to load posts");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const data: any[] = await res.json();
    return data.map((p) => ({
        slug: p.slug,
        title: p.title,
        summary: p.summary,
        readTime: p.read_time,
        date: p.published_at
            ? new Date(p.published_at).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
            })
            : "—",
        category: p.category ?? "General",
    }));
}

// ─── Category definitions (order + display label) ────────────────────────────

const CATEGORY_ORDER = [
    "All",
    "Case Studies",
    "Macro 101",
    "Backtesting",
    "Sentiment",
    "GAS & Regimes",
    "General",
];

function getCategoryOrder(cat: string): number {
    const idx = CATEGORY_ORDER.indexOf(cat);
    return idx === -1 ? CATEGORY_ORDER.length : idx;
}

// ─── Page Component ───────────────────────────────────────────────────────────

export default function LearnPage() {
    const { data: posts, error, isLoading } = useSWR<Post[]>("learn-posts", fetchPosts, {
        revalidateOnFocus: false,
    });

    const [activeCategory, setActiveCategory] = useState("All");

    // Derive sorted, unique category list from posts
    const categories = useMemo(() => {
        if (!posts) return ["All"];
        const cats = Array.from(new Set(posts.map((p) => p.category)));
        cats.sort((a, b) => getCategoryOrder(a) - getCategoryOrder(b));
        return ["All", ...cats];
    }, [posts]);

    // Filter and sort posts
    const filtered = useMemo(() => {
        if (!posts) return [];
        const list =
            activeCategory === "All"
                ? [...posts]
                : posts.filter((p) => p.category === activeCategory);
        return list.sort(
            (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
        );
    }, [posts, activeCategory]);

    return (
        <div className="container mx-auto px-4 py-8 max-w-7xl animate-fade-in-up">
            {/* ── Header ─────────────────────────────────────────────────────── */}
            <div className="mb-10">
                <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-zinc-900 to-zinc-500 dark:from-white dark:to-zinc-400 mb-4">
                    Learn &amp; Insights
                </h1>
                <p className="text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl">
                    Master the concepts behind GAS, explore in-depth case studies of real
                    market crises, and understand how to navigate different regimes.
                </p>
            </div>

            {/* ── Category filter ─────────────────────────────────────────────── */}
            {!isLoading && !error && categories.length > 1 && (
                <div className="mb-8 flex flex-wrap gap-2">
                    {categories.map((cat) => (
                        <button
                            key={cat}
                            onClick={() => setActiveCategory(cat)}
                            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                                activeCategory === cat
                                    ? cat === "Case Studies"
                                        ? "bg-violet-600 text-white"
                                        : "bg-blue-600 text-white"
                                    : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
                            }`}
                        >
                            {cat}
                        </button>
                    ))}
                </div>
            )}

            {/* ── Case Studies hero banner (shown when that category is active) ── */}
            {activeCategory === "Case Studies" && !isLoading && (
                <div className="mb-8 rounded-2xl border border-violet-700/30 bg-violet-950/20 px-6 py-5 flex gap-4 items-start">
                    <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-violet-900/40 border border-violet-700/30">
                        <BookOpen className="h-5 w-5 text-violet-400" />
                    </div>
                    <div>
                        <h2 className="text-base font-semibold text-violet-200 mb-1">
                            Historical Case Studies
                        </h2>
                        <p className="text-sm text-violet-300/70 leading-relaxed">
                            Deep retrospective analyses showing how Fin-Eye&apos;s GAS, macro
                            indicators, and sentiment signals would have behaved during major
                            historical crises — including 2008 and 2020. Written with{" "}
                            <span className="font-medium text-violet-300">full hindsight caveats</span>{" "}
                            for educational purposes only.
                        </p>
                    </div>
                </div>
            )}

            {/* ── States ─────────────────────────────────────────────────────── */}
            {isLoading && (
                <div className="flex items-center justify-center py-24">
                    <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                </div>
            )}

            {error && (
                <div className="py-16 text-center text-sm text-rose-400">
                    Unable to load articles. Please try again later.
                </div>
            )}

            {!isLoading && !error && filtered.length === 0 && (
                <div className="flex flex-col items-center justify-center py-24 text-center">
                    <p className="text-slate-500 text-lg">No articles in this category yet.</p>
                    <p className="text-slate-600 text-sm mt-2">
                        Check back soon — content is on the way.
                    </p>
                </div>
            )}

            {/* ── Grid ───────────────────────────────────────────────────────── */}
            {!isLoading && !error && filtered.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {filtered.map((post) => (
                        <BlogCard key={post.slug} {...post} />
                    ))}
                </div>
            )}
        </div>
    );
}
