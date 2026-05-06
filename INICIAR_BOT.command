#!/bin/bash

# ==========================================
# 🛸 TRADING BOT AGENT PRO - ACTIVADOR
# ==========================================

# Navegar al directorio donde está el script
CDIR="$(dirname "$0")"
cd "$CDIR"

# Configurar logs
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
SERVER_LOG="$LOG_DIR/web_server.log"
ORCH_LOG="$LOG_DIR/orchestrator.log"

echo "------------------------------------------"
echo "🚀 INICIANDO SISTEMA DE TRADING"
echo "------------------------------------------"
echo "📍 Directorio: $CDIR"

# 1. Limpieza de procesos previos
echo "🧹 Limpiando procesos antiguos..."
pkill -f orchestrator.py
pkill -f web_server.py
sleep 2

# 2. Verificar Entorno Virtual
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

echo "🔌 Activando entorno..."
source venv/bin/activate

# 3. Verificar dependencias (rápido)
echo "🔍 Verificando dependencias..."
pip install -q -r requirements.txt

# 4. Iniciar el Servidor Web (que a su vez inicia el orquestador)
echo "🔥 Levantando Servidor Web..."
nohup python3 web_server.py > "$SERVER_LOG" 2>&1 &

# Dar un momento para que el servidor levante y lance el orquestador
sleep 3

# 5. Mantener la Mac despierta
echo "☕ Evitando que la Mac entre en reposo..."
# Mata procesos previos de caffeinate de este bot
pkill -f "caffeinate -i -t 28800"
nohup caffeinate -i -t 28800 > /dev/null 2>&1 & 

echo "------------------------------------------"
echo "✅ BOT OPERANDO EN SEGUNDO PLANO"
echo "🔗 URL PANEL: http://localhost:3000"
echo "📝 Logs en: $LOG_DIR/"
echo "------------------------------------------"

# Notificación visual en macOS
osascript -e 'display notification "Trading Bot Activado 🚀" with title "Trading Agent Pro"'

# Cerrar terminal después de 5 segundos
echo "Cerrando ventana en 5s..."
sleep 5
osascript -e 'tell application "Terminal" to close first window' & exit
