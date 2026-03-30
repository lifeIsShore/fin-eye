"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import useSWR from "swr";
import { PageBanner } from "@/components/ui/PageBanner";
import {
    fetchShowcaseProducts,
    trackShowcaseClick,
    ShowcaseProductDto,
} from "@/lib/api";
import {
    X,
    ExternalLink,
    CheckCircle2,
    Loader2,
    ShoppingBag,
    Tag,
    ChevronRight,
    Package,
    Bell,
    BellOff,
    Eye,
    Sparkles,
} from "lucide-react";

// ─── Category colours ────────────────────────────────────────────────────────

const CATEGORY_STYLES: Record<string, string> = {
    "Templates":       "bg-sky-900/30 text-sky-300 border-sky-700/30",
    "Portfolio Tools": "bg-violet-900/30 text-violet-300 border-violet-700/30",
    "Education":       "bg-emerald-900/30 text-emerald-300 border-emerald-700/30",
    "Workflow":        "bg-amber-900/30 text-amber-300 border-amber-700/30",
    "Integrations":    "bg-rose-900/30 text-rose-300 border-rose-700/30",
    "General":         "bg-slate-800 text-slate-300 border-slate-700",
    "Planning Tools":  "bg-violet-900/30 text-violet-300 border-violet-700/30",
    "Educational":     "bg-emerald-900/30 text-emerald-300 border-emerald-700/30",
};

function categoryStyle(cat: string): string {
    return CATEGORY_STYLES[cat] ?? CATEGORY_STYLES["General"];
}

const CATEGORY_FILTER_ACTIVE: Record<string, string> = {
    "Templates":       "bg-sky-600 text-white",
    "Portfolio Tools": "bg-violet-600 text-white",
    "Education":       "bg-emerald-600 text-white",
    "Workflow":        "bg-amber-600 text-white",
    "Integrations":    "bg-rose-600 text-white",
    "All":             "bg-slate-600 text-white",
    "Planning Tools":  "bg-violet-600 text-white",
    "Educational":     "bg-emerald-600 text-white",
};

// ─── Coming Soon products ─────────────────────────────────────────────────────

const COMING_SOON = [
    { slug: "fire-calculator",         label: "FIRE Calculator",             icon: "🔥", desc: "Calculate your FI number and savings rate." },
    { slug: "tax-loss-harvesting",     label: "Tax-Loss Harvesting Tracker", icon: "📉", desc: "Identify unrealised losses and offset gains." },
    { slug: "crypto-tax-report",       label: "Crypto Tax Report",           icon: "₿",  desc: "Auto-generate tax reports for crypto trades." },
    { slug: "real-estate-analyzer",    label: "Real Estate Analyzer",        icon: "🏠", desc: "Rental yield, cap rate, and cashflow modeller." },
];

// Removed hardcoded BUNDLE_ITEMS handling as it is now dynamic
// ─── Preview Modal ────────────────────────────────────────────────────────────

function PreviewModal({ previewUrl, onClose }: { previewUrl: string; onClose: () => void }) {
    useEffect(() => {
        const fn = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
        window.addEventListener("keydown", fn);
        return () => window.removeEventListener("keydown", fn);
    }, [onClose]);

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-sm"
            onClick={onClose}
        >
            <div
                className="relative w-full max-w-3xl rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                        <Eye className="h-4 w-4 text-sky-400" />
                        <span className="text-sm font-semibold text-slate-200">Sample Preview</span>
                        <span className="text-[10px] text-amber-400 bg-amber-900/30 border border-amber-800/30 rounded-full px-2 py-0.5">
                            Sample Only
                        </span>
                    </div>
                    <button onClick={onClose} className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition">
                        <X className="h-4 w-4" />
                    </button>
                </div>

                {/* iframe + watermark */}
                <div className="relative h-[60vh]">
                    <iframe
                        src={previewUrl}
                        className="w-full h-full border-0 bg-white"
                        sandbox="allow-same-origin allow-scripts"
                        title="Product preview"
                    />
                    {/* Watermark overlay */}
                    <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                        <div className="rotate-[-35deg] text-white/10 text-7xl font-black tracking-widest select-none">
                            SAMPLE ONLY
                        </div>
                    </div>
                </div>
                <p className="px-5 py-3 text-xs text-slate-600 border-t border-slate-800">
                    This is a watermarked sample. Purchase to unlock the full version.
                </p>
            </div>
        </div>
    );
}

