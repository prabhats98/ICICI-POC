"""
Azure Log Service — Pulls diagnostic logs from Azure Monitor REST API.
Collects from: Azure Front Door, Application Gateway, API Management, VM.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_time_filter(
    hours_back: int = 6,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> str:
    """Build a KQL time filter clause.

    If explicit start/end datetimes are provided, use them.
    Otherwise fall back to `ago(Xh)`.
    """
    if start_time and end_time:
        s = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        e = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        return f"| where TimeGenerated >= datetime('{s}') and TimeGenerated <= datetime('{e}')"
    return f"| where TimeGenerated > ago({hours_back}h)"


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

    async def collect_frontdoor_logs(
        self,
        hours_back: int = 6,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Pull Azure Front Door logs: requests, WAF events, routing, latency, 4xx/5xx."""
        time_filter = _build_time_filter(hours_back, start_time, end_time)
        kql = f"""AzureDiagnostics
{time_filter}
| where ResourceProvider == "MICROSOFT.CDN" or ResourceProvider == "MICROSOFT.NETWORK"
| where Category in ("FrontDoorAccessLog", "FrontDoorHealthProbeLog", "FrontDoorWebApplicationFirewallLog")
| extend Level = column_ifexists("Level", "Information")
| order by TimeGenerated desc
| limit 500"""
        try:
            rows = await self._query_log_analytics(kql)
            logger.info(f"Log Collector: Collected {len(rows)} Front Door logs")
            return self._normalize_rows(rows, "azure-front-door", "Azure Front Door")
        except Exception as e:
            logger.warning(f"Front Door log collection skipped: {e}")
            return []

    async def collect_appgateway_logs(
        self,
        hours_back: int = 6,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Pull Application Gateway logs: access, performance, firewall, health probes."""
        time_filter = _build_time_filter(hours_back, start_time, end_time)
        kql = f"""AzureDiagnostics
{time_filter}
| where ResourceProvider == "MICROSOFT.NETWORK"
| where Category in ("ApplicationGatewayAccessLog", "ApplicationGatewayPerformanceLog", "ApplicationGatewayFirewallLog")
| extend httpStat = column_ifexists("httpStatus_d", 0.0)
| extend srvStat  = column_ifexists("serverStatus_d", 0.0)
| extend StatusCode = toint(iff(httpStat > 0, httpStat, srvStat))
| extend Level = iff(StatusCode >= 500, "Error", iff(StatusCode >= 400, "Warning", "Information"))
| extend host_s       = column_ifexists("host_s", "")
| extend requestUri_s = column_ifexists("requestUri_s", "")
| extend clientIP_s   = column_ifexists("clientIP_s", "")
| extend timeTaken_d  = column_ifexists("timeTaken_d", 0.0)
| extend instanceId_s = column_ifexists("instanceId_s", "")
| project TimeGenerated, Level, Category, OperationName, ResourceId,
          httpStatus_d = httpStat, serverStatus_d = srvStat, timeTaken_d,
          host_s, requestUri_s, clientIP_s, instanceId_s,
          ResultDescription = tostring(StatusCode)
| order by TimeGenerated desc
| limit 500"""
        try:
            rows = await self._query_log_analytics(kql)
            logger.info(f"Log Collector: Collected {len(rows)} App Gateway logs")
            return self._normalize_rows(rows, "azure-app-gateway", "Azure Application Gateway")
        except Exception as e:
            logger.error(f"App Gateway log collection failed: {e}")
            return []

    async def collect_apim_logs(
        self,
        hours_back: int = 6,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Pull API Management logs: gateway, backend responses, policy failures."""
        time_filter = _build_time_filter(hours_back, start_time, end_time)
        # ApiManagementGatewayLogs dedicated table (Consumption tier)
        kql_dedicated = f"""ApiManagementGatewayLogs
{time_filter}
| extend Level = iff(ResponseCode >= 500, "Error", iff(ResponseCode >= 400, "Warning", "Information"))
| order by TimeGenerated desc
| limit 500"""
        # Fallback: AzureDiagnostics
        kql_diag = f"""AzureDiagnostics
{time_filter}
| where ResourceProvider == "MICROSOFT.APIMANAGEMENT"
| where Category in ("GatewayLogs")
| extend Level = column_ifexists("Level", "Information")
| order by TimeGenerated desc
| limit 500"""
        try:
            rows = []
            try:
                rows = await self._query_log_analytics(kql_dedicated)
            except Exception:
                pass
            if not rows:
                rows = await self._query_log_analytics(kql_diag)
            logger.info(f"Log Collector: Collected {len(rows)} APIM logs")
            return self._normalize_rows(rows, "azure-apim", "Azure API Management")
        except Exception as e:
            logger.warning(f"APIM log collection skipped: {e}")
            return []

    async def collect_vm_logs(
        self,
        hours_back: int = 6,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        """Pull VM logs: syslog, heartbeat, performance counters."""
        time_filter = _build_time_filter(hours_back, start_time, end_time)
        kql = f"""
let syslog = Syslog
{time_filter}
| project TimeGenerated, SeverityLevel, Facility, SyslogMessage, Computer, HostIP;
let perf = Perf
{time_filter}
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

    async def collect_all(
        self,
        hours_back: int = 1,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Collect logs from all Azure sources via Log Analytics KQL.
        
        Always runs all queries regardless of whether resource IDs are set —
        the workspace ID alone is sufficient for KQL. Returns real logs only.

        If start_time and end_time are provided, queries use an explicit
        datetime window instead of ago(Xh).
        """
        results = {}

        if not settings.azure_log_analytics_workspace_id:
            logger.warning("Log Collector: AZURE_LOG_ANALYTICS_WORKSPACE_ID not set — skipping collection")
            return results

        # Log the time window being queried
        if start_time and end_time:
            logger.info(
                f"Log Collector: Querying Log Analytics for time range "
                f"{start_time.isoformat()} to {end_time.isoformat()} (GMT)"
            )
        else:
            logger.info(f"Log Collector: Querying Log Analytics for last {hours_back}h of logs")

        kwargs = {"hours_back": hours_back, "start_time": start_time, "end_time": end_time}

        frontdoor_logs = await self.collect_frontdoor_logs(**kwargs)
        if frontdoor_logs:
            results["azure-front-door"] = frontdoor_logs

        appgw_logs = await self.collect_appgateway_logs(**kwargs)
        if appgw_logs:
            results["azure-app-gateway"] = appgw_logs

        apim_logs = await self.collect_apim_logs(**kwargs)
        if apim_logs:
            results["azure-apim"] = apim_logs

        vm_logs = await self.collect_vm_logs(**kwargs)
        if vm_logs:
            results["azure-vm"] = vm_logs

        total = sum(len(v) for v in results.values())
        if total > 0:
            logger.info(
                f"Log Collector: Collected {total} real Azure logs from {len(results)} sources — "
                + ", ".join(f"{k}: {len(v)}" for k, v in results.items())
            )
        else:
            logger.info("Log Collector: No real logs found in Log Analytics yet — waiting for traffic")

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
