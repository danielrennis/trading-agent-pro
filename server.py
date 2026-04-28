from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import threading
import signal
import sys
from orchestrator import Orchestrator

app = Flask(__name__)
CORS(app)

# Rutas de archivos
CONFIG_FILE = "config.json"
STATE_FILE = "state.json"
PANEL_DIR = "panel"

# Instancia global del orquestador
bot_thread = None
orchestrator_instance = None

def run_bot():
    global orchestrator_instance
    orchestrator_instance = Orchestrator()
    orchestrator_instance.run()

@app.route('/')
def index():
    return send_from_directory(PANEL_DIR, 'index.html')

@app.route('/api/status')
def get_status():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({"error": "State not found"})

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        new_config = request.json
        with open(CONFIG_FILE, 'w') as f:
            json.dump(new_config, f, indent=4)
        return jsonify({"status": "success"})
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return jsonify(json.load(f))
    return jsonify({"error": "Config not found"})

@app.route('/api/restart', methods=['POST'])
def restart_bot():
    os._exit(0)
    return jsonify({"status": "restarting"})

@app.route('/api/cancel_sl', methods=['POST'])
def cancel_sl():
    symbol = request.args.get('symbol')
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        
        if symbol in state.get("positions", {}):
            state["positions"][symbol]["pending_sl"] = False
            if "sl_countdown" in state["positions"][symbol]:
                del state["positions"][symbol]["sl_countdown"]
            
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=4)
            return jsonify({"status": "cancelled"})
    return jsonify({"status": "error", "message": "Symbol not found"})

def start_background_bot():
    global bot_thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    start_background_bot()
    
    # Cambiado a 5001 para evitar conflictos con AirPlay en macOS
    port = int(os.environ.get("PORT", 5001))
    print(f"🚀 Panel disponible en: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port)