// ─── Investor Bundle Card ─────────────────────────────────────────────────────

function BundleCard({ product, onPreview }: { product: ShowcaseProductDto; onPreview: (url: string) => void }) {
    const [expanded, setExpanded] = useState(false);
    
    // Fallback just in case
    const items = product.bundle_items && product.bundle_items.length > 0 
        ? product.bundle_items 
        : ["Macro Regime Cheat Sheet", "Trade Journal Template", "Sector Rotation Playbook"];

    const previewUrl = product.preview_url ?? null;

    useEffect(() => { trackShowcaseClick(product.id, "view"); }, [product.id]);

    const handleBuy = useCallback(() => {
        trackShowcaseClick(product.id, "outbound");
        const url = product.external_url.includes("?")
            ? `${product.external_url}&product_id=${product.id}&source=terminal`
            : `${product.external_url}?product_id=${product.id}&source=terminal`;
        window.open(url, "_blank", "noopener,noreferrer");
    }, [product]);

    return (
        <div className="rounded-2xl border-2 border-blue-700/40 bg-gradient-to-br from-blue-950/40 to-slate-900/80 p-6 space-y-4">
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                    <div className="rounded-xl bg-blue-700/30 p-2.5">
                        <Package className="h-5 w-5 text-blue-300" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="text-base font-bold text-slate-100">{product.title}</h3>
                            <span className="text-[10px] font-bold text-emerald-300 bg-emerald-900/40 border border-emerald-700/30 rounded-full px-2 py-0.5">
                                Bundle Deal
                            </span>
                        </div>
                        <p className="text-sm text-slate-400 mt-0.5">{product.tagline}</p>
                    </div>
                </div>
                <div className="text-right">
                    <p className="text-xl font-black text-slate-100">{product.price_label}</p>
                </div>
            </div>

            <p className="text-sm text-slate-300 leading-relaxed">{product.description}</p>

            <button
                onClick={() => setExpanded(v => !v)}
                className="flex items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300 transition"
            >
                <ChevronRight className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-90" : ""}`} />
                {expanded ? "Hide" : "See"} what's included ({items.length} tools)
            </button>

            {expanded && (
                <ul className="space-y-1.5 pl-1">
                    {items.map((item: string, idx: number) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-slate-300">
                            <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                            {item}
                        </li>
                    ))}
                </ul>
            )}

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
                {previewUrl && (
                    <button
                        onClick={() => onPreview(previewUrl)}
                        className="flex-1 flex w-full items-center justify-center gap-2 rounded-lg border border-sky-800/40 bg-sky-900/20 px-4 py-2.5 text-sm font-medium text-sky-300 hover:bg-sky-900/40 transition-colors"
                    >
                        <Eye className="h-4 w-4" />
                        Preview sample ↗
                    </button>
                )}
                <button 
                    onClick={handleBuy}
                    className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-blue-600 hover:bg-blue-500 px-5 py-2.5 text-sm font-semibold text-white transition-colors">
                    <Sparkles className="h-4 w-4" />
                    Get Bundle
                </button>
            </div>
        </div>
    );
}

// ─── Coming Soon Section ──────────────────────────────────────────────────────

