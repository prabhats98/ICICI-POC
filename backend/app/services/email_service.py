"""
Email Service - Sends alert emails for high-priority incidents via SMTP.
Uses demo credentials by default; replace in .env for production.
"""

import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import aiosmtplib

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """Async email service for sending priority alert emails."""

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
        Send an HTML alert email to the production manager.

        Args:
            subject: Email subject line
            html_body: HTML formatted email body
            to_email: Recipient email (defaults to SMTP_TO_EMAIL from .env)

        Returns:
            True if email sent successfully, False otherwise
        """
        recipient = to_email or self.default_to_email

        # Build the email message
        message = MIMEMultipart("alternative")
        message["From"] = self.from_email
        message["To"] = recipient
        message["Subject"] = subject
        message["X-Priority"] = "1"  # High priority
        message["X-Mailer"] = "Banking Cloud Log Analyser"

        # Plain text fallback
        plain_text = f"CRITICAL ALERT\n\n{subject}\n\nPlease view this email in an HTML-capable client for full details."
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
            logger.info(f"Alert email sent to {recipient}: {subject}")
            return True
        except aiosmtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {recipient}: {e}")
            return False
        except Exception as e:
            # Demo mode: log but don't crash when using demo credentials
            logger.warning(
                f"Email sending failed (using demo credentials?): {e}. "
                f"Email would have been sent to {recipient} with subject: {subject}"
            )
            return False


# Singleton instance
email_service = EmailService()
