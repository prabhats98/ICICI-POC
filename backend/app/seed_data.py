"""
Seed script — Inserts sample Azure cloud logs into the `raw_logs` table
in PostgreSQL for testing the segregation pipeline.

Agent 1 will pick these up, segregate them, and store structured data
in the `cloud_logs` table.

Run: python -m app.seed_data
"""

import asyncio
import uuid
import json
import random
from datetime import datetime, timedelta

from app.database import async_session, init_db
from app.models.raw_log import RawLog


# Sample raw Azure cloud log payloads (as they would arrive from Azure Monitor)
SAMPLE_RAW_PAYLOADS = [
    {
        "level": "Error",
        "source": "Azure App Service",
        "category": "Authentication",
        "message": "Failed login attempt from IP 203.0.113.42 - Account lockout threshold exceeded for user admin@bankingportal.com",
        "operationName": "Microsoft.Web/sites/login",
        "resourceId": "/subscriptions/sub-001/resourceGroups/banking-prod/providers/Microsoft.Web/sites/banking-portal",
        "resourceGroup": "banking-prod-rg",
        "subscriptionId": "sub-001",
        "correlationId": None,  # Will be auto-generated
    },
    {
        "level": "Critical",
        "source": "Azure SQL Database",
        "category": "Performance",
        "message": "DTU consumption exceeded 95% on production database 'BankingTransactionsDB'. Query timeout errors detected across 12 connections.",
        "operationName": "Microsoft.Sql/servers/databases/metrics",
        "resourceId": "/subscriptions/sub-002/resourceGroups/banking-prod/providers/Microsoft.Sql/servers/banking-sql",
        "resourceGroup": "banking-prod-rg",
        "subscriptionId": "sub-002",
    },
    {
        "level": "Error",
        "source": "Azure Key Vault",
        "category": "Security",
        "message": "Unauthorized access attempt to secret 'prod-encryption-key' from unrecognized IP 198.51.100.77. Access policy violation.",
        "operationName": "Microsoft.KeyVault/vaults/secrets/read",
        "resourceId": "/subscriptions/sub-001/resourceGroups/banking-prod/providers/Microsoft.KeyVault/vaults/banking-keyvault",
    },
    {
        "level": "Warning",
        "source": "Azure API Management",
        "category": "Rate Limiting",
        "message": "Rate limit threshold reached for API 'payment-processing-v2'. 2,847 requests/min vs 2,000 limit. Client: merchant-gateway-prod.",
        "operationName": "Microsoft.ApiManagement/service/apis/throttled",
        "resourceId": "/subscriptions/sub-003/resourceGroups/banking-prod/providers/Microsoft.ApiManagement/service/banking-apim",
    },
    {
        "level": "Error",
        "source": "Azure Functions",
        "message": "Function 'ProcessTransactionBatch' failed with OutOfMemoryException after processing 15,000 records. Memory limit: 1.5GB exceeded.",
        "operationName": "Microsoft.Web/sites/functions/execution",
    },
    {
        "level": "Information",
        "message": "Autoscale rule triggered: Scaled out App Service Plan 'banking-prod-plan' from 4 to 8 instances due to CPU > 80%.",
        "operationName": "Microsoft.Insights/autoscaleSettings/scaleUp",
    },
    {
        "level": "Warning",
        "message": "Storage account 'bankingdoclake' approaching capacity limit. Current usage: 4.7TB of 5TB provisioned. Consider scaling tier.",
        "operationName": "Microsoft.Storage/storageAccounts/capacity",
    },
    {
        "level": "Error",
        "message": "Dead letter queue 'transaction-dlq' has 1,247 messages. Oldest message age: 4 hours. Consumer group 'fraud-detection' appears stuck.",
        "operationName": "Microsoft.ServiceBus/namespaces/queues/deadLetterMessages",
    },
    {
        "level": "Critical",
        "message": "Multiple failed MFA challenges detected for privileged accounts. 23 failures in last 15 minutes. Potential brute force attack on admin portal.",
        "operationName": "Microsoft.AAD/signInLogs/failure",
    },
    {
        "level": "Information",
        "message": "Release 'banking-core-api-v3.2.1' deployed to production slot. Health check passed. Rolling update 100% complete.",
        "operationName": "Microsoft.DevOps/pipelines/releases/deploy",
    },
    {
        "level": "Warning",
        "message": "Request unit consumption spike detected on container 'CustomerProfiles'. RU/s: 45,000 (provisioned: 50,000). Partition key hotspot on region 'US-East'.",
        "operationName": "Microsoft.DocumentDB/databaseAccounts/metrics",
    },
    {
        "level": "Error",
        "message": "Backend pool 'banking-web-servers' health probe failures: 3 of 8 instances unhealthy. SYN timeout on ports 443, 8443.",
        "operationName": "Microsoft.Network/loadBalancers/probes/failed",
    },
    {
        "level": "Information",
        "message": "Scheduled backup completed for vault 'banking-prod-vault'. 47 VMs protected. RPO compliance: 100%. Last backup: 2 hours ago.",
        "operationName": "Microsoft.RecoveryServices/vaults/backupJobs",
    },
    {
        "level": "Warning",
        "message": "Suspicious outbound traffic detected from subnet 'banking-app-tier'. 847 connection attempts to known C2 domains blocked in last hour.",
        "operationName": "Microsoft.Network/azureFirewalls/threatIntel",
    },
    {
        "level": "Error",
        "message": "Throughput unit capacity exceeded on namespace 'banking-events-prod'. Event ingestion dropped 2,340 events. Consumer lag: 45 minutes.",
        "operationName": "Microsoft.EventHub/namespaces/throughputExceeded",
    },
    {
        "level": "Critical",
        "message": "Health endpoint /api/health returning 503 for 'banking-portal-prod'. Instance restart triggered. Downtime: 3 minutes. Affected users: ~2,400.",
        "operationName": "Microsoft.Web/sites/health/degraded",
    },
    {
        "level": "Information",
        "message": "Compliance scan completed. 94% compliant. 3 non-compliant resources: missing encryption-at-rest tags on storage accounts.",
        "operationName": "Microsoft.PolicyInsights/complianceResults",
    },
    {
        "level": "Error",
        "message": "Cache hit ratio dropped to 34% (baseline: 92%). Memory fragmentation ratio: 2.3. Session store 'banking-sessions' experiencing high eviction rate.",
        "operationName": "Microsoft.Cache/Redis/metrics",
    },
    {
        "level": "Warning",
        "message": "Container 'fraud-ml-scorer' replica count at maximum (20). Queue depth: 5,432. Average response time degraded to 4.2s (SLA: 2s).",
        "operationName": "Microsoft.App/containerApps/scaling",
    },
    {
        "level": "Error",
        "message": "Geo-replication lag on 'BankingTransactionsDB' secondary exceeded 30 seconds. Primary region: East US. Secondary: West US. Potential data consistency risk.",
        "operationName": "Microsoft.Sql/servers/databases/replicationLinks",
    },
]