function ComingSoonSection() {
    const [notified, setNotified] = useState<Record<string, boolean>>(() => {
        try {
            return JSON.parse(localStorage.getItem("showcase_notify") ?? "{}");
        } catch { return {}; }
    });

    const toggle = useCallback(async (slug: string) => {
        const next = { ...notified, [slug]: !notified[slug] };
        setNotified(next);
        localStorage.setItem("showcase_notify", JSON.stringify(next));
        // Fire API stub (no-op if endpoint not yet live)
        try {
            await fetch("/api/v1/showcase/notify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ product_slug: slug, notify: !notified[slug] }),
            });
        } catch { /* silently ignore */ }
    }, [notified]);

    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">Coming Soon</h2>
                <span className="text-[10px] text-slate-600 border border-slate-800 rounded-full px-2 py-0.5">
                    Notify me when ready
                </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {COMING_SOON.map(item => {
                    const on = !!notified[item.slug];
                    return (
                        <div
                            key={item.slug}
                            className="rounded-xl border border-dashed border-slate-700/60 bg-slate-900/30 p-4 space-y-2"
                        >
                            <div className="text-2xl">{item.icon}</div>
                            <p className="text-sm font-semibold text-slate-300">{item.label}</p>
                            <p className="text-xs text-slate-500 leading-relaxed">{item.desc}</p>
                            <button
                                onClick={() => toggle(item.slug)}
                                className={`mt-1 flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all ${
                                    on
                                        ? "bg-sky-900/40 border border-sky-700/40 text-sky-300"
                                        : "bg-slate-800 border border-slate-700/40 text-slate-500 hover:text-slate-300"
                                }`}
                            >
                                {on ? <Bell className="h-3 w-3" /> : <BellOff className="h-3 w-3" />}
                                {on ? "Notifying me" : "Notify me"}
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ─── Detail Modal ─────────────────────────────────────────────────────────────

function ProductModal({ product, onClose }: { product: ShowcaseProductDto; onClose: () => void }) {
    useEffect(() => { trackShowcaseClick(product.id, "detail"); }, [product.id]);

    const handleBuy = useCallback(() => {
        trackShowcaseClick(product.id, "outbound");
        const url = product.external_url.includes("?")
            ? `${product.external_url}&product_id=${product.id}&source=terminal`
            : `${product.external_url}?product_id=${product.id}&source=terminal`;
        window.open(url, "_blank", "noopener,noreferrer");
    }, [product]);

    useEffect(() => {
        const fn = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
        window.addEventListener("keydown", fn);
        return () => window.removeEventListener("keydown", fn);
    }, [onClose]);

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
            onClick={onClose}
        >
            <div
                className="relative w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
                onClick={e => e.stopPropagation()}
            >
                <div className="flex items-start justify-between p-6 pb-4 border-b border-slate-800">
                    <div className="pr-8">
                        <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium mb-2 ${categoryStyle(product.category)}`}>
                            <Tag className="h-3 w-3" />
                            {product.category}
                        </span>
                        <h2 className="text-xl font-bold text-slate-100 leading-tight">{product.title}</h2>
                        <p className="mt-1 text-sm text-slate-400">{product.tagline}</p>
                    </div>
                    <button onClick={onClose} className="flex-shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition-colors">
                        <X className="h-5 w-5" />
                    </button>
                </div>

                <div className="p-6 space-y-5 max-h-[60vh] overflow-y-auto">
                    <p className="text-sm text-slate-300 leading-relaxed">{product.description}</p>
                    {product.features.length > 0 && (
                        <div>
                            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                                What&apos;s included
                            </h3>
                            <ul className="space-y-2">
                                {product.features.map((f, i) => (
                                    <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                                        <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                                        {f}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                    <p className="text-xs text-slate-600 border-t border-slate-800 pt-4">
                        All tools are for educational purposes only and do not constitute investment advice.
                        You will be redirected to an external storefront to complete your purchase.
                    </p>
                </div>

                <div className="flex items-center justify-between p-6 pt-4 border-t border-slate-800">
                    <span className="text-2xl font-black text-slate-100">{product.price_label}</span>
                    <button
                        onClick={handleBuy}
                        className="flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-sky-500 transition-colors"
                    >
                        Buy now <ExternalLink className="h-4 w-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}

// ─── Product Card ─────────────────────────────────────────────────────────────

function ProductCard({
    product,
    onOpen,
    onPreview,
}: {
    product: ShowcaseProductDto;
    onOpen: (p: ShowcaseProductDto) => void;
    onPreview: (url: string) => void;
}) {
    useEffect(() => { trackShowcaseClick(product.id, "view"); }, [product.id]);

    // Derive a preview URL
    const previewUrl = product.preview_url ?? null;

    return (
        <div className="flex flex-col rounded-2xl border border-slate-800 bg-slate-900/50 hover:border-slate-700 transition-colors">
            <div className="flex-1 p-6">
                <div className="flex items-start justify-between mb-3">
                    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${categoryStyle(product.category)}`}>
                        <Tag className="h-3 w-3" />
                        {product.category}
                    </span>
                    <span className="text-sm font-bold text-slate-200">{product.price_label}</span>
                </div>

                <h3 className="text-base font-bold text-slate-100 mb-1 leading-snug">{product.title}</h3>
                <p className="text-sm text-slate-400 line-clamp-2 mb-4">{product.tagline}</p>

                {product.features.length > 0 && (
                    <ul className="space-y-1.5 mb-4">
                        {product.features.slice(0, 3).map((f, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-slate-500">
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500/70 flex-shrink-0 mt-0.5" />
                                {f}
                            </li>
                        ))}
                        {product.features.length > 3 && (
                            <li className="text-xs text-slate-600 pl-5">+{product.features.length - 3} more…</li>
                        )}
                    </ul>
                )}
            </div>

            <div className="px-6 pb-5 space-y-2">
                {previewUrl && (
                    <button
                        onClick={() => onPreview(previewUrl)}
                        className="flex w-full items-center justify-center gap-2 rounded-lg border border-sky-800/40 bg-sky-900/20 px-4 py-1.5 text-xs font-medium text-sky-300 hover:bg-sky-900/40 transition-colors"
                    >
                        <Eye className="h-3.5 w-3.5" />
                        Preview sample ↗
                    </button>
                )}
                <button
                    onClick={() => onOpen(product)}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-colors"
                >
                    View details <ChevronRight className="h-4 w-4 text-slate-400" />
                </button>
            </div>
        </div>
    );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const CATEGORY_ORDER = ["All", "Templates", "Portfolio Tools", "Education", "Workflow", "Integrations", "General", "Planning Tools", "Educational"];

export default function ShowcasePage() {
    const { data: products, error, isLoading } = useSWR<ShowcaseProductDto[]>(
        "showcase-products",
        () => fetchShowcaseProducts(),
        { revalidateOnFocus: false },
    );

    const [activeCategory, setActiveCategory] = useState("All");
    const [priceFilter, setPriceFilter] = useState<"all" | "free" | "paid">("all");
    const [selectedProduct, setSelectedProduct] = useState<ShowcaseProductDto | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    const categories = useMemo(() => {
        if (!products) return ["All"];
        const cats = Array.from(new Set(products.map(p => p.category)));
        cats.sort((a, b) =>
            (CATEGORY_ORDER.indexOf(a) === -1 ? 99 : CATEGORY_ORDER.indexOf(a)) -
            (CATEGORY_ORDER.indexOf(b) === -1 ? 99 : CATEGORY_ORDER.indexOf(b)),
        );
        return ["All", ...cats];
    }, [products]);

    const filtered = useMemo(() => {
        if (!products) return [];
        let list = activeCategory === "All" ? products : products.filter(p => p.category === activeCategory);
        if (priceFilter === "free") list = list.filter(p => p.price_label.toLowerCase() === "free");
        if (priceFilter === "paid") list = list.filter(p => p.price_label.toLowerCase() !== "free");
        return list;
    }, [products, activeCategory, priceFilter]);

    const bundles = useMemo(() => filtered.filter(p => p.is_bundle), [filtered]);
    const regularProducts = useMemo(() => filtered.filter(p => !p.is_bundle), [filtered]);

    return (
        <div className="space-y-10">
            <PageBanner
                icon={<ShoppingBag className="h-5 w-5" />}
                title="Pro Tools"
                description="Curated templates, calculators, and guides to complement your Fin-Eye workflow. Educational use only."
                badge={products ? `${products.length} Products` : undefined}
                badgeColor="sky"
            />

            {/* ── Investor Bundle(s) ──────────────────────────────────────────── */}
            {!isLoading && !error && bundles.length > 0 && (
                <div className="space-y-4">
                    {bundles.map(b => (
                        <BundleCard key={b.id} product={b} onPreview={setPreviewUrl} />
                    ))}
                </div>
            )}

            {/* ── Filters ──────────────────────────────────────────────────── */}
            {!isLoading && !error && (
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex gap-1 rounded-lg bg-slate-900 border border-slate-800 p-1">
                        {(["all", "free", "paid"] as const).map(f => (
                            <button key={f} onClick={() => setPriceFilter(f)}
                                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                                    priceFilter === f ? "bg-slate-700 text-slate-100" : "text-slate-500 hover:text-slate-300"
                                }`}>
                                {f === "all" ? "All prices" : f === "free" ? "Free" : "Paid"}
                            </button>
                        ))}
                    </div>
                    <div className="h-4 w-px bg-slate-700 hidden sm:block" />
                    {categories.length > 1 && categories.map(cat => {
                        const isActive = activeCategory === cat;
                        const activeClass = CATEGORY_FILTER_ACTIVE[cat] ?? "bg-slate-600 text-white";
                        return (
                            <button
                                key={cat}
                                onClick={() => setActiveCategory(cat)}
                                className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                                    isActive ? activeClass : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                                }`}
                            >
                                {cat}
                                {!isLoading && products && cat !== "All" && (
                                    <span className="ml-1.5 text-xs opacity-60">{products.filter(p => p.category === cat).length}</span>
                                )}
                                {cat === "All" && products && (
                                    <span className="ml-1.5 text-xs opacity-60">{products.length}</span>
                                )}
                            </button>
                        );
                    })}
                </div>
            )}

            {/* ── States ───────────────────────────────────────────────────── */}
            {isLoading && (
                <div className="flex items-center justify-center py-24">
                    <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                </div>
            )}
            {error && <div className="py-16 text-center text-sm text-rose-400">Unable to load products. Please try again later.</div>}
            {!isLoading && !error && filtered.length === 0 && (
                <div className="py-16 text-center text-slate-500">No products in this category yet.</div>
            )}

            {/* ── Product grid ─────────────────────────────────────────────── */}
            {!isLoading && !error && regularProducts.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {regularProducts.map(product => (
                        <ProductCard
                            key={product.id}
                            product={product}
                            onOpen={setSelectedProduct}
                            onPreview={setPreviewUrl}
                        />
                    ))}
                </div>
            )}

            {/* ── Coming Soon ───────────────────────────────────────────────── */}
            <ComingSoonSection />

            {/* ── Disclaimer ───────────────────────────────────────────────── */}
            {!isLoading && !error && filtered.length > 0 && (
                <p className="text-xs text-slate-600 border-t border-slate-800/50 pt-4">
                    All products listed are for educational and informational purposes only.
                    Fin-Eye does not guarantee results. Clicking &ldquo;Buy now&rdquo; will redirect you to an external storefront.
                    Fin-Eye is not responsible for third-party transactions.
                </p>
            )}

            {/* ── Modals ───────────────────────────────────────────────────── */}
            {selectedProduct && (
                <ProductModal product={selectedProduct} onClose={() => setSelectedProduct(null)} />
            )}
            {previewUrl && (
                <PreviewModal previewUrl={previewUrl} onClose={() => setPreviewUrl(null)} />
            )}
        </div>
    );
}
