"""
Synthetic Log Generator
=======================
Generates realistic Azure-style logs for:
  - Azure Front Door
  - Azure Application Gateway
  - Azure API Management

Simulates all scenario types:
  200 OK, 404, 500, 401 Unauthorized, 429 Rate Limit,
  Backend Timeout, WAF Block, High Latency

Injects directly into the raw_logs PostgreSQL table so the
8-agent pipeline can process them immediately.

Also optionally uploads to Azure Log Analytics via the
Data Collector (HTTP) API for production-like flow.
"""

import uuid
import logging
import random
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

from app.database import async_session
from app.models.raw_log import RawLog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

FRONT_DOOR_ENDPOINTS = [
    "/api/v1/accounts",
    "/api/v1/transactions",
    "/api/v1/auth/login",
    "/api/v1/auth/token",
    "/api/v1/payments/initiate",
    "/api/v1/statements",
    "/api/v1/beneficiaries",
    "/health",
    "/api/v1/kyc/verify",
    "/api/v1/cards",
]

APP_GATEWAY_BACKENDS = [
    "10.0.1.10:8080",
    "10.0.1.11:8080",
    "10.0.1.12:8080",
]

APIM_APIS = [
    "banking-core-api",
    "payment-gateway-api",
    "auth-service-api",
    "kyc-verification-api",
    "notification-api",
]

CLIENT_IPS = [
    "203.0.113.45", "198.51.100.22", "192.0.2.100",
    "185.220.101.10",  # suspicious
    "103.145.12.88",   # suspicious
    "59.144.12.34", "202.55.66.77",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "KrelixirBankingApp/3.2.1 (iOS 17.4)",
    "KrelixirBankingApp/3.2.1 (Android 14)",
    "python-httpx/0.27.0",  # suspicious bot
    "curl/7.88.0",
]

SUBSCRIPTION_ID = "ffe9a8d4-3d21-44e9-8288-f86ddae2d807"
RESOURCE_GROUP = "banking-log-analyser-rg"


# ---------------------------------------------------------------------------
# Scenario factories
# ---------------------------------------------------------------------------

def _make_frontdoor_log(scenario: str, ts: datetime) -> dict[str, Any]:
    """Generate an Azure Front Door access log entry."""
    endpoint = random.choice(FRONT_DOOR_ENDPOINTS)
    client_ip = random.choice(CLIENT_IPS)
    ua = random.choice(USER_AGENTS)
    request_id = str(uuid.uuid4())

    base = {
        "TimeGenerated": ts.isoformat(),
        "Category": "FrontDoorAccessLog",
        "ResourceProvider": "MICROSOFT.CDN",
        "ResourceId": f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Cdn/profiles/banking-frontdoor",
        "CorrelationId": request_id,
        "clientIp_s": client_ip,
        "requestUri_s": f"https://banking.krelixir.com{endpoint}",
        "host_s": "banking.krelixir.com",
        "userAgent_s": ua,
        "httpMethod_s": random.choice(["GET", "POST", "PUT", "DELETE"]),
        "source": "Azure Front Door",
        "source_system": "azure-front-door",
    }

    if scenario == "success":
        base.update({
            "httpStatusCode_d": random.choice([200, 201, 204]),
            "timeTaken_d": random.uniform(45, 250),
            "Level": "Informational",
            "message": f"Request to {endpoint} completed successfully",
        })
    elif scenario == "not_found":
        ep = f"/api/v1/nonexistent/{uuid.uuid4().hex[:8]}"
        base.update({
            "httpStatusCode_d": 404,
            "requestUri_s": f"https://banking.krelixir.com{ep}",
            "timeTaken_d": random.uniform(10, 50),
            "Level": "Warning",
            "errorInfo_s": "ResourceNotFound",
            "message": f"404 Not Found: {ep}",
        })
    elif scenario == "server_error":
        base.update({
            "httpStatusCode_d": 500,
            "timeTaken_d": random.uniform(1500, 30000),
            "Level": "Error",
            "errorInfo_s": "InternalServerError",
            "message": f"500 Internal Server Error on {endpoint} — backend threw unhandled exception",
        })
    elif scenario == "unauthorized":
        base.update({
            "httpStatusCode_d": 401,
            "timeTaken_d": random.uniform(5, 30),
            "Level": "Warning",
            "errorInfo_s": "Unauthorized",
            "message": f"401 Unauthorized: missing or invalid Bearer token for {endpoint}",
        })
    elif scenario == "rate_limit":
        base.update({
            "httpStatusCode_d": 429,
            "timeTaken_d": random.uniform(5, 20),
            "Level": "Warning",
            "errorInfo_s": "TooManyRequests",
            "message": f"429 Rate Limit Exceeded: client {client_ip} exceeded 100 req/min on {endpoint}",
        })
    elif scenario == "waf_block":
        base.update({
            "httpStatusCode_d": 403,
            "Category": "FrontDoorWebApplicationFirewallLog",
            "timeTaken_d": random.uniform(2, 15),
            "Level": "Warning",
            "action_s": "Block",
            "ruleName_s": f"OWASP_{random.choice(['SQLi', 'XSS', 'LFI', 'RCE'])}_{random.randint(900, 999)}",
            "errorInfo_s": "WAFBlock",
            "message": f"WAF blocked request from {client_ip} — SQL injection attempt detected on {endpoint}",
        })
    elif scenario == "high_latency":
        latency = random.uniform(8000, 30000)
        base.update({
            "httpStatusCode_d": 200,
            "timeTaken_d": latency,
            "Level": "Warning",
            "message": f"High latency response: {latency:.0f}ms on {endpoint} — backend pool degraded",
        })
    elif scenario == "backend_timeout":
        base.update({
            "httpStatusCode_d": 504,
            "timeTaken_d": 30000,
            "Level": "Error",
            "errorInfo_s": "GatewayTimeout",
            "message": f"504 Gateway Timeout: upstream backend did not respond within 30s for {endpoint}",
        })

    return base


