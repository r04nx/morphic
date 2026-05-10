"""
Notification Agent — Layer 3 (Action)
Sends human-readable incident summary emails via SMTP.
"""

import logging
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from config import Config
from db import postgres

logger = logging.getLogger(__name__)

MORPHIC_LOGO_PNG_BASE64 = "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"

# Severity → colour map for the HTML email
_SEVERITY_COLORS = {
    "LOW":      "#10b981",   # green
    "MEDIUM":   "#f59e0b",   # amber
    "HIGH":     "#ef4444",   # red
    "CRITICAL": "#7c3aed",   # purple
}


def _build_html(
    rca: dict[str, Any],
    pr_url: str | None,
    dashboard_url: str,
) -> str:
    trace_id = rca.get("trace_id", "unknown")
    classification = rca.get("classification", "Unknown Incident")
    blast_radius = rca.get("blast_radius", "MEDIUM")
    root_cause = rca.get("root_cause", "Not determined")
    impact = rca.get("impact", "")
    confidence = rca.get("confidence_score", 0.0)
    color = _SEVERITY_COLORS.get(blast_radius, "#6b7280")
    incident_url = f"{dashboard_url}/incidents?trace={trace_id}" if dashboard_url else "#"
    signals = rca.get("log_signals", {})

    pr_section = ""
    if pr_url:
        pr_section = f"""
        <tr>
          <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">GitHub PR</td>
          <td style="padding: 8px 0; font-size: 14px;">
            <a href="{pr_url}" style="color: #3b82f6;">View Auto-Fix PR →</a>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;">
  <div style="max-width:680px;margin:24px auto;background-color:#ffffff;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">

    <div style="background-color:#111827;color:#ffffff;padding:18px 20px;">
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="width:44px;vertical-align:middle;">
            <img alt="Morphic" width="32" height="32" style="display:block;border-radius:6px;" src="data:image/png;base64,{MORPHIC_LOGO_PNG_BASE64}" />
          </td>
          <td style="vertical-align:middle;text-align:left;">
            <div style="font-size:14px;letter-spacing:0.3px;font-weight:600;line-height:18px;">Morphic</div>
            <div style="font-size:12px;opacity:0.85;line-height:16px;">Incident Notification</div>
          </td>
        </tr>
      </table>
    </div>

    <div style="padding:18px 20px;text-align:left;">
      <div style="display:inline-block;padding:6px 10px;border-radius:999px;background:{color}22;color:{color};border:1px solid {color};font-size:12px;font-weight:700;letter-spacing:0.6px;text-transform:uppercase;">
        {blast_radius}
      </div>

      <h2 style="margin:14px 0 10px 0;font-size:16px;line-height:22px;color:#111827;">{classification}</h2>

      <table style="width:100%;border-collapse:collapse;margin:0 0 14px 0;">
        <tr>
          <td style="padding:8px 0;width:140px;color:#6b7280;font-size:12px;font-weight:600;">Trace ID</td>
          <td style="padding:8px 0;color:#111827;font-size:12px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;">{trace_id}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;width:140px;color:#6b7280;font-size:12px;font-weight:600;">Service</td>
          <td style="padding:8px 0;color:#111827;font-size:12px;">{signals.get("service", "unknown")}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;width:140px;color:#6b7280;font-size:12px;font-weight:600;">Endpoint</td>
          <td style="padding:8px 0;color:#111827;font-size:12px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;">{signals.get("endpoint", "")}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;width:140px;color:#6b7280;font-size:12px;font-weight:600;">Exception</td>
          <td style="padding:8px 0;color:#111827;font-size:12px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;">{signals.get("exception_class", "")}</td>
        </tr>
        <tr>
          <td style="padding:8px 0;width:140px;color:#6b7280;font-size:12px;font-weight:600;">Confidence</td>
          <td style="padding:8px 0;color:#111827;font-size:12px;">{confidence:.0%}</td>
        </tr>
        {pr_section}
      </table>

      <div style="border:1px solid #e5e7eb;background-color:#f9fafb;border-radius:10px;padding:12px 12px;margin-bottom:14px;">
        <div style="color:#6b7280;font-size:12px;font-weight:600;margin-bottom:6px;">Root Cause</div>
        <div style="color:#111827;font-size:13px;line-height:18px;white-space:pre-wrap;">{root_cause}</div>
      </div>

      {('<div style="border:1px solid #e5e7eb;background-color:#f9fafb;border-radius:10px;padding:12px 12px;margin-bottom:14px;"><div style="color:#6b7280;font-size:12px;font-weight:600;margin-bottom:6px;">Impact</div><div style="color:#111827;font-size:13px;line-height:18px;white-space:pre-wrap;">' + impact + '</div></div>') if impact else ''}

      <div style="margin-top:12px;">
        <a href="{incident_url}" style="display:inline-block;background-color:#111827;color:#ffffff;text-decoration:none;padding:10px 14px;border-radius:8px;font-size:12px;font-weight:600;">View in Dashboard</a>
      </div>
    </div>

    <div style="border-top:1px solid #e5e7eb;background-color:#ffffff;padding:14px 20px;text-align:left;">
      <div style="color:#6b7280;font-size:11px;line-height:16px;">Automated alert from Morphic. Do not reply.</div>
    </div>
  </div>
</body>
</html>"""


