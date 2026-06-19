"""
Azure Notification Service — Send emails via Azure Communication Services.
"""

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AzureNotificationService:
    """Send emails via Azure Communication Services Email SDK."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy-init the Azure Communication Email client."""
        if self._client is None:
            try:
                from azure.communication.email import EmailClient
                self._client = EmailClient.from_connection_string(
                    settings.azure_communication_connection_string
                )
            except Exception as e:
                logger.error(f"Failed to initialize Azure Communication Email client: {e}")
                raise
        return self._client

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
    ) -> bool:
        """
        Send an email via Azure Communication Services.

        Returns True if sent successfully.
        """
        try:
            message = {
                "senderAddress": settings.azure_communication_sender,
                "recipients": {
                    "to": [{"address": to_email}],
                },
                "content": {
                    "subject": subject,
                    "html": html_body,
                },
            }

            poller = self.client.begin_send(message)
            result = poller.result()
            status = result.get("status", "Unknown")

            if status == "Succeeded":
                logger.info(f"ACS email sent to {to_email}: {subject}")
                return True
            else:
                logger.warning(f"ACS email status {status} for {to_email}: {subject}")
                return False

        except Exception as e:
            logger.error(f"ACS email failed to {to_email}: {e}")
            return False


# Singleton
azure_notification_service = AzureNotificationService()
