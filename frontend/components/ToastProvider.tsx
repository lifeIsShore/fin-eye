/**
 * components/ToastProvider.tsx
 *
 * todos-v3.md UX-UI-02 — Global toast / snackbar system.
 *
 * Usage anywhere in the app:
 *   const { toast } = useToast();
 *   toast({ title: "Saved!", type: "success" });
 *   toast({ title: "API error", description: "Retry in 30s", type: "error", duration: 6000 });
 *
 * Types: "success" | "error" | "warning" | "info"
 * Auto-dismiss after `duration` ms (default 4000).
 * Max 5 toasts visible at once — oldest auto-removed.
 *
 * Wire into layout.tsx by wrapping children with <ToastProvider>.
 */

"use client";

import React, {
    createContext,
    useCallback,
    useContext,
    useState,
    useEffect,
    useRef,
} from "react";
import { X, CheckCircle2, AlertCircle, AlertTriangle, Info } from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastOptions {
    title: string;
    description?: string;
    type?: ToastType;
    /** Duration in ms before auto-dismiss. 0 = never auto-dismiss. Default 4000. */
    duration?: number;
}

interface ToastEntry extends ToastOptions {
    id: string;
    type: ToastType;
    duration: number;
    createdAt: number;
}

interface ToastContextValue {
    toast: (opts: ToastOptions) => void;
    dismiss: (id: string) => void;
}

// ── Context ───────────────────────────────────────────────────────────────────

const ToastContext = createContext<ToastContextValue>({
    toast: () => {},
    dismiss: () => {},
});

export function useToast() {
    return useContext(ToastContext);
}

// ── Toast item ────────────────────────────────────────────────────────────────

const ICONS: Record<ToastType, React.ReactNode> = {
    success: <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0 mt-0.5" />,
    error:   <AlertCircle  className="h-4 w-4 text-rose-400    flex-shrink-0 mt-0.5" />,
    warning: <AlertTriangle className="h-4 w-4 text-amber-400  flex-shrink-0 mt-0.5" />,
    info:    <Info          className="h-4 w-4 text-sky-400     flex-shrink-0 mt-0.5" />,
};

const BORDER: Record<ToastType, string> = {
    success: "border-emerald-800/50 bg-emerald-950/40",
    error:   "border-rose-800/50    bg-rose-950/40",
    warning: "border-amber-800/50   bg-amber-950/40",
    info:    "border-sky-800/50     bg-sky-950/40",
};

function ToastItem({
    entry,
    onDismiss,
}: {
    entry: ToastEntry;
    onDismiss: (id: string) => void;
}) {
    const [visible, setVisible] = useState(false);

    // Animate in
    useEffect(() => {
        const t = setTimeout(() => setVisible(true), 10);
        return () => clearTimeout(t);
    }, []);

    const handleDismiss = () => {
        setVisible(false);
        setTimeout(() => onDismiss(entry.id), 300);
    };

    return (
        <div
            className={`
                flex items-start gap-3 rounded-xl border px-4 py-3 shadow-2xl backdrop-blur-sm
                transition-all duration-300 ease-out min-w-[280px] max-w-[400px]
                ${BORDER[entry.type]}
                ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"}
            `}
        >
            {ICONS[entry.type]}
            <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-100 leading-tight">{entry.title}</p>
                {entry.description && (
                    <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{entry.description}</p>
                )}
            </div>
            <button
                onClick={handleDismiss}
                className="text-slate-500 hover:text-slate-300 transition-colors flex-shrink-0 ml-1"
                aria-label="Dismiss"
            >
                <X className="h-3.5 w-3.5" />
            </button>
        </div>
    );
}

// ── Provider ──────────────────────────────────────────────────────────────────

const MAX_TOASTS = 5;
const DEFAULT_DURATION = 4000;

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<ToastEntry[]>([]);
    const counterRef = useRef(0);

    const toast = useCallback((opts: ToastOptions) => {
        const id = `toast-${++counterRef.current}`;
        const entry: ToastEntry = {
            id,
            title:       opts.title,
            description: opts.description,
            type:        opts.type ?? "info",
            duration:    opts.duration ?? DEFAULT_DURATION,
            createdAt:   Date.now(),
        };

        setToasts((prev) => {
            const next = [...prev, entry];
            // If over limit, drop the oldest
            return next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next;
        });

        // Auto-dismiss
        if (entry.duration > 0) {
            setTimeout(() => {
                setToasts((prev) => prev.filter((t) => t.id !== id));
            }, entry.duration);
        }
    }, []);

    const dismiss = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    return (
        <ToastContext.Provider value={{ toast, dismiss }}>
            {children}

            {/* Toast container — bottom-right, above everything */}
            <div
                className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2 pointer-events-none"
                aria-live="polite"
                aria-label="Notifications"
            >
                {toasts.map((entry) => (
                    <div key={entry.id} className="pointer-events-auto">
                        <ToastItem entry={entry} onDismiss={dismiss} />
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}
