#!/bin/bash
# startup.sh — Azure App Service startup script (Linux Python 3.11)
set -e

echo "=== Banking Sample API Startup ==="
echo "PORT=${PORT:-8080}"

# Install dependencies if not already done by Oryx
if [ -f requirements.txt ]; then
    pip install -r requirements.txt --quiet
fi

# Start the main API using Azure-provided PORT
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
