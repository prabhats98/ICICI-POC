"""
Continuous Traffic Generator — runs as a background process on Azure App Service.
Sends realistic mixed-traffic requests to the banking API via Azure Front Door URL
every 15 seconds to generate a continuous stream of real diagnostic logs.
"""

import asyncio
import random
import logging
import os
import signal
import sys
from datetime import datetime

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("traffic-gen")

# --- Configuration -------------------------------------------------------
# Set via App Service environment variable after Front Door is deployed
AFD_URL = os.getenv("TRAFFIC_TARGET_URL", "http://localhost:8080")
REQUESTS_PER_MINUTE = int(os.getenv("REQUESTS_PER_MINUTE", "4"))  # 1 every 15s
INTERVAL_SECONDS = 60 / REQUESTS_PER_MINUTE

# Endpoint weights: (path, method, weight, body)
ENDPOINTS = [
    # High-frequency healthy traffic
    ("/", "GET", 10, None),
    ("/health", "GET", 8, None),
    ("/api/accounts", "GET", 12, None),
    ("/api/accounts/ACC001", "GET", 6, None),
    ("/api/accounts/ACC002", "GET", 4, None),
    ("/api/accounts/INVALID999", "GET", 3, None),  # 404
    ("/api/transactions", "GET", 10, None),
    ("/api/payments/history", "GET", 6, None),

    # Auth (25% chance of 401 in handler)
    ("/api/auth/login", "POST", 8, {"username": "user@bank.com", "password": "pass"}),
    ("/api/auth/token/refresh", "GET", 4, None),  # No auth header → 401

    # Transfers (10% 500, 15% 400)
    ("/api/transfer", "POST", 7, {"from": "ACC001", "to": "ACC002", "amount": 5000}),
    ("/api/payments/process", "POST", 6, {"amount": 1500, "card": "4xxx"}),

    # Reports (slow, 2-5s — triggers latency)
    ("/api/reports/monthly", "GET", 3, None),
    ("/api/reports/risk", "GET", 3, None),   # 20% 503

    # Admin — always 403 (WAF simulation)
    ("/api/admin", "GET", 2, None),
    ("/api/admin/reset", "DELETE", 1, None),

    # 404s
    ("/api/nonexistent", "GET", 2, None),
    ("/api/users/9999", "GET", 2, None),
    ("/favicon.ico", "GET", 1, None),
]

PATHS = [e[0] for e in ENDPOINTS]
METHODS = [e[1] for e in ENDPOINTS]
WEIGHTS = [e[2] for e in ENDPOINTS]
BODIES = [e[3] for e in ENDPOINTS]


running = True


def handle_shutdown(sig, frame):
    global running
    logger.info("Shutting down traffic generator...")
    running = False


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)


async def send_request(client: httpx.AsyncClient, path: str, method: str, body: dict | None):
    """Send a single request and log the result."""
    try:
        url = f"{AFD_URL}{path}"
        kwargs = {"timeout": 30.0}
        if body:
            kwargs["json"] = body

        if method == "GET":
            resp = await client.get(url, **kwargs)
        elif method == "POST":
            resp = await client.post(url, **kwargs)
        elif method == "DELETE":
            resp = await client.delete(url, **kwargs)
        else:
            resp = await client.get(url, **kwargs)

        level = "INFO"
        if resp.status_code >= 500:
            level = "ERROR"
        elif resp.status_code >= 400:
            level = "WARNING"

        logger.log(
            getattr(logging, level),
            f"{method} {path} → {resp.status_code} ({resp.elapsed.total_seconds() * 1000:.0f}ms)"
        )
        return resp.status_code

    except Exception as e:
        logger.error(f"{method} {path} → FAILED: {e}")
        return 0


async def run_traffic_loop():
    """Main traffic generation loop."""
    logger.info(f"Traffic generator started → {AFD_URL} @ {REQUESTS_PER_MINUTE} req/min")

    stats = {"total": 0, "2xx": 0, "4xx": 0, "5xx": 0, "errors": 0}

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={
            "User-Agent": "BankingLogAnalyser/1.0 TrafficGen",
            "X-Source": "traffic-generator",
        },
    ) as client:
        while running:
            # Pick a weighted random endpoint
            idx = random.choices(range(len(ENDPOINTS)), weights=WEIGHTS, k=1)[0]
            path, method, _, body = ENDPOINTS[idx]

            # Send request
            status = await send_request(client, path, method, body)

            # Update stats
            stats["total"] += 1
            if 200 <= status < 300:
                stats["2xx"] += 1
            elif 400 <= status < 500:
                stats["4xx"] += 1
            elif status >= 500:
                stats["5xx"] += 1
            else:
                stats["errors"] += 1

            # Log summary every 20 requests
            if stats["total"] % 20 == 0:
                logger.info(
                    f"Stats: total={stats['total']} | "
                    f"2xx={stats['2xx']} | 4xx={stats['4xx']} | "
                    f"5xx={stats['5xx']} | errors={stats['errors']}"
                )

            await asyncio.sleep(INTERVAL_SECONDS)

    logger.info(f"Traffic generator stopped. Final stats: {stats}")


if __name__ == "__main__":
    asyncio.run(run_traffic_loop())
