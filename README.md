# Azure Incident Log Pipeline

Multi-agent AI system for analyzing Azure cloud infrastructure logs in banking environments.

## Architecture

```
Azure Front Door → App Gateway → API Management → Logs →
                                                        ↓
                                              Azure Virtual Machine
                                                ┌─────────────────┐
                                                │  6-hour Scheduler │
                                                │                   │
                                                │  8-Agent Pipeline │
                                                │  ┌──────────────┐│
                                                │  │Log Collector  ││
                                                │  │Preprocessing  ││
                                                │  │Classification ││
                                                │  │Priority (P1-3)││
                                                │  │Context Lookup ││
                                                │  │Resolution     ││
                                                │  │Orchestrator   ││
                                                │  │Notification   ││
                                                │  └──────────────┘│
                                                │                   │
                                                │  React Dashboard  │
                                                │  FastAPI Backend  │
                                                └─────────────────┘
                                                        ↓
                                              Azure PostgreSQL
                                              Email (SMTP / ACS)
```

## Quick Start

### 1. Configure

```bash
cd backend
cp .env.example .env
# Fill in your Azure credentials, PostgreSQL connection, and Gemini API key
```

### 2. Run Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### 3. Deploy to Azure VM

```bash
docker compose up -d
```

## .env Configuration

All configuration is in `backend/.env`. Key settings:

| Setting | Description |
|---------|-------------|
| `DATABASE_URL` | Azure PostgreSQL connection string |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription for log collection |
| `AZURE_TENANT_ID` / `CLIENT_ID` / `CLIENT_SECRET` | Azure AD app registration |
| `AZURE_FRONTDOOR_RESOURCE_ID` | Front Door resource ID |
| `AZURE_APPGATEWAY_RESOURCE_ID` | Application Gateway resource ID |
| `AZURE_APIM_RESOURCE_ID` | API Management resource ID |
| `AZURE_LOG_ANALYTICS_WORKSPACE_ID` | Log Analytics workspace |
| `GCP_PROJECT_ID` | Google Cloud project for Gemini |
| `SCHEDULER_INTERVAL_HOURS` | Pipeline run interval (default: 6) |
| `PIPELINE_ENABLED` | Master on/off switch |
| `NOTIFICATION_CHANNEL` | `smtp` or `azure_communication_service` |

## Agent Pipeline

| # | Agent | Role |
|---|-------|------|
| 1 | **Log Collector** | Pulls logs from Azure Monitor (Front Door, App Gateway, APIM, VM) |
| 2 | **Preprocessing Engine** | Cleans, deduplicates, normalizes timestamps, extracts fields |
| 3 | **Classification Agent** | Uses Gemini to detect incident type, intent, and severity |
| 4 | **Priority Agent** | Assigns P1 (critical) / P2 (warning) / P3 (info) |
| 5 | **Context Agent** | Queries PostgreSQL for similar past incidents and fixes |
| 6 | **Resolution Agent** | Generates AI-powered fix recommendations and runbooks |
| 7 | **Orchestrator Agent** | Coordinates outputs, aggregates summary, routes notifications |
| 8 | **Notification Agent** | Sends email alerts (P1 immediate, P2 digest, P3 dashboard only) |

## Dashboard Features

- **Top cards**: Total incidents, open, P1/P2/P3 counts, resolved, avg resolution time
- **Pipeline on/off toggle**: Enable or disable the 6-hour scheduler
- **Manual run button**: Trigger pipeline on demand
- **Live incident table**: Service, severity, status, recommended fix
- **Run history**: Trigger type, logs processed, P1/P2/P3 counts, duration
- **Incident detail panel**: Classification, priority justification, historical context, resolution, runbook

## Tech Stack

- **Backend**: FastAPI, LangGraph, SQLAlchemy, APScheduler
- **AI**: Gemini 2.5 Flash (Vertex AI)
- **Database**: Azure Database for PostgreSQL
- **Frontend**: React, Zustand, React Flow
- **Deployment**: Docker Compose, Nginx, Azure VM
