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
    print("🚀 Iniciando orquestador de trading en segundo plano...")
    restart_orchestrator()
    print("✅ Orquestador iniciado correctamente.")

def restart_orchestrator():
    global ORCHESTRATOR_PROC
    
    # 1. Intentar apagado suave del proceso conocido
    if ORCHESTRATOR_PROC:
        try:
            os.kill(ORCHESTRATOR_PROC.pid, signal.SIGTERM)
            import time
            time.sleep(1.0) # Dar tiempo para consolidar info y guardar state.json
        except:
            pass

    # 2. Limpieza de procesos huérfanos remanentes
    try:
        import subprocess
        subprocess.run(["pkill", "-f", "orchestrator.py"], capture_output=True)
    except:
        pass
    
    # 3. Iniciar nuevo orquestador
    import sys
    cmd = [sys.executable, "-u", "orchestrator.py"]
    log_file = open("orchestrator.log", "a")
    ORCHESTRATOR_PROC = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
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

import socket
@app.get("/api/status")
async def get_status():
    status = {"positions": {}, "opportunities": {}, "history": [], "balance": 0, "instance": {}}
    hostname = socket.gethostname().split('.')[0].upper().replace('-', ' ')
    my_id = os.getenv("INSTANCE_NAME", hostname)
    
    authorized_id = "UNKNOWN"
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                authorized_id = cfg.get("authorized_instance", "UNKNOWN")
        except: pass

    status["instance"] = {
        "current": my_id,
        "authorized": authorized_id,
        "is_authorized": my_id == authorized_id
    }
    
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                for k, v in state.items():
                    if k != "instance":
                        status[k] = v
        except: pass
    return status

@app.post("/api/authorize_me")
async def authorize_me():
    hostname = socket.gethostname().split('.')[0].upper().replace('-', ' ')
    my_id = os.getenv("INSTANCE_NAME", hostname)
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        config["authorized_instance"] = my_id
        
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
            
        restart_orchestrator()
        return {"status": "success", "message": f"Instancia '{my_id}' ahora tiene el control."}
    return {"status": "error", "message": "No se pudo actualizar la configuración."}

@app.get("/api/config")
async def get_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: pass
    return {"trading_mode": "normal", "strategy": {"initial_sl_pct": 0.99, "initial_tp_pct": 1.015, "trailing_sl_pct": 0.988, "trailing_tp_pct": 1.01, "risk_balance_pct": 0.1, "min_buy_score": 8.0}, "watchlist": []}

def stop_orchestrator():
    global ORCHESTRATOR_PROC
    if ORCHESTRATOR_PROC:
        try:
            os.kill(ORCHESTRATOR_PROC.pid, signal.SIGTERM)
            ORCHESTRATOR_PROC = None
        except: pass
    try:
        import subprocess
        subprocess.run(["pkill", "-f", "orchestrator.py"], capture_output=True)
    except: pass

@app.post("/api/config")
async def update_config(new_config: dict):
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    
    old_paused = config.get("trading_paused", False)
    
    # Merge strategy safely
    if "strategy" in new_config:
        if "strategy" not in config: config["strategy"] = {}
        config["strategy"].update(new_config["strategy"])
    
    # Merge other top-level fields
    for key, value in new_config.items():
        if key != "strategy":
            config[key] = value

    new_paused = config.get("trading_paused", False)
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
        
    # Reaccionar al cambio de pausa
    if old_paused != new_paused:
        if new_paused:
            stop_orchestrator()
        else:
            restart_orchestrator()
            
    return {"status": "success"}

@app.post("/api/pause")
async def pause_trading():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    config["trading_paused"] = True
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
    stop_orchestrator()
    return {"status": "success", "message": "Trading pausado y proceso detenido."}

@app.post("/api/take_control")
async def take_control():
    my_id = os.getenv("INSTANCE_NAME", "UNKNOWN")
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        config["authorized_instance"] = my_id
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        restart_orchestrator()
        return {"status": "success", "message": f"Control tomado por {my_id}"}
    return {"status": "error", "message": "Config not found"}

@app.post("/api/resume")
async def resume_trading():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    config["trading_paused"] = False
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)
    restart_orchestrator()
    return {"status": "success", "message": "Trading reanudado y proceso iniciado."}

