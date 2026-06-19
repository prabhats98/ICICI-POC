"""
Email Service — Sends alert emails via SMTP or Azure Communication Services.
Channel selection is driven by NOTIFICATION_CHANNEL in .env.
"""

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """Unified email service supporting SMTP and Azure Communication Services."""

    def __init__(self):
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.default_to_email = settings.smtp_to_email

    async def send_alert_email(
        self,
        subject: str,
        html_body: str,
        to_email: str | None = None,
    ) -> bool:
        """
        Send an alert email using the configured channel.
        Tries Azure Communication Services first if configured, falls back to SMTP.
        """
        recipient = to_email or self.default_to_email
        channel = settings.notification_channel

        # Try Azure Communication Services
        if channel == "azure_communication_service":
            try:
                from app.services.azure_notification_service import azure_notification_service
                sent = await azure_notification_service.send_email(recipient, subject, html_body)
                if sent:
                    return True
                logger.warning("ACS failed, falling back to SMTP")
            except Exception as e:
                logger.warning(f"ACS unavailable ({e}), falling back to SMTP")

        # SMTP (primary or fallback)
        return await self._send_smtp(recipient, subject, html_body)

    async def _send_smtp(self, to_email: str, subject: str, html_body: str) -> bool:
        """Send email via SMTP."""
        message = MIMEMultipart("alternative")
        message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = subject
        message["X-Priority"] = "1"
        message["X-Mailer"] = "Azure Incident Log Pipeline"

        plain_text = f"ALERT\n\n{subject}\n\nPlease view this email in an HTML-capable client."
        message.attach(MIMEText(plain_text, "plain"))
        message.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=False,
                start_tls=True,
            )
            logger.info(f"SMTP email sent to {to_email}: {subject}")
            return True
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending to {to_email}: {e}")
            return False
        except Exception as e:
            logger.warning(
                f"Email sending failed: {e}. "
                f"Would have sent to {to_email} with subject: {subject}"
            )
            return False


# Singleton
email_service = EmailService()
