"""
app/services/email_service.py

Resend-powered email service for Fin-Eye.

Handles:
  - Transactional onboarding sequence (CORE-EMAIL-01)
  - Optional weekly digest (CORE-EMAIL-02)
  - Unsubscribe / opt-out mechanics

Environment variables required:
  RESEND_API_KEY   — Resend API key
  FROM_EMAIL       — Sending address (e.g. noreply@fin-eye.com)
  FRONTEND_URL     — Used to build unsubscribe links (default: http://localhost:3000)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

RESEND_API_URL = "https://api.resend.com/emails"


# ─── Low-level send helper ─────────────────────────────────────────────────────


async def _send(
    to: str,
    subject: str,
    html: str,
    *,
    tags: Optional[list[dict]] = None,
) -> bool:
    """
    Send a single email via Resend.
    Returns True on success, False on any error (never raises — email must not break the app).
    """
    api_key = settings.resend_api_key
    from_addr = settings.from_email

    if not api_key or api_key == "":
        logger.warning("RESEND_API_KEY not set — skipping email to %s ('%s')", to, subject)
        return False

    payload: dict = {
        "from": from_addr,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if tags:
        payload["tags"] = tags

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code in (200, 201):
            logger.info("Email sent to %s: '%s'", to, subject)
            return True
        else:
            logger.error(
                "Resend API error %s sending to %s: %s",
                resp.status_code, to, resp.text[:200],
            )
            return False
    except Exception as exc:  # noqa: BLE001
        logger.error("Email send exception for %s: %s", to, exc)
        return False


# ─── HTML template helpers ─────────────────────────────────────────────────────


def _base_template(content: str, unsubscribe_url: Optional[str] = None) -> str:
    footer = ""
    if unsubscribe_url:
        footer = f"""
        <p style="margin-top:32px;font-size:12px;color:#888;text-align:center;">
          You're receiving this because you signed up for Fin-Eye.<br>
          <a href="{unsubscribe_url}" style="color:#888;">Unsubscribe from marketing emails</a>
        </p>"""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Fin-Eye</title>
    </head>
    <body style="margin:0;padding:0;background:#0f172a;font-family:'Segoe UI',Arial,sans-serif;color:#e2e8f0;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
        <tr>
          <td align="center" style="padding:40px 16px;">
            <table width="600" cellpadding="0" cellspacing="0"
                   style="background:#1e293b;border-radius:12px;overflow:hidden;max-width:600px;width:100%;">
              <!-- Header -->
              <tr>
                <td style="background:linear-gradient(135deg,#1e40af,#0891b2);padding:32px 40px;">
                  <h1 style="margin:0;font-size:24px;font-weight:700;color:#fff;letter-spacing:-0.5px;">
                    📈 Fin-Eye
                  </h1>
                  <p style="margin:4px 0 0;font-size:13px;color:#bfdbfe;">
                    Market Intelligence Platform
                  </p>
                </td>
              </tr>
              <!-- Body -->
              <tr>
                <td style="padding:40px;">
                  {content}
                </td>
              </tr>
              <!-- Footer -->
              <tr>
                <td style="background:#0f172a;padding:24px 40px;border-top:1px solid #334155;">
                  <p style="margin:0;font-size:12px;color:#64748b;text-align:center;">
                    ⚠️ Fin-Eye is an <strong>educational tool only</strong>. Nothing in this email
                    constitutes financial advice or a recommendation to buy or sell any security.
                    Always consult a qualified financial advisor before making investment decisions.
                  </p>
                  {footer}
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


def _btn(url: str, label: str) -> str:
    return (
        f'<a href="{url}" style="display:inline-block;margin-top:20px;padding:12px 28px;'
        f'background:#2563eb;color:#fff;border-radius:8px;text-decoration:none;'
        f'font-weight:600;font-size:14px;">{label}</a>'
    )


# ─── Onboarding sequence (CORE-EMAIL-01) ──────────────────────────────────────

FRONTEND_URL_DEFAULT = "http://localhost:3000"


def _frontend_url() -> str:
    return getattr(settings, "frontend_url", FRONTEND_URL_DEFAULT).rstrip("/")


async def send_welcome_email(
    to: str,
    name: Optional[str],
    unsubscribe_token: str,
) -> bool:
    """
    Email 1 of 3 — sent immediately after signup.
    Introduces the platform and directs the user to the dashboard.
    """
    display = name or "there"
    unsub_url = f"{_frontend_url()}/unsubscribe?token={unsubscribe_token}"
    dashboard_url = f"{_frontend_url()}/"

    content = f"""
    <h2 style="margin:0 0 16px;font-size:22px;color:#f1f5f9;">
      Welcome to Fin-Eye, {display}! 👋
    </h2>
    <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px;">
      You're now part of a community of data-driven investors using quantitative signals
      to understand the market — not guess at it.
    </p>
    <p style="color:#94a3b8;line-height:1.7;margin:0 0 20px;">
      Here's what's waiting for you on your dashboard:
    </p>
    <table cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td style="padding:12px 16px;background:#0f172a;border-radius:8px;margin-bottom:8px;border-left:3px solid #2563eb;">
          <strong style="color:#f1f5f9;">📊 Global Alignment Score (GAS)</strong>
          <p style="margin:4px 0 0;color:#94a3b8;font-size:14px;">
            A single 0–100 score combining technical ML signals, macro data, and market sentiment.
          </p>
        </td>
      </tr>
    </table>
    <br/>
    <table cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td style="padding:12px 16px;background:#0f172a;border-radius:8px;margin-bottom:8px;border-left:3px solid #0891b2;">
          <strong style="color:#f1f5f9;">🔮 Macro Intelligence</strong>
          <p style="margin:4px 0 0;color:#94a3b8;font-size:14px;">
            Yield curve, recession probability, macro stress index — updated daily from FRED.
          </p>
        </td>
      </tr>
    </table>
    <br/>
    <table cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td style="padding:12px 16px;background:#0f172a;border-radius:8px;margin-bottom:8px;border-left:3px solid #7c3aed;">
          <strong style="color:#f1f5f9;">📰 Sentiment Analysis</strong>
          <p style="margin:4px 0 0;color:#94a3b8;font-size:14px;">
            FinBERT-powered news sentiment and Reddit retail sentiment — 30-day trend per ticker.
          </p>
        </td>
      </tr>
    </table>
    {_btn(dashboard_url, "Open My Dashboard →")}
    <p style="margin-top:24px;color:#64748b;font-size:13px;">
      Over the next few days we'll share tips for getting the most out of the platform.
    </p>
    """
    return await _send(
        to,
        "Welcome to Fin-Eye — your market intelligence dashboard is ready",
        _base_template(content, unsubscribe_url=unsub_url),
        tags=[{"name": "sequence", "value": "onboarding_1"}],
    )


async def send_day3_email(
    to: str,
    name: Optional[str],
    unsubscribe_token: str,
) -> bool:
    """
    Email 2 of 3 — Day 3 after signup.
    Deep-dive on backtesting and strategy library.
    """
    display = name or "there"
    unsub_url = f"{_frontend_url()}/unsubscribe?token={unsubscribe_token}"
    backtest_url = f"{_frontend_url()}/backtesting"
    learn_url = f"{_frontend_url()}/learn"

    content = f"""
    <h2 style="margin:0 0 16px;font-size:22px;color:#f1f5f9;">
      Hey {display} — have you tried the backtesting engine? 🧪
    </h2>
    <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px;">
      One of Fin-Eye's most powerful features is the <strong style="color:#f1f5f9;">backtesting engine</strong>.
      It lets you test momentum strategies on any ticker — with a buy-and-hold benchmark,
      max drawdown, Sharpe ratio, and an overfitting warning if your results look too good to be true.
    </p>
    <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px;">
      You can also <strong style="color:#f1f5f9;">save strategies</strong> to your library and share them
      with the community — anonymous, metrics-only, no personal data exposed.
    </p>
    <p style="color:#64748b;font-size:13px;font-style:italic;margin:0 0 20px;">
      Remember: backtested results are historical and do not predict future performance.
      Past returns are not indicative of future results.
    </p>
    {_btn(backtest_url, "Try the Backtesting Engine →")}
    <p style="margin-top:20px;color:#94a3b8;font-size:14px;">
      New to quantitative concepts?
      <a href="{learn_url}" style="color:#60a5fa;">Visit the Learn tab</a> for guides on
      GAS, macro regimes, volatility, and options hedging.
    </p>
    """
    return await _send(
        to,
        "Fin-Eye tip: backtest any strategy in 30 seconds",
        _base_template(content, unsubscribe_url=unsub_url),
        tags=[{"name": "sequence", "value": "onboarding_2"}],
    )


async def send_day7_email(
    to: str,
    name: Optional[str],
    unsubscribe_token: str,
) -> bool:
    """
    Email 3 of 3 — Day 7 after signup.
    Highlights advanced features: 2FA, alerts, hedging.
    """
    display = name or "there"
    unsub_url = f"{_frontend_url()}/unsubscribe?token={unsubscribe_token}"
    alerts_url = f"{_frontend_url()}/alerts"
    hedge_url = f"{_frontend_url()}/hedge"
    settings_url = f"{_frontend_url()}/settings"

    content = f"""
    <h2 style="margin:0 0 16px;font-size:22px;color:#f1f5f9;">
      {display}, here are 3 features power users love 🚀
    </h2>

    <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:16px;">
      <tr>
        <td style="padding:16px;background:#0f172a;border-radius:8px;border-left:3px solid #f59e0b;">
          <strong style="color:#f1f5f9;">🔔 Price & GAS Alerts</strong>
          <p style="margin:6px 0 0;color:#94a3b8;font-size:14px;line-height:1.6;">
            Set alerts when a ticker crosses a price threshold or its Global Alignment Score
            changes significantly. Get notified in the app in real time.
          </p>
          <a href="{alerts_url}" style="color:#60a5fa;font-size:13px;">Set up alerts →</a>
        </td>
      </tr>
    </table>

    <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:16px;">
      <tr>
        <td style="padding:16px;background:#0f172a;border-radius:8px;border-left:3px solid #10b981;">
          <strong style="color:#f1f5f9;">🛡️ Hedging Simulator</strong>
          <p style="margin:6px 0 0;color:#94a3b8;font-size:14px;line-height:1.6;">
            Model Protective Puts, Collars, and Inverse ETF overlays. Compare equity curves
            and cost-of-protection across scenarios — before you pay a cent in options premium.
          </p>
          <a href="{hedge_url}" style="color:#60a5fa;font-size:13px;">Open Hedging Simulator →</a>
        </td>
      </tr>
    </table>

    <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;">
      <tr>
        <td style="padding:16px;background:#0f172a;border-radius:8px;border-left:3px solid #8b5cf6;">
          <strong style="color:#f1f5f9;">🔐 Two-Factor Authentication</strong>
          <p style="margin:6px 0 0;color:#94a3b8;font-size:14px;line-height:1.6;">
            Protect your account with TOTP 2FA — works with Google Authenticator, Authy,
            and any RFC 6238-compatible app. Enable it in Settings → Security.
          </p>
          <a href="{settings_url}" style="color:#60a5fa;font-size:13px;">Go to Settings →</a>
        </td>
      </tr>
    </table>

    <p style="color:#64748b;font-size:13px;line-height:1.6;">
      This is the last email in your onboarding series. You'll continue to receive the
      optional weekly market digest if you have it enabled in Settings → Notifications.
    </p>
    """
    return await _send(
        to,
        "Fin-Eye: 3 features that power users rely on",
        _base_template(content, unsubscribe_url=unsub_url),
        tags=[{"name": "sequence", "value": "onboarding_3"}],
    )


async def send_weekly_digest(
    to: str,
    name: Optional[str],
    unsubscribe_token: str,
    *,
    macro_summary: Optional[str] = None,
    recent_posts: Optional[list[dict]] = None,
) -> bool:
    """
    Optional weekly digest email.
    Content: macro summary, recent blog/learn posts, product updates.
    No trade recommendations — educational only.
    """
    display = name or "there"
    unsub_url = f"{_frontend_url()}/unsubscribe?token={unsubscribe_token}"
    week_str = datetime.now(timezone.utc).strftime("Week of %B %d, %Y")
    dashboard_url = f"{_frontend_url()}/"
    macro_url = f"{_frontend_url()}/macro"
    learn_url = f"{_frontend_url()}/learn"

    # Build macro section
    if macro_summary:
        macro_block = f"""
        <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;">
          <tr>
            <td style="padding:16px;background:#0f172a;border-radius:8px;">
              <h3 style="margin:0 0 8px;color:#f1f5f9;font-size:16px;">📊 Macro Snapshot</h3>
              <p style="margin:0;color:#94a3b8;font-size:14px;line-height:1.7;">{macro_summary}</p>
              <a href="{macro_url}" style="color:#60a5fa;font-size:13px;display:inline-block;margin-top:8px;">
                Full macro dashboard →
              </a>
            </td>
          </tr>
        </table>
        """
    else:
        macro_block = ""

    # Build posts section
    posts_block = ""
    if recent_posts:
        posts_html = ""
        for post in recent_posts[:3]:
            post_url = f"{_frontend_url()}/learn/{post.get('slug', '')}"
            posts_html += f"""
            <tr>
              <td style="padding:12px 0;border-bottom:1px solid #1e293b;">
                <a href="{post_url}" style="color:#60a5fa;font-weight:600;text-decoration:none;font-size:15px;">
                  {post.get('title', 'Untitled')}
                </a>
                <p style="margin:4px 0 0;color:#64748b;font-size:13px;">
                  {post.get('excerpt', '')}
                </p>
              </td>
            </tr>
            """
        posts_block = f"""
        <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:24px;">
          <tr>
            <td style="padding:16px;background:#0f172a;border-radius:8px;">
              <h3 style="margin:0 0 12px;color:#f1f5f9;font-size:16px;">📚 From the Learn Tab</h3>
              <table cellpadding="0" cellspacing="0" width="100%">
                {posts_html}
              </table>
              <a href="{learn_url}" style="color:#60a5fa;font-size:13px;display:inline-block;margin-top:12px;">
                View all articles →
              </a>
            </td>
          </tr>
        </table>
        """

    content = f"""
    <h2 style="margin:0 0 8px;font-size:22px;color:#f1f5f9;">
      Your weekly market digest 📈
    </h2>
    <p style="margin:0 0 24px;color:#64748b;font-size:13px;">{week_str}</p>

    <p style="color:#94a3b8;line-height:1.7;margin:0 0 24px;">
      Hi {display}, here's your Fin-Eye weekly roundup — macro context, recent content,
      and a reminder that all signals are <strong style="color:#f1f5f9;">educational only</strong>.
      Nothing here is a recommendation to buy or sell.
    </p>

    {macro_block}
    {posts_block}

    <table cellpadding="0" cellspacing="0" width="100%" style="margin-bottom:16px;">
      <tr>
        <td style="padding:16px;background:#0f172a;border-radius:8px;border-left:3px solid #2563eb;">
          <strong style="color:#f1f5f9;">Tip of the week</strong>
          <p style="margin:6px 0 0;color:#94a3b8;font-size:14px;line-height:1.6;">
            Use the Conflict Detector on the dashboard to spot when your technical signals,
            macro backdrop, and sentiment are pointing in different directions — divergence
            often precedes volatility.
          </p>
        </td>
      </tr>
    </table>

    {_btn(dashboard_url, "Open Dashboard →")}

    <p style="margin-top:24px;color:#64748b;font-size:13px;">
      You can adjust your digest frequency or unsubscribe at any time in
      <a href="{_frontend_url()}/settings" style="color:#60a5fa;">Settings → Notifications</a>.
    </p>
    """
    return await _send(
        to,
        f"Fin-Eye Weekly Digest — {week_str}",
        _base_template(content, unsubscribe_url=unsub_url),
        tags=[{"name": "type", "value": "weekly_digest"}],
    )


# ─── SEC-07: Email Verification ───────────────────────────────────────────

async def send_verification_email(to: str, token: str) -> bool:
    """
    SEC-07: Send the email-verification link to a newly registered user.
    The link points to the frontend /verify-email?token=... route which
    calls POST /api/v1/auth/verify-email on the backend.
    Token expires 24h after generation.
    """
    verify_url = f"{_frontend_url()}/verify-email?token={token}"

    content = f"""
    <h2 style="margin:0 0 16px;font-size:22px;color:#f1f5f9;">
      Verify your email address ✉️
    </h2>
    <p style="color:#94a3b8;line-height:1.7;margin:0 0 16px;">
      Thanks for signing up for Fin-Eye! Please verify your email address
      to unlock full access to the platform.
    </p>
    <p style="color:#94a3b8;line-height:1.7;margin:0 0 24px;">
      This link expires in <strong style="color:#f1f5f9;">24 hours</strong>.
    </p>
    {_btn(verify_url, 'Verify My Email →')}
    <p style="margin-top:24px;color:#64748b;font-size:13px;">
      If you didn’t sign up for Fin-Eye, you can safely ignore this email.
    </p>
    <p style="margin-top:8px;color:#475569;font-size:12px;word-break:break-all;">
      Or copy this link: {verify_url}
    </p>
    """
    return await _send(
        to,
        "Verify your Fin-Eye email address",
        _base_template(content),
        tags=[{"name": "type", "value": "verification"}],
    )
