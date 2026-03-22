"use client";

/**
 * /settings/notifications — Notification Preferences page (UX-SETTINGS-01)
 *
 * Lets users control:
 *   1. In-app alert triggers    — GAS threshold crossings, model drift alerts
 *   2. Email digest preferences — weekly / bi-weekly / off
 *   3. Marketing emails         — toggle
 *
 * Persists email prefs via PATCH /api/v1/email/preferences.
 * Alert preferences are surfaced read-only (edit via /alerts page for now).
 */

import React, { useState, useCallback } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  Bell,
  Mail,
  Megaphone,
  ChevronLeft,
  CheckCircle2,
  X,
  Loader2,
  BellOff,
  BellRing,
  CalendarClock,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import {
  fetchEmailPreferences,
  updateEmailPreferences,
  fetchAlerts,
  type EmailPreferenceDto,
} from "@/lib/api";

// ── Shared UI helpers ─────────────────────────────────────────────────────────

function SectionCard({
  icon,
  title,
  description,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 space-y-5">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-slate-800 text-slate-400">
          {icon}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{description}</p>
        </div>
      </div>
      {children}
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  disabled = false,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full border transition-colors duration-200 focus:outline-none ${
        disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
      } ${
        checked
          ? "bg-sky-600 border-sky-500"
          : "bg-slate-700 border-slate-600"
      }`}
      aria-checked={checked}
      role="switch"
    >
      <span
        className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform duration-200 ${
          checked ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}

function StatusBanner({
  type,
  message,
}: {
  type: "success" | "error";
  message: string;
}) {
  return (
    <div
      className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${
        type === "success"
          ? "border border-emerald-800/40 bg-emerald-950/30 text-emerald-400"
          : "border border-red-800/40 bg-red-950/30 text-red-400"
      }`}
    >
      {type === "success" ? (
        <CheckCircle2 className="h-3.5 w-3.5 flex-shrink-0" />
      ) : (
        <X className="h-3.5 w-3.5 flex-shrink-0" />
      )}
      {message}
    </div>
  );
}

// ── Digest frequency selector ─────────────────────────────────────────────────

function FrequencyPicker({
  value,
  onChange,
  disabled,
}: {
  value: "weekly" | "biweekly";
  onChange: (v: "weekly" | "biweekly") => void;
  disabled: boolean;
}) {
  const options: { key: "weekly" | "biweekly"; label: string; sub: string }[] = [
    { key: "weekly",   label: "Weekly",    sub: "Every Monday" },
    { key: "biweekly", label: "Bi-weekly", sub: "Every other Monday" },
  ];
  return (
    <div className="flex gap-2 flex-wrap">
      {options.map((o) => (
        <button
          key={o.key}
          onClick={() => !disabled && onChange(o.key)}
          disabled={disabled}
          className={`flex flex-col items-start gap-0.5 rounded-lg border px-3 py-2.5 text-left transition-colors ${
            disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
          } ${
            value === o.key
              ? "border-sky-600 bg-sky-950/40 text-sky-400"
              : "border-slate-700 bg-slate-900/50 text-slate-400 hover:border-slate-600"
          }`}
        >
          <span className="text-xs font-semibold">{o.label}</span>
          <span className="text-[10px] text-slate-500">{o.sub}</span>
        </button>
      ))}
    </div>
  );
}

// ── Active alerts summary (read-only) ────────────────────────────────────────

