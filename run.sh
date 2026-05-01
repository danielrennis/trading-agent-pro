#!/bin/bash
# Script de arranque rápido para macOS
cd "$(dirname "$0")"

if [ -d "venv" ]; then
    echo "📦 Activando entorno virtual..."
    source venv/bin/activate
fi

echo "🚀 Iniciando Trading Bot..."
python3 main.py
