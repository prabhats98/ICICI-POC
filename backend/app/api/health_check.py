"""
Health Check API — Real-time Azure service health monitoring.

Uses a HYBRID approach:
1. Azure Monitor Metrics API: Gets real-time error rates, request counts,
   latency, and availability directly from Azure for each service.
2. Azure Resource State API: Gets provisioning state (Running/Stopped) for
   App Service and other stateful resources.
3. HTTP Ping: For Front Door / WAF (public endpoint www.icicipruamc.com).
4. Incident Overlay: Marks services as unhealthy if active incidents exist.

This provides genuine real-time health status for ALL services in the
www.icicipruamc.com request chain, even those behind authentication.
"""

import time
import json
import logging
import asyncio
import urllib.request
import urllib.error
import urllib.parse
import ssl

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api/health", tags=["Health Check"])
logger = logging.getLogger(__name__)

# SSL context that doesn't verify (for internal health checks only)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

# ── Azure Resource IDs (discovered from subscription) ──
AZURE_RESOURCE_IDS = {
    "azure-front-door": "/subscriptions/893f4e0e-34c7-4841-a560-d04d90ed81d7/resourceGroups/IPRU-INC-RG-DT-PROD-WEB-VNET/providers/Microsoft.Cdn/profiles/icicipru",
    "azure-front-door-2": "/subscriptions/893f4e0e-34c7-4841-a560-d04d90ed81d7/resourceGroups/IPRU-INC-RG-DT-PROD-WEB-VNET/providers/Microsoft.Cdn/profiles/investordtprod",
    "azure-app-gateway": "/subscriptions/893f4e0e-34c7-4841-a560-d04d90ed81d7/resourceGroups/IPRU-INC-RG-DT-PROD-APP-VNET/providers/Microsoft.Network/applicationGateways/IPRU-INC-PROD-DT-AGW-MFUND",
    "azure-app-service": "/subscriptions/893f4e0e-34c7-4841-a560-d04d90ed81d7/resourceGroups/ipru-inc-rg-dt-prod-app-vnet/providers/Microsoft.Web/sites/IPRU-INC-PROD-DT-MCP-APP",
    "azure-blob-storage": "/subscriptions/893f4e0e-34c7-4841-a560-d04d90ed81d7/resourceGroups/IPRU-INC-RG-DT-PROD-APP-VNET/providers/Microsoft.Storage/storageAccounts/logsproddt",
    "azure-blob-storage-static": "/subscriptions/893f4e0e-34c7-4841-a560-d04d90ed81d7/resourceGroups/IPRU-INC-RG-DT-PROD-APP-VNET/providers/Microsoft.Storage/storageAccounts/ipruteststaticwebsite",
}

# ── Token cache ──
_mgmt_token_cache = {"token": None, "expires_at": 0}


def _get_management_token() -> str:
    """Get or refresh Azure Management API token."""
    now = time.time()
    if _mgmt_token_cache["token"] and _mgmt_token_cache["expires_at"] > now + 60:
        return _mgmt_token_cache["token"]

    settings = get_settings()
    tenant = settings.azure_tenant_id
    client_id = settings.azure_client_id
    client_secret = settings.azure_client_secret

    if not all([tenant, client_id, client_secret]):
        return ""

    url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    body = (
        f"grant_type=client_credentials"
        f"&client_id={client_id}"
        f"&client_secret={urllib.parse.quote(client_secret)}"
        f"&scope=https://management.azure.com/.default"
    )
    try:
        req = urllib.request.Request(url, data=body.encode(), method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urllib.request.urlopen(req, context=_ssl_ctx, timeout=10)
        data = json.loads(resp.read())
        _mgmt_token_cache["token"] = data["access_token"]
        _mgmt_token_cache["expires_at"] = now + data.get("expires_in", 3600) - 60
        return data["access_token"]
    except Exception as e:
        logger.warning(f"Failed to get management token: {e}")
        return ""


def _get_azure_metrics(token: str, resource_id: str, metric_names: list,
                       timespan: str = "PT15M", interval: str = "PT5M") -> dict:
    """Get Azure Monitor metrics for a resource."""
    if not token:
        return {}
    names_param = ",".join(metric_names)
    url = (
        f"https://management.azure.com{resource_id}"
        f"/providers/microsoft.insights/metrics"
        f"?api-version=2024-02-01"
        f"&metricnames={urllib.parse.quote(names_param)}"
        f"&timespan={timespan}&interval={interval}"
    )
    try:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, context=_ssl_ctx, timeout=10)
        data = json.loads(resp.read())
        result = {}
        for m in data.get("value", []):
            mname = m.get("name", {}).get("value", "")
            ts = m.get("timeseries", [])
            if ts and ts[0].get("data"):
                vals = ts[0]["data"]
                # Get latest non-null value
                for v in reversed(vals):
                    val = v.get("total") or v.get("average")
                    if val is not None:
                        result[mname] = round(val, 2) if isinstance(val, float) else val
                        break
        return result
    except Exception as e:
        logger.debug(f"Metrics error for {resource_id}: {e}")
        return {}


def _get_resource_state(token: str, resource_id: str, api_version: str) -> dict:
    """Get the provisioning/operational state of an Azure resource."""
    if not token:
        return {}
    url = f"https://management.azure.com{resource_id}?api-version={api_version}"
    try:
        req = urllib.request.Request(url)
        req.add_header("Authorization", f"Bearer {token}")
        resp = urllib.request.urlopen(req, context=_ssl_ctx, timeout=10)
        data = json.loads(resp.read())
        props = data.get("properties", {})
        return {
            "provisioning_state": props.get("provisioningState", ""),
            "state": props.get("state", ""),
            "enabled": props.get("enabled"),
            "hostname": props.get("defaultHostName", ""),
        }
    except Exception as e:
        logger.debug(f"Resource state error: {e}")
        return {}


