"""Email notification helper — uses Gmail SMTP.

Reads credentials from Streamlit secrets (.streamlit/secrets.toml):

    [email]
    sender = "you@gmail.com"
    app_password = "xxxx xxxx xxxx xxxx"

If secrets are not configured, all calls silently return without error.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def _get_email_config() -> tuple[str, str] | None:
    """Return (sender, app_password) or None if not configured."""
    try:
        import streamlit as st
        email_cfg = st.secrets.get("email")
        if not email_cfg:
            return None
        sender = email_cfg.get("sender", "")
        app_password = email_cfg.get("app_password", "")
        if sender and app_password:
            return sender, app_password
    except Exception:
        pass
    return None


def send_scan_complete(to_email: str, job_count: int) -> bool:
    """Send a notification email when a job scan finishes.

    Returns True if sent, False if skipped or failed.
    """
    if not to_email:
        return False

    config = _get_email_config()
    if config is None:
        logger.info("Email secrets not configured — skipping notification.")
        return False

    sender, app_password = config

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"AcademicFinder: Scan Complete — {job_count} jobs found"
    msg["From"] = sender
    msg["To"] = to_email

    text = (
        f"Your AcademicFinder scan has finished!\n\n"
        f"Found {job_count} unique positions.\n\n"
        f"Log in to view your results and matched positions.\n"
    )
    html = (
        f"<h2>AcademicFinder Scan Complete</h2>"
        f"<p>Your job scan has finished!</p>"
        f"<p><strong>{job_count}</strong> unique positions found.</p>"
        f"<p>Log in to view your results and matched positions.</p>"
    )
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.send_message(msg)
        logger.info("Scan notification sent to %s", to_email)
        return True
    except Exception as exc:
        logger.warning("Failed to send email to %s: %s", to_email, exc)
        return False
