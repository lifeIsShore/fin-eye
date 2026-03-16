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
} from "lucide-react";

// ─── Category colours ────────────────────────────────────────────────────────

const CATEGORY_STYLES: Record<string, string> = {
    "Templates":       "bg-sky-900/30 text-sky-300 border-sky-700/30",
    "Portfolio Tools": "bg-violet-900/30 text-violet-300 border-violet-700/30",
    "Education":       "bg-emerald-900/30 text-emerald-300 border-emerald-700/30",
    "Workflow":        "bg-amber-900/30 text-amber-300 border-amber-700/30",
    "Integrations":    "bg-rose-900/30 text-rose-300 border-rose-700/30",
    "General":         "bg-slate-800 text-slate-300 border-slate-700",
    // legacy support
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
    // legacy
    "Planning Tools":  "bg-violet-600 text-white",
    "Educational":     "bg-emerald-600 text-white",
};

// ─── Detail Modal ─────────────────────────────────────────────────────────────

function ProductModal({
    product,
    onClose,
}: {
    product: ShowcaseProductDto;
    onClose: () => void;
}) {
    // Track detail-open once on mount
    useEffect(() => {
        trackShowcaseClick(product.id, "detail");
    }, [product.id]);

    const handleBuy = useCallback(() => {
        trackShowcaseClick(product.id, "outbound");
        const url = product.external_url.includes("?")
            ? `${product.external_url}&product_id=${product.id}&source=terminal`
            : `${product.external_url}?product_id=${product.id}&source=terminal`;
        window.open(url, "_blank", "noopener,noreferrer");
    }, [product]);

    // Close on backdrop click or Escape
    useEffect(() => {
        function onKey(e: KeyboardEvent) {
            if (e.key === "Escape") onClose();
        }
        window.addEventListener("keydown", onKey);
        return () => window.removeEventListener("keydown", onKey);
    }, [onClose]);

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm"
            onClick={onClose}
        >
            <div
                className="relative w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-start justify-between p-6 pb-4 border-b border-slate-800">
                    <div className="pr-8">
                        <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium mb-2 ${categoryStyle(product.category)}`}>
                            <Tag className="h-3 w-3" />
                            {product.category}
                        </span>
                        <h2 className="text-xl font-bold text-slate-100 leading-tight">
                            {product.title}
                        </h2>
                        <p className="mt-1 text-sm text-slate-400">{product.tagline}</p>
                    </div>
                    <button
                        onClick={onClose}
                        className="flex-shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition-colors"
                        aria-label="Close"
                    >
                        <X className="h-5 w-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-5 max-h-[60vh] overflow-y-auto">
                    <p className="text-sm text-slate-300 leading-relaxed">
                        {product.description}
                    </p>

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

                    {/* Educational disclaimer */}
                    <p className="text-xs text-slate-600 border-t border-slate-800 pt-4">
                        All tools are for educational purposes only and do not constitute
                        investment advice. You will be redirected to an external storefront
                        to complete your purchase.
                    </p>
                </div>

                {/* Footer — price + CTA */}
                <div className="flex items-center justify-between p-6 pt-4 border-t border-slate-800">
                    <span className="text-2xl font-black text-slate-100">
                        {product.price_label}
                    </span>
                    <button
                        onClick={handleBuy}
                        className="flex items-center gap-2 rounded-lg bg-sky-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-sky-500 transition-colors"
                    >
                        Buy now
                        <ExternalLink className="h-4 w-4" />
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
}: {
    product: ShowcaseProductDto;
    onOpen: (p: ShowcaseProductDto) => void;
}) {
    // Track card view once on mount
    useEffect(() => {
        trackShowcaseClick(product.id, "view");
    }, [product.id]);

    return (
        <div className="flex flex-col rounded-2xl border border-slate-800 bg-slate-900/50 hover:border-slate-700 transition-colors">
            {/* Card body */}
            <div className="flex-1 p-6">
                <div className="flex items-start justify-between mb-3">
                    <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium ${categoryStyle(product.category)}`}>
                        <Tag className="h-3 w-3" />
                        {product.category}
                    </span>
                    <span className="text-sm font-bold text-slate-200">
                        {product.price_label}
                    </span>
                </div>

                <h3 className="text-base font-bold text-slate-100 mb-1 leading-snug">
                    {product.title}
                </h3>
                <p className="text-sm text-slate-400 line-clamp-2 mb-4">
                    {product.tagline}
                </p>

                {/* Feature preview — first 3 */}
                {product.features.length > 0 && (
                    <ul className="space-y-1.5 mb-4">
                        {product.features.slice(0, 3).map((f, i) => (
                            <li key={i} className="flex items-start gap-2 text-xs text-slate-500">
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500/70 flex-shrink-0 mt-0.5" />
                                {f}
                            </li>
                        ))}
                        {product.features.length > 3 && (
                            <li className="text-xs text-slate-600 pl-5">
                                +{product.features.length - 3} more…
                            </li>
                        )}
                    </ul>
                )}
            </div>

            {/* Card footer */}
            <div className="px-6 pb-5">
                <button
                    onClick={() => onOpen(product)}
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-700 hover:text-white transition-colors"
                >
                    View details
                    <ChevronRight className="h-4 w-4 text-slate-400" />
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

    // Build category list from data
    const categories = useMemo(() => {
        if (!products) return ["All"];
        const cats = Array.from(new Set(products.map((p) => p.category)));
        cats.sort(
            (a, b) =>
                (CATEGORY_ORDER.indexOf(a) === -1 ? 99 : CATEGORY_ORDER.indexOf(a)) -
                (CATEGORY_ORDER.indexOf(b) === -1 ? 99 : CATEGORY_ORDER.indexOf(b)),
        );
        return ["All", ...cats];
    }, [products]);

    const filtered = useMemo(() => {
        if (!products) return [];
        let list = activeCategory === "All" ? products : products.filter((p) => p.category === activeCategory);
        if (priceFilter === "free") list = list.filter((p) => p.price_label.toLowerCase() === "free");
        if (priceFilter === "paid") list = list.filter((p) => p.price_label.toLowerCase() !== "free");
        return list;
    }, [products, activeCategory, priceFilter]);

    return (
        <div className="space-y-8">
            <PageBanner
                icon={<ShoppingBag className="h-5 w-5" />}
                title="Pro Tools"
                description="Curated templates, calculators, and guides to complement your Fin-Eye workflow. Educational use only."
                badge={products ? `${products.length} Products` : undefined}
                badgeColor="sky"
            />

            {/* ── Filters ─────────────────────────────────────────────────── */}
            {!isLoading && !error && (
                <div className="flex flex-wrap items-center gap-3">
                    {/* Price filter */}
                    <div className="flex gap-1 rounded-lg bg-slate-900 border border-slate-800 p-1">
                        {(["all", "free", "paid"] as const).map((f) => (
                            <button key={f} onClick={() => setPriceFilter(f)}
                                className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
                                    priceFilter === f
                                        ? "bg-slate-700 text-slate-100"
                                        : "text-slate-500 hover:text-slate-300"
                                }`}>
                                {f === "all" ? "All prices" : f === "free" ? "Free" : "Paid"}
                            </button>
                        ))}
                    </div>

                    <div className="h-4 w-px bg-slate-700 hidden sm:block" />

                    {/* Category filter */}
                    {categories.length > 1 && categories.map((cat) => {
                        const isActive = activeCategory === cat;
                        const activeClass = CATEGORY_FILTER_ACTIVE[cat] ?? "bg-slate-600 text-white";
                        return (
                            <button
                                key={cat}
                                onClick={() => setActiveCategory(cat)}
                                className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                                    isActive
                                        ? activeClass
                                        : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200"
                                }`}
                            >
                                {cat}
                                {!isLoading && products && cat !== "All" && (
                                    <span className="ml-1.5 text-xs opacity-60">
                                        {products.filter((p) => p.category === cat).length}
                                    </span>
                                )}
                                {cat === "All" && products && (
                                    <span className="ml-1.5 text-xs opacity-60">
                                        {products.length}
                                    </span>
                                )}
                            </button>
                        );
                    })}
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
                    Unable to load products. Please try again later.
                </div>
            )}

            {!isLoading && !error && filtered.length === 0 && (
                <div className="py-16 text-center text-slate-500">
                    No products in this category yet.
                </div>
            )}

            {/* ── Product grid ─────────────────────────────────────────────────── */}
            {!isLoading && !error && filtered.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {filtered.map((product) => (
                        <ProductCard
                            key={product.id}
                            product={product}
                            onOpen={setSelectedProduct}
                        />
                    ))}
                </div>
            )}

            {/* ── Disclaimer footer ─────────────────────────────────────────── */}
            {!isLoading && !error && filtered.length > 0 && (
                <p className="text-xs text-slate-600 border-t border-slate-800/50 pt-4">
                    All products listed are for educational and informational purposes only.
                    Fin-Eye does not guarantee results. Clicking &ldquo;Buy now&rdquo; will
                    redirect you to an external storefront. Fin-Eye is not responsible for
                    third-party transactions.
                </p>
            )}

            {/* ── Detail modal ──────────────────────────────────────────────── */}
            {selectedProduct && (
                <ProductModal
                    product={selectedProduct}
                    onClose={() => setSelectedProduct(null)}
                />
            )}
        </div>
    );
}
