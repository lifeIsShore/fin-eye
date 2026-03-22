/**
 * components/Tooltip.tsx
 *
 * todos-v3.md UX-EDU-01 — [i] icon tooltips on score widgets.
 *
 * Exports:
 *   Tooltip           — generic wrapper: hover any children to show tooltip text
 *   InfoTooltip       — the standard [i] icon that opens a tooltip on hover/focus
 *   ScoreTooltip      — combines InfoTooltip with a pre-formatted score explanation
 *
 * Usage:
 *   <InfoTooltip text="GAS is a weighted composite of three signal layers." />
 *
 *   <ScoreTooltip
 *     label="GAS"
 *     description="Weighted composite of Technical, Sentiment, and Macro layers."
 *     range="0–100 · Higher = more bullish alignment"
 *   />
 *
 * Design:
 *   - Pure CSS + Tailwind, no library dependency
 *   - Positions above by default, auto-flips to below when near top of viewport
 *   - Accessible: focusable via keyboard (Tab), dismissed with Escape
 *   - Max width 260px, dark slate theme consistent with the rest of the app
 */

"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { Info } from "lucide-react";

// ── Tooltip primitive ─────────────────────────────────────────────────────────

interface TooltipProps {
    children: React.ReactNode;
    content: React.ReactNode;
    /** Preferred side — defaults to "top". Falls back automatically. */
    side?: "top" | "bottom" | "left" | "right";
    className?: string;
}

export function Tooltip({ children, content, side = "top", className = "" }: TooltipProps) {
    const [visible, setVisible] = useState(false);
    const [position, setPosition] = useState<"top" | "bottom">("top");
    const wrapRef = useRef<HTMLDivElement>(null);

    const show = useCallback(() => {
        // Auto-flip: if trigger is in the top 120px of viewport, show below
        if (wrapRef.current) {
            const rect = wrapRef.current.getBoundingClientRect();
            setPosition(rect.top < 120 ? "bottom" : "top");
        }
        setVisible(true);
    }, []);

    const hide = useCallback(() => setVisible(false), []);

    useEffect(() => {
        if (!visible) return;
        function onKey(e: KeyboardEvent) { if (e.key === "Escape") hide(); }
        document.addEventListener("keydown", onKey);
        return () => document.removeEventListener("keydown", onKey);
    }, [visible, hide]);

    const effectiveSide = side === "top" || side === "bottom" ? position : side;

    const positionClasses: Record<string, string> = {
        top:    "bottom-full left-1/2 -translate-x-1/2 mb-2",
        bottom: "top-full   left-1/2 -translate-x-1/2 mt-2",
        left:   "right-full top-1/2  -translate-y-1/2 mr-2",
        right:  "left-full  top-1/2  -translate-y-1/2 ml-2",
    };

    const arrowClasses: Record<string, string> = {
        top:    "top-full  left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-b-transparent border-t-slate-700",
        bottom: "bottom-full left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-t-transparent border-b-slate-700",
        left:   "left-full  top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-r-transparent border-l-slate-700",
        right:  "right-full top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-l-transparent border-r-slate-700",
    };

    return (
        <div
            ref={wrapRef}
            className={`relative inline-flex ${className}`}
            onMouseEnter={show}
            onMouseLeave={hide}
            onFocus={show}
            onBlur={hide}
        >
            {children}

            {visible && (
                <div
                    role="tooltip"
                    className={`
                        absolute z-50 w-max max-w-[260px] rounded-xl border border-slate-700
                        bg-slate-900 px-3 py-2.5 shadow-2xl pointer-events-none
                        ${positionClasses[effectiveSide]}
                    `}
                >
                    {/* Arrow */}
                    <span
                        className={`absolute h-0 w-0 border-4 ${arrowClasses[effectiveSide]}`}
                    />
                    {content}
                </div>
            )}
        </div>
    );
}

// ── InfoTooltip — the standard [i] icon ──────────────────────────────────────

interface InfoTooltipProps {
    text: string;
    /** Optional sub-text shown in smaller type below the main text */
    sub?: string;
    side?: "top" | "bottom" | "left" | "right";
    /** Size of the icon — default "sm" */
    size?: "xs" | "sm" | "md";
    className?: string;
}

const SIZE_CLASSES = {
    xs: "h-3 w-3",
    sm: "h-3.5 w-3.5",
    md: "h-4 w-4",
};

export function InfoTooltip({
    text,
    sub,
    side = "top",
    size = "sm",
    className = "",
}: InfoTooltipProps) {
    return (
        <Tooltip
            side={side}
            content={
                <div className="space-y-1">
                    <p className="text-xs text-slate-200 leading-relaxed">{text}</p>
                    {sub && (
                        <p className="text-[11px] text-slate-400 leading-relaxed">{sub}</p>
                    )}
                </div>
            }
            className={className}
        >
            <button
                type="button"
                tabIndex={0}
                aria-label="More information"
                className="flex items-center justify-center rounded-full text-slate-500 hover:text-slate-300 focus:outline-none focus:ring-1 focus:ring-slate-500 transition-colors"
            >
                <Info className={SIZE_CLASSES[size]} />
            </button>
        </Tooltip>
    );
}

// ── ScoreTooltip — labelled score explanation ─────────────────────────────────

interface ScoreTooltipProps {
    /** Short label e.g. "GAS Score" */
    label: string;
    /** One or two sentence explanation */
    description: string;
    /** e.g. "0–100 · Higher = more bullish" */
    range?: string;
    /** Data source attribution */
    source?: string;
    side?: "top" | "bottom" | "left" | "right";
    size?: "xs" | "sm" | "md";
    className?: string;
}

export function ScoreTooltip({
    label,
    description,
    range,
    source,
    side = "top",
    size = "sm",
    className = "",
}: ScoreTooltipProps) {
    return (
        <Tooltip
            side={side}
            content={
                <div className="space-y-2">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                        {label}
                    </p>
                    <p className="text-xs text-slate-200 leading-relaxed">{description}</p>
                    {range && (
                        <p className="text-[11px] text-slate-400 font-mono">{range}</p>
                    )}
                    {source && (
                        <p className="text-[10px] text-slate-500 border-t border-slate-700/50 pt-1.5">
                            Source: {source}
                        </p>
                    )}
                </div>
            }
            className={className}
        >
            <button
                type="button"
                tabIndex={0}
                aria-label={`About ${label}`}
                className="flex items-center justify-center rounded-full text-slate-500 hover:text-slate-300 focus:outline-none focus:ring-1 focus:ring-slate-500 transition-colors"
            >
                <Info className={SIZE_CLASSES[size]} />
            </button>
        </Tooltip>
    );
}