def _make_appgateway_log(scenario: str, ts: datetime) -> dict[str, Any]:
    """Generate an Azure Application Gateway access log entry."""
    endpoint = random.choice(FRONT_DOOR_ENDPOINTS)
    client_ip = random.choice(CLIENT_IPS)
    backend = random.choice(APP_GATEWAY_BACKENDS)
    request_id = str(uuid.uuid4())

    base = {
        "TimeGenerated": ts.isoformat(),
        "Category": "ApplicationGatewayAccessLog",
        "ResourceProvider": "MICROSOFT.NETWORK",
        "ResourceId": f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Network/applicationGateways/banking-appgateway",
        "CorrelationId": request_id,
        "clientIP_s": client_ip,
        "requestUri_s": endpoint,
        "host_s": "10.0.0.5",
        "serverRouted_s": backend,
        "httpMethod_s": random.choice(["GET", "POST"]),
        "source": "Azure Application Gateway",
        "source_system": "azure-app-gateway",
    }

    if scenario == "success":
        base.update({
            "httpStatus_d": random.choice([200, 201]),
            "serverStatus_d": 200,
            "timeTaken_d": random.uniform(30, 200),
            "Level": "Informational",
            "message": f"Request routed successfully to {backend} for {endpoint}",
        })
    elif scenario == "not_found":
        base.update({
            "httpStatus_d": 404,
            "serverStatus_d": 404,
            "timeTaken_d": random.uniform(10, 40),
            "Level": "Warning",
            "message": f"Backend {backend} returned 404 for {endpoint}",
        })
    elif scenario == "server_error":
        base.update({
            "httpStatus_d": 502,
            "serverStatus_d": 500,
            "timeTaken_d": random.uniform(2000, 20000),
            "Level": "Error",
            "message": f"Bad Gateway: backend {backend} returned 500 on {endpoint}",
        })
    elif scenario == "unauthorized":
        base.update({
            "httpStatus_d": 403,
            "serverStatus_d": 403,
            "timeTaken_d": random.uniform(5, 25),
            "Level": "Warning",
            "message": f"Access denied by WAF policy for client {client_ip} on {endpoint}",
        })
    elif scenario == "backend_timeout":
        base.update({
            "httpStatus_d": 504,
            "serverStatus_d": 0,
            "timeTaken_d": 60000,
            "Level": "Error",
            "message": f"Backend {backend} timed out after 60s for {endpoint} — health probe failing",
        })
    elif scenario == "high_latency":
        latency = random.uniform(5000, 25000)
        base.update({
            "httpStatus_d": 200,
            "serverStatus_d": 200,
            "timeTaken_d": latency,
            "Level": "Warning",
            "message": f"High backend latency: {latency:.0f}ms routing to {backend} for {endpoint}",
        })
    elif scenario == "rate_limit":
        base.update({
            "httpStatus_d": 429,
            "serverStatus_d": 429,
            "timeTaken_d": 10,
            "Level": "Warning",
            "message": f"Rate limit hit: {client_ip} exceeded connection limit on App Gateway",
        })
    elif scenario == "waf_block":
        base.update({
            "Category": "ApplicationGatewayFirewallLog",
            "httpStatus_d": 403,
            "timeTaken_d": 5,
            "Level": "Warning",
            "action_s": "Blocked",
            "ruleName_s": f"REQUEST-{random.randint(920, 944)}-SQLI-ATTACK",
            "message": f"WAF blocked malicious request from {client_ip} — XSS pattern detected",
        })

    return base


