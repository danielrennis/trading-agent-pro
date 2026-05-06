#!/bin/bash

# ==========================================
# 🛑 TRADING BOT AGENT PRO - DESACTIVADOR
# ==========================================

# Navegar al directorio donde está el script
cd "$(dirname "$0")"

echo "------------------------------------------"
echo "🛑 DETENIENDO SISTEMA DE TRADING"
echo "------------------------------------------"

# 1. Matar procesos específicos del bot
echo "⏳ Apagando orquestador..."
pkill -f orchestrator.py

echo "⏳ Apagando servidor web..."
pkill -f web_server.py

echo "⏳ Deteniendo caffeinate..."
pkill -f "caffeinate -i -t 28800"

echo "------------------------------------------"
echo "✅ Bot detenido y procesos cerrados."

# Notificación visual en macOS
osascript -e 'display notification "Trading Bot Detenido 🛑" with title "Trading Agent Pro"'

echo "Cerrando ventana en 3s..."
sleep 3
osascript -e 'tell application "Terminal" to close first window' & exit
