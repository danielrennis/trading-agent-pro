from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
import json
import os
import subprocess
import signal
from core.iol_client import IOLClient

app = FastAPI()

STATE_FILE = "state.json"
CONFIG_FILE = "config.json"
ORCHESTRATOR_PROC = None

@app.on_event("startup")
async def startup_event():
    # Optional: Start orchestrator automatically
    # restart_orchestrator()
    pass

def restart_orchestrator():
    global ORCHESTRATOR_PROC
    # Kill existing if any
    if ORCHESTRATOR_PROC:
        try:
            os.kill(ORCHESTRATOR_PROC.pid, signal.SIGTERM)
        except:
            pass
    
    # Run orchestrator as a background process
    # We use the same python interpreter
    import sys
    cmd = [sys.executable, "orchestrator.py"]
    ORCHESTRATOR_PROC = subprocess.Popen(cmd)
    return True

@app.post("/api/restart")
async def api_restart():
    success = restart_orchestrator()
    if success:
        return {"status": "success", "message": "Orquestador reiniciado con éxito."}
    return {"status": "error", "message": "Error al reiniciar."}

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("panel/index.html", "r") as f:
        return f.read()

@app.get("/api/status")
async def get_status():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"positions": {}, "opportunities": {}, "history": [], "balance": 0}

@app.get("/api/config")
async def get_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"strategy": {"initial_sl_pct": 0.99, "initial_tp_pct": 1.015, "trailing_sl_pct": 0.988, "trailing_tp_pct": 1.01, "risk_balance_pct": 0.1, "min_buy_score": 8.0}, "watchlist": []}

@app.post("/api/config")
async def update_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
    return {"status": "success"}

@app.post("/api/rotate")
async def rotate_position(current_symbol: str, target_symbol: str):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        
        if current_symbol in state["positions"]:
            # 1. Simular Venta
            pos = state["positions"][current_symbol]
            current_price = pos.get('current_price', pos['entry_price']) # Fallback if not updated
            
            # Log to history
            if "history" not in state: state["history"] = []
            profit_pct = ((current_price / pos['entry_price']) - 1) * 100
            is_bond_or_on = (len(current_symbol) == 5 and current_symbol.startswith(('AL', 'GD', 'TL', 'BA', 'MR')))
            multiplier = pos.get('multiplier', 0.01 if is_bond_or_on else 1)
            profit_amount = (current_price - pos['entry_price']) * pos['qty'] * multiplier
            from datetime import datetime
            
            state["history"].append({
                "symbol": current_symbol,
                "type": "SELL (Rotation)",
                "entry_price": pos['entry_price'],
                "exit_price": current_price,
                "qty": pos['qty'],
                "profit_pct": profit_pct,
                "profit_amount": profit_amount,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            from core.iol_client import IOLClient
            iol = IOLClient()
            iol.login()
            
            # 1. EVALUAR PLAZO ÓPTIMO (Priorizar t0, fallback a t2)
            plazo_optimo = "t2"
            sell_price = current_price
            
            # Intentar t0
            quote_t0_target = iol.get_quote(target_symbol, plazo="t0")
            quote_t0_current = iol.get_quote(current_symbol, plazo="t0")
            
            if quote_t0_target and quote_t0_current:
                liq_venta = sum([p.get("cantidadVenta", 0) for p in quote_t0_target.get("puntas", [])])
                liq_compra = sum([p.get("cantidadCompra", 0) for p in quote_t0_current.get("puntas", [])])
                
                # Si hay liquidez en t0 para vender lo nuestro y para comprar algo del target
                if liq_venta > 0 and liq_compra >= pos['qty']:
                    plazo_optimo = "t0"
                    sell_price = quote_t0_current.get('ultimoPrecio', current_price)
            
            # Obtener el precio final del target según el plazo elegido
            quote_target = quote_t0_target if plazo_optimo == "t0" else iol.get_quote(target_symbol, plazo="t2")
            if not quote_target or not quote_target.get('ultimoPrecio'):
                return {"status": "error", "message": f"No se pudo obtener cotización de {target_symbol} en {plazo_optimo}."}
                
            entry_price = quote_target['ultimoPrecio']
            amount_invested = sell_price * pos['qty']
            new_qty = int(amount_invested / entry_price)
            
            if new_qty == 0:
                return {"status": "error", "message": "Monto insuficiente para comprar 1 unidad del nuevo activo."}
            
            # 2. INTENTO DE VENTA
            res_sell = iol.place_order(current_symbol, pos['qty'], sell_price, action="vender", validity=plazo_optimo)
            if isinstance(res_sell, list) or not isinstance(res_sell, dict) or "numeroOperacion" not in res_sell:
                return {"status": "error", "message": f"IOL rechazó la venta de {current_symbol} en {plazo_optimo}. Rotación cancelada."}
            
            del state["positions"][current_symbol]
            
            # 3. COMPRA DEL TARGET
            res_buy = iol.place_order(target_symbol, new_qty, entry_price, action="comprar", validity=plazo_optimo)
            if isinstance(res_buy, dict) and "numeroOperacion" in res_buy:
                # Cargar config para SL/TP dinámicos
                config = {}
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r") as cf:
                        config = json.load(cf)
                initial_sl_pct = config.get("strategy", {}).get("initial_sl_pct", 0.99)
                initial_tp_pct = config.get("strategy", {}).get("initial_tp_pct", 1.021)
                
                state["positions"][target_symbol] = {
                    "entry_price": entry_price,
                    "qty": new_qty,
                    "sl": entry_price * initial_sl_pct,
                    "tp": entry_price * initial_tp_pct,
                    "step": 0,
                    "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                msg = f"Rotación exitosa en {plazo_optimo.upper()}: {current_symbol} -> {target_symbol}"
            else:
                msg = f"Venta OK en {plazo_optimo.upper()}, pero falló la compra de {target_symbol}. Saldo libre."
            
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=4)
            
            return {"status": "success" if "Rotación exitosa" in msg else "warning", "message": msg}
    
    return {"status": "error", "message": "No se pudo realizar la rotación."}

@app.post("/api/update_sl_tp")
async def update_sl_tp(symbol: str, sl: float, tp: float):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        if symbol in state["positions"]:
            state["positions"][symbol]["sl"] = sl
            state["positions"][symbol]["tp"] = tp
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=4)
            return {"status": "success"}
    return {"status": "error", "message": "Symbol not found"}

@app.post("/api/cancel_sl")
async def cancel_sl(symbol: str):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        if symbol in state["positions"]:
            # Quitamos el flag de pendiente
            if "pending_sl" in state["positions"][symbol]:
                del state["positions"][symbol]["pending_sl"]
            
            # Bajamos el SL un 0.5% extra para dar aire y que no triggeree al instante de nuevo
            state["positions"][symbol]["sl"] *= 0.995
            
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=4)
            return {"status": "success", "message": "Venta cancelada. SL ajustado -0.5%."}
    return {"status": "error", "message": "Símbolo no encontrado."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)