"""
Azure Log Service — Pulls diagnostic logs from Azure Monitor REST API.
Collects from: Azure Front Door, Application Gateway, API Management, VM.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AzureLogService:
    """Pulls diagnostic logs from Azure Monitor using Log Analytics queries."""

    def __init__(self):
        self._token: str | None = None
        self._token_expires: datetime | None = None

    async def _get_token(self) -> str:
        """Get Azure AD bearer token using client credentials."""
        if self._token and self._token_expires and datetime.now(timezone.utc) < self._token_expires:
            return self._token

        url = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.azure_client_id,
            "client_secret": settings.azure_client_secret,
            "scope": "https://api.loganalytics.io/.default",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            result = resp.json()
            self._token = result["access_token"]
            self._token_expires = datetime.now(timezone.utc) + timedelta(seconds=result.get("expires_in", 3500))
            return self._token

    async def _query_log_analytics(self, kql: str) -> list[dict[str, Any]]:
        """Execute a KQL query against the Log Analytics workspace."""
        workspace_id = settings.azure_log_analytics_workspace_id
        if not workspace_id:
            logger.warning("AZURE_LOG_ANALYTICS_WORKSPACE_ID not configured, skipping query")
            return []

        token = await self._get_token()
        url = f"https://api.loganalytics.io/v1/workspaces/{workspace_id}/query"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json={"query": kql}, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # Parse the tabular response into list of dicts
        rows = []
        for table in data.get("tables", []):
            columns = [col["name"] for col in table.get("columns", [])]
            for row in table.get("rows", []):
                rows.append(dict(zip(columns, row)))

        return rows

    async def collect_frontdoor_logs(self, hours_back: int = 6) -> list[dict[str, Any]]:
        """Pull Azure Front Door logs: requests, WAF events, routing, latency, 4xx/5xx."""
        kql = f"""
AzureDiagnostics
| where TimeGenerated > ago({hours_back}h)
| where ResourceProvider == "MICROSOFT.CDN" or ResourceProvider == "MICROSOFT.NETWORK"
| where Category in ("FrontDoorAccessLog", "FrontDoorHealthProbeLog", "FrontDoorWebApplicationFirewallLog")
| project TimeGenerated, Level, Category, OperationName, ResourceId,
          httpStatusCode_d, requestUri_s, clientIp_s, timeTaken_d,
          action_s, ruleName_s, host_s, errorInfo_s, ResultDescription
| order by TimeGenerated desc
| limit 500
"""
        try:
            rows = await self._query_log_analytics(kql)
            logger.info(f"Log Collector: Collected {len(rows)} Front Door logs")
            return self._normalize_rows(rows, "azure-front-door", "Azure Front Door")
        except Exception as e:
            logger.error(f"Front Door log collection failed: {e}")
            return []

    async def collect_appgateway_logs(self, hours_back: int = 6) -> list[dict[str, Any]]:
        """Pull Application Gateway logs: access, performance, firewall, health probes."""
        kql = f"""
AzureDiagnostics
| where TimeGenerated > ago({hours_back}h)
| where ResourceProvider == "MICROSOFT.NETWORK"
| where Category in ("ApplicationGatewayAccessLog", "ApplicationGatewayPerformanceLog",
                      "ApplicationGatewayFirewallLog")
| project TimeGenerated, Level, Category, OperationName, ResourceId,
          httpStatus_d, serverStatus_d, timeTaken_d, host_s, requestUri_s,
          clientIP_s, serverRouted_s, instanceId_s, ResultDescription
| order by TimeGenerated desc
| limit 500
"""
        try:
            rows = await self._query_log_analytics(kql)
            logger.info(f"Log Collector: Collected {len(rows)} App Gateway logs")
            return self._normalize_rows(rows, "azure-app-gateway", "Azure Application Gateway")
        except Exception as e:
            logger.error(f"App Gateway log collection failed: {e}")
            return []

    async def collect_apim_logs(self, hours_back: int = 6) -> list[dict[str, Any]]:
        """Pull API Management logs: gateway, backend responses, policy failures."""
        kql = f"""
AzureDiagnostics
| where TimeGenerated > ago({hours_back}h)
| where ResourceProvider == "MICROSOFT.APIMANAGEMENT"
| where Category in ("GatewayLogs")
| project TimeGenerated, Level, Category, OperationName, ResourceId,
          responseCode_d, method_s, url_s, cache_s, apiId_s,
          backendResponseCode_d, backendTime_d, clientTime_d, ResultDescription