@app.post("/api/rotate")
async def rotate_position(current_symbol: str, target_symbol: str):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        
        if current_symbol in state["positions"]:
            pos = state["positions"][current_symbol]
            current_price = pos.get('current_price', pos['entry_price'])
            
            if "history" not in state: state["history"] = []
            profit_pct = ((current_price / pos['entry_price']) - 1) * 100
            is_bond_or_on = (len(current_symbol) == 5 and current_symbol.startswith(('AL', 'GD', 'TL', 'BA', 'MR')))
            multiplier = pos.get('multiplier', 0.01 if is_bond_or_on else 1)
            profit_amount = (current_price - pos['entry_price']) * pos['qty'] * multiplier
            from datetime import datetime
            
            iol = IOLClient()
            iol.login()
            
            # 1. EVALUAR PLAZO CI (T0)
            quote_t0_target = iol.get_quote(target_symbol, plazo="t0")
            quote_t0_current = iol.get_quote(current_symbol, plazo="t0")
            
            if not quote_t0_target or not quote_t0_current:
                return {"status": "error", "message": "No hay cotización CI (T0) disponible. Rotación cancelada."}

            # Validar liquidez en T0
            book_target = iol.get_book(target_symbol, "t0")
            book_current = iol.get_book(current_symbol, "t0")
            
            if not book_target or not book_target.get('asks') or len(book_target['asks']) == 0:
                return {"status": "error", "message": f"Sin puntas de VENTA en CI para {target_symbol}."}
            if not book_current or not book_current.get('bids') or len(book_current['bids']) == 0:
                return {"status": "error", "message": f"Sin puntas de COMPRA en CI para {current_symbol}."}

            sell_price = quote_t0_current.get('ultimoPrecio', current_price)
            entry_price = quote_t0_target.get('ultimoPrecio')
            
            amount_invested = sell_price * pos['qty']
            new_qty = int(amount_invested / entry_price)
            
            if new_qty == 0:
                return {"status": "error", "message": "Monto insuficiente para comprar 1 unidad del nuevo activo."}
            
            # 2. EJECUTAR VENTA (CI)
            res_sell = iol.place_order(current_symbol, pos['qty'], sell_price, action="vender", validity="t0")
            if isinstance(res_sell, dict) and "numeroOperacion" in res_sell:
                # Registrar venta en historial
                state["history"].append({
                    "symbol": current_symbol, "type": "VENTA (Rotación)", "entry_price": pos['entry_price'],
                    "exit_price": sell_price, "qty": pos['qty'], "profit_pct": profit_pct,
                    "profit_amount": profit_amount, "steps": pos.get('step', 0),
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                del state["positions"][current_symbol]
                
                # 3. EJECUTAR COMPRA (CI)
                res_buy = iol.place_order(target_symbol, new_qty, entry_price, action="comprar", validity="t0")
                if isinstance(res_buy, dict) and "numeroOperacion" in res_buy:
                    with open(CONFIG_FILE, "r") as cf:
                        config = json.load(cf)
                    
                    state["positions"][target_symbol] = {
                        "entry_price": entry_price, "qty": new_qty, "step": 0,
                        "sl": entry_price * config.get("strategy", {}).get("initial_sl_pct", 0.99),
                        "tp": entry_price * config.get("strategy", {}).get("initial_tp_pct", 1.02),
                        "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    state["history"].append({
                        "symbol": target_symbol, "type": "COMPRA (Rotación)", "entry_price": entry_price,
                        "exit_price": 0, "qty": new_qty, "profit_pct": 0,
                        "profit_amount": 0, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    msg = f"Rotación CI exitosa: {current_symbol} -> {target_symbol}"
                else:
                    msg = f"Venta CI OK, pero falló compra de {target_symbol}. Saldo liberado."
            else:
                return {"status": "error", "message": f"IOL rechazó la venta CI de {current_symbol}."}
            
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=4)
            return {"status": "success" if "exitosa" in msg else "warning", "message": msg}
    
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

@app.post("/api/buy")
async def manual_buy(symbol: str):
    iol = IOLClient()
    if not iol.login():
        return {"status": "error", "message": "No se pudo conectar con IOL."}
    
    # Obtener configuración y estado
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
        
    # Calcular cantidad (Sincronizado con orquestador)
    balance = iol.get_balance()
    total_equity = balance
    for s, p in state.get("positions", {}).items():
        total_equity += p["qty"] * p.get("current_price", p["entry_price"])
    
    fixed_amount = config["strategy"].get("fixed_investment_amount", 0)
    
    # Si el usuario no configuró un monto fijo, usa un límite alto para que se tome el saldo disponible
    if fixed_amount <= 0:
        target_amount = 999999999
    else:
        target_amount = fixed_amount
        
    # El monto real será el monto fijo, pero nunca más del 95% del efectivo disponible (para cubrir comisiones y variaciones)
    amount = min(target_amount, balance * 0.95)
    
    # Obtener precio actual
    ticker = iol.get_quote(symbol, plazo="t0")
    if not ticker:
        return {"status": "error", "message": f"No se pudo obtener precio de {symbol} en CI."}
    
    current_price = ticker['ultimoPrecio']
    qty = int(amount / current_price)
    
    if qty <= 0:
        return {"status": "error", "message": f"Monto insuficiente (${amount:.0f}) para comprar {symbol}. Saldo CI: ${balance:.0f}"}

    # Determinar precio basado en configuración (Mercado o Límite)
    order_type = config.get("strategy", {}).get("buy_order_type", "limit")
    if order_type == "market":
        buy_price = 0
        order_desc = "A MERCADO"
    else:
        # Ejecutar compra (Redondeo BYMA)
        buy_price = int(current_price) if current_price > 100 else round(current_price, 2)
        order_desc = f"LÍMITE a ${buy_price}"

    # Log detallado para depuración de monto 0
    print(f"DEBUG MANUAL BUY: {symbol} | Qty: {qty} | Price: {current_price} | OrderType: {order_type}", flush=True)
    
    res = iol.place_order(symbol, qty, current_price if buy_price == 0 else buy_price, action="comprar", validity="t0", order_type_str=order_type)
    
    if isinstance(res, dict) and "numeroOperacion" in res:
        # Registrar en estado local
        from datetime import datetime
        # Congelar estrategia para esta posición
        strategy_params = config["strategy"].copy()
        state["positions"][symbol] = {
            "entry_price": current_price, "qty": qty, "step": 0,
            "sl": current_price * strategy_params.get("initial_sl_pct", 0.99),
            "tp": current_price * strategy_params.get("initial_tp_pct", 1.02),
            "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "strategy_snapshot": {
                "initial_sl_pct": strategy_params.get("initial_sl_pct", 0.99),
                "initial_tp_pct": strategy_params.get("initial_tp_pct", 1.02),
                "trailing_sl_pct": strategy_params.get("trailing_sl_pct", 0.988),
                "trailing_tp_pct": strategy_params.get("trailing_tp_pct", 1.01)
            }
        }
        if "history" not in state: state["history"] = []
        state["history"].append({
            "symbol": symbol, "type": "COMPRA (Manual)", "entry_price": current_price,
            "exit_price": 0, "qty": qty, "profit_pct": 0,
            "profit_amount": 0, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
            
        return {"status": "success", "message": f"Orden de COMPRA enviada ({order_desc}): {qty} {symbol}"}
    
    err_msg = res.get("message", "Error desconocido") if isinstance(res, dict) else str(res)
    return {"status": "error", "message": f"Broker rechazó la orden: {err_msg}"}

@app.post("/api/exclude")
async def exclude_symbol(symbol: str):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        
        if "excluded_symbols" not in state:
            state["excluded_symbols"] = []
        
        if symbol not in state["excluded_symbols"]:
            state["excluded_symbols"].append(symbol)
            
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
            
        return {"status": "success", "message": f"{symbol} excluido por hoy."}
    return {"status": "error", "message": "No se pudo acceder al estado."}

@app.post("/api/add_symbol")
async def add_symbol(symbol: str):
    iol = IOLClient()
    if not iol.login():
        return {"status": "error", "message": "No se pudo conectar con IOL."}
    
    # Validar si el símbolo existe en IOL
    ticker = iol.get_quote(symbol)
    if not ticker:
        return {"status": "error", "message": f"El símbolo {symbol} no es válido o no existe en IOL."}
    
    # Agregar a config.json
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        if "watchlist" not in config:
            config["watchlist"] = []
            
        if symbol not in config["watchlist"]:
            config["watchlist"].append(symbol)
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            return {"status": "success", "message": f"{symbol} agregado a la watchlist."}
        else:
            return {"status": "error", "message": f"{symbol} ya está en la watchlist."}
            
    return {"status": "error", "message": "No se pudo acceder a la configuración."}

@app.get("/calendar", response_class=HTMLResponse)
async def get_calendar_page():
    with open("panel/earnings.html", "r") as f:
        return f.read()

@app.get("/api/earnings_calendar")
async def get_earnings_calendar():
    import yfinance as yf
    from datetime import datetime
    
    # Lista completa solicitada
    full_watchlist = [
        "AAPL", "TSLA", "NVDA", "AMZN", "AMD", "META", "MSFT", "GOOG", "INTC", "ORCL", "BABA",
        "NU", "MELI", "GGAL", "YPF", "PBR", "VIST", "PAM", "KO", "PEP", "SPY", "ALUA.BA", "TGNO4.BA"
    ]
    
    def fetch_earnings(symbol):
        try:
            ticker = yf.Ticker(symbol)
            cal = ticker.calendar
            e_date, eps = "N/A", "N/A"
            
            if cal and isinstance(cal, dict):
                dates = cal.get('Earnings Date', [])
                if dates:
                    d = dates[0]
                    e_date = d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d)
                eps = cal.get('Earnings Average', "N/A")
            
            return {
                "symbol": symbol,
                "earnings_date": e_date,
                "eps": eps
            }
        except:
            return {"symbol": symbol, "earnings_date": "N/A", "eps": "N/A"}

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_earnings, full_watchlist))
        
    # Ordenar cronológicamente
    results.sort(key=lambda x: x['earnings_date'] if x['earnings_date'] != "N/A" else "9999-12-31")
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
run(app, host="0.0.0.0", port=3000)