def _send_telegram(
    rca: dict[str, Any],
    pr_url: str | None,
) -> dict[str, Any]:
    """
    Send a Telegram message for an incident.
    Returns {"success": bool, "error": str | None}
    Fails gracefully — never raises.
    """
    token   = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID

    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping Telegram notification")
        return {"success": False, "error": "TELEGRAM_BOT_TOKEN not configured"}
    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID not set — skipping Telegram notification")
        return {"success": False, "error": "TELEGRAM_CHAT_ID not configured"}

    blast_radius   = rca.get("blast_radius", "MEDIUM")
    classification = rca.get("classification", "Unknown Incident")
    root_cause     = rca.get("root_cause", "Not determined")
    impact         = rca.get("impact", "\u2014")
    confidence     = rca.get("confidence_score", 0.0)
    trace_id       = rca.get("trace_id", "unknown")
    signals        = rca.get("log_signals", {})
    service        = signals.get("service") or rca.get("service", "unknown")
    confidence_pct = int(float(confidence) * 100)

    lines = [
        f"\U0001f6a8 *[{blast_radius}] {classification}*",
        "",
        f"*Root Cause:* {root_cause}",
        f"*Impact:* {impact}",
        f"*Confidence:* {confidence_pct}%",
        f"*Trace ID:* `{trace_id}`",
        f"*Service:* {service}",
    ]
    if pr_url:
        lines.append(f"*PR:* {pr_url}")

    text = "\n".join(lines)

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id":    chat_id,
                "text":       text,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info("Telegram alert sent for trace_id=%s", trace_id)
            return {"success": True, "error": None}
        err = resp.text
        logger.warning("Telegram API error: %s", err)
        return {"success": False, "error": err}
    except Exception as exc:
        logger.warning("Telegram notification failed: %s", exc)
        return {"success": False, "error": str(exc)}


def send_alert(
    rca: dict[str, Any],
    incident: dict[str, Any],
    pr_url: str | None = None,
) -> dict[str, Any]:
    """
    Send an incident alert email.

    Returns {"success": bool, "error": str | None}
    """
    if not Config.EMAIL_FROM or not Config.EMAIL_PASSWORD or not Config.EMAIL_TO:
        logger.warning("Email not configured — skipping notification")
        return {"success": False, "error": "Email credentials not configured"}

    trace_id = rca.get("trace_id") or incident.get("trace_id", "unknown")
    classification = rca.get("classification", "Unknown Incident")
    blast_radius = rca.get("blast_radius", "MEDIUM")
    incident_id = incident.get("incident_id")

    subject = f"[Morphic] {blast_radius} — {classification} | trace: {trace_id[:12]}"
    html_body = _build_html(rca, pr_url, Config.DASHBOARD_URL)
    text_body = (
        f"Morphic Incident Alert\n\n"
        f"Severity:    {blast_radius}\n"
        f"Class:       {classification}\n"
        f"Root Cause:  {rca.get('root_cause', 'unknown')}\n"
        f"Trace ID:    {trace_id}\n"
        f"Service:     {rca.get('log_signals', {}).get('service', 'unknown')}\n"
        f"Confidence:  {rca.get('confidence_score', 0.0):.0%}\n"
        + (f"PR:          {pr_url}\n" if pr_url else "")
        + f"Dashboard:   {Config.DASHBOARD_URL}/incidents?trace={trace_id}\n"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = Config.EMAIL_FROM
    msg["To"] = Config.EMAIL_TO
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    # Record action in DB
    action_row = None
    if incident_id:
        try:
            action_row = postgres.insert_action({
                "incident_id": incident_id,
                "action_type": "email",
                "status":      "running",
                "details":     {"to": Config.EMAIL_TO, "subject": subject},
            })
        except Exception as exc:
            logger.warning("Could not record email action: %s", exc)

    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(Config.EMAIL_FROM, Config.EMAIL_PASSWORD)
            server.sendmail(Config.EMAIL_FROM, Config.EMAIL_TO.split(","), msg.as_string())
        logger.info("Alert email sent to %s for trace_id=%s", Config.EMAIL_TO, trace_id)

        if action_row:
            postgres.complete_action(
                str(action_row["id"]),
                "completed",
                {"to": Config.EMAIL_TO, "subject": subject},
            )
        email_result = {"success": True, "error": None}

    except smtplib.SMTPAuthenticationError:
        err = "SMTP authentication failed — check EMAIL_FROM / EMAIL_PASSWORD"
        logger.error(err)
        if action_row:
            postgres.complete_action(str(action_row["id"]), "failed", {"error": err})
        email_result = {"success": False, "error": err}
    except Exception as exc:
        err = str(exc)
        logger.error("Failed to send alert email: %s", err)
        if action_row:
            try:
                postgres.complete_action(str(action_row["id"]), "failed", {"error": err})
            except Exception:
                pass
        email_result = {"success": False, "error": err}

    # ── Telegram (independent — never blocks email result) ──────────────
    telegram_result = _send_telegram(rca, pr_url)

    return {
        "success":  email_result["success"] or telegram_result["success"],
        "email":    email_result,
        "telegram": telegram_result,
        "error":    email_result["error"] if not email_result["success"] else None,
    }