def _make_apim_log(scenario: str, ts: datetime) -> dict[str, Any]:
    """Generate an Azure API Management gateway log entry."""
    api = random.choice(APIM_APIS)
    endpoint = random.choice(FRONT_DOOR_ENDPOINTS)
    request_id = str(uuid.uuid4())

    base = {
        "TimeGenerated": ts.isoformat(),
        "Category": "GatewayLogs",
        "ResourceProvider": "MICROSOFT.APIMANAGEMENT",
        "ResourceId": f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.ApiManagement/service/banking-apim",
        "CorrelationId": request_id,
        "apiId_s": api,
        "url_s": endpoint,
        "method_s": random.choice(["GET", "POST", "PUT"]),
        "cache_s": random.choice(["miss", "hit", "none"]),
        "source": "Azure API Management",
        "source_system": "azure-apim",
    }

    if scenario == "success":
        base.update({
            "responseCode_d": 200,
            "backendResponseCode_d": 200,
            "clientTime_d": random.uniform(20, 150),
            "backendTime_d": random.uniform(10, 100),
            "Level": "Informational",
            "message": f"API call to {api}{endpoint} completed in {random.uniform(30, 200):.0f}ms",
        })
    elif scenario == "not_found":
        base.update({
            "responseCode_d": 404,
            "backendResponseCode_d": 404,
            "clientTime_d": random.uniform(5, 30),
            "backendTime_d": 0,
            "Level": "Warning",
            "message": f"API {api}: operation not found for {endpoint}",
        })
    elif scenario == "server_error":
        base.update({
            "responseCode_d": 500,
            "backendResponseCode_d": 500,
            "clientTime_d": random.uniform(1000, 15000),
            "backendTime_d": random.uniform(1000, 15000),
            "Level": "Error",
            "message": f"API {api}: backend service threw 500 Internal Server Error on {endpoint}",
        })
    elif scenario == "unauthorized":
        base.update({
            "responseCode_d": 401,
            "backendResponseCode_d": 0,
            "clientTime_d": random.uniform(5, 20),
            "backendTime_d": 0,
            "Level": "Warning",
            "message": f"API {api}: JWT token validation failed — missing or expired subscription key",
        })
    elif scenario == "rate_limit":
        base.update({
            "responseCode_d": 429,
            "backendResponseCode_d": 0,
            "clientTime_d": 5,
            "backendTime_d": 0,
            "Level": "Warning",
            "message": f"API {api}: rate limit policy triggered — 429 Too Many Requests for product 'banking-unlimited'",
        })
    elif scenario == "backend_timeout":
        base.update({
            "responseCode_d": 504,
            "backendResponseCode_d": 0,
            "clientTime_d": 30000,
            "backendTime_d": 30000,
            "Level": "Error",
            "message": f"API {api}: backend timeout after 30s for {endpoint} — circuit breaker may trigger",
        })
    elif scenario == "high_latency":
        latency = random.uniform(4000, 20000)
        base.update({
            "responseCode_d": 200,
            "backendResponseCode_d": 200,
            "clientTime_d": latency,
            "backendTime_d": latency * 0.9,
            "Level": "Warning",
            "message": f"API {api}: high response time {latency:.0f}ms — backend degradation detected",
        })
    elif scenario == "waf_block":
        base.update({
            "responseCode_d": 403,
            "backendResponseCode_d": 0,
            "clientTime_d": 10,
            "backendTime_d": 0,
            "Level": "Warning",
            "message": f"API {api}: request blocked by APIM policy — IP {random.choice(CLIENT_IPS)} blacklisted",
        })

    return base


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

