"use client";

import { useEffect, useState, useCallback } from "react";
import {
  fetchAlerts,
  fetchAlertHistory,
  createAlert,
  deleteAlert,
  fetchTriggeredAlerts,
  acknowledgeAlert,
  AlertDto,
  AlertHistoryDto,
  TriggeredAlertDto,
  AlertCreatePayload,
} from "@/lib/api";
import { PageBanner } from "@/components/ui/PageBanner";
import { Bell } from "lucide-react";

// ── Types ─────────────────────────────────────────────────────────────────────

type AlertType = "price_above" | "price_below" | "gas_above" | "gas_below";

const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  price_above: "Price rises above",
  price_below: "Price falls below",
  gas_above: "GAS score rises above",
  gas_below: "GAS score falls below",
};

const ALERT_TYPE_COLORS: Record<string, string> = {
  price_above: "text-emerald-400",
  price_below: "text-rose-400",
  gas_above: "text-sky-400",
  gas_below: "text-amber-400",
};

// ── Component ─────────────────────────────────────────────────────────────────

type PageView = "active" | "history";

const ALERT_TYPE_COLORS_HISTORY: Record<string, string> = {
  price_above: "bg-emerald-900/30 text-emerald-300 border-emerald-800/40",
  price_below: "bg-rose-900/30 text-rose-300 border-rose-800/40",
  gas_above:   "bg-sky-900/30 text-sky-300 border-sky-800/40",
  gas_below:   "bg-amber-900/30 text-amber-300 border-amber-800/40",
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertDto[]>([]);
  const [triggered, setTriggered] = useState<TriggeredAlertDto[]>([]);
  const [history, setHistory] = useState<AlertHistoryDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<PageView>("active");

  // Form state
  const [symbol, setSymbol] = useState("AAPL");
  const [alertType, setAlertType] = useState<AlertType>("price_above");
  const [threshold, setThreshold] = useState("");
  const [deliveryChannel, setDeliveryChannel] = useState<"in_app" | "email">("in_app");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [list, trig] = await Promise.all([
        fetchAlerts(),
        fetchTriggeredAlerts(),
      ]);
      setAlerts(list.alerts);
      setTriggered(trig);
    } catch (e: any) {
      setError(e.message ?? "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await fetchAlertHistory(50);
      setHistory(data.history);
    } catch {
      // silently fail — history is non-critical
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    // Poll triggered alerts every 30s
    const interval = setInterval(async () => {
      try {
        const trig = await fetchTriggeredAlerts();
        setTriggered(trig);
      } catch {}
    }, 30_000);
    return () => clearInterval(interval);
  }, [load]);

  useEffect(() => {
    if (view === "history") loadHistory();
  }, [view, loadHistory]);

  const handleCreate = async () => {
    setFormError(null);
    const val = parseFloat(threshold);
    if (!symbol.trim()) return setFormError("Symbol is required.");
    if (isNaN(val) || val <= 0) return setFormError("Threshold must be a positive number.");

    setCreating(true);
    try {
      const payload: AlertCreatePayload = {
        symbol: symbol.trim().toUpperCase(),
        alert_type: alertType,
        threshold: val,
        delivery_channel: deliveryChannel,
      };
      const created = await createAlert(payload);
      setAlerts((prev) => [created, ...prev]);
      setThreshold("");
    } catch (e: any) {
      setFormError(e.message ?? "Failed to create alert.");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    await deleteAlert(id);
    setAlerts((prev) => prev.filter((a) => a.id !== id));
    setTriggered((prev) => prev.filter((a) => a.id !== id));
  };

  const handleAck = async (id: number) => {
    await acknowledgeAlert(id);
    setTriggered((prev) => prev.filter((a) => a.id !== id));
    setAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, is_active: false } : a))
    );
  };

  return (
    <div className="space-y-6">
      <PageBanner
        icon={<Bell className="h-5 w-5" />}
        title="Alerts & Notifications"
        description="Get notified when a price or GAS score crosses your threshold. Evaluated every 5 minutes."
        badge="Live Monitoring"
        badgeColor="amber"
      />

      {/* View switcher */}
      <div className="flex gap-1 border-b border-gray-800 max-w-3xl">
        {(["active", "history"] as PageView[]).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={`px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
              view === v
                ? "border-amber-500 text-amber-400"
                : "border-transparent text-gray-500 hover:text-gray-300"
            }`}
          >
            {v === "active" ? `🔔 Active Alerts (${alerts.length})` : `📋 History`}
          </button>
        ))}
      </div>

      <div className="max-w-3xl space-y-8">

        {/* Triggered banner */}
        {triggered.length > 0 && (
          <div className="space-y-2">
            <h2 className="text-sm font-semibold text-amber-400 uppercase tracking-wide">
              🔔 {triggered.length} Alert{triggered.length > 1 ? "s" : ""} Fired
            </h2>
            {triggered.map((t) => (
              <div
                key={t.id}
                className="flex items-start justify-between bg-amber-900/30 border border-amber-700/40 rounded-lg p-4"
              >
                <div>
                  <span className="font-semibold text-amber-300">{t.symbol}</span>
                  <p className="text-sm text-gray-300 mt-0.5">{t.message}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(t.triggered_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex gap-2 ml-4 shrink-0">
                  <button
                    onClick={() => handleAck(t.id)}
                    className="text-xs bg-amber-700 hover:bg-amber-600 px-3 py-1.5 rounded text-white transition"
                  >
                    Dismiss
                  </button>
                  <button
                    onClick={() => handleDelete(t.id)}
                    className="text-xs bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded text-gray-300 transition"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create form */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h2 className="text-lg font-semibold text-white">Create New Alert</h2>
          {/* Delivery channel */}
          <div className="flex items-center gap-4 mb-1">
            <p className="text-xs text-gray-400">Notify via:</p>
            <div className="flex gap-2">
              {(["in_app", "email"] as const).map((ch) => (
                <button
                  key={ch}
                  type="button"
                  onClick={() => setDeliveryChannel(ch)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition ${
                    deliveryChannel === ch
                      ? "bg-sky-700 border-sky-600 text-white"
                      : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200"
                  }`}
                >
                  {ch === "in_app" ? "🔔 In-app" : "✉️ Email"}
                </button>
              ))}
            </div>
            {deliveryChannel === "email" && (
              <p className="text-[10px] text-sky-400">
                An email will be sent to your account address when this alert fires.
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Ticker</label>
              <input
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-1 focus:ring-sky-500"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder="e.g. AAPL"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Condition</label>
              <select
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-1 focus:ring-sky-500"
                value={alertType}
                onChange={(e) => setAlertType(e.target.value as AlertType)}
              >
                {(Object.keys(ALERT_TYPE_LABELS) as AlertType[]).map((t) => (
                  <option key={t} value={t}>
                    {ALERT_TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Threshold</label>
              <input
                type="number"
                step="any"
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:ring-1 focus:ring-sky-500"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                placeholder={alertType.startsWith("gas") ? "0–100" : "e.g. 195.00"}
              />
            </div>
          </div>
          {formError && (
            <p className="text-xs text-rose-400">{formError}</p>
          )}
          <button
            onClick={handleCreate}
            disabled={creating}
            className="bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm font-medium px-5 py-2 rounded transition"
          >
            {creating ? "Creating…" : "+ Add Alert"}
          </button>
        </div>

        {/* Alert list */}
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            Your Alerts ({alerts.length})
          </h2>

          {loading && (
            <p className="text-gray-500 text-sm">Loading…</p>
          )}
          {error && (
            <p className="text-rose-400 text-sm">{error}</p>
          )}
          {!loading && alerts.length === 0 && (
            <div className="text-center py-12 text-gray-600 text-sm">
              No alerts yet. Create one above.
            </div>
          )}

          <div className="space-y-2">
            {alerts.map((alert) => {
              const isTriggered = !!alert.triggered_at && alert.is_active;
              return (
                <div
                  key={alert.id}
                  className={`flex items-center justify-between rounded-lg px-4 py-3 border ${
                    isTriggered
                      ? "bg-amber-900/20 border-amber-700/30"
                      : alert.is_active
                      ? "bg-gray-900 border-gray-800"
                      : "bg-gray-900/40 border-gray-800/50 opacity-50"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        isTriggered
                          ? "bg-amber-400 animate-pulse"
                          : alert.is_active
                          ? "bg-emerald-500"
                          : "bg-gray-600"
                      }`}
                    />
                    <div>
                      <span className="font-semibold text-white text-sm">{alert.symbol}</span>
                      <span className={`ml-2 text-sm ${ALERT_TYPE_COLORS[alert.alert_type] ?? "text-gray-400"}`}>
                        {ALERT_TYPE_LABELS[alert.alert_type as AlertType] ?? alert.alert_type}
                      </span>
                      <span className="ml-2 text-white font-mono text-sm">{alert.threshold}</span>
                      <span className="ml-2 text-[10px] text-gray-600">
                        {alert.delivery_channel === "email" ? "✉️ email" : "🔔 in-app"}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    {!alert.is_active && (
                      <span className="bg-gray-700 text-gray-400 px-2 py-0.5 rounded">Dismissed</span>
                    )}
                    {isTriggered && (
                      <span className="text-amber-400">Fired @ {alert.triggered_value?.toFixed(2)}</span>
                    )}
                    <button
                      onClick={() => handleDelete(alert.id)}
                      className="text-gray-600 hover:text-rose-400 transition ml-2 text-base leading-none"
                      title="Delete alert"
                    >
                      ×
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer note */}
        {view === "active" && (
          <p className="text-xs text-gray-600 text-center">
            Alerts are evaluated every 5 minutes during US market hours (9am–5pm ET).
            Email alerts are sent via Resend and arrive within minutes of the threshold being breached.
          </p>
        )}

        {/* History view */}
        {view === "history" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
                Trigger History ({history.length})
              </h2>
              <button
                onClick={loadHistory}
                disabled={historyLoading}
                className="text-xs text-gray-500 hover:text-gray-300 transition"
              >
                {historyLoading ? "Loading…" : "↻ Refresh"}
              </button>
            </div>

            {historyLoading && (
              <p className="text-gray-500 text-sm">Loading history…</p>
            )}

            {!historyLoading && history.length === 0 && (
              <div className="text-center py-12 text-gray-600 text-sm rounded-xl border border-gray-800">
                No alert history yet. Alerts will appear here once they fire.
              </div>
            )}

            {!historyLoading && history.length > 0 && (
              <div className="rounded-xl border border-gray-800 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-800 text-gray-500">
                        <th className="text-left px-4 py-2.5 font-medium">Time</th>
                        <th className="text-left px-3 py-2.5 font-medium">Symbol</th>
                        <th className="text-left px-3 py-2.5 font-medium">Condition</th>
                        <th className="text-right px-3 py-2.5 font-medium">Threshold</th>
                        <th className="text-right px-3 py-2.5 font-medium">Actual</th>
                        <th className="text-center px-3 py-2.5 font-medium">Via</th>
                        <th className="text-center px-4 py-2.5 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((h) => (
                        <tr
                          key={h.id}
                          className="border-b border-gray-900 last:border-0 hover:bg-gray-900/40"
                        >
                          <td className="px-4 py-2.5 text-gray-400 whitespace-nowrap">
                            {new Date(h.triggered_at).toLocaleString("en-DE", {
                              month: "short",
                              day: "2-digit",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </td>
                          <td className="px-3 py-2.5 font-bold text-white">{h.symbol}</td>
                          <td className="px-3 py-2.5">
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                                ALERT_TYPE_COLORS_HISTORY[h.alert_type] ??
                                "bg-gray-800 text-gray-400 border-gray-700"
                              }`}
                            >
                              {ALERT_TYPE_LABELS[h.alert_type as AlertType] ?? h.alert_type}
                            </span>
                          </td>
                          <td className="px-3 py-2.5 text-right font-mono text-gray-300">
                            {h.threshold.toFixed(2)}
                          </td>
                          <td className="px-3 py-2.5 text-right font-mono font-bold text-amber-300">
                            {h.triggered_value.toFixed(2)}
                          </td>
                          <td className="px-3 py-2.5 text-center text-gray-500">
                            {h.delivery_channel === "email" ? "✉️" : "🔔"}
                          </td>
                          <td className="px-4 py-2.5 text-center">
                            {h.is_active ? (
                              <span className="text-[10px] text-amber-400 font-semibold">Active</span>
                            ) : (
                              <span className="text-[10px] text-gray-600">Dismissed</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
