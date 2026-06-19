# Banking Cloud Log Analyser

Multi-agent AI system for monitoring and analyzing Azure cloud logs in banking infrastructure. Powered by **Gemini 2.5 Flash** via Vertex AI, orchestrated with **LangGraph**, served by **FastAPI**, and visualized with **React + React Flow**.

## Architecture

```
Frontend (React + Vite)  ←→  Backend (FastAPI)  ←→  PostgreSQL
                                    ↓
                            LangGraph Pipeline
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
              Agent 1          Agent 2          Agent 3
           Log Extractor   Anomaly Detector  Priority Classifier
                                                    ↓
                                    ┌───────────────┼───────────────┐
                                    ↓               ↓               ↓
                              Agent 4a         Agent 4b         Agent 4c
                           HIGH Priority    MEDIUM Priority    LOW Priority
                           Email + Fix      Auto-Solution      Log & Monitor
```

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- GCP Service Account with Vertex AI access

### 1. Database Setup
```bash
# Start PostgreSQL (or use Docker)
docker compose up db -d

# Or create the database manually
createdb banking_log_analyser
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Seed test data
python -m app.seed_data

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

### 4. Open the app
- **Frontend**: http://localhost:5173
- **Backend API Docs**: http://localhost:8000/docs

## Agent Pipeline

| Agent | Role | LLM? |
|-------|------|------|
| **Agent 1: Log Extractor** | Extracts unprocessed logs from PostgreSQL | No |
| **Agent 2: Anomaly Detector** | Analyzes logs for anomalies using Gemini | ✅ |
| **Agent 3: Priority Classifier** | Classifies issues as HIGH/MEDIUM/LOW | ✅ |
| **Agent 4a: High Priority** | Sends email with solution to prod manager | ✅ |
| **Agent 4b: Medium Priority** | Generates solution (visible in dashboard) | ✅ |
| **Agent 4c: Low Priority** | Logs for monitoring (no action needed) | No |

## Configuration

All settings are in `backend/.env`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCP_LOCATION` | Vertex AI region |
| `GEMINI_MODEL` | Gemini model name |
| `SMTP_*` | Email server configuration |
| `SCHEDULER_INTERVAL_MINUTES` | How often the pipeline runs |

## Tech Stack

- **Frontend**: React 19, Vite, React Flow, Zustand, Axios
- **Backend**: FastAPI, SQLAlchemy, LangGraph, APScheduler
- **AI**: Gemini 2.5 Flash (Vertex AI)
- **Database**: PostgreSQL
- **Real-time**: WebSocket
