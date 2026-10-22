#!/usr/bin/env bash
set -euo pipefail
mkdir -p outputs
if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
  exit 0
fi
nohup python -m uvicorn webapp:app --host 0.0.0.0 --port 8000 > outputs/server.log 2>&1 < /dev/null &
echo "Monitor STS iniciando na porta 8000. Abra a aba Ports do Codespaces."
