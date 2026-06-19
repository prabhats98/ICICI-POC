"""
Ingest Azure Logs — Reads a JSONL file of raw Azure cloud logs and inserts
each entry into the `raw_logs` table for pipeline processing.

Usage:
    python -m app.ingest_azure_logs <path_to_jsonl_file>
    
    # Or with default file:
    python -m app.ingest_azure_logs
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from app.database import async_session, init_db
from app.models.raw_log import RawLog


DEFAULT_FILE = r"C:\Users\Suvendu Behera\Downloads\azure_logs_raw (1).jsonl"


async def ingest_jsonl(file_path: str):
    """
    Read a JSONL file and insert each line as a RawLog entry
    into the raw_logs table.
    """
    path = Path(file_path)
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    print(f"📂 Reading logs from: {file_path}")

    # Parse all lines
    raw_entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                raw_entries.append(payload)
            except json.JSONDecodeError as e:
                print(f"⚠️  Skipping line {line_num}: invalid JSON - {e}")

    if not raw_entries:
        print("❌ No valid log entries found in the file.")
        sys.exit(1)

    print(f"📊 Parsed {len(raw_entries)} log entries")

    # Initialize database tables
    await init_db()

    # Insert into raw_logs table
    async with async_session() as session:
        now = datetime.utcnow()
        raw_logs = []

        for payload in raw_entries:
            # Extract message from the payload (different structures)
            message = ""
            if "properties" in payload and isinstance(payload["properties"], dict):
                message = payload["properties"].get("message", "") or payload["properties"].get("statusMessage", "")
            if not message:
                message = payload.get("resultDescription", "") or payload.get("operationName", "")

            # Detect source system from payload
            resource_provider = payload.get("resourceProvider", "").upper()
            source_system = "azure-monitor-jsonl-import"
            if "CDN" in resource_provider or "FRONTDOOR" in resource_provider:
                source_system = "azure-front-door"
            elif "NETWORK" in resource_provider and "GATEWAY" in str(payload.get("category", "")):
                source_system = "azure-app-gateway"
            elif "APIMANAGEMENT" in resource_provider:
                source_system = "azure-apim"
            elif "COMPUTE" in resource_provider:
                source_system = "azure-vm"

            raw_log = RawLog(
                id=str(uuid.uuid4()),
                ingested_at=now,
                source_system=source_system,
                raw_payload=payload,
                raw_text=message,
                is_preprocessed=False,
            )
            raw_logs.append(raw_log)

        session.add_all(raw_logs)
        await session.commit()

        print(f"✅ Successfully ingested {len(raw_logs)} log entries into 'raw_logs' table")
        print(f"   → Run the agent pipeline to preprocess them into 'cloud_logs'")


if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE
    asyncio.run(ingest_jsonl(file_path))
