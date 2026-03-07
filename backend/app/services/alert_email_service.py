"""
app/services/alert_email_service.py
─────────────────────────────────────────────────────────────────────────────
CORE-NOTIF-ADV-01 — Alert Email Dispatcher

Responsibility:
  When an Alert with delivery_channel="email" fires, this service:
    1. Renders a polished HTML email (re-using the existing _base_template
       and _send helpers from email_service.py).
    2. Logs the send to EmailLog for deduplication — each alert-ID fires
       exactly once (the alert is deactivated after firing anyway, but the
       log gives us a durable audit trail and protects against race conditions
       if the scheduler fires twice in the same window).
    3. Returns True/False so the caller can log the outcome.

Email types (one per alert_type):
    alert_price_above_{alert_id}
    alert_price_below_{alert_id}
    alert_gas_above_{alert_id}
    alert_gas_below_{alert_id}

This module is called exclusively from alert_service.evaluate_all_email_alerts()
which is itself called by the APScheduler job every 5 minutes.

No new dependencies — uses httpx (already installed) via email_service._send().
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.email_preference import EmailLog
from app.models.user import User
from app.services.email_service import _base_template, _btn, _send, _frontend_url

logger = logging.getLogger(__name__)


# ─── Deduplication ────────────────────────────────────────────────────────────

def _email_type_for_alert(alert: Alert) -> str:
    """Unique email_type key stored in EmailLog — one entry per alert firing."""
    return f"alert_{alert.alert_type}_{alert.id}"


async def _already_sent(db: AsyncSession, alert: Alert) -> bool:
    """Return True if we already sent an email for this alert firing."""
    email_type = _email_type_for_alert(alert)
    result = await db.execute(
        select(EmailLog).where(
            EmailLog.user_id == alert.user_id,
            EmailLog.email_type == email_type,
        )
    )
    return result.scalar_one_or_none() is not None


async def _log_send(db: AsyncSession, alert: Alert, success: bool) -> None:
    """Record the send attempt so we never double-fire."""
    log = EmailLog(
        user_id=alert.user_id,
        email_type=_email_type_for_alert(alert),
        success=success,
    )
    db.add(log)
    # Flush inside the caller's transaction — committed by the job runner.


# ─── HTML templates ───────────────────────────────────────────────────────────

def _render_price_alert(
    user_name: Optional[str],
    symbol: str,
    alert_type: str,          # "price_above" | "price_below"
    threshold: float,
    triggered_value: float,
    unsubscribe_token: str,
) -> tuple[str, str]:
    """Returns (subject, html)."""
    direction   = "above" if alert_type == "price_above" else "below"
    arrow       = "🔼" if alert_type == "price_above" else "🔽"
    colour      = "#10b981" if alert_type == "price_above" else "#f87171"
    display     = user_name or "there"
    unsub_url   = f"{_frontend_url()}/unsubscribe?token={unsubscribe_token}"
    alerts_url  = f"{_frontend_url()}/alerts"
    chart_url   = f"{_frontend_url()}/?symbol={symbol}"

    pct_diff = ((triggered_value - threshold) / threshold) * 100
    pct_str  = f"{'+' if pct_diff >= 0 else ''}{pct_diff:.2f}%"

    subject = f"{arrow} {symbol} price alert: ${triggered_value:,.2f} ({direction} ${threshold:,.2f})"

    content = f"""
    <h2 style="margin:0 0 8px;font-size:22px;color:#f1f5f9;">
      {arrow} Price Alert Triggered
    </h2>
    <p style="margin:0 0 24px;color:#64748b;font-size:13px;">
      Hi {display} — your Fin-Eye price alert just fired.
    </p>

    <!-- Alert card -->
    <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;">
      <tr>
        <td style="padding:24px;background:#0f172a;border-radius:12px;border-left:4px solid {colour};">
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td>
                <p style="margin:0;font-size:32px;font-weight:900;color:#f1f5f9;letter-spacing:-1px;">
                  {symbol}
                </p>
                <p style="margin:4px 0 0;font-size:13px;color:#64748b;">Price alert · {direction} threshold</p>
              </td>
              <td style="text-align:right;vertical-align:top;">
                <p style="margin:0;font-size:28px;font-weight:900;color:{colour};font-family:monospace;">
                  ${triggered_value:,.2f}
                </p>
                <p style="margin:4px 0 0;font-size:12px;color:#64748b;">{pct_str} vs threshold</p>
              </td>
            </tr>
          </table>

          <!-- Divider -->
          <table cellpadding="0" cellspacing="0" width="100%" style="margin:16px 0;">
            <tr><td style="border-top:1px solid #1e293b;"></td></tr>
          </table>

          <!-- Threshold vs actual -->
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td style="width:50%;">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">
                  Your threshold
                </p>
                <p style="margin:4px 0 0;font-size:20px;font-weight:700;color:#94a3b8;font-family:monospace;">
                  ${threshold:,.2f}
                </p>
              </td>
              <td style="width:50%;text-align:right;">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">
                  Triggered at
                </p>
                <p style="margin:4px 0 0;font-size:20px;font-weight:700;color:{colour};font-family:monospace;">
                  ${triggered_value:,.2f}
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>

    {_btn(chart_url, f"View {symbol} Dashboard →")}

    <p style="margin-top:20px;color:#64748b;font-size:13px;">
      This alert has been deactivated. You can create a new alert at any time from the
      <a href="{alerts_url}" style="color:#60a5fa;">Alerts page</a>.
    </p>

    <p style="margin-top:16px;padding:12px;background:#0f172a;border-radius:8px;
              font-size:12px;color:#475569;border-left:3px solid #334155;">
      ⚠️ Price data is sourced from Yahoo Finance and may be delayed up to 15 minutes.
      This alert is for informational purposes only and does not constitute investment advice.
    </p>
    """
    return subject, _base_template(content, unsubscribe_url=unsub_url)


def _render_gas_alert(
    user_name: Optional[str],
    symbol: str,
    alert_type: str,          # "gas_above" | "gas_below"
    threshold: float,
    triggered_value: float,
    unsubscribe_token: str,
) -> tuple[str, str]:
    """Returns (subject, html)."""
    direction = "above" if alert_type == "gas_above" else "below"
    arrow     = "📈" if alert_type == "gas_above" else "📉"
    colour    = "#10b981" if alert_type == "gas_above" else "#f87171"
    display   = user_name or "there"
    unsub_url = f"{_frontend_url()}/unsubscribe?token={unsubscribe_token}"
    alerts_url = f"{_frontend_url()}/alerts"
    dash_url   = f"{_frontend_url()}/?symbol={symbol}"

    # GAS label helper (same thresholds as gas_precompute.py)
    def gas_label(score: float) -> str:
        if score >= 75: return "Mild Support"
        if score >= 55: return "Mixed Signals"
        if score >= 35: return "Headwind"
        return "High Instability"

    def gas_colour(score: float) -> str:
        if score >= 75: return "#10b981"
        if score >= 55: return "#eab308"
        if score >= 35: return "#f97316"
        return "#f87171"

    triggered_label = gas_label(triggered_value)
    triggered_colour = gas_colour(triggered_value)

    # Gauge-like visual — simple bar using table widths
    fill_pct = max(2, min(98, int(triggered_value)))
    empty_pct = 100 - fill_pct

    subject = f"{arrow} {symbol} GAS alert: score {triggered_value:.0f} ({direction} {threshold:.0f})"

    content = f"""
    <h2 style="margin:0 0 8px;font-size:22px;color:#f1f5f9;">
      {arrow} Global Alignment Score Alert
    </h2>
    <p style="margin:0 0 24px;color:#64748b;font-size:13px;">
      Hi {display} — your GAS alert for <strong style="color:#f1f5f9;">{symbol}</strong> just fired.
    </p>

    <!-- Alert card -->
    <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;">
      <tr>
        <td style="padding:24px;background:#0f172a;border-radius:12px;border-left:4px solid {colour};">

          <!-- Header row -->
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td>
                <p style="margin:0;font-size:32px;font-weight:900;color:#f1f5f9;letter-spacing:-1px;">
                  {symbol}
                </p>
                <p style="margin:4px 0 0;font-size:13px;color:#64748b;">GAS alert · {direction} threshold</p>
              </td>
              <td style="text-align:right;vertical-align:top;">
                <p style="margin:0;font-size:40px;font-weight:900;color:{triggered_colour};font-family:monospace;line-height:1;">
                  {triggered_value:.0f}
                </p>
                <p style="margin:4px 0 0;font-size:12px;color:{triggered_colour};">
                  {triggered_label}
                </p>
              </td>
            </tr>
          </table>

          <!-- Score bar -->
          <table cellpadding="0" cellspacing="0" width="100%" style="margin:20px 0 8px;">
            <tr>
              <td width="{fill_pct}%" height="8"
                  style="background:linear-gradient(to right,#f87171,#f97316,#eab308,#10b981);
                         border-radius:4px 0 0 4px;"></td>
              <td width="{empty_pct}%" height="8"
                  style="background:#1e293b;border-radius:0 4px 4px 0;"></td>
            </tr>
          </table>
          <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:16px;">
            <tr>
              <td style="font-size:10px;color:#64748b;">0 — High Instability</td>
              <td style="font-size:10px;color:#64748b;text-align:right;">100 — Mild Support</td>
            </tr>
          </table>

          <!-- Divider -->
          <table cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 16px;">
            <tr><td style="border-top:1px solid #1e293b;"></td></tr>
          </table>

          <!-- Threshold vs actual -->
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td style="width:50%;">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">
                  Your threshold
                </p>
                <p style="margin:4px 0 0;font-size:20px;font-weight:700;color:#94a3b8;font-family:monospace;">
                  {threshold:.0f}
                </p>
              </td>
              <td style="width:50%;text-align:right;">
                <p style="margin:0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em;">
                  Current GAS
                </p>
                <p style="margin:4px 0 0;font-size:20px;font-weight:700;color:{triggered_colour};font-family:monospace;">
                  {triggered_value:.1f}
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>

    <!-- GAS explanation -->
    <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;">
      <tr>
        <td style="padding:16px;background:#0f172a;border-radius:8px;">
          <p style="margin:0 0 8px;font-size:13px;font-weight:600;color:#94a3b8;">What is the GAS score?</p>
          <table cellpadding="0" cellspacing="0" width="100%">
            <tr>
              <td style="width:33%;padding:4px 8px;font-size:12px;color:#64748b;border-right:1px solid #1e293b;">
                <strong style="color:#60a5fa;">40%</strong><br>Technical (ML signals)
              </td>
              <td style="width:33%;padding:4px 8px;font-size:12px;color:#64748b;border-right:1px solid #1e293b;text-align:center;">
                <strong style="color:#a78bfa;">30%</strong><br>Sentiment (FinBERT)
              </td>
              <td style="width:33%;padding:4px 8px;font-size:12px;color:#64748b;text-align:right;">
                <strong style="color:#34d399;">30%</strong><br>Macro (FRED data)
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>

    {_btn(dash_url, f"View {symbol} on Dashboard →")}

    <p style="margin-top:20px;color:#64748b;font-size:13px;">
      This alert has been deactivated. Set a new GAS alert any time from the
      <a href="{alerts_url}" style="color:#60a5fa;">Alerts page</a>.
    </p>

    <p style="margin-top:16px;padding:12px;background:#0f172a;border-radius:8px;
              font-size:12px;color:#475569;border-left:3px solid #334155;">
      ⚠️ The Global Alignment Score is a quantitative signal for educational use only.
      A high or low GAS score is not a buy or sell recommendation. Past score levels
      do not predict future price performance. Always consult a qualified financial advisor.
    </p>
    """
    return subject, _base_template(content, unsubscribe_url=unsub_url)


# ─── Main dispatch function ───────────────────────────────────────────────────

async def send_alert_email(
    db: AsyncSession,
    alert: Alert,
    user: User,
    unsubscribe_token: str,
) -> bool:
    """
    Send a triggered-alert email to the user.
    Guards against double-send via EmailLog.
    Returns True if email was sent, False if skipped or failed.
    """
    # 1. Deduplication guard
    if await _already_sent(db, alert):
        logger.info(
            "Alert %d email already sent to user %s — skipping",
            alert.id, alert.user_id,
        )
        return False

    # 2. Render template
    symbol          = alert.symbol
    threshold       = alert.threshold
    triggered_value = alert.triggered_value or threshold
    user_name       = getattr(user, "name", None)

    if alert.alert_type in ("price_above", "price_below"):
        subject, html = _render_price_alert(
            user_name, symbol, alert.alert_type,
            threshold, triggered_value, unsubscribe_token,
        )
    else:
        subject, html = _render_gas_alert(
            user_name, symbol, alert.alert_type,
            threshold, triggered_value, unsubscribe_token,
        )

    # 3. Send
    success = await _send(
        to=user.email,
        subject=subject,
        html=html,
        tags=[{"name": "type", "value": "alert_notification"}],
    )

    # 4. Log the attempt (whether success or failure)
    await _log_send(db, alert, success)

    if success:
        logger.info(
            "Alert email sent — alert_id=%d user=%s symbol=%s type=%s value=%.2f",
            alert.id, user.email, symbol, alert.alert_type, triggered_value,
        )
    else:
        logger.warning(
            "Alert email FAILED — alert_id=%d user=%s",
            alert.id, user.email,
        )

    return success