| order by TimeGenerated desc
| limit 500
"""
        try:
            rows = await self._query_log_analytics(kql)
            logger.info(f"Log Collector: Collected {len(rows)} APIM logs")
            return self._normalize_rows(rows, "azure-apim", "Azure API Management")
        except Exception as e:
            logger.error(f"APIM log collection failed: {e}")
            return []

    async def collect_vm_logs(self, hours_back: int = 6) -> list[dict[str, Any]]:
        """Pull VM logs: syslog, heartbeat, performance counters."""
        kql = f"""
let syslog = Syslog
| where TimeGenerated > ago({hours_back}h)
| project TimeGenerated, SeverityLevel, Facility, SyslogMessage, Computer, HostIP;
let perf = Perf
| where TimeGenerated > ago({hours_back}h)
| where CounterName in ("% Processor Time", "Available MBytes", "Disk Reads/sec")
| where CounterValue > 90 or CounterName == "Available MBytes" and CounterValue < 500
| project TimeGenerated, CounterName, CounterValue, Computer, InstanceName;
syslog
| extend Level = SeverityLevel, Message = SyslogMessage, Source = "VM-Syslog"
| project TimeGenerated, Level, Message, Source, Computer
| union (
    perf
    | extend Level = "WARNING", Message = strcat(CounterName, " = ", CounterValue), Source = "VM-Perf"
    | project TimeGenerated, Level, Message, Source, Computer
)
| order by TimeGenerated desc
| limit 200
"""
        try:
            rows = await self._query_log_analytics(kql)
            logger.info(f"Log Collector: Collected {len(rows)} VM logs")
            return self._normalize_rows(rows, "azure-vm", "Azure Virtual Machine")
        except Exception as e:
            logger.error(f"VM log collection failed: {e}")
            return []

    async def collect_all(self, hours_back: int = 6) -> dict[str, list[dict[str, Any]]]:
        """Collect logs from all configured Azure sources."""
        results = {}
        sources = settings.azure_log_source_ids

        if "azure-front-door" in sources:
            results["azure-front-door"] = await self.collect_frontdoor_logs(hours_back)
        if "azure-app-gateway" in sources:
            results["azure-app-gateway"] = await self.collect_appgateway_logs(hours_back)
        if "azure-apim" in sources:
            results["azure-apim"] = await self.collect_apim_logs(hours_back)
        if "azure-vm" in sources:
            results["azure-vm"] = await self.collect_vm_logs(hours_back)

        total = sum(len(v) for v in results.values())
        logger.info(f"Log Collector: Total collected = {total} logs from {len(results)} sources")
        return results

    def _normalize_rows(
        self, rows: list[dict], source_system: str, source_name: str
    ) -> list[dict[str, Any]]:
        """Normalize Azure Monitor rows into a common format."""
        normalized = []
        for row in rows:
            # Build message from available fields
            message_parts = []
            for key in ("ResultDescription", "Message", "SyslogMessage", "errorInfo_s", "requestUri_s", "url_s"):
                if row.get(key):
                    message_parts.append(str(row[key]))
            message = " | ".join(message_parts) if message_parts else str(row)

            # Detect level
            level = row.get("Level") or row.get("SeverityLevel") or "INFO"
            level = self._map_level(level, row)

            normalized.append({
                "timestamp": row.get("TimeGenerated", datetime.now(timezone.utc).isoformat()),
                "level": level,
                "source": source_name,
                "source_system": source_system,
                "category": row.get("Category", ""),
                "message": message[:5000],
                "resource_id": row.get("ResourceId", ""),
                "operation_name": row.get("OperationName", ""),
                "raw_payload": row,
            })
        return normalized

    def _map_level(self, level: str, row: dict) -> str:
        """Map Azure log levels to standard CRITICAL/ERROR/WARNING/INFO."""
        level_upper = str(level).upper()

        # Check HTTP status codes for severity
        for key in ("httpStatusCode_d", "httpStatus_d", "responseCode_d", "backendResponseCode_d", "serverStatus_d"):
            code = row.get(key)
            if code and isinstance(code, (int, float)):
                code = int(code)
                if code >= 500:
                    return "ERROR"
                if code >= 400:
                    return "WARNING"

        mapping = {
            "CRITICAL": "CRITICAL", "FATAL": "CRITICAL", "EMERG": "CRITICAL",
            "ERROR": "ERROR", "ERR": "ERROR", "ALERT": "ERROR",
            "WARNING": "WARNING", "WARN": "WARNING",
            "INFORMATIONAL": "INFO", "INFO": "INFO", "NOTICE": "INFO",
            "DEBUG": "INFO", "VERBOSE": "INFO",
        }
        return mapping.get(level_upper, "INFO")


# Singleton
azure_log_service = AzureLogService()
