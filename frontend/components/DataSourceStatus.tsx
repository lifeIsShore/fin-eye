"use client";

/**
 * components/DataSourceStatus.tsx — Sprint 32
 *
 * Reusable banner shown when a data source is unavailable or stale.
 * Replaces silent empty UI with a clear, dismissable message.
 *
 * Usage:
 *   <DataSourceStatus source="Sentiment" error={sentimentError} />
 *   <DataSourceStatus source="Macro (FRED)" error={macroError} description="GAS is computed without the macro layer." />
 *   <DataSourceStatus source="Price data" isStale staleSince="14 min ago" />
 */

import { useState } from "react";
import { AlertTriangle, WifiOff, Clock, X } from "lucide-react";

type StatusVariant = "error" | "stale" | "warning";

interface DataSourceStatusProps {
  /** Short label for the data source, e.g. "Macro (FRED)", "Sentiment", "Price data" */
  source: string;
  /** Truthy = show error banner */
  error?: unknown;
  /** Show a stale-data warning instead of an error */
  isStale?: boolean;
  /** How long ago data was last updated, e.g. "47 min ago" */
  staleSince?: string;
  /** Optional extra context for the user */
  description?: string;
  /** Dismiss callback — if omitted, banner is not dismissable */
  onDismiss?: () => void;
  /** Variant override — inferred from props if omitted */
  variant?: StatusVariant;
  className?: string;
}

const VARIANT_STYLES: Record<StatusVariant, {
  border: string; bg: string; iconColor: string; titleColor: string;
}> = {
  error:   { border: "border-rose-800/40",   bg: "bg-rose-950/15",   iconColor: "text-rose-400",   titleColor: "text-rose-300"   },
  stale:   { border: "border-amber-800/40",  bg: "bg-amber-950/15",  iconColor: "text-amber-400",  titleColor: "text-amber-300"  },
  warning: { border: "border-amber-700/30",  bg: "bg-amber-950/10",  iconColor: "text-amber-400",  titleColor: "text-amber-300"  },
};

const VARIANT_ICONS: Record<StatusVariant, React.ReactNode> = {
  error:   <WifiOff className="h-4 w-4 flex-shrink-0 mt-0.5" />,
  stale:   <Clock className="h-4 w-4 flex-shrink-0 mt-0.5" />,
  warning: <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" />,
};

export function DataSourceStatus({
  source,
  error,
  isStale,
  staleSince,
  description,
  onDismiss,
  variant: variantOverride,
  className = "",
}: DataSourceStatusProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;
  if (!error && !isStale && !variantOverride) return null;

  const variant: StatusVariant = variantOverride
    ?? (isStale ? "stale" : "error");

  const styles = VARIANT_STYLES[variant];
  const icon   = VARIANT_ICONS[variant];

  const defaultDescription =
    variant === "stale"
      ? `Data may be outdated${staleSince ? ` — last updated ${staleSince}` : ""}. The platform is showing the last known values.`
      : `${source} is temporarily unavailable. Some signals may use fallback values or be missing.`;

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  return (
    <div
      className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${styles.border} ${styles.bg} ${className}`}
      role="alert"
    >
      <span className={styles.iconColor}>{icon}</span>

      <div className="flex-1 min-w-0">
        <p className={`text-sm font-semibold ${styles.titleColor}`}>
          {variant === "stale" ? `${source} data may be stale` : `${source} unavailable`}
        </p>
        <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
          {description ?? defaultDescription}
        </p>
        {error instanceof Error && error.message && (
          <p className="text-[10px] text-slate-600 mt-1 font-mono">
            {error.message.slice(0, 120)}
          </p>
        )}
      </div>

      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className="flex-shrink-0 text-slate-600 hover:text-slate-400 transition-colors"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export default DataSourceStatus;
