@echo off
echo Starting PharmaFlow...
start "PharmaFlow Backend" cmd /k "cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"
start "PharmaFlow Frontend" cmd /k "cd frontend && npm run dev"
echo Both services started!
