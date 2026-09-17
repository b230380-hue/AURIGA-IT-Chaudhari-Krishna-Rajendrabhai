#!/bin/bash
set -e

echo "=== Setting up PharmaFlow in Codespaces ==="

# Backend setup
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python3 -m app.seed
cd ..

# Frontend setup
cd frontend
npm install
cd ..

echo "=== PharmaFlow setup complete! ==="
echo "To run backend: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000"
echo "To run frontend: cd frontend && npm run dev"
