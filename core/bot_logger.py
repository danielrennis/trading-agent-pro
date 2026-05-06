import logging
import os
from datetime import datetime

# Configuración de log de actividad del BOT
LOG_FILE = "bot_activity.log"

def log_bot(category, message, level="INFO"):
    """Registra actividad interna del bot (decisiones, sincronización, etc.)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] [{category}] {message}\n"
    
    with open(LOG_FILE, "a") as f:
        f.write(log_entry)
    
    # También imprimir a consola para que se vea en orchestrator.log
    print(f"🤖 [{category}] {message}", flush=True)

def log_trade(symbol, action, qty, price, reason=""):
    """Log específico para operaciones de trading."""
    msg = f"{action.upper()} {symbol} x {qty} @ ${price:,.2f}"
    if reason:
        msg += f" | Razón: {reason}"
    log_bot("TRADING", msg)

def log_sync(message):
    """Log para eventos de sincronización."""
    log_bot("SYNC", message)
