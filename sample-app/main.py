"""
Banking Sample API — Lightweight Azure App Service application
that generates realistic mixed traffic for log analytics demo.

Endpoints produce a realistic mix of 200/400/401/403/404/500 responses
to drive meaningful logs in Front Door, App Gateway, and APIM.
"""

import asyncio
import random
import time
import uuid
import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("banking-api")

app = FastAPI(
    title="Banking Sample API",
    description="Sample banking API for Azure log analytics demonstration",
    version="1.0.0",
)


# ── Middleware: log every request ─────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    request_id = str(uuid.uuid4())[:8]
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000)
    logger.info(
        f"[{request_id}] {request.method} {request.url.path} "
        f"→ {response.status_code} ({duration_ms}ms) "
        f"client={request.client.host if request.client else 'unknown'}"
    )
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Response-Time"] = f"{duration_ms}ms"
    return response


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
async def root():
    return {
        "service": "Banking Sample API",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ── Accounts ──────────────────────────────────────────────────────────────────

ACCOUNTS = [
    {"id": "ACC001", "name": "Prabhat Singh", "balance": 125000.50, "type": "savings"},
    {"id": "ACC002", "name": "Krelixir Corp", "balance": 4500000.00, "type": "current"},
    {"id": "ACC003", "name": "ICICI Holdings", "balance": 987654.32, "type": "savings"},
]


@app.get("/api/accounts", tags=["accounts"])
async def get_accounts():
    # Occasional slow response to trigger latency warnings
    if random.random() < 0.05:
        await asyncio.sleep(random.uniform(3, 6))
    return {"accounts": ACCOUNTS, "total": len(ACCOUNTS), "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/accounts/{account_id}", tags=["accounts"])
async def get_account(account_id: str):
    account = next((a for a in ACCOUNTS if a["id"] == account_id), None)
    if not account:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return account


# ── Transactions ──────────────────────────────────────────────────────────────

@app.get("/api/transactions", tags=["transactions"])
async def get_transactions():
    transactions = [
        {
            "id": f"TXN{random.randint(10000, 99999)}",
            "from": "ACC001",
            "to": "ACC002",
            "amount": round(random.uniform(100, 50000), 2),
            "type": random.choice(["debit", "credit", "transfer"]),
            "status": random.choice(["completed", "pending", "failed"]),
            "timestamp": datetime.utcnow().isoformat(),
        }
        for _ in range(random.randint(5, 15))
    ]
    return {"transactions": transactions, "count": len(transactions)}


@app.post("/api/transfer", tags=["transactions"])
async def transfer_funds(request: Request):
    """Simulates fund transfer — randomly fails to generate error logs."""
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}

    # 10% chance of backend error (500) — triggers pipeline alert
    if random.random() < 0.10:
        logger.error("Transfer failed: database connection timeout")
        raise HTTPException(status_code=500, detail="Database connection timeout during transfer")

    # 15% chance of validation error (400)
    if random.random() < 0.15:
        raise HTTPException(status_code=400, detail="Insufficient funds or invalid account")

    await asyncio.sleep(random.uniform(0.1, 0.5))
    return {
        "transaction_id": f"TXN{random.randint(100000, 999999)}",
        "status": "completed",
        "amount": body.get("amount", 1000),
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Authentication ────────────────────────────────────────────────────────────

@app.post("/api/auth/login", tags=["auth"])
async def login(request: Request):
    """Auth endpoint — 25% chance of failure to generate security logs."""
    if random.random() < 0.25:
        logger.warning("Authentication failed: invalid credentials attempt")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {
        "token": f"eyJ{uuid.uuid4().hex}",
        "expires_in": 3600,
        "user_id": "USER001",
    }


@app.get("/api/auth/token/refresh", tags=["auth"])
async def refresh_token(authorization: str = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    return {"token": f"eyJ{uuid.uuid4().hex}", "expires_in": 3600}


# ── Reports (heavy endpoint) ───────────────────────────────────────────────────

@app.get("/api/reports/monthly", tags=["reports"])
async def monthly_report():
    """Heavy endpoint — always slow, triggers latency alerts."""
    await asyncio.sleep(random.uniform(2, 5))
    return {
        "report_id": str(uuid.uuid4()),
        "period": "2026-06",
        "total_transactions": random.randint(10000, 50000),
        "total_volume": round(random.uniform(1000000, 10000000), 2),
        "generated_at": datetime.utcnow().isoformat(),
    }


@app.get("/api/reports/risk", tags=["reports"])
async def risk_report():
    """Risk report — occasionally fails."""
    await asyncio.sleep(random.uniform(1, 3))
    if random.random() < 0.20:
        raise HTTPException(status_code=503, detail="Risk engine temporarily unavailable")
    return {
        "risk_score": random.randint(1, 100),
        "flags": random.randint(0, 5),
        "generated_at": datetime.utcnow().isoformat(),
    }


# ── Admin (blocked by WAF policy) ────────────────────────────────────────────

@app.get("/api/admin", tags=["admin"])
async def admin_panel():
    """Admin endpoint — always 403, simulates WAF block."""
    logger.warning("Unauthorized admin access attempt blocked")
    raise HTTPException(status_code=403, detail="Access denied: insufficient privileges")


@app.delete("/api/admin/reset", tags=["admin"])
async def admin_reset():
    raise HTTPException(status_code=403, detail="Access denied: dangerous operation blocked")


# ── Payments ──────────────────────────────────────────────────────────────────

@app.post("/api/payments/process", tags=["payments"])
async def process_payment(request: Request):
    if random.random() < 0.08:
        raise HTTPException(status_code=500, detail="Payment gateway timeout")
    if random.random() < 0.12:
        raise HTTPException(status_code=402, detail="Payment declined: card limit exceeded")
    await asyncio.sleep(random.uniform(0.2, 1.0))
    return {
        "payment_id": f"PAY{uuid.uuid4().hex[:8].upper()}",
        "status": "approved",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/payments/history", tags=["payments"])
async def payment_history():
    return {
        "payments": [
            {"id": f"PAY{i:05d}", "amount": round(random.uniform(100, 5000), 2), "status": "completed"}
            for i in range(random.randint(3, 10))
        ]
    }


# ── Catch-all 404 ─────────────────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "path": str(request.url.path)},
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, log_level="info")
