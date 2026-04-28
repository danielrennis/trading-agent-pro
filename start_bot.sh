#!/bin/bash
# Actualizado para el usuario correcto y rutas locales
export PATH="/Users/hugodanielrennis/Desktop/Inversion/trading-agent/venv/bin:$PATH"
cd /Users/hugodanielrennis/Desktop/Inversion/trading-agent
nohup python3 web_server.py > web_server.log 2>&1 &
nohup python3 orchestrator.py > orchestrator.log 2>&1 &
echo "Bot started in background."