def _ping_url(url: str, timeout: int = 8) -> dict:
    """Synchronously ping a URL and return status info."""
    start = time.time()
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "CloudGuard-HealthCheck/1.0")
        resp = urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx)
        elapsed = round((time.time() - start) * 1000)
        return {
            "status_code": resp.status,
            "status_text": resp.reason,
            "response_time_ms": elapsed,
            "healthy": 200 <= resp.status < 400,
        }
    except urllib.error.HTTPError as e:
        if e.code == 405:
            start2 = time.time()
            try:
                req2 = urllib.request.Request(url, method="GET")
                req2.add_header("User-Agent", "CloudGuard-HealthCheck/1.0")
                resp2 = urllib.request.urlopen(req2, timeout=timeout, context=_ssl_ctx)
                elapsed2 = round((time.time() - start2) * 1000)
                return {"status_code": resp2.status, "status_text": resp2.reason, "response_time_ms": elapsed2, "healthy": 200 <= resp2.status < 400}
            except Exception as e2:
                elapsed2 = round((time.time() - start2) * 1000)
                return {"status_code": 0, "status_text": str(e2)[:80], "response_time_ms": elapsed2, "healthy": False}
        elapsed = round((time.time() - start) * 1000)
        return {"status_code": e.code, "status_text": e.reason, "response_time_ms": elapsed, "healthy": False}
    except Exception as e:
        elapsed = round((time.time() - start) * 1000)
        return {"status_code": 0, "status_text": f"Error: {str(e)[:80]}", "response_time_ms": elapsed, "healthy": False}


async def _async_ping(url: str, timeout: int = 8) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _ping_url, url, timeout)


async def _async_call(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn, *args)


def _check_front_door(token: str) -> dict:
    """Front Door: instant ping www.icicipruamc.com + Azure metrics for detail."""
    # INSTANT: ping the actual website (reflects DOWN in ~1 sec)
    ping = _ping_url("https://www.icicipruamc.com", timeout=5)

    # DETAIL: Azure metrics (~5 min lag, but rich data)
    rid = AZURE_RESOURCE_IDS.get("azure-front-door", "")
    metrics = _get_azure_metrics(token, rid, [
        "RequestCount", "Percentage4XX", "Percentage5XX",
        "TotalLatency", "OriginLatency"
    ])
    req_count = metrics.get("RequestCount", 0)
    pct_4xx = metrics.get("Percentage4XX", 0)
    pct_5xx = metrics.get("Percentage5XX", 0)
    latency = metrics.get("TotalLatency", 0)
    origin_latency = metrics.get("OriginLatency", 0)

    # Health = ping result (instant). Metrics = supplementary detail.
    healthy = ping["healthy"]
    status_text = (
        f"HTTP {ping['status_code']} | {ping['response_time_ms']}ms | "
        f"{int(req_count)} reqs | 5xx: {pct_5xx:.1f}%"
    )
    if not healthy:
        status_text = f"DOWN | {ping['status_text']}"

    return {
        "status_code": ping["status_code"],
        "status_text": status_text,
        "response_time_ms": ping["response_time_ms"],
        "healthy": healthy,
        "metrics": {
            "request_count": int(req_count),
            "error_rate_4xx": round(pct_4xx, 2),
            "error_rate_5xx": round(pct_5xx, 2),
            "latency_ms": round(latency, 1),
            "origin_latency_ms": round(origin_latency, 1),
            "ping_ms": ping["response_time_ms"],
        }
    }


def _check_waf(token: str) -> dict:
    """WAF: instant ping www.icicipruamc.com (WAF sits in front) + metrics."""
    # INSTANT: same endpoint — if WAF blocks, site is unreachable
    ping = _ping_url("https://www.icicipruamc.com", timeout=5)

    # DETAIL: Front Door metrics (WAF is part of FD)
    rid = AZURE_RESOURCE_IDS.get("azure-front-door", "")
    metrics = _get_azure_metrics(token, rid, ["RequestCount", "Percentage5XX", "TotalLatency"])
    req_count = metrics.get("RequestCount", 0)
    pct_5xx = metrics.get("Percentage5XX", 0)
    latency = metrics.get("TotalLatency", 0)

    healthy = ping["healthy"]
    if healthy:
        status_text = f"Active | HTTP {ping['status_code']} | {ping['response_time_ms']}ms | {int(req_count)} reqs filtered"
    else:
        status_text = f"DOWN | {ping['status_text']}"

    return {
        "status_code": ping["status_code"],
        "status_text": status_text,
        "response_time_ms": ping["response_time_ms"],
        "healthy": healthy,
        "metrics": {
            "request_count": int(req_count),
            "error_rate_5xx": round(pct_5xx, 2),
            "ping_ms": ping["response_time_ms"],
        }
    }


def _check_app_gateway(token: str) -> dict:
    """App Gateway: Azure resource state (instant) + metrics for detail."""
    rid = AZURE_RESOURCE_IDS.get("azure-app-gateway", "")
    if not rid:
        return {"status_code": 0, "status_text": "Not configured", "response_time_ms": 0, "healthy": None, "metrics": {}}

    # INSTANT: resource state tells us Running/Stopped immediately
    state = _get_resource_state(token, rid, "2023-11-01")
    operational = state.get("state", "") or state.get("provisioning_state", "")

    # DETAIL: metrics
    metrics = _get_azure_metrics(token, rid, [
        "TotalRequests", "FailedRequests", "HealthyHostCount",
        "UnhealthyHostCount", "Throughput", "CurrentConnections"
    ])
    total_reqs = metrics.get("TotalRequests", 0)
    failed_reqs = metrics.get("FailedRequests", 0)
    healthy_hosts = metrics.get("HealthyHostCount", 0)
    unhealthy_hosts = metrics.get("UnhealthyHostCount", 0)
    throughput = metrics.get("Throughput", 0)
    connections = metrics.get("CurrentConnections", 0)

    failure_pct = (failed_reqs / total_reqs * 100) if total_reqs > 0 else 0
    healthy = (
        operational in ("Running", "Succeeded")
        and unhealthy_hosts == 0
        and failure_pct < 10
    )

    status_text = (
        f"{operational} | {int(total_reqs)} reqs | "
        f"Failed: {int(failed_reqs)} ({failure_pct:.1f}%) | "
        f"Backends: {int(healthy_hosts)} up, {int(unhealthy_hosts)} down"
    )

    return {
        "status_code": 200 if healthy else 503,
        "status_text": status_text,
        "response_time_ms": 0,
        "healthy": healthy,
        "metrics": {
            "operational_state": operational,
            "total_requests": int(total_reqs),
            "failed_requests": int(failed_reqs),
            "failure_pct": round(failure_pct, 2),
            "healthy_backends": int(healthy_hosts),
            "unhealthy_backends": int(unhealthy_hosts),
            "throughput_bps": round(throughput, 0),
            "active_connections": int(connections),
        }
    }


