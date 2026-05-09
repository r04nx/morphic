"""
Notification Agent — Layer 3 (Action)
Sends human-readable incident summary emails via SMTP.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from config import Config
from db import postgres

logger = logging.getLogger(__name__)

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
<body style="margin:0; padding:0; background-color:#0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
  <div style="max-width: 600px; margin: 40px auto; background: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 25px 50px rgba(0,0,0,0.5);">

    <!-- Header -->
    <div style="background: linear-gradient(135deg, #1e3a5f, #0f172a); padding: 32px; text-align: center; border-bottom: 1px solid #334155;">
      <div style="font-size: 36px; margin-bottom: 8px;">🚨</div>
      <h1 style="color: #f1f5f9; font-size: 22px; margin: 0 0 8px; font-weight: 700;">Morphic Incident Alert</h1>
      <span style="background: {color}22; color: {color}; border: 1px solid {color}; border-radius: 9999px; padding: 4px 16px; font-size: 13px; font-weight: 700; letter-spacing: 1px;">
        {blast_radius} SEVERITY
      </span>
    </div>

    <!-- Body -->
    <div style="padding: 32px;">
      <h2 style="color: #f1f5f9; font-size: 18px; margin: 0 0 16px; font-weight: 600;">{classification}</h2>

      <!-- Root Cause -->
      <div style="background: #0f172a; border-left: 4px solid {color}; border-radius: 4px; padding: 16px; margin-bottom: 24px;">
        <p style="color: #94a3b8; font-size: 12px; margin: 0 0 4px; text-transform: uppercase; letter-spacing: 1px;">Root Cause</p>
        <p style="color: #f1f5f9; margin: 0; font-size: 15px; line-height: 1.6;">{root_cause}</p>
      </div>

      <!-- Impact -->
      {'<div style="background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px; margin-bottom: 24px;"><p style="color: #94a3b8; font-size: 12px; margin: 0 0 4px; text-transform: uppercase; letter-spacing: 1px;">Impact</p><p style="color: #f1f5f9; margin: 0; font-size: 14px; line-height: 1.6;">' + impact + '</p></div>' if impact else ''}

      <!-- Metadata table -->
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
        <tr style="border-bottom: 1px solid #334155;">
          <td style="padding: 8px 0; color: #6b7280; font-size: 14px; width: 40%;">Trace ID</td>
          <td style="padding: 8px 0; font-size: 14px; font-family: monospace; color: #a5b4fc;">{trace_id}</td>
        </tr>
        <tr style="border-bottom: 1px solid #334155;">
          <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Service</td>
          <td style="padding: 8px 0; font-size: 14px; color: #f1f5f9;">{signals.get("service", "unknown")}</td>
        </tr>
        <tr style="border-bottom: 1px solid #334155;">
          <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Endpoint</td>
          <td style="padding: 8px 0; font-size: 14px; color: #f1f5f9; font-family: monospace;">{signals.get("endpoint", "")}</td>
        </tr>
        <tr style="border-bottom: 1px solid #334155;">
          <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Exception</td>
          <td style="padding: 8px 0; font-size: 14px; color: #fca5a5; font-family: monospace;">{signals.get("exception_class", "")}</td>
        </tr>
        <tr style="border-bottom: 1px solid #334155;">
          <td style="padding: 8px 0; color: #6b7280; font-size: 14px;">Confidence</td>
          <td style="padding: 8px 0; font-size: 14px; color: #f1f5f9;">{confidence:.0%}</td>
        </tr>
        {pr_section}
      </table>

      <!-- CTA -->
      <div style="text-align: center; margin-top: 24px;">
        <a href="{incident_url}" style="background: linear-gradient(135deg, #3b82f6, #6366f1); color: white; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 15px; display: inline-block;">
          View Incident Dashboard →
        </a>
      </div>
    </div>

    <!-- Footer -->
    <div style="padding: 20px 32px; background: #0f172a; border-top: 1px solid #334155; text-align: center;">
      <p style="color: #475569; font-size: 12px; margin: 0;">Morphic Self-Healing Incident Assistant • Automated alert — do not reply</p>
    </div>
  </div>
</body>
</html>"""


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
        return {"success": True, "error": None}

    except smtplib.SMTPAuthenticationError:
        err = "SMTP authentication failed — check EMAIL_FROM / EMAIL_PASSWORD"
        logger.error(err)
        if action_row:
            postgres.complete_action(str(action_row["id"]), "failed", {"error": err})
        return {"success": False, "error": err}
    except Exception as exc:
        err = str(exc)
        logger.error("Failed to send alert email: %s", err)
        if action_row:
            try:
                postgres.complete_action(str(action_row["id"]), "failed", {"error": err})
            except Exception:
                pass
        return {"success": False, "error": err}
