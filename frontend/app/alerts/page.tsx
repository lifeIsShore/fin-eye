"use client";

import { useEffect, useState, useCallback } from "react";
import {
  fetchAlerts,
  createAlert,
  deleteAlert,
  fetchTriggeredAlerts,
  acknowledgeAlert,
  AlertDto,
  TriggeredAlertDto,
  AlertCreatePayload,
} from "@/lib/api";

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

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertDto[]>([]);
  const [triggered, setTriggered] = useState<TriggeredAlertDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
    <div className="min-h-screen bg-gray-950 text-gray-100 p-6">
      <div className="max-w-3xl mx-auto space-y-8">

        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Alerts & Notifications</h1>
          <p className="text-gray-400 text-sm mt-1">
            Get notified when a price or GAS score crosses your threshold.
          </p>
        </div>

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
        <p className="text-xs text-gray-600 text-center">
          Alerts are evaluated every 5 minutes during US market hours (9am–5pm ET).
          Email alerts are sent via Resend and arrive within minutes of the threshold being breached.
        </p>
      </div>
    </div>
  );
}
