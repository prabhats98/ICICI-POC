"""
Firestore Service - Fetches raw Azure log data from Firestore
and ingests it into the local PostgreSQL raw_logs table.
"""

from google.cloud.firestore_v1.base_query import FieldFilter

import logging
from pathlib import Path
from typing import Any

from google.cloud import firestore
from google.oauth2 import service_account

from app.config import get_settings

logger = logging.getLogger(__name__)


class FirestoreService:
    """Handles fetching log data from Firestore and tracking ingested docs."""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> firestore.Client:
        """Lazy-initialize the Firestore client."""
        if self._client is None:
            settings = get_settings()

            # Resolve service account path relative to backend dir
            # This file is at backend/app/services/firestore_service.py
            # so .parent.parent.parent = backend/
            sa_path = Path(settings.firestore_service_account)
            if not sa_path.is_absolute():
                sa_path = Path(__file__).parent.parent.parent / sa_path
            sa_path = sa_path.resolve()

            credentials = service_account.Credentials.from_service_account_file(
                str(sa_path)
            )
            self._client = firestore.Client(
                project=credentials.project_id,
                credentials=credentials,
                database="(default)",
            )
            logger.info(
                f"Firestore client initialized for project: {credentials.project_id}"
            )
        return self._client

    def fetch_unprocessed_logs(self, batch_size: int = 200) -> list[dict[str, Any]]:
        """
        Fetch documents from Firestore that haven't been ingested yet.

        Documents are marked with `is_ingested: true` after being pulled
        into PostgreSQL so they aren't fetched again on the next run.

        Returns:
            List of dicts, each containing 'firestore_doc_id' and 'payload'.
        """
        settings = get_settings()
        collection_name = settings.firestore_collection

        logger.info(
            f"Fetching unprocessed logs from Firestore collection: {collection_name}"
        )

        collection_ref = self.client.collection(collection_name)

        # Query for documents not yet ingested (use filter keyword to avoid deprecation)
        query = (
            collection_ref
            .where(filter=FieldFilter("is_ingested", "==", False))
            .limit(batch_size)
        )
        docs = list(query.stream())

        # If no docs found with is_ingested == False, also try docs
        # that don't have the is_ingested field at all (first-time fetch)
        if not docs:
            all_docs = list(collection_ref.limit(batch_size).stream())
            docs = [
                doc for doc in all_docs
                if not doc.to_dict().get("is_ingested", False)
            ]

        results = []
        for doc in docs:
            data = doc.to_dict()
            results.append({
                "firestore_doc_id": doc.id,
                "payload": data,
            })

        logger.info(f"Fetched {len(results)} unprocessed documents from Firestore")
        return results

    def mark_as_ingested(self, doc_ids: list[str]) -> None:
        """
        Mark Firestore documents as ingested so they won't be fetched again.

        Uses batched writes for efficiency (Firestore batch limit: 500).
        """
        if not doc_ids:
            return

        settings = get_settings()
        collection_name = settings.firestore_collection
        batch_size = 400

        for i in range(0, len(doc_ids), batch_size):
            batch = self.client.batch()
            chunk = doc_ids[i:i + batch_size]

            for doc_id in chunk:
                doc_ref = self.client.collection(collection_name).document(doc_id)
                batch.update(doc_ref, {"is_ingested": True})

            batch.commit()

        logger.info(f"Marked {len(doc_ids)} Firestore documents as ingested")

    def reset_ingestion_flags(self) -> None:
        """Reset is_ingested flag on all Firestore documents so they can be re-ingested."""
        settings = get_settings()
        collection_name = settings.firestore_collection

        docs = self.client.collection(collection_name).where(
            filter=FieldFilter("is_ingested", "==", True)
        ).stream()

        doc_ids = []
        batch = self.client.batch()
        count = 0

        for doc in docs:
            doc_ref = self.client.collection(collection_name).document(doc.id)
            batch.update(doc_ref, {"is_ingested": False})
            doc_ids.append(doc.id)
            count += 1

            if count % 400 == 0:
                batch.commit()
                batch = self.client.batch()

        if count % 400 != 0:
            batch.commit()

        logger.info(f"Reset is_ingested flag on {count} Firestore documents")


# Singleton instance
firestore_service = FirestoreService()
