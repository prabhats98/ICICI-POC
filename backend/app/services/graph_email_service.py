"""
Graph API Email Service — Sends emails via Microsoft Graph API using SP credentials.
Uses the same Azure SP credentials already configured for log collection.
"""

import logging
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GraphEmailService:
    """Send emails via Microsoft Graph API using Service Principal auth."""

    def __init__(self):
        self.tenant_id = settings.azure_tenant_id
        self.client_id = settings.azure_client_id
        self.client_secret = settings.azure_client_secret
        self.sender_email = settings.graph_sender_email
        self._token: str | None = None

    async def _get_access_token(self) -> str:
        """Get an Azure AD access token for Graph API."""
        token_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        )
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(token_url, data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
            })
            data = resp.json()
            if "access_token" not in data:
                raise RuntimeError(f"Graph auth failed: {data.get('error_description', data)}")
            self._token = data["access_token"]
            return self._token

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        sender: str | None = None,
    ) -> bool:
        """
        Send an email via Microsoft Graph API.

        If sender is provided, sends from that user's mailbox.
        If no sender is configured, uses /me (delegated) which won't work
        for app-only auth — requires a sender UPN.
        """
        try:
            token = await self._get_access_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            # Support comma-separated multiple recipients
            recipients = [
                {"emailAddress": {"address": addr.strip()}}
                for addr in to_email.split(",")
                if addr.strip()
            ]

            email_msg = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html_body,
                    },
                    "toRecipients": recipients,
                },
                "saveToSentItems": "false",
            }

            from_user = sender or self.sender_email
            if from_user:
                # App-only: send from specific user mailbox
                url = f"https://graph.microsoft.com/v1.0/users/{from_user}/sendMail"
            else:
                # Fallback: try without specific sender
                url = "https://graph.microsoft.com/v1.0/me/sendMail"

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, headers=headers, json=email_msg)

            if resp.status_code == 202:
                logger.info(f"Graph API email sent to {to_email}: {subject}")
                return True
            else:
                error_detail = resp.text[:300]
                logger.error(
                    f"Graph API email failed ({resp.status_code}): {error_detail}"
                )
                return False

        except Exception as e:
            logger.error(f"Graph API email error: {e}")
            return False


# Singleton
graph_email_service = GraphEmailService()