SCENARIOS = [
    "success", "success", "success", "success",   # 40% success
    "not_found", "not_found",                       # 20% 404
    "server_error", "server_error",                 # 20% 500
    "unauthorized",                                 # 10% 401
    "rate_limit",                                   # 5% 429
    "backend_timeout",                              # 3% timeout
    "high_latency",                                 # 3% latency
    "waf_block",                                    # 4% WAF
]

SERVICE_GENERATORS = {
    "azure-front-door": ("Azure Front Door", _make_frontdoor_log),
    "azure-app-gateway": ("Azure Application Gateway", _make_appgateway_log),
    "azure-apim": ("Azure API Management", _make_apim_log),
}


async def generate_and_inject_logs(
    count: int = 60,
    run_id: str | None = None,
    spread_minutes: int = 30,
) -> dict[str, Any]:
    """
    Generate `count` synthetic Azure logs across all three services
    and inject them directly into the raw_logs PostgreSQL table.

    Args:
        count: Total number of log entries to generate
        run_id: Pipeline run ID to tag the logs with
        spread_minutes: Spread logs over the past N minutes

    Returns:
        Stats dict with per-source counts and total
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    now = datetime.now(timezone.utc)
    per_source: dict[str, int] = {}
    raw_log_ids: list[str] = []

    services = list(SERVICE_GENERATORS.keys())

    async with async_session() as session:
        for i in range(count):
            # Pick service (round-robin with randomisation)
            service_key = services[i % len(services)]
            if random.random() < 0.3:
                service_key = random.choice(services)

            _, generator_fn = SERVICE_GENERATORS[service_key]

            # Random timestamp spread over past N minutes
            offset_seconds = random.randint(0, spread_minutes * 60)
            ts = now - timedelta(seconds=offset_seconds)

            # Pick scenario — weight towards errors for interesting pipeline output
            scenario = random.choice(SCENARIOS)

            payload = generator_fn(scenario, ts)
            payload["scenario"] = scenario
            payload["synthetic"] = True

            message = payload.get("message", f"Synthetic {scenario} log from {service_key}")

            raw_log = RawLog(
                id=str(uuid.uuid4()),
                ingested_at=datetime.utcnow(),
                source_system=service_key,
                raw_payload=payload,
                raw_text=str(message)[:5000],
                is_preprocessed=False,
                pipeline_run_id=run_id,
            )
            session.add(raw_log)
            raw_log_ids.append(raw_log.id)
            per_source[service_key] = per_source.get(service_key, 0) + 1

        await session.commit()

    total = len(raw_log_ids)
    logger.info(
        f"Synthetic Log Generator: Injected {total} logs — "
        + ", ".join(f"{k}: {v}" for k, v in per_source.items())
    )

    return {
        "total_injected": total,
        "per_source": per_source,
        "raw_log_ids": raw_log_ids,
        "run_id": run_id,
    }


async def generate_continuous(
    duration_minutes: int = 2,
    logs_per_minute: int = 20,
) -> dict[str, Any]:
    """
    Continuously generate logs for duration_minutes at logs_per_minute rate.
    Useful for stress-testing the pipeline.
    """
    total_injected = 0
    iterations = duration_minutes
    per_source_total: dict[str, int] = {}

    for _ in range(iterations):
        result = await generate_and_inject_logs(count=logs_per_minute)
        total_injected += result["total_injected"]
        for k, v in result["per_source"].items():
            per_source_total[k] = per_source_total.get(k, 0) + v
        await asyncio.sleep(60)

    return {
        "total_injected": total_injected,
        "per_source": per_source_total,
        "duration_minutes": duration_minutes,
    }