async def seed_raw_logs(count: int = 50):
    """
    Insert sample raw Azure cloud logs into the `raw_logs` table.
    
    These will be picked up by Agent 1 (Log Extractor) which will:
    1. Parse the raw JSON payloads
    2. Segregate by level, source, category
    3. Store structured entries in the `cloud_logs` table
    """
    await init_db()

    async with async_session() as session:
        now = datetime.utcnow()
        raw_logs = []

        for i in range(count):
            sample = random.choice(SAMPLE_RAW_PAYLOADS)

            # Build a raw payload as it would arrive from Azure Monitor
            payload = {
                **sample,
                "timestamp": (now - timedelta(minutes=random.randint(1, 1440))).isoformat() + "Z",
                "correlationId": str(uuid.uuid4()),
                "properties": {
                    "statusCode": random.choice(["200", "400", "401", "403", "500", "502", "503"]),
                    "durationMs": random.randint(50, 30000),
                    "region": random.choice(["East US", "West US", "Central US", "North Europe"]),
                },
            }

            raw_log = RawLog(
                id=str(uuid.uuid4()),
                ingested_at=now - timedelta(minutes=random.randint(1, 60)),
                source_system="azure-monitor",
                raw_payload=payload,
                raw_text=sample.get("message", ""),
                is_segregated=False,
            )
            raw_logs.append(raw_log)

        session.add_all(raw_logs)
        await session.commit()

        print(f"✅ Seeded {count} raw Azure cloud logs into 'raw_logs' table")
        print(f"   → Run the pipeline to segregate them into 'cloud_logs'")
        print(f"   → Agent 1 will categorize by level, source, and category")


if __name__ == "__main__":
    asyncio.run(seed_raw_logs())
