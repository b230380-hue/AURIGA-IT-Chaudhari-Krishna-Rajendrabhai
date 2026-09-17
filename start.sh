#!/bin/bash
# PharmaFlow dual-runner script
trap 'kill $(jobs -p)' EXIT

echo "Starting PharmaFlow Backend on http://localhost:8000 ..."
cd backend
source .venv/bin/activate || source .venv/Scripts/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

echo "Starting PharmaFlow Frontend on http://localhost:5173 ..."
cd frontend
npm run dev -- --host &
FRONTEND_PID=$!
cd ..

echo "PharmaFlow is running! Press Ctrl+C to stop."
wait