function AlertsSummary() {
  const { data, isLoading, error, mutate } = useSWR(
    "alerts-active",
    () => fetchAlerts(true),
    { shouldRetryOnError: false },
  );

  const count = data?.total ?? 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-slate-300">
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" />
          ) : error ? (
            <BellOff className="h-3.5 w-3.5 text-slate-600" />
          ) : count > 0 ? (
            <BellRing className="h-3.5 w-3.5 text-sky-400" />
          ) : (
            <BellOff className="h-3.5 w-3.5 text-slate-600" />
          )}
          <span>
            {isLoading
              ? "Loading…"
              : error
              ? "Could not load alerts"
              : count === 0
              ? "No active price or GAS alerts"
              : `${count} active alert${count !== 1 ? "s" : ""}`}
          </span>
        </div>
        <button
          onClick={() => mutate()}
          className="text-slate-600 hover:text-slate-400 transition-colors"
          title="Refresh"
        >
          <RefreshCw className="h-3 w-3" />
        </button>
      </div>

      {!isLoading && !error && count > 0 && (
        <ul className="space-y-1.5">
          {(data?.alerts ?? []).slice(0, 5).map((a) => (
            <li
              key={a.id}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/30 px-3 py-2 text-xs"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-mono font-bold text-slate-200">{a.symbol}</span>
                <span className="text-slate-500 truncate">
                  {a.alert_type.replace(/_/g, " ")} {a.threshold}
                </span>
              </div>
              <span className="text-[10px] text-emerald-400 flex-shrink-0">Active</span>
            </li>
          ))}
          {count > 5 && (
            <p className="text-[10px] text-slate-600 pl-1">
              +{count - 5} more — view all on the Alerts page
            </p>
          )}
        </ul>
      )}

      <Link
        href="/alerts"
        className="inline-flex items-center gap-1.5 text-xs text-sky-400 hover:text-sky-300 font-medium transition-colors"
      >
        Manage alerts <ExternalLink className="h-3 w-3" />
      </Link>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function NotificationsSettingsPage() {
  const [status, setStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [saving, setSaving] = useState(false);

  const {
    data: prefs,
    isLoading,
    mutate,
  } = useSWR("email-prefs", fetchEmailPreferences, { shouldRetryOnError: false });

  const patch = useCallback(
    async (update: Partial<Pick<EmailPreferenceDto, "marketing_opted_in" | "digest_opted_in" | "digest_frequency">>) => {
      setSaving(true);
      setStatus(null);
      try {
        const updated = await updateEmailPreferences(update);
        await mutate(updated, { revalidate: false });
        setStatus({ type: "success", message: "Preferences saved." });
      } catch {
        setStatus({ type: "error", message: "Failed to save. Please try again." });
      } finally {
        setSaving(false);
        setTimeout(() => setStatus(null), 3500);
      }
    },
    [mutate],
  );

  return (
    <div className="max-w-2xl mx-auto space-y-6 py-2">
      {/* Header */}
      <div>
        <Link
          href="/settings"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 mb-4 transition-colors"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Back to Settings
        </Link>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-800 border border-slate-700 text-slate-300">
            <Bell className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-tight text-slate-100">
              Notification Preferences
            </h1>
            <p className="text-sm text-slate-400 mt-0.5">
              Control how and when Fin-Eye reaches out to you.
            </p>
          </div>
        </div>
      </div>

      {/* Status banner */}
      {status && <StatusBanner type={status.type} message={status.message} />}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="rounded-xl border border-slate-800 bg-slate-900/50 p-6 animate-pulse"
            >
              <div className="flex gap-3">
                <div className="h-9 w-9 rounded-lg bg-slate-800" />
                <div className="space-y-2 flex-1">
                  <div className="h-4 w-32 rounded bg-slate-800" />
                  <div className="h-3 w-64 rounded bg-slate-800" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!isLoading && (
        <>
          {/* 1 — Email Digest */}
          <SectionCard
            icon={<CalendarClock className="h-4.5 w-4.5" />}
            title="Weekly Digest Email"
            description="Get a curated GAS summary for your watchlist symbols delivered to your inbox."
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm text-slate-200 font-medium">
                  {prefs?.digest_opted_in ? "Digest is enabled" : "Digest is disabled"}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {prefs?.digest_opted_in
                    ? "You will receive a GAS summary digest email."
                    : "No digest emails will be sent."}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" />}
                <Toggle
                  checked={prefs?.digest_opted_in ?? false}
                  onChange={(v) => patch({ digest_opted_in: v })}
                  disabled={saving}
                />
              </div>
            </div>

            {prefs?.digest_opted_in && (
              <div className="border-t border-slate-800 pt-4 space-y-2">
                <p className="text-xs text-slate-400 font-medium">Digest frequency</p>
                <FrequencyPicker
                  value={prefs.digest_frequency}
                  onChange={(v) => patch({ digest_frequency: v })}
                  disabled={saving}
                />
              </div>
            )}
          </SectionCard>

          {/* 2 — Marketing emails */}
          <SectionCard
            icon={<Megaphone className="h-4.5 w-4.5" />}
            title="Marketing & Product Updates"
            description="Occasional emails about new Fin-Eye features, educational content, and announcements."
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm text-slate-200 font-medium">
                  {prefs?.marketing_opted_in ? "Marketing emails on" : "Marketing emails off"}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  You can opt out at any time. Transactional emails (receipts, security) are always sent.
                </p>
              </div>
              <div className="flex items-center gap-2">
                {saving && <Loader2 className="h-3.5 w-3.5 animate-spin text-slate-500" />}
                <Toggle
                  checked={prefs?.marketing_opted_in ?? false}
                  onChange={(v) => patch({ marketing_opted_in: v })}
                  disabled={saving}
                />
              </div>
            </div>
          </SectionCard>

          {/* 3 — In-app price / GAS alerts */}
          <SectionCard
            icon={<Bell className="h-4.5 w-4.5" />}
            title="Price & GAS Alerts"
            description="In-app alerts that trigger when a symbol crosses your set threshold."
          >
            <AlertsSummary />
          </SectionCard>

          {/* 4 — Unsubscribe link */}
          <SectionCard
            icon={<Mail className="h-4.5 w-4.5" />}
            title="Global Email Opt-Out"
            description="Unsubscribe from all non-essential emails with a single click."
          >
            <p className="text-xs text-slate-500">
              You can unsubscribe from all marketing and digest emails at once.
              Transactional emails (account security, receipts) will still be delivered.
            </p>
            <button
              onClick={() => patch({ marketing_opted_in: false, digest_opted_in: false })}
              disabled={saving || (!prefs?.marketing_opted_in && !prefs?.digest_opted_in)}
              className="mt-2 inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {saving ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <BellOff className="h-3.5 w-3.5" />
              )}
              Unsubscribe from all emails
            </button>
            {!prefs?.marketing_opted_in && !prefs?.digest_opted_in && (
              <p className="mt-2 text-[11px] text-emerald-500">
                ✓ You are already opted out of all non-essential emails.
              </p>
            )}
          </SectionCard>
        </>
      )}
    </div>
  );
}