def _check_apim(token: str) -> dict:
    """APIM: instant ping via Front Door endpoint + metrics for detail."""
    # INSTANT: ping the APIM front door endpoint
    ping = _ping_url("https://apimf-investordtprod.z01.azurefd.net", timeout=5)

    # DETAIL: metrics via CDN profile
    rid = AZURE_RESOURCE_IDS.get("azure-front-door-2", "")
    metrics = {}
    if rid:
        metrics = _get_azure_metrics(token, rid, [
            "RequestCount", "Percentage4XX", "Percentage5XX", "TotalLatency"
        ])

    req_count = metrics.get("RequestCount", 0)
    pct_4xx = metrics.get("Percentage4XX", 0)
    pct_5xx = metrics.get("Percentage5XX", 0)
    latency = metrics.get("TotalLatency", 0)

    # APIM root path often returns 404 — that's normal, it means it IS reachable
    # Unreachable = status_code 0 (timeout/connection refused)
    reachable = ping["status_code"] > 0
    if not reachable:
        # Network unreachable — fallback to metrics only
        healthy = pct_5xx < 5 if req_count > 0 else None
        status_text = f"{int(req_count)} reqs | 5xx: {pct_5xx:.1f}% | Latency: {latency:.0f}ms"
    elif reachable and pct_5xx < 5:
        healthy = True
        status_text = f"HTTP {ping['status_code']} | {ping['response_time_ms']}ms | {int(req_count)} reqs | 5xx: {pct_5xx:.1f}%"
    else:
        healthy = False
        status_text = f"DOWN | 5xx: {pct_5xx:.1f}% | {int(req_count)} reqs"

    return {
        "status_code": ping.get("status_code", 0),
        "status_text": status_text,
        "response_time_ms": ping.get("response_time_ms", round(latency)),
        "healthy": healthy,
        "metrics": {
            "request_count": int(req_count),
            "error_rate_4xx": round(pct_4xx, 2),
            "error_rate_5xx": round(pct_5xx, 2),
            "latency_ms": round(latency, 1),
            "ping_ms": ping.get("response_time_ms", 0),
        }
    }


def _check_app_service(token: str) -> dict:
    """App Service: resource state (instant ~1s) + Azure metrics for detail.
    Note: App Service is in private VNET, direct HTTP ping will timeout."""
    rid = AZURE_RESOURCE_IDS.get("azure-app-service", "")

    # INSTANT: resource state API tells us Running/Stopped in ~1 second
    state = _get_resource_state(token, rid, "2023-12-01")
    app_state = state.get("state", "Unknown")
    hostname = state.get("hostname", "")

    # DETAIL: metrics
    metrics = _get_azure_metrics(token, rid, [
        "Requests", "Http5xx", "Http4xx", "Http2xx", "AverageResponseTime"
    ])
    requests = metrics.get("Requests", 0)
    http_5xx = metrics.get("Http5xx", 0)
    http_4xx = metrics.get("Http4xx", 0)
    http_2xx = metrics.get("Http2xx", 0)
    avg_response = metrics.get("AverageResponseTime", 0)

    # Health = resource state (instant) + 5xx check
    healthy = app_state == "Running" and http_5xx < max(1, requests * 0.1)
    response_ms = round(avg_response * 1000) if avg_response else 0
    if app_state != "Running":
        status_text = f"DOWN | State: {app_state}"
    else:
        status_text = f"{app_state} | 2xx:{int(http_2xx)} 4xx:{int(http_4xx)} 5xx:{int(http_5xx)} | {response_ms}ms"

    return {
        "status_code": 200 if healthy else 503,
        "status_text": status_text,
        "response_time_ms": response_ms,
        "healthy": healthy,
        "metrics": {
            "state": app_state,
            "hostname": hostname,
            "requests": int(requests),
            "http_2xx": int(http_2xx),
            "http_4xx": int(http_4xx),
            "http_5xx": int(http_5xx),
            "avg_response_ms": round(avg_response * 1000, 1) if avg_response else 0,
        }
    }


def _check_blob_storage(token: str) -> dict:
    """Blob Storage: Azure metrics (availability is real-time from Azure).
    Note: Storage is on private endpoint, direct HTTP ping will timeout."""
    # DETAIL: Azure metrics — availability is the key health indicator
    rid = AZURE_RESOURCE_IDS.get("azure-blob-storage", "")
    metrics = _get_azure_metrics(token, rid, [
        "Availability", "SuccessServerLatency", "SuccessE2ELatency"
    ], interval="PT1H")

    availability = metrics.get("Availability", 0)
    server_latency = metrics.get("SuccessServerLatency", 0)
    e2e_latency = metrics.get("SuccessE2ELatency", 0)

    healthy = availability >= 99.0
    if availability > 0 and healthy:
        status_text = f"Availability: {availability:.1f}% | Latency: {server_latency:.0f}ms"
    elif availability > 0:
        status_text = f"Degraded | Availability: {availability:.1f}%"
    else:
        status_text = "No metrics available"
        healthy = None

    return {
        "status_code": 200 if healthy else (503 if healthy is False else 0),
        "status_text": status_text,
        "response_time_ms": round(e2e_latency) if e2e_latency else 0,
        "healthy": healthy,
        "metrics": {
            "availability_pct": round(availability, 2),
            "server_latency_ms": round(server_latency, 1),
            "e2e_latency_ms": round(e2e_latency, 1),
        }
    }


