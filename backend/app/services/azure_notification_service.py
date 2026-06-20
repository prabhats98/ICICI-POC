"""
Azure Notification Service — Send emails via Azure Communication Services.
"""

import logging
import re
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
        """Lazy-init the Azure Communication Email client with no internal retries."""
        if self._client is None:
            try:
                from azure.communication.email import EmailClient
                from azure.core.pipeline.policies import RetryPolicy

                # Disable the SDK's internal retry policy so that 429s
                # surface immediately as exceptions instead of blocking
                # for the full Retry-After period (which can be 60+ mins).
                self._client = EmailClient.from_connection_string(
                    settings.azure_communication_connection_string,
                    retry_policy=RetryPolicy(retry_total=0),
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

        The begin_send + poller.result() are both synchronous/blocking SDK
        calls, so we run the entire operation in a thread with a strict
        timeout to prevent blocking the async event loop.
        """
        import asyncio

        SEND_TIMEOUT_SECONDS = 20  # Max time for the entire send operation

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

        def _blocking_send():
            """Run the synchronous SDK send in a thread."""
            poller = self.client.begin_send(message)
            return poller.result()

        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(_blocking_send),
                timeout=SEND_TIMEOUT_SECONDS,
            )
            status = result.get("status", "Unknown")

            if status == "Succeeded":
                logger.info(f"ACS email sent to {to_email}: {subject}")
                return True
            else:
                logger.warning(f"ACS email status '{status}' for {to_email}: {subject}")
                return False

        except asyncio.TimeoutError:
            logger.error(
                f"ACS email timed out after {SEND_TIMEOUT_SECONDS}s for {to_email}. "
                f"The service may be rate-limited. Failing fast."
            )
            return False
        except Exception as e:
            err_str = str(e)
            if "TooManyRequests" in err_str or "429" in err_str:
                retry_after = self._extract_retry_after(err_str)
                wait_msg = f" (Retry-After: ~{retry_after // 60}m)" if retry_after else ""
                logger.error(
                    f"ACS rate-limited{wait_msg}. "
                    f"Email to {to_email} will not be sent. "
                    f"Subject: {subject}"
                )
            else:
                logger.error(f"ACS email failed to {to_email}: {e}")
            return False

    @staticmethod
    def _extract_retry_after(error_str: str) -> int | None:
        """Try to extract Retry-After seconds from an error message."""
        match = re.search(r"[Rr]etry-[Aa]fter['\"]?\s*[:=]\s*['\"]?(\d+)", error_str)
        if match:
            return int(match.group(1))
        return None


# Singleton
azure_notification_service = AzureNotificationService()

