"""Async email sending via SMTP (aiosmtplib)."""
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


async def send_email(
    to: str | list[str],
    subject: str,
    body_html: str,
    body_text: str | None = None,
    attachments: list[tuple[bytes, str, str]] | None = None,
) -> bool:
    """
    Send an email. Returns True on success, False if SMTP is unconfigured or fails.

    attachments: list of (content_bytes, filename, mime_type)
    """
    from core.config import settings

    if not settings.smtp_host or not settings.smtp_user:
        log.warning("SMTP not configured — email not sent to %s", to)
        return False

    recipients = [to] if isinstance(to, str) else to

    msg = MIMEMultipart("mixed")
    msg["From"] = settings.from_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    alt = MIMEMultipart("alternative")
    if body_text:
        alt.attach(MIMEText(body_text, "plain"))
    alt.attach(MIMEText(body_html, "html"))
    msg.attach(alt)

    for content, filename, mime_type in (attachments or []):
        main_type, sub_type = mime_type.split("/", 1)
        part = MIMEApplication(content, _subtype=sub_type)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    try:
        import aiosmtplib
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_port == 465,
            start_tls=settings.smtp_port == 587,
        )
        log.info("Email sent to %s: %s", recipients, subject)
        return True
    except Exception as exc:
        log.error("Failed to send email to %s: %s", recipients, exc)
        return False


def proposal_html(proposal, amount: float | None = None) -> str:
    amount_str = f"${amount:,.2f}" if amount else "See attached proposal"
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="background: #1a3a5c; padding: 20px; border-radius: 8px 8px 0 0;">
    <h1 style="color: white; margin: 0; font-size: 22px;">BAMS AI — Proposal</h1>
  </div>
  <div style="background: #f9fafb; padding: 24px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
    <p>Dear {proposal.client_name or "Valued Client"},</p>
    <p>Please find attached our proposal <strong>{proposal.proposal_number or f"P-{proposal.id:04d}"}</strong>
       for <em>{proposal.title}</em>.</p>
    {"<p>Proposed amount: <strong>" + amount_str + "</strong></p>" if amount else ""}
    <p>This proposal is valid for {proposal.validity_days or 30} days from the date of issue.</p>
    <p>Please don't hesitate to reach out with any questions.</p>
    <p style="margin-top: 24px;">Best regards,<br><strong>BAMS AI</strong></p>
  </div>
</body>
</html>
"""
