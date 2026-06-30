"""
Azure Log Service — Pulls diagnostic logs from Azure Monitor REST API.
Falls back to Azure Blob Storage when Log Analytics has no data.
Collects from: Azure Front Door, Application Gateway, API Management, VM, and Blob Storage.
"""

import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Azure Blob Storage fallback for diagnostic logs
BLOB_STORAGE_URL = "https://aisaaclecsa8e5f0.blob.core.windows.net"
BLOB_CONTAINERS = [
    ("insights-logs-errors", "SQL-Errors"),
    ("insights-logs-timeouts", "SQL-Timeouts"),
    ("insights-logs-deadlocks", "SQL-Deadlocks"),
    ("insights-logs-appservicehttplogs", "AppService-HTTP"),
    ("insights-logs-appserviceconsolelogs", "AppService-Console"),
    ("insights-logs-frontdoorwebapplicationfirewalllog", "FrontDoor-WAF"),
    ("insights-logs-frontdooraccesslog", "FrontDoor-Access"),
]
BLOB_RESOURCE_PREFIX = "resourceId=/SUBSCRIPTIONS/893F4E0E-34C7-4841-A560-D04D90ED81D7/RESOURCEGROUPS"


class AzureLogService:
    """Pulls diagnostic logs from Azure Monitor using Log Analytics queries.
    Falls back to Azure Blob Storage when Log Analytics has no data for the requested date range."""

    def __init__(self):
        self._token: str | None = None
        self._token_expires: datetime | None = None
        self._storage_token: str | None = None
        self._storage_token_expires: datetime | None = None

    async def _get_token(self) -> str:
        """Get Azure AD bearer token for Log Analytics."""
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

    async def _get_storage_token(self) -> str:
        """Get Azure AD bearer token for Blob Storage."""
        if self._storage_token and self._storage_token_expires and datetime.now(timezone.utc) < self._storage_token_expires:
            return self._storage_token

        url = f"https://login.microsoftonline.com/{settings.azure_tenant_id}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.azure_client_id,
            "client_secret": settings.azure_client_secret,
            "scope": "https://storage.azure.com/.default",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=data)
            resp.raise_for_status()
            result = resp.json()
            self._storage_token = result["access_token"]
            self._storage_token_expires = datetime.now(timezone.utc) + timedelta(seconds=result.get("expires_in", 3500))
            return self._storage_token

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

    def _time_filter(self, hours_back: int, start_date: str = None, end_date: str = None) -> str:
        """Generate KQL time filter clause supporting both ago() and explicit datetime range."""
        if start_date and end_date:
            return f'| where TimeGenerated >= datetime("{start_date}") and TimeGenerated <= datetime("{end_date}")'
        return f'| where TimeGenerated > ago({hours_back}h)'

    # ─── Blob Storage Fallback Methods ───────────────────────────

    async def _list_blobs(self, token: str, container: str, prefix: str = "", max_results: int = 50) -> list[dict]:
        """List blobs in a container with optional prefix."""
        url = f"{BLOB_STORAGE_URL}/{container}?restype=container&comp=list&maxresults={max_results}"
        if prefix:
            url += f"&prefix={prefix}"
        headers = {"Authorization": f"Bearer {token}", "x-ms-version": "2021-08-06"}
        async with httpx.AsyncClient(timeout=30) as c:
            resp = await c.get(url, headers=headers)
            if resp.status_code != 200:
                return []
        root = ET.fromstring(resp.text)
        return [
            {
                "name": b.find("Name").text,
                "size": b.find("Properties/Content-Length").text
                if b.find("Properties/Content-Length") is not None else "0",
            }
            for b in root.findall(".//Blob")
        ]

    async def _download_blob(self, token: str, container: str, blob_name: str, max_bytes: int = 2_000_000) -> bytes | None:
        """Download a blob (up to max_bytes)."""
        url = f"{BLOB_STORAGE_URL}/{container}/{blob_name}"
        headers = {"Authorization": f"Bearer {token}", "x-ms-version": "2021-08-06"}
        if max_bytes:
            headers["Range"] = f"bytes=0-{max_bytes}"
        async with httpx.AsyncClient(timeout=120) as c:
            resp = await c.get(url, headers=headers)
            if resp.status_code in (200, 206):
                return resp.content
        return None

    def _parse_blob_records(self, raw_bytes: bytes) -> list[dict]:
        """Parse JSON records from Azure diagnostic blob."""
        text = raw_bytes.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
            return data.get("records", [data] if isinstance(data, dict) else data)
        except json.JSONDecodeError:
            # Try line-by-line JSON
            records = []
            for line in text.strip().split("\n"):
                line = line.strip().rstrip(",")
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
            return records

    def _record_matches_timerange(self, record: dict, start_dt: datetime, end_dt: datetime) -> bool:
        """Check if a record's timestamp falls within the requested range."""
        ts = record.get("time", "") or record.get("Time", "") or record.get("timeStamp", "")
        if not ts:
            return True  # Include records without timestamps
        try:
            # Parse ISO timestamp
            rec_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if rec_dt.tzinfo is None:
                rec_dt = rec_dt.replace(tzinfo=timezone.utc)
            return start_dt <= rec_dt <= end_dt
        except (ValueError, TypeError):
            return True

    async def collect_from_blob_storage(self, start_date: str, end_date: str) -> dict[str, list[dict[str, Any]]]:
        """Fallback: Pull diagnostic logs from Azure Blob Storage for the given date range.
        
        This is used when Log Analytics doesn't have data for the requested period 
        (e.g., older dates beyond Log Analytics retention).
        """
        logger.info(f"Log Collector: Falling back to Azure Blob Storage ({BLOB_STORAGE_URL})")
        logger.info(f"Log Collector: Blob Storage date range: {start_date} to {end_date}")

        try:
            token = await self._get_storage_token()
        except Exception as e:
            logger.error(f"Log Collector: Failed to get storage token: {e}")
            return {}

        # Parse the date range to determine which days to search
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            # Handle format like "2026-03-31T12:00" without timezone
            try:
                start_dt = datetime.strptime(start_date[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
                end_dt = datetime.strptime(end_date[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
            except Exception:
                start_dt = datetime.strptime(start_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                end_dt = datetime.strptime(end_date[:10], "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

        # Generate day prefixes for blob search
        days = []
        current = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        while current <= end_dt:
            days.append(current)
            current += timedelta(days=1)

        results = {}
        total_records = 0
        MAX_RECORDS_PER_CONTAINER = 500
        MAX_TOTAL_RECORDS = 2500

        for container, source_label in BLOB_CONTAINERS:
            # If we already have enough total records, stop early
            if total_records >= MAX_TOTAL_RECORDS:
                logger.info(f"Log Collector: Reached total cap ({MAX_TOTAL_RECORDS}), skipping {source_label}")
                break

            container_records = []

            for day in days:
                if len(container_records) >= MAX_RECORDS_PER_CONTAINER:
                    break

                # Build the blob prefix for this day
                # Format: resourceId=/.../y=2026/m=03/d=31
                prefix = f"{BLOB_RESOURCE_PREFIX}"

                # Try to find blobs for this day across resource group subdirectories
                day_prefix_patterns = [
                    f"y={day.year}/m={day.month:02d}/d={day.day:02d}",
                ]

                try:
                    # First, discover available resource group prefixes
                    top_blobs = await self._list_blobs(token, container, prefix="resourceId=", max_results=5)
                    if not top_blobs:
                        # Try without prefix
                        top_blobs = await self._list_blobs(token, container, max_results=5)

                    if top_blobs:
                        # Extract the resource group path from the first blob
                        first_blob = top_blobs[0]["name"]
                        # Find the y= part and replace with our date
                        y_idx = first_blob.find("/y=")
                        if y_idx >= 0:
                            base_path = first_blob[:y_idx]
                            day_prefix = f"{base_path}/y={day.year}/m={day.month:02d}/d={day.day:02d}"
                            day_blobs = await self._list_blobs(token, container, prefix=day_prefix, max_results=50)

                            for blob_info in day_blobs:
                                if len(container_records) >= MAX_RECORDS_PER_CONTAINER:
                                    break

                                blob_name = blob_info["name"]
                                blob_size = int(blob_info.get("size", "0"))

                                # Skip very large blobs (>5MB) — download first 2MB only
                                max_bytes = min(blob_size, 2_000_000) if blob_size > 0 else 2_000_000

                                try:
                                    raw = await self._download_blob(token, container, blob_name, max_bytes)
                                    if raw:
                                        records = self._parse_blob_records(raw)
                                        # Filter records by timestamp
                                        for rec in records:
                                            if len(container_records) >= MAX_RECORDS_PER_CONTAINER:
                                                break
                                            if self._record_matches_timerange(rec, start_dt, end_dt):
                                                # For high-volume containers (AppService), only keep errors/warnings
                                                if source_label in ("AppService-Console", "AppService-HTTP"):
                                                    level = (rec.get("level") or rec.get("Level") or "").upper()
                                                    result_desc = str(rec.get("resultDescription", "")).lower()
                                                    # Parse properties if it's a JSON string
                                                    props = rec.get("properties", {})
                                                    if isinstance(props, str):
                                                        try:
                                                            import json as _j
                                                            props = _j.loads(props)
                                                        except Exception:
                                                            props = {}
                                                    # Check HTTP status code from properties
                                                    sc_status = str(props.get("ScStatus", props.get("httpStatusCode", "200")))
                                                    is_http_error = sc_status.startswith("4") or sc_status.startswith("5")
                                                    # Check for error keywords in message/description
                                                    has_error = any(k in result_desc for k in ["error", "fail", "exception", "timeout", "500", "502", "503", "504"])
                                                    if level not in ("ERROR", "WARNING", "CRITICAL") and not has_error and not is_http_error:
                                                        continue
                                                container_records.append(rec)
                                except Exception as e:
                                    logger.debug(f"Blob download error ({blob_name}): {e}")
                                    continue
                except Exception as e:
                    logger.debug(f"Blob listing error ({container}/{day}): {e}")
                    continue

            if container_records:
                # Normalize blob records to pipeline format
                normalized = self._normalize_blob_records(container_records, source_label, container)
                source_key = f"blob-{source_label.lower().replace(' ', '-')}"
                results[source_key] = normalized
                total_records += len(normalized)
                logger.info(f"Log Collector: Blob Storage [{source_label}]: {len(normalized)} records")

        if total_records > 0:
            logger.info(
                f"Log Collector: Blob Storage collected {total_records} logs from {len(results)} containers — "
                + ", ".join(f"{k}: {len(v)}" for k, v in results.items())
            )
        else:
            logger.info("Log Collector: No logs found in Blob Storage for this date range")

        return results

    def _normalize_blob_records(
        self, records: list[dict], source_label: str, container: str
    ) -> list[dict[str, Any]]:
        """Normalize Azure Blob Storage diagnostic records into pipeline format."""
        normalized = []
        for rec in records:
            ts = rec.get("time", "") or rec.get("Time", "") or datetime.now(timezone.utc).isoformat()
            category = rec.get("category", "") or rec.get("Category", "") or source_label
            op_name = rec.get("operationName", "") or rec.get("OperationName", "")
            result_desc = rec.get("resultDescription", "") or rec.get("ResultDescription", "")

            # Extract properties
            props = rec.get("properties", {})
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except Exception:
                    props = {}

            # Build message
            message_parts = []
            if category:
                message_parts.append(f"Category: {category}")
            if op_name:
                message_parts.append(f"Operation: {op_name}")

            # HTTP status from properties
            sc = props.get("ScStatus", props.get("httpStatusCode", ""))
            if sc:
                message_parts.append(f"HTTP {sc}")
            method = props.get("CsMethod", "")
            if method:
                message_parts.append(f"Method: {method}")
            uri = props.get("CsUriStem", "")
            if uri:
                message_parts.append(f"URI: {uri}")
            host = props.get("CsHost", props.get("hostName", ""))
            if host:
                message_parts.append(f"Host: {host}")
            if result_desc:
                message_parts.append(str(result_desc)[:500])

            # SQL error message
            msg = rec.get("message", "") or props.get("message", "") or rec.get("error_message_s", "")
            if msg:
                message_parts.append(str(msg)[:500])

            message = " | ".join(message_parts) if message_parts else json.dumps(rec, default=str)[:2000]

            # Determine level
            level = "INFO"
            level_val = rec.get("level", "") or rec.get("Level", "")
            if level_val and str(level_val).upper() in ("ERROR", "CRITICAL", "FATAL"):
                level = "ERROR"
            elif sc and int(str(sc)) >= 500:
                level = "ERROR"
            elif sc and int(str(sc)) >= 400:
                level = "WARNING"
            elif "error" in container.lower() or "deadlock" in container.lower():
                level = "ERROR"
            elif "timeout" in container.lower():
                level = "WARNING"

            normalized.append({
                "timestamp": ts,
                "level": level,
                "source": f"Azure Blob Storage ({source_label})",
                "source_system": f"blob-{container}",
                "category": category,
                "message": message[:5000],
                "resource_id": rec.get("resourceId", ""),
                "operation_name": op_name,
                "raw_payload": rec,
            })
        return normalized

    # ─── Log Analytics Query Methods ─────────────────────────────

    async def collect_frontdoor_logs(self, hours_back: int = 6, start_date: str = None, end_date: str = None) -> list[dict[str, Any]]:
        """Pull Azure Front Door ERROR logs only: 4xx/5xx, WAF blocks, DELETE ops, high latency."""
        tf = self._time_filter(hours_back, start_date, end_date)
        kql = f"""AzureDiagnostics
{tf}
| where ResourceProvider == "MICROSOFT.CDN" or ResourceProvider == "MICROSOFT.NETWORK"
| where Category in ("FrontDoorAccessLog", "FrontDoorWebApplicationFirewallLog")
| extend wafAction = column_ifexists("action_s", "")
| extend timeTakenSec = todouble(column_ifexists("timeTaken_s", "0"))
| extend statusCode = toint(column_ifexists("httpStatusCode_d", 0))
| extend httpMethod = column_ifexists("httpMethod_s", "")
| extend requestUri = column_ifexists("requestUri_s", "")
| extend errorInfo = column_ifexists("errorInfo_s", "")
| where wafAction in ("Block", "Redirect")
    or statusCode >= 400
    or timeTakenSec > 10.0
    or httpMethod == "DELETE"
| extend Level = case(
    wafAction == "Block", "Error",
    statusCode >= 500, "Error",
    httpMethod == "DELETE", "Error",
    statusCode >= 400, "Warning",
    timeTakenSec > 10.0, "Error",
    "Information")
| order by TimeGenerated desc"""
        try:
            rows = await self._query_log_analytics(kql)
            logger.info(f"Log Collector: Collected {len(rows)} Front Door logs")
            return self._normalize_rows(rows, "azure-front-door", "Azure Front Door")
        except Exception as e:
            logger.warning(f"Front Door log collection skipped: {e}")
            return []

    async def collect_appgateway_logs(self, hours_back: int = 6, start_date: str = None, end_date: str = None) -> list[dict[str, Any]]:
        """Pull Application Gateway logs: access, performance, firewall, health probes."""
        tf = self._time_filter(hours_back, start_date, end_date)
        kql = f"""AzureDiagnostics
{tf}
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
| order by TimeGenerated desc"""
        try:
            rows = await self._query_log_analytics(kql)
            logger.info(f"Log Collector: Collected {len(rows)} App Gateway logs")
            return self._normalize_rows(rows, "azure-app-gateway", "Azure Application Gateway")
        except Exception as e:
            logger.error(f"App Gateway log collection failed: {e}")
            return []

    async def collect_apim_logs(self, hours_back: int = 6, start_date: str = None, end_date: str = None) -> list[dict[str, Any]]:
        """Pull API Management logs: gateway, backend responses, policy failures."""
        tf = self._time_filter(hours_back, start_date, end_date)
        # ApiManagementGatewayLogs dedicated table (Consumption tier)
        kql_dedicated = f"""ApiManagementGatewayLogs
{tf}
| extend Level = iff(ResponseCode >= 500, "Error", iff(ResponseCode >= 400, "Warning", "Information"))
| order by TimeGenerated desc"""
        # Fallback: AzureDiagnostics
        kql_diag = f"""AzureDiagnostics
{tf}
| where ResourceProvider == "MICROSOFT.APIMANAGEMENT"
| where Category in ("GatewayLogs")
| extend Level = column_ifexists("Level", "Information")
| order by TimeGenerated desc"""
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

    async def collect_vm_logs(self, hours_back: int = 6, start_date: str = None, end_date: str = None) -> list[dict[str, Any]]:
        """Pull VM logs: syslog, heartbeat, performance counters."""
        tf = self._time_filter(hours_back, start_date, end_date)
        kql = f"""
let syslog = Syslog
{tf}
| project TimeGenerated, SeverityLevel, Facility, SyslogMessage, Computer, HostIP;
let perf = Perf
{tf}
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
"""
        try:
            rows = await self._query_log_analytics(kql)
            logger.info(f"Log Collector: Collected {len(rows)} VM logs")
            return self._normalize_rows(rows, "azure-vm", "Azure Virtual Machine")
        except Exception as e:
            logger.error(f"VM log collection failed: {e}")
            return []

    async def collect_all(self, hours_back: int = 1, start_date: str = None, end_date: str = None) -> dict[str, list[dict[str, Any]]]:
        """Collect logs from all Azure sources.
        
        Strategy (explicit routing based on date):
        - Before March 31, 2026: Use Azure Blob Storage ONLY (historical data)
        - After March 31, 2026:  Use Azure Log Analytics ONLY (real-time data)
        
        Args:
            hours_back: Fallback hours to look back if no dates provided
            start_date: ISO date string for custom range start
            end_date: ISO date string for custom range end
        """
        results = {}
        CUTOFF_DATE = datetime(2026, 3, 31, tzinfo=timezone.utc)

        # Determine which source to use based on date range
        use_blob = False
        use_log_analytics = False

        if start_date and end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                try:
                    end_dt = datetime.strptime(end_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                except Exception:
                    end_dt = datetime.now(timezone.utc)

            if end_dt < CUTOFF_DATE:
                use_blob = True
                logger.info(f"Log Collector: Date range ends before March 31, 2026 → using Blob Storage ONLY")
            else:
                use_log_analytics = True
                logger.info(f"Log Collector: Date range is after March 31, 2026 → using Log Analytics ONLY")
        else:
            # No date range specified → use Log Analytics for recent data
            use_log_analytics = True
            logger.info(f"Log Collector: No date range → using Log Analytics for last {hours_back}h")

        # ─── Route 1: Blob Storage (historical, before March 31 2026) ───
        if use_blob:
            logger.info(f"Log Collector: Pulling from Azure Blob Storage: {start_date} to {end_date}")
            try:
                blob_results = await self.collect_from_blob_storage(start_date, end_date)
                results.update(blob_results)
            except Exception as e:
                logger.error(f"Log Collector: Blob Storage failed: {e}")

        # ─── Route 2: Log Analytics (real-time, after March 31 2026) ───
        if use_log_analytics:
            if not settings.azure_log_analytics_workspace_id:
                logger.warning("Log Collector: AZURE_LOG_ANALYTICS_WORKSPACE_ID not set — skipping Log Analytics")
            else:
                import asyncio as _aio

                if start_date and end_date:
                    logger.info(f"Log Collector: Using Log Analytics date range: {start_date} to {end_date}")
                else:
                    logger.info(f"Log Collector: Querying Log Analytics for last {hours_back}h of logs")

                # Run all 4 Log Analytics queries CONCURRENTLY for speed
                fd_task = self.collect_frontdoor_logs(hours_back, start_date, end_date)
                ag_task = self.collect_appgateway_logs(hours_back, start_date, end_date)
                ap_task = self.collect_apim_logs(hours_back, start_date, end_date)
                vm_task = self.collect_vm_logs(hours_back, start_date, end_date)

                fd_logs, ag_logs, ap_logs, vm_logs = await _aio.gather(
                    fd_task, ag_task, ap_task, vm_task,
                    return_exceptions=True,
                )

                if isinstance(fd_logs, list) and fd_logs:
                    results["azure-front-door"] = fd_logs
                if isinstance(ag_logs, list) and ag_logs:
                    results["azure-app-gateway"] = ag_logs
                if isinstance(ap_logs, list) and ap_logs:
                    results["azure-apim"] = ap_logs
                if isinstance(vm_logs, list) and vm_logs:
                    results["azure-vm"] = vm_logs

        total = sum(len(v) for v in results.values())

        if total > 0:
            logger.info(
                f"Log Collector: Collected {total} Azure logs from {len(results)} sources — "
                + ", ".join(f"{k}: {len(v)}" for k, v in results.items())
            )
        else:
            logger.info("Log Collector: No logs found in Log Analytics or Blob Storage for this range")

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
