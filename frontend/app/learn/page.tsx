"use client";

/**
 * /learn — Sprint 30 redesign
 *
 * Structured learn hub with:
 *   1. Six "module" intro cards (GAS Methodology, FinBERT, Technical Consensus,
 *      Conflict Detector, Backtesting Pitfalls, Macro 101) — always visible
 *   2. Category filter tabs
 *   3. Article grid from CMS (unchanged data fetching)
 *
 * Source: todos.md §2 🟠 + todos-v3.md §8 🟠
 */

import { useState, useMemo } from "react";
import useSWR from "swr";
import Link from "next/link";
import { BlogCard } from "@/components/learn/BlogCard";
import {
  BookOpen, Loader2, Zap, Globe, BarChart2,
  TrendingUp, Shield, FlaskConical, ArrowRight,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Post {
  slug: string;
  title: string;
  summary: string;
  readTime: string;
  date: string;
  category: string;
}

// ─── Data fetching ────────────────────────────────────────────────────────────

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchPosts(): Promise<Post[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/cms/posts/published`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to load posts");
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

// ─── Hub module cards ─────────────────────────────────────────────────────────

interface Module {
  icon: React.ReactNode;
  title: string;
  description: string;
  category: string;          // maps to article category filter
  color: string;
  bgColor: string;
  borderColor: string;
}

const MODULES: Module[] = [
  {
    icon: <Zap className="h-5 w-5" />,
    title: "GAS Methodology",
    description:
      "How the Global Alignment Score combines Technical ML, Sentiment, and Macro into a single 0–100 signal. Understand what moves it and how to interpret the weather labels.",
    category: "GAS & Regimes",
    color: "text-sky-400",
    bgColor: "bg-sky-950/30",
    borderColor: "border-sky-800/40",
  },
  {
    icon: <BookOpen className="h-5 w-5" />,
    title: "FinBERT & Sentiment",
    description:
      "How Fin-Eye uses FinBERT (a financial BERT model) to score news headlines as Bullish, Bearish, or Neutral — and how the 1d/7d/30d averages are derived.",
    category: "Sentiment",
    color: "text-violet-400",
    bgColor: "bg-violet-950/30",
    borderColor: "border-violet-800/40",
  },
  {
    icon: <BarChart2 className="h-5 w-5" />,
    title: "Technical Consensus",
    description:
      "How multi-timeframe ML models (XGBoost, LightGBM, ensemble) are trained, scored by Sharpe ratio, and blended into a Sharpe-weighted directional consensus.",
    category: "GAS & Regimes",
    color: "text-emerald-400",
    bgColor: "bg-emerald-950/30",
    borderColor: "border-emerald-800/40",
  },
  {
    icon: <Shield className="h-5 w-5" />,
    title: "Conflict Detector",
    description:
      "When Technical, Sentiment, and Macro disagree — the Conflict Detector surfaces divergences. Learn how to read split signals and when to wait for alignment.",
    category: "GAS & Regimes",
    color: "text-amber-400",
    bgColor: "bg-amber-950/30",
    borderColor: "border-amber-800/40",
  },
  {
    icon: <FlaskConical className="h-5 w-5" />,
    title: "Backtesting Pitfalls",
    description:
      "Survivorship bias, look-ahead bias, overfitting, and why a great backtest doesn't mean a great strategy. How walk-forward validation guards against false confidence.",
    category: "Backtesting",
    color: "text-rose-400",
    bgColor: "bg-rose-950/30",
    borderColor: "border-rose-800/40",
  },
  {
    icon: <Globe className="h-5 w-5" />,
    title: "Macro 101",
    description:
      "What yield curve inversion means, how VIX drives regime detection, and why the Fed Funds rate matters to equities. The macro layer in plain English.",
    category: "Macro 101",
    color: "text-teal-400",
    bgColor: "bg-teal-950/30",
    borderColor: "border-teal-800/40",
  },
];

// ─── Category config ──────────────────────────────────────────────────────────

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

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LearnPage() {
  const { data: posts, error, isLoading } = useSWR<Post[]>("learn-posts", fetchPosts, {
    revalidateOnFocus: false,
  });

  const [activeCategory, setActiveCategory] = useState("All");

  const categories = useMemo(() => {
    if (!posts) return ["All"];
    const cats = Array.from(new Set(posts.map((p) => p.category)));
    cats.sort((a, b) => getCategoryOrder(a) - getCategoryOrder(b));
    return ["All", ...cats];
  }, [posts]);

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

  // Filter modules by active category
  const visibleModules =
    activeCategory === "All"
      ? MODULES
      : MODULES.filter((m) => m.category === activeCategory);

  return (
    <div className="max-w-6xl mx-auto space-y-10">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="border-b border-slate-800 pb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-sky-950/40 border border-sky-800/40">
            <BookOpen className="h-5 w-5 text-sky-400" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Learn Hub</h1>
        </div>
        <p className="text-sm text-slate-400 max-w-2xl">
          Master the concepts behind Fin-Eye — from how the GAS score is computed to
          how to avoid backtesting pitfalls. Start with the modules below, then read
          the in-depth articles.
        </p>
      </div>

      {/* ── Module cards ───────────────────────────────────────────────── */}
      {visibleModules.length > 0 && (
        <section className="space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600">
            {activeCategory === "All" ? "Core Concepts" : `${activeCategory} — Overview`}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {visibleModules.map((mod) => (
              <button
                key={mod.title}
                onClick={() => setActiveCategory(mod.category)}
                className={`group text-left rounded-xl border p-4 space-y-2 transition-all hover:brightness-110 ${mod.bgColor} ${mod.borderColor}`}
              >
                <div className="flex items-center justify-between">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900/50 border border-slate-700/40 ${mod.color}`}>
                    {mod.icon}
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-slate-600 group-hover:text-slate-400 transition-colors" />
                </div>
                <div>
                  <p className={`text-sm font-semibold ${mod.color}`}>{mod.title}</p>
                  <p className="text-[11px] text-slate-500 leading-relaxed mt-0.5 line-clamp-3">
                    {mod.description}
                  </p>
                </div>
                <p className="text-[10px] text-slate-600 group-hover:text-slate-400 transition-colors">
                  View {mod.category} articles →
                </p>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* ── Category filter ─────────────────────────────────────────────── */}
      {!isLoading && !error && (
        <section className="space-y-3">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-slate-600">Articles</p>
          <div className="flex flex-wrap gap-1.5">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                  activeCategory === cat
                    ? cat === "Case Studies"
                      ? "bg-violet-600 text-white"
                      : "bg-sky-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                }`}
              >
                {cat}
                {posts && (
                  <span className="ml-1.5 text-[10px] opacity-60">
                    {cat === "All"
                      ? posts.length
                      : posts.filter((p) => p.category === cat).length}
                  </span>
                )}
              </button>
            ))}
          </div>
        </section>
      )}

      {/* ── Case Studies hero ───────────────────────────────────────────── */}
      {activeCategory === "Case Studies" && !isLoading && (
        <div className="flex gap-4 items-start rounded-2xl border border-violet-700/30 bg-violet-950/20 px-6 py-5">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-violet-900/40 border border-violet-700/30">
            <BookOpen className="h-5 w-5 text-violet-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-violet-200 mb-1">Historical Case Studies</h2>
            <p className="text-sm text-violet-300/70 leading-relaxed">
              Deep retrospective analyses showing how Fin-Eye&#39;s GAS, macro indicators, and sentiment
              signals would have behaved during major historical crises — including 2008 and 2020.
              Written with{" "}
              <span className="font-medium text-violet-300">full hindsight caveats</span>{" "}
              for educational purposes only.
            </p>
          </div>
        </div>
      )}

      {/* ── Loading / error / empty ─────────────────────────────────────── */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
        </div>
      )}

      {error && (
        <div className="py-12 text-center">
          <p className="text-sm text-rose-400">Unable to load articles. Check backend connectivity.</p>
        </div>
      )}

      {!isLoading && !error && filtered.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <BookOpen className="h-8 w-8 text-slate-700" />
          <p className="text-slate-500">No articles in this category yet.</p>
          <button
            onClick={() => setActiveCategory("All")}
            className="text-xs text-sky-400 hover:text-sky-300 transition-colors"
          >
            View all articles →
          </button>
        </div>
      )}

      {/* ── Article grid ─────────────────────────────────────────────────── */}
      {!isLoading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((post) => (
            <BlogCard key={post.slug} {...post} />
          ))}
        </div>
      )}

      {/* ── Footer disclaimer ───────────────────────────────────────────── */}
      <p className="text-[10px] text-slate-700 border-t border-slate-800/50 pt-4">
        All content is for educational purposes only and does not constitute investment advice.
      </p>
    </div>
  );
}
