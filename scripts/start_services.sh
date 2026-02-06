#!/bin/bash
# Start API, Dashboard and Nginx reverse proxy for Azure deployment
# Nginx listens on port 80, routes to API (8000) and Dashboard (8501)

set -e

echo "Starting AvatarFactory services..."

# Start API service in background
echo "Starting API on port 8000..."
python -m avatarfactory.daemon_runner --mode full --host 127.0.0.1 --port 8000 &
API_PID=$!

# Wait for API to be ready
sleep 5
curl -sf http://127.0.0.1:8000/health && echo " API healthy" || echo " API starting..."

# Start Dashboard (Streamlit) in background
echo "Starting Dashboard on port 8501..."
streamlit run avatarfactory/dashboard/Dashboard.py \
    --server.port 8501 \
    --server.address 127.0.0.1 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --browser.gatherUsageStats false &
DASHBOARD_PID=$!

# Wait for Dashboard to be ready
sleep 3

# Start Nginx reverse proxy in foreground
echo "Starting Nginx reverse proxy on port 80..."
exec nginx -c /app/scripts/nginx.conf -g "daemon off;"