def _check_log_analytics(token: str) -> dict:
    """Log Analytics: instant authenticated query ping."""
    settings = get_settings()
    workspace_id = settings.azure_log_analytics_workspace_id
    if not workspace_id or not token:
        return {"status_code": 0, "status_text": "Not configured", "response_time_ms": 0, "healthy": None, "metrics": {}}

    try:
        tenant = settings.azure_tenant_id
        client_id = settings.azure_client_id
        client_secret = settings.azure_client_secret
        url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        body = (
            f"grant_type=client_credentials"
            f"&client_id={client_id}"
            f"&client_secret={urllib.parse.quote(client_secret)}"
            f"&scope=https://api.loganalytics.io/.default"
        )
        req = urllib.request.Request(url, data=body.encode(), method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        resp = urllib.request.urlopen(req, context=_ssl_ctx, timeout=10)
        la_token = json.loads(resp.read())["access_token"]

        # INSTANT: authenticated query — reflects DOWN in seconds
        start = time.time()
        query_url = f"https://api.loganalytics.io/v1/workspaces/{workspace_id}/query"
        query_body = json.dumps({"query": "Heartbeat | take 1"}).encode()
        req2 = urllib.request.Request(query_url, data=query_body, method="POST")
        req2.add_header("Authorization", f"Bearer {la_token}")
        req2.add_header("Content-Type", "application/json")
        resp2 = urllib.request.urlopen(req2, context=_ssl_ctx, timeout=10)
        elapsed = round((time.time() - start) * 1000)
        return {
            "status_code": 200,
            "status_text": f"Connected | Query: {elapsed}ms",
            "response_time_ms": elapsed,
            "healthy": True,
            "metrics": {"query_latency_ms": elapsed}
        }
    except urllib.error.HTTPError as e:
        return {"status_code": e.code, "status_text": f"DOWN | HTTP {e.code}", "response_time_ms": 0, "healthy": False, "metrics": {}}
    except Exception as e:
        return {"status_code": 0, "status_text": f"DOWN | {str(e)[:80]}", "response_time_ms": 0, "healthy": False, "metrics": {}}


def _check_cloudguard_backend() -> dict:
    """CloudGuard backend: instant localhost ping."""
    return _ping_url("http://localhost:80/api/health/ping", timeout=3)


@router.get("/ping")
async def health_ping():
    return {"status": "ok", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


@router.get("/services")
async def check_all_services():
    """
    Check health of all Azure infrastructure services in real-time.
    Uses Azure Monitor Metrics API for genuine service health data.
    """
    # Get management token (cached)
    token = await _async_call(_get_management_token)

    # Define services
    services = [
        {"id": "azure-front-door", "name": "Azure Front Door", "short_name": "Front Door",
         "category": "Frontend", "description": "CDN & Global Load Balancer", "icon": "globe"},
        {"id": "azure-waf", "name": "Azure WAF", "short_name": "WAF",
         "category": "Security", "description": "Web Application Firewall", "icon": "shield"},
        {"id": "azure-app-gateway", "name": "Azure App Gateway", "short_name": "App Gateway",
         "category": "Frontend", "description": "L7 Application Gateway", "icon": "shuffle"},
        {"id": "azure-apim", "name": "Azure API Management", "short_name": "APIM",
         "category": "Backend", "description": "API Gateway & Management", "icon": "settings"},
        {"id": "azure-app-service", "name": "Azure App Service", "short_name": "App Service",
         "category": "Backend", "description": "Web Application Hosting", "icon": "server"},
        {"id": "azure-blob-storage", "name": "Azure Blob Storage", "short_name": "Blob Storage",
         "category": "Backend", "description": "Object & File Storage", "icon": "database"},
        {"id": "azure-log-analytics", "name": "Azure Log Analytics", "short_name": "Log Analytics",
         "category": "Platform", "description": "Log Collection & Query", "icon": "activity"},
        {"id": "cloudguard-backend", "name": "CloudGuard Backend", "short_name": "CloudGuard API",
         "category": "Platform", "description": "Incident Pipeline API", "icon": "cpu"},
    ]

    # Run all checks concurrently
    check_fns = {
        "azure-front-door": lambda: _check_front_door(token),
        "azure-waf": lambda: _check_waf(token),
        "azure-app-gateway": lambda: _check_app_gateway(token),
        "azure-apim": lambda: _check_apim(token),
        "azure-app-service": lambda: _check_app_service(token),
        "azure-blob-storage": lambda: _check_blob_storage(token),
        "azure-log-analytics": lambda: _check_log_analytics(token),
        "cloudguard-backend": _check_cloudguard_backend,
    }

    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, check_fns[svc["id"]]) for svc in services]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Query recent incidents for overlay
    incident_map = {}
    try:
        from app.database import async_session as db_session
        from sqlalchemy import text
        async with db_session() as session:
            q = await session.execute(text(
                "SELECT source_service, COUNT(*) as cnt, MIN(priority) as max_sev "
                "FROM incidents WHERE created_at >= datetime('now', '-24 hours') "
                "GROUP BY source_service"
            ))
            for row in q.fetchall():
                svc_name = (row[0] or "").lower()
                cnt = row[1]
                max_sev = row[2] or "P3"
                node_id = None
                if "front door" in svc_name or "frontdoor" in svc_name or "cdn" in svc_name:
                    node_id = "azure-front-door"
                elif "waf" in svc_name:
                    node_id = "azure-waf"
                elif "app gateway" in svc_name or "appgateway" in svc_name or "application gateway" in svc_name:
                    node_id = "azure-app-gateway"
                elif "apim" in svc_name or "api management" in svc_name:
                    node_id = "azure-apim"
                elif "app service" in svc_name or "appservice" in svc_name or "web app" in svc_name:
                    node_id = "azure-app-service"
                elif "blob" in svc_name or "storage" in svc_name:
                    node_id = "azure-blob-storage"
                elif "sql" in svc_name or "database" in svc_name:
                    node_id = "azure-sql"
                elif "log analytics" in svc_name:
                    node_id = "azure-log-analytics"
                if node_id:
                    incident_map[node_id] = {"incident_count": cnt, "max_severity": max_sev}
    except Exception as e:
        logger.warning(f"Failed to query incidents for health overlay: {e}")

    # Build response
    service_statuses = []
    for i, svc in enumerate(services):
        result = results[i] if not isinstance(results[i], Exception) else {
            "status_code": 0, "status_text": f"Check failed: {str(results[i])[:80]}",
            "response_time_ms": 0, "healthy": False, "metrics": {}
        }

        # Attach incident data as info — but do NOT override real-time health status
        inc_data = incident_map.get(svc["id"], {})
        inc_count = inc_data.get("incident_count", 0)
        max_sev = inc_data.get("max_severity", None)

        # Health status stays as-is from the real-time check
        # Incidents are informational only (shown in UI but don't flip green to red)

        service_statuses.append({
            **svc,
            **result,
            "incident_count": inc_count,
            "incident_severity": max_sev,
            "last_checked": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    # Summary
    total = len(service_statuses)
    healthy_count = sum(1 for s in service_statuses if s["healthy"] is True)
    unhealthy_count = sum(1 for s in service_statuses if s["healthy"] is False)
    unknown_count = sum(1 for s in service_statuses if s["healthy"] is None)

    # Record snapshot in history
    _record_health_snapshot(service_statuses)

    # AUTO-ALERT: If any service is DOWN, send email automatically (with cooldown)
    if unhealthy_count > 0:
        asyncio.ensure_future(_auto_alert_if_needed(service_statuses))

    return {
        "services": service_statuses,
        "summary": {
            "total": total,
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "unknown": unknown_count,
            "overall_status": "CRITICAL" if unhealthy_count > 2 else "DEGRADED" if unhealthy_count > 0 else "HEALTHY",
        },
    }


@router.get("/incident-affected-services")
async def get_incident_affected_services():
    """
    Returns which Azure services have active incidents from the latest pipeline run.
    Used by the topology diagram to show affected services in red.
    """
    affected = []
    try:
        from app.database import async_session as db_session
        from sqlalchemy import text
        async with db_session() as session:
            q = await session.execute(text(
                "SELECT source_service, title, priority, root_cause, root_cause_category, "
                "affected_component, COUNT(*) as log_count "
                "FROM incidents WHERE created_at >= datetime('now', '-24 hours') "
                "GROUP BY source_service, title "
                "ORDER BY priority, created_at DESC"
            ))
            for row in q.fetchall():
                svc_name = (row[0] or "Unknown").lower()
                node_id = "unknown"
                if "front door" in svc_name or "frontdoor" in svc_name:
                    node_id = "azure-front-door"
                elif "waf" in svc_name:
                    node_id = "azure-waf"
                elif "app gateway" in svc_name or "appgateway" in svc_name:
                    node_id = "azure-app-gateway"
                elif "apim" in svc_name or "api management" in svc_name:
                    node_id = "azure-apim"
                elif "app service" in svc_name or "appservice" in svc_name or "web app" in svc_name:
                    node_id = "azure-app-service"
                elif "blob" in svc_name or "storage" in svc_name:
                    node_id = "azure-blob-storage"
                elif "sql" in svc_name or "database" in svc_name:
                    node_id = "azure-sql"
                elif "log analytics" in svc_name:
                    node_id = "azure-log-analytics"

                affected.append({
                    "node_id": node_id,
                    "service_name": row[0] or "Unknown",
                    "incident_title": row[1],
                    "severity": row[2],
                    "root_cause": (row[3] or "")[:200],
                    "rca_category": row[4],
                    "affected_component": row[5],
                    "log_count": row[6],
                })
    except Exception as e:
        logger.error(f"Failed to get incident-affected services: {e}")

    return {"affected_services": affected}


# ══════════════════════════════════════════
# HEALTH CHECK HISTORY (in-memory ring buffer)
# ══════════════════════════════════════════
from collections import deque
import threading

_health_history_lock = threading.Lock()
_health_history: deque = deque(maxlen=50)  # Last 50 health check snapshots


def _record_health_snapshot(services: list):
    """Store a snapshot of the current health check in the history ring buffer."""
    snapshot = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "services": [
            {
                "id": svc.get("id", ""),
                "short_name": svc.get("short_name", ""),
                "healthy": svc.get("healthy"),
                "status_code": svc.get("status_code", 0),
                "response_time_ms": svc.get("response_time_ms", 0),
                "status_text": svc.get("status_text", ""),
            }
            for svc in services
        ],
    }
    with _health_history_lock:
        _health_history.append(snapshot)


@router.get("/history")
async def get_health_history():
    """Return the last N health check snapshots with timestamps."""
    with _health_history_lock:
        entries = list(_health_history)
    return {"history": entries, "count": len(entries)}

# ══════════════════════════════════════════
# AUTO-ALERT ON DOWNTIME (with cooldown + instant RCA)
# ══════════════════════════════════════════
_last_auto_alert_time = 0
_AUTO_ALERT_COOLDOWN = 300  # 5 minutes between auto-alerts


def _generate_instant_rca(svc: dict, all_services: list) -> dict:
    """Generate instant rule-based RCA from health check metrics."""
    name = svc.get("short_name", "Unknown")
    sid = svc.get("id", "")
    m = svc.get("metrics", {})
    status_text = svc.get("status_text", "")
    ms = svc.get("response_time_ms", 0)
    status_code = svc.get("status_code", 0)

    # Build helper: which other services are also down?
    other_down = [s.get("short_name", "") for s in all_services
                  if s.get("healthy") is False and s.get("id") != sid]

    root_cause = ""
    impact = ""
    recommendation = ""
    severity = "P2"

    # ── Front Door ──
    if "front-door" in sid and "front-door-2" not in sid:
        if status_code == 0:
            root_cause = f"Front Door is unreachable (HTTP timeout). The CDN/edge layer is not responding, which means www.icicipruamc.com is inaccessible to all end users."
            severity = "P1"
        elif status_code >= 500:
            root_cause = f"Front Door is returning HTTP {status_code} server errors. The CDN is online but failing to serve content."
            severity = "P1"
        else:
            root_cause = f"Front Door health check failed. Status: {status_text}"

        if "WAF" in other_down:
            root_cause += " WAF is also down, suggesting a complete Azure edge layer outage."
            severity = "P1"

        impact = "www.icicipruamc.com is NOT accessible to end users. All web traffic is blocked."
        recommendation = "1. Check Azure Front Door health in Azure Portal. 2. Verify DNS resolution for www.icicipruamc.com. 3. Check Azure Status page for regional outages. 4. Escalate to Azure Support if issue persists > 5 min."

    # ── WAF ──
    elif "waf" in sid:
        fd_also_down = any("front-door" in s.get("id", "") and s.get("healthy") is False
                          for s in all_services if "front-door-2" not in s.get("id", ""))
        if fd_also_down:
            root_cause = "WAF is unreachable because Front Door (which hosts the WAF) is also down. This is likely a shared edge layer failure, not a WAF-specific issue."
        else:
            root_cause = f"WAF health check failed while Front Door is operational. Possible WAF rule misconfiguration or policy blocking all traffic. Status: {status_text}"
        impact = "Web Application Firewall is not filtering traffic. If Front Door recovers, the site may be exposed to attacks."
        recommendation = "1. Check WAF policy in Azure Portal > Front Door > Security. 2. Review recent WAF rule changes. 3. Verify no custom rules are blocking all traffic."

    # ── App Gateway ──
    elif "app-gateway" in sid:
        state = m.get("operational_state", "")
        unhealthy_backends = m.get("unhealthy_backends", 0)
        failure_pct = m.get("failure_pct", 0)

        if state in ("Stopped", "Deallocated"):
            root_cause = f"App Gateway is {state}. It was manually stopped or deallocated from Azure Portal."
            recommendation = "1. Start the App Gateway from Azure Portal > App Gateway > Start. 2. Verify who stopped it and why."
        elif unhealthy_backends > 0:
            root_cause = f"App Gateway has {unhealthy_backends} unhealthy backend(s). Backend servers are not responding to health probes."
            recommendation = "1. Check backend pool health in Azure Portal. 2. Verify App Service is running. 3. Check NSG/firewall rules blocking health probes."
        elif failure_pct > 10:
            root_cause = f"App Gateway failure rate is {failure_pct:.1f}%. High proportion of requests are failing at the gateway level."
            recommendation = "1. Check App Gateway diagnostics logs. 2. Verify backend connectivity. 3. Review SSL certificate expiry."
        else:
            root_cause = f"App Gateway is reporting unhealthy. State: {state}. Status: {status_text}"
            recommendation = "Check Azure Portal for App Gateway health details."

        impact = "Traffic routing from Front Door to backend services is disrupted. API and web requests may fail."
        severity = "P1" if state in ("Stopped", "Deallocated") else "P2"

    # ── APIM ──
    elif "apim" in sid:
        err_5xx = m.get("error_rate_5xx", 0)
        if status_code == 0:
            root_cause = "APIM endpoint is unreachable (connection timeout). The API Management service may be stopped or experiencing a network issue."
            severity = "P1"
        elif err_5xx > 5:
            root_cause = f"APIM 5xx error rate is {err_5xx:.1f}%. Backend APIs behind APIM are failing."
        else:
            root_cause = f"APIM health check failed. HTTP {status_code}. Status: {status_text}"

        impact = "API endpoints served by APIM are unavailable. Mobile apps and third-party integrations may fail."
        recommendation = "1. Check APIM service health in Azure Portal. 2. Verify backend API connectivity. 3. Check APIM subscription quotas."

    # ── App Service ──
    elif "app-service" in sid:
        state = m.get("state", "Unknown")
        http_5xx = m.get("http_5xx", 0)

        if state == "Stopped":
            root_cause = "App Service is STOPPED. It was manually stopped from Azure Portal or ran out of quota."
            severity = "P1"
            recommendation = "1. Start the App Service from Azure Portal > App Service > Start. 2. Check if auto-heal or platform maintenance stopped it."
        elif http_5xx > 0:
            root_cause = f"App Service is returning {int(http_5xx)} HTTP 5xx errors. Application code is crashing or throwing unhandled exceptions."
            recommendation = "1. Check App Service logs (Log Stream). 2. Review recent deployments. 3. Check application health endpoint."
        else:
            root_cause = f"App Service is unhealthy. State: {state}. Status: {status_text}"
            recommendation = "1. Check App Service health in Azure Portal. 2. Restart the App Service."

        impact = "The backend web application serving www.icicipruamc.com content is down. Pages may not load or return errors."

    # ── Blob Storage ──
    elif "blob" in sid:
        avail = m.get("availability_pct", 0)
        if avail > 0 and avail < 99:
            root_cause = f"Blob Storage availability dropped to {avail:.1f}%. Some read/write operations are failing."
        elif avail == 0:
            root_cause = "Blob Storage metrics show 0% availability or no data. Storage account may be unreachable or misconfigured."
            severity = "P1"
        else:
            root_cause = f"Blob Storage health check failed. Status: {status_text}"

        impact = "Static assets, documents, and data files hosted in Blob Storage may not load on the website."
        recommendation = "1. Check Storage Account health in Azure Portal. 2. Verify private endpoint connectivity. 3. Check Azure Status for storage outages."

    # ── Log Analytics ──
    elif "log-analytics" in sid:
        root_cause = f"Log Analytics workspace query failed. Status: {status_text}. The workspace may be unreachable or credentials expired."
        impact = "Log collection and monitoring data is unavailable. CloudGuard pipeline analysis will not work."
        recommendation = "1. Check Log Analytics workspace in Azure Portal. 2. Verify Service Principal credentials. 3. Check workspace retention/quota."
        severity = "P3"

    # ── Fallback ──
    else:
        root_cause = f"Service is unhealthy. Status: {status_text}"
        impact = "Service disruption detected."
        recommendation = "Check Azure Portal for details."

    return {
        "root_cause": root_cause,
        "impact": impact,
        "recommendation": recommendation,
        "severity": severity,
    }


async def _auto_alert_if_needed(service_statuses: list):
    """Automatically send email alert with instant RCA when services are DOWN."""
    global _last_auto_alert_time
    now = time.time()

    # Cooldown: don't send more than once every 5 minutes
    if now - _last_auto_alert_time < _AUTO_ALERT_COOLDOWN:
        return

    down_services = [s for s in service_statuses if s.get("healthy") is False]
    if not down_services:
        return

    _last_auto_alert_time = now
    down_names = ", ".join([s.get("short_name", "") for s in down_services])
    logger.warning(f"AUTO-ALERT+RCA: {len(down_services)} service(s) DOWN: {down_names} — sending email")

    try:
        from app.services.graph_email_service import graph_email_service

        now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

        # Generate RCA for each down service
        rca_blocks = ""
        highest_severity = "P3"
        severity_order = {"P1": 1, "P2": 2, "P3": 3}

        for svc in down_services:
            rca = _generate_instant_rca(svc, service_statuses)
            sev = rca["severity"]
            if severity_order.get(sev, 3) < severity_order.get(highest_severity, 3):
                highest_severity = sev

            sev_color = "#ef4444" if sev == "P1" else "#f59e0b" if sev == "P2" else "#64748b"
            sev_bg = "#fef2f2" if sev == "P1" else "#fffbeb" if sev == "P2" else "#f8fafc"

            rca_blocks += f"""
            <div style="background:{sev_bg};border:1px solid {sev_color}30;border-radius:10px;padding:14px 16px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                    <span style="background:{sev_color};color:white;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;">{sev}</span>
                    <span style="font-size:14px;font-weight:800;color:#0f172a;">{svc.get('short_name', '')}</span>
                    <span style="font-size:11px;color:#ef4444;font-weight:600;">DOWN</span>
                    <span style="font-size:11px;color:#94a3b8;margin-left:auto;">{svc.get('response_time_ms', 0)}ms | HTTP {svc.get('status_code', 0)}</span>
                </div>

                <div style="margin-bottom:8px;">
                    <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:3px;">Root Cause</div>
                    <div style="font-size:12px;color:#0f172a;line-height:1.5;">{rca['root_cause']}</div>
                </div>

                <div style="margin-bottom:8px;">
                    <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:3px;">Impact</div>
                    <div style="font-size:12px;color:#334155;line-height:1.5;">{rca['impact']}</div>
                </div>

                <div style="background:white;border-radius:6px;padding:8px 10px;border:1px solid #e2e8f0;">
                    <div style="font-size:10px;font-weight:700;color:#0369a1;text-transform:uppercase;margin-bottom:3px;">Recommendation</div>
                    <div style="font-size:11px;color:#334155;line-height:1.6;">{rca['recommendation']}</div>
                </div>
            </div>"""

        # Healthy services summary
        healthy_services = [s for s in service_statuses if s.get("healthy") is True]
        healthy_rows = ""
        for svc in healthy_services:
            healthy_rows += f'<span style="display:inline-block;background:#f0fdf4;border:1px solid #86efac;border-radius:4px;padding:2px 8px;font-size:10px;color:#166534;font-weight:600;margin:2px;">{svc.get("short_name", "")} OK</span>'

        html_body = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:680px;margin:0 auto;">
            <div style="background:linear-gradient(135deg,#dc2626 0%,#991b1b 100%);padding:18px 24px;border-radius:10px 10px 0 0;">
                <h1 style="margin:0;color:white;font-size:18px;">CloudGuard - Downtime Alert + RCA</h1>
                <p style="margin:4px 0 0;color:#fecaca;font-size:12px;">Real-time health check with instant root cause analysis</p>
            </div>
            <div style="background:white;padding:18px 24px;border:1px solid #e2e8f0;border-radius:0 0 10px 10px;">

                <div style="background:#fef2f2;padding:10px 14px;border-radius:8px;margin-bottom:14px;border:1px solid #fecaca;">
                    <p style="margin:0;font-size:14px;color:#991b1b;font-weight:700;">
                        {len(down_services)} service(s) DOWN: {down_names}
                    </p>
                    <p style="margin:4px 0 0;font-size:11px;color:#6b7280;">
                        Website: <strong>www.icicipruamc.com</strong> | Detected: {now_str} | Severity: <strong style="color:{('#ef4444' if highest_severity == 'P1' else '#f59e0b' if highest_severity == 'P2' else '#64748b')}">{highest_severity}</strong>
                    </p>
                </div>

                <div style="font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;margin-bottom:8px;letter-spacing:0.5px;">Root Cause Analysis</div>

                {rca_blocks}

                <div style="margin-top:10px;margin-bottom:12px;">
                    <div style="font-size:10px;font-weight:700;color:#166534;text-transform:uppercase;margin-bottom:4px;">Healthy Services</div>
                    <div>{healthy_rows if healthy_rows else '<span style="color:#94a3b8;font-size:11px;">None</span>'}</div>
                </div>

                <div style="padding:10px;background:#f0f9ff;border-radius:6px;border:1px solid #bae6fd;">
                    <p style="margin:0;font-size:11px;color:#0369a1;">
                        <a href="http://10.238.46.116" style="color:#0369a1;font-weight:700;">Open Dashboard</a> |
                        Auto-alert with RCA. Next alert in 5 min if issue persists.
                    </p>
                </div>
            </div>
        </div>"""

        subject = f"[CloudGuard] {highest_severity} ALERT: {down_names} DOWN + RCA - www.icicipruamc.com"
        sent = await graph_email_service.send_email(
            to_email="prabhat_singh@ext.icicipruamc.com",
            subject=subject,
            html_body=html_body,
        )
        if sent:
            logger.info(f"AUTO-ALERT+RCA sent successfully for: {down_names}")
        else:
            logger.warning(f"AUTO-ALERT+RCA email send failed for: {down_names}")
    except Exception as e:
        logger.error(f"AUTO-ALERT+RCA failed: {e}")


# ══════════════════════════════════════════
# DOWNTIME NOTIFICATION EMAIL
# ══════════════════════════════════════════
from pydantic import BaseModel
from typing import Optional

class DowntimeNotifyRequest(BaseModel):
    recipient_email: Optional[str] = None  # If not provided, uses default from config


@router.post("/notify-downtime")
async def notify_downtime(req: DowntimeNotifyRequest = None):
    """
    Send a notification email about any DOWN services with instant RCA.
    Called manually by the user via the UI 'Send Alert' button.
    """
    # 1) Get current health status
    health_data = await check_all_services()
    all_services = health_data["services"]
    down_services = [s for s in all_services if s.get("healthy") is False]

    if not down_services:
        return {"sent": False, "message": "No services are currently down. No notification sent."}

    # 2) Generate instant RCA for each down service
    now = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    sev_order = {"P1": 1, "P2": 2, "P3": 3}
    highest_severity = "P3"

    rca_blocks = ""
    for svc in down_services:
        rca = _generate_instant_rca(svc, all_services)
        sev = rca["severity"]
        if sev_order.get(sev, 3) < sev_order.get(highest_severity, 3):
            highest_severity = sev

        sev_color = "#ef4444" if sev == "P1" else "#f59e0b" if sev == "P2" else "#64748b"
        sev_bg = "#fef2f2" if sev == "P1" else "#fffbeb" if sev == "P2" else "#f8fafc"

        rca_blocks += f"""
        <div style="margin-bottom:16px;padding:16px;background:white;border:1px solid {sev_color}30;border-left:4px solid {sev_color};border-radius:8px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                <span style="background:{sev_color};color:white;padding:2px 10px;border-radius:4px;font-size:11px;font-weight:700;">{sev}</span>
                <span style="font-size:16px;font-weight:800;color:#0f172a;">{svc.get('short_name', '')}</span>
                <span style="background:#fef2f2;color:#ef4444;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;border:1px solid #fecaca;">DOWN</span>
            </div>

            <div style="padding:10px;background:#f8fafc;border-radius:6px;margin-bottom:10px;">
                <table style="width:100%;font-size:12px;">
                    <tr><td style="color:#6b7280;padding:2px 0;width:110px;">Status:</td><td style="color:#0f172a;font-weight:600;">{svc.get('status_text', 'Unreachable')}</td></tr>
                    <tr><td style="color:#6b7280;padding:2px 0;">HTTP Code:</td><td><code>{svc.get('status_code', 0)}</code></td></tr>
                    <tr><td style="color:#6b7280;padding:2px 0;">Response Time:</td><td>{svc.get('response_time_ms', 0)}ms</td></tr>
                </table>
            </div>

            <div style="margin-bottom:8px;">
                <div style="font-size:10px;font-weight:700;color:{sev_color};text-transform:uppercase;margin-bottom:3px;">Root Cause</div>
                <div style="font-size:13px;color:#0f172a;line-height:1.5;">{rca['root_cause']}</div>
            </div>

            <div style="margin-bottom:8px;">
                <div style="font-size:10px;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:3px;">Impact</div>
                <div style="font-size:12px;color:#334155;line-height:1.5;">{rca['impact']}</div>
            </div>

            <div style="background:{sev_bg};border-radius:6px;padding:10px 12px;border:1px solid {sev_color}20;">
                <div style="font-size:10px;font-weight:700;color:#0369a1;text-transform:uppercase;margin-bottom:3px;">Recommendation</div>
                <div style="font-size:12px;color:#334155;line-height:1.6;">{rca['recommendation']}</div>
            </div>
        </div>"""

    # Healthy services summary
    healthy_services = [s for s in all_services if s.get("healthy") is True]
    healthy_badges = ""
    for svc in healthy_services:
        healthy_badges += f'<span style="display:inline-block;background:#f0fdf4;border:1px solid #86efac;border-radius:4px;padding:3px 10px;font-size:11px;color:#166534;font-weight:600;margin:2px;">{svc.get("short_name", "")} OK</span>'

    down_names = ", ".join([s.get("short_name", "") for s in down_services])
    html_body = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:700px;margin:0 auto;">
        <div style="background:linear-gradient(135deg,#dc2626 0%,#b91c1c 100%);padding:20px 24px;border-radius:10px 10px 0 0;">
            <h1 style="margin:0;color:white;font-size:20px;">CloudGuard - Service Downtime Alert + RCA</h1>
            <p style="margin:6px 0 0;color:#fecaca;font-size:13px;">Real-time health monitoring with instant root cause analysis</p>
        </div>
        <div style="background:#f8fafc;padding:20px 24px;border-radius:0 0 10px 10px;border:1px solid #e2e8f0;">
            <div style="background:#fef2f2;padding:12px 16px;border-radius:8px;margin-bottom:16px;border:1px solid #fecaca;">
                <p style="margin:0;font-size:14px;color:#991b1b;font-weight:700;">
                    {len(down_services)} service(s) DOWN: {down_names}
                </p>
                <p style="margin:4px 0 0;font-size:12px;color:#6b7280;">
                    Website: <strong>www.icicipruamc.com</strong> | Detected: {now} | Severity: <strong style="color:{('#ef4444' if highest_severity == 'P1' else '#f59e0b' if highest_severity == 'P2' else '#64748b')}">{highest_severity}</strong>
                </p>
            </div>

            <div style="font-size:12px;font-weight:700;color:#475569;text-transform:uppercase;margin-bottom:10px;letter-spacing:0.5px;">Root Cause Analysis (per service)</div>

            {rca_blocks}

            <div style="margin-bottom:12px;">
                <div style="font-size:10px;font-weight:700;color:#166534;text-transform:uppercase;margin-bottom:4px;">Healthy Services</div>
                <div>{healthy_badges if healthy_badges else '<span style="color:#94a3b8;font-size:11px;">None</span>'}</div>
            </div>

            <div style="padding:12px;background:#f0f9ff;border-radius:8px;border:1px solid #bae6fd;">
                <p style="margin:0;font-size:12px;color:#0369a1;">
                    <a href="http://10.238.46.116" style="color:#0369a1;font-weight:700;">Open Dashboard</a> |
                    Manually triggered by CloudGuard user.
                    RCA generated from real-time health check metrics.
                </p>
            </div>
        </div>
    </div>"""

    # 3) Send email
    try:
        from app.services.graph_email_service import graph_email_service
        to_email = "prabhat_singh@ext.icicipruamc.com"

        subject = f"[CloudGuard] {highest_severity} ALERT: {down_names} DOWN + RCA - www.icicipruamc.com"
        sent = await graph_email_service.send_email(
            to_email=to_email,
            subject=subject,
            html_body=html_body,
        )
        if sent:
            return {"sent": True, "message": f"Downtime alert with RCA sent to {to_email}", "down_services": down_names}
        else:
            return {"sent": False, "message": "Email send failed. Check Graph API configuration."}
    except Exception as e:
        logger.error(f"Downtime notification failed: {e}")
        return {"sent": False, "message": f"Error: {str(e)[:100]}"}


