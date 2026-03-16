"use client";

import React from "react";

interface PageBannerAction {
    label: string;
    onClick?: () => void;
    href?: string;
    variant?: "primary" | "secondary";
}

interface PageBannerProps {
    icon: React.ReactNode;
    title: string;
    description: string;
    badge?: string;
    badgeColor?: "sky" | "emerald" | "amber" | "rose" | "violet";
    actions?: PageBannerAction[];
    /** Right-side slot for e.g. freshness indicator */
    meta?: React.ReactNode;
}

const BADGE_STYLES: Record<string, string> = {
    sky:     "bg-sky-900/40 text-sky-300 border-sky-700/40",
    emerald: "bg-emerald-900/40 text-emerald-300 border-emerald-700/40",
    amber:   "bg-amber-900/40 text-amber-300 border-amber-700/40",
    rose:    "bg-rose-900/40 text-rose-300 border-rose-700/40",
    violet:  "bg-violet-900/40 text-violet-300 border-violet-700/40",
};

export function PageBanner({
    icon,
    title,
    description,
    badge,
    badgeColor = "sky",
    actions = [],
    meta,
}: PageBannerProps) {
    return (
        <div className="mb-6 flex flex-col gap-3 border-b border-slate-800 pb-5 sm:flex-row sm:items-start sm:justify-between">
            {/* Left: icon + title + description */}
            <div className="flex items-start gap-3 min-w-0">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-slate-800 border border-slate-700 text-sky-400">
                    {icon}
                </div>
                <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <h1 className="text-2xl font-black tracking-tight text-slate-100">
                            {title}
                        </h1>
                        {badge && (
                            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide ${BADGE_STYLES[badgeColor]}`}>
                                {badge}
                            </span>
                        )}
                    </div>
                    <p className="mt-0.5 text-sm text-slate-400 leading-relaxed">
                        {description}
                    </p>
                </div>
            </div>

            {/* Right: actions + meta */}
            {(actions.length > 0 || meta) && (
                <div className="flex flex-shrink-0 flex-col items-start gap-2 sm:items-end">
                    {meta && <div className="text-xs text-slate-500">{meta}</div>}
                    {actions.length > 0 && (
                        <div className="flex flex-wrap gap-2">
                            {actions.map((action, i) => {
                                const base = "rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors";
                                const style =
                                    action.variant === "primary"
                                        ? `${base} bg-sky-600 text-white hover:bg-sky-500`
                                        : `${base} border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-slate-100`;

                                if (action.href) {
                                    return (
                                        <a key={i} href={action.href} className={style}>
                                            {action.label}
                                        </a>
                                    );
                                }
                                return (
                                    <button key={i} onClick={action.onClick} className={style}>
                                        {action.label}
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
