import logging
import os
from datetime import datetime

# Configuración de log de actividad API
LOG_FILE = "api_activity.log"

def log_api_call(action, symbol, qty, price, plazo, response):
    """Registra una llamada a la API de IOL con detalles completos."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Determinar si fue exitosa
    status = "SUCCESS"
    order_id = "N/A"
    if isinstance(response, dict):
        if "numeroOperacion" in response:
            order_id = response["numeroOperacion"]
        elif "error" in response or "message" in response:
            status = "ERROR"
    elif response is None:
        status = "FAILED (No response)"
        
    log_entry = (
        f"[{timestamp}] [{status}] {action.upper()} | "
        f"Symbol: {symbol: <6} | Qty: {qty: <6} | Price: {price: <10} | "
        f"Plazo: {plazo} | ID: {order_id} | Response: {response}\n"
    )
    
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)

def log_generic(message):
    """Registra un mensaje genérico en el log de actividad."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] [INFO] {message}\n")
