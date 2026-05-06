import time
import json
import os
import threading
import signal
import sys
from datetime import datetime, time as dtime
from agents.strategy_agent import StrategyAgent
from core.iol_client import IOLClient
from core.trailing_engine import TrailingEngine
from core.telegram_client import TelegramClient
from core.bot_logger import log_bot, log_sync, log_trade
import pandas as pd

class Orchestrator:
    def __init__(self, symbols=None):
        self.config_file = "config.json"
        self.config = self._load_config()
        self.symbols = symbols if symbols else self.config.get("symbols", ["NVDA", "AMD"])
        self.iol = IOLClient()
        self.trailing = TrailingEngine()
        self.telegram = TelegramClient()
        self.state_file = "state.json"
        self.state_lock = threading.Lock()
        self.state = self._load_state()
        self.active_sl_threads = set()
        self.last_valuation = self.state.get("balances", {}).get("total_pesos", 0)
        self._setup_signals()

    def _setup_signals(self):
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        print(f"\n🛑 Señal {signum} recibida. Consolidando información y guardando estado...", flush=True)
        with self.state_lock:
            if "system_info" not in self.state: self.state["system_info"] = {}
            self.state["system_info"]["last_shutdown"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.state["system_info"]["status"] = "stopped"
            self._save_state_locked()
        print("✅ Estado guardado. Apagando orquestador.", flush=True)
        sys.exit(0)

    def _load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    if "history" not in state: state["history"] = []
                    if "opportunities" not in state: state["opportunities"] = {}
                    if "excluded_symbols" not in state: state["excluded_symbols"] = []
                    if "system_info" not in state: state["system_info"] = {}
                    if "equity_history" not in state: state["equity_history"] = []
                    return state
            except Exception as e:
                print(f"⚠️ Error cargando estado: {e}. Usando estado base.")
        return {"positions": {}, "history": [], "opportunities": {}, "excluded_symbols": [], "system_info": {}, "equity_history": []}

    def _record_equity_snapshot(self, current_valuation):
        """Registra un punto en la curva de patrimonio una vez por hora"""
        now = datetime.now()
        last_snapshot_str = self.state.get("system_info", {}).get("last_equity_snapshot")
        
        should_record = False
        if not last_snapshot_str:
            should_record = True
        else:
            last_snapshot = datetime.strptime(last_snapshot_str, "%Y-%m-%d %H:%M:%S")
            # Grabamos si pasó más de 1 hora
            if (now - last_snapshot).total_seconds() >= 3600:
                should_record = True
        
        if should_record:
            snapshot = {
                "timestamp": now.strftime("%Y-%m-%d %H:%M"),
                "value": current_valuation
            }
            self.state["equity_history"].append(snapshot)
            # Mantener solo los últimos 500 puntos para no inflar el JSON infinitamente
            if len(self.state["equity_history"]) > 500:
                self.state["equity_history"] = self.state["equity_history"][-500:]
                
            self.state["system_info"]["last_equity_snapshot"] = now.strftime("%Y-%m-%d %H:%M:%S")
            print(f"📈 Equity Snapshot registrado: ${current_valuation:,.2f}", flush=True)

    def _update_total_invested_from_file(self):
        """Lee el archivo de movimientos de IOL y actualiza el total invertido en config.json"""
        file_path = "MovimientosHistoricos.xls"
        if not os.path.exists(file_path):
            return

        try:
            # IOL exporta HTML con extensión .xls
            dfs = pd.read_html(file_path)
            if not dfs: return
            df = dfs[0]
            
            # Filtrar depósitos en pesos
            mask = (df['Tipo Mov.'].str.contains("Depósito|Transferencia", case=False, na=False)) & \
                   (df['Tipo Cuenta'].str.contains("Pesos", case=False, na=False))
            depositos = df[mask]
            
            # Cálculo de USD Histórico usando Dólar Oficial de cada fecha (Abril 2026)
            # 12/04: ~1398, 14/04: ~1400, 24/04: ~1410, 29/04: ~1414, 30/04: ~1415
            total_ars = 0
            total_usd_hist = 0
            for _, row in depositos.iterrows():
                monto_raw = str(row['Monto']).replace(".", "").replace(",", ".")
                monto = float(monto_raw)
                total_ars += monto
                
                fecha = str(row['Concert.'])
                rate = 1415 # Default
                if "12/04" in fecha: rate = 1398
                elif "14/04" in fecha: rate = 1400
                elif "24/04" in fecha: rate = 1410
                elif "29/04" in fecha: rate = 1414
                elif "30/04" in fecha: rate = 1415
                total_usd_hist += monto / rate
            
            # Si el valor de ARS o USD cambió, actualizar config
            # RECARGA DE SEGURIDAD: Evitar pisar cambios del panel web
            with open(self.config_file, 'r') as f:
                current_disk_config = json.load(f)
            
            current_ars = current_disk_config.get("strategy", {}).get("total_invested", 0)
            current_usd = current_disk_config.get("strategy", {}).get("total_invested_usd", 0)
            
            if total_ars > 0 and (total_ars != current_ars or total_usd_hist != current_usd):
                if "strategy" not in current_disk_config: current_disk_config["strategy"] = {}
                current_disk_config["strategy"]["total_invested"] = total_ars
                current_disk_config["strategy"]["total_invested_usd"] = total_usd_hist
                current_disk_config["strategy"]["usd_type"] = "Oficial"
                
                with open(self.config_file, 'w') as f:
                    json.dump(current_disk_config, f, indent=4)
                
                self.config = current_disk_config # Sincronizar memoria
                print(f"✅ Inversión total actualizada automáticamente: ${total_ars:,.2f}", flush=True)
                self.telegram.send_message(f"🔄 *Configuración Actualizada*\nSe detectaron nuevos movimientos.\nARS: ${total_ars:,.2f}\nUSD: u$d {total_usd_hist:,.2f}")
        except Exception as e:
            print(f"⚠️ Error procesando archivo de movimientos: {e}")

    def _save_state(self):
        with self.state_lock:
            self._save_state_locked()

    def _save_state_locked(self):
        # Asume que ya tiene el lock
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=4)

    def _check_eod_liquidation(self):
        """Estrategia de Cierre de Día (EOD) para evitar Gaps de apertura."""
        if not self.trading_enabled: return
        
        eod_config = self.config.get("strategy", {}).get("eod_strategy", "selective")
        if eod_config == "off": return

        now = datetime.now().time()
        # Rango de cierre: 16:50 a 16:58
        if dtime(16, 50) <= now <= dtime(16, 58):
            threshold = self.config.get("strategy", {}).get("eod_profit_threshold", 1.5)
            
            for symbol, pos in list(self.state["positions"].items()):
                if symbol in self.active_sl_threads: continue
                
                profit = pos.get('profit_pct', 0)
                should_liquidate = False
                
                if eod_config == "full":
                    should_liquidate = True
                    reason = "Estrategia Full EOD"
                elif eod_config == "selective" and profit >= threshold:
                    should_liquidate = True
                    reason = f"Profit {profit:.2f}% > Umbral {threshold}%"
                
                if should_liquidate:
                    print(f"💰 [EOD] Liquidando {symbol} por {reason}", flush=True)
                    self.telegram.send_message(f"💰 *CIERRE EOD*: Liquidando {symbol} ({reason}) para evitar riesgo overnight.")
                    threading.Thread(target=self._execute_sl_worker, args=(symbol, pos, pos.get('current_price', 0)), daemon=True).start()

    def can_trade(self):
        now = datetime.now().time()
        is_market_open = dtime(10, 30) <= now <= dtime(17, 0)
        is_paused = self.config.get("trading_paused", False)
        return is_market_open and not is_paused

    def _sync_portfolio(self):
        try:
            portfolio = self.iol.get_portfolio()
            if not portfolio or "activos" not in portfolio: return
            
            # 1. Conciliación Agresiva de Historial (Captura ventas/compras externas o pasadas)
            ops_history = self.iol.get_operations(state="terminadas")
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            with self.state_lock:
                current_history_dates = [h.get("date") for h in self.state.get("history", [])]
                
                for op in ops_history:
                    if today_str not in op.get("fechaOrden", ""): continue
                    
                    op_id = op.get("numero")
                    op_date = op.get("fechaOperada", op.get("fechaOrden")).replace('T', ' ')
                    
                    # Evitar duplicados (por fecha/hora exacta o ID si lo tuviéramos guardado)
                    if any(op_date in h_date for h_date in current_history_dates):
                        continue

                    sym = op.get("simbolo")
                    tipo = op.get("tipo")
                    
                    if tipo == "Venta":
                        # Intentar encontrar el precio de entrada en el historial previo
                        # (Si no se encuentra, se usa el precio operado como fallback con profit 0)
                        entry_price = 0
                        for h in reversed(self.state["history"]):
                            if h["symbol"] == sym and "COMPRA" in h["type"]:
                                entry_price = h["entry_price"]
                                break
                        
                        exit_price = op.get("precioOperado", 0)
                        qty = op.get("cantidadOperada", 0)
                        profit_pct = ((exit_price / entry_price) - 1) * 100 if entry_price > 0 else 0
                        
                        self.state["history"].append({
                            "symbol": sym,
                            "type": f"VENTA ({op.get('plazo', 'Sincro')})",
                            "entry_price": entry_price,
                            "exit_price": exit_price,
                            "qty": qty,
                            "profit_pct": profit_pct,
                            "profit_amount": (exit_price - entry_price) * qty if entry_price > 0 else 0,
                            "date": op_date,
                            "op_id": op_id
                        })
                        log_sync(f"Reconciliada VENTA externa: {sym} @ ${exit_price:,.2f}")
                    
                    elif tipo == "Compra":
                        self.state["history"].append({
                            "symbol": sym,
                            "type": f"COMPRA ({op.get('plazo', 'Sincro')})",
                            "entry_price": op.get("precioOperado", 0),
                            "exit_price": 0,
                            "qty": op.get("cantidadOperada", 0),
                            "profit_pct": 0,
                            "profit_amount": 0,
                            "date": op_date,
                            "op_id": op_id
                        })
                        log_sync(f"Reconciliada COMPRA externa: {sym} @ ${op.get('precioOperado'):,.2f}")

            # 2. Sincronización de Posiciones Abiertas
            real_positions = {}
            for act in portfolio["activos"]:
                sym = act["titulo"]["simbolo"]
                qty = act["cantidad"]
                if qty > 0: real_positions[sym] = act
            
            with self.state_lock:
                # Reset excluded symbols if it's a new day
                last_reset = self.state.get("last_reset_date")
                today = datetime.now().strftime("%Y-%m-%d")
                if last_reset != today:
                    self.state["excluded_symbols"] = []
                    self.state["last_reset_date"] = today

                state_pos = self.state.get("positions", {})
                
                # Eliminar posiciones que ya no están en IOL
                to_remove = [sym for sym in state_pos if sym not in real_positions]
                for sym in to_remove:
                    if sym not in self.active_sl_threads:
                        del state_pos[sym]
                        log_sync(f"Posición {sym} removida por sincronización (ya no existe en IOL)")
                    
                # Agregar/Actualizar posiciones desde IOL
                for sym, act in real_positions.items():
                    if sym not in state_pos:
                        avg_price = act.get("ppc", act.get("ultimoPrecio", 0))
                        isl_pct = self.config["strategy"].get("initial_sl_pct", 0.98)
                        itp_pct = self.config["strategy"].get("initial_tp_pct", 1.05)
                        
                        state_pos[sym] = {
                            "entry_price": avg_price,
                            "current_price": act.get("ultimoPrecio", avg_price),
                            "qty": act["cantidad"],
                            "sl": avg_price * isl_pct,
                            "tp": avg_price * itp_pct,
                            "step": 0,
                            "buy_time": f"SINCRO ({datetime.now().strftime('%d/%m %H:%M')})"
                        }
                        log_sync(f"Nueva posición detectada en IOL: {sym} x {act['cantidad']}")
                    else:
                        state_pos[sym]["qty"] = act["cantidad"]
                        state_pos[sym]["current_price"] = act.get("ultimoPrecio", state_pos[sym]["current_price"])

                self.state["positions"] = state_pos
                self._save_state_locked()

        except Exception as e:
            log_sync(f"Error crítico en _sync_portfolio: {e}")

    def run(self):
        print("🚀 Starting Trading Orchestrator...", flush=True)
        # Registrar inicio en el estado
        with self.state_lock:
            if "system_info" not in self.state: self.state["system_info"] = {}
            self.state["system_info"]["last_start"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.state["system_info"]["status"] = "running"
            self._save_state_locked()

        while True:
            try:
                # Recargar config (esto es seguro)
                self.config = self._load_config()
                self._update_total_invested_from_file()
                
                # SEGURO EXTREMO: Si el bot está pausado, el proceso se mata a sí mismo
                if self.config.get("trading_paused", False):
                    print("🛑 AUTODESTRUCCIÓN: El bot está pausado. Cerrando orquestador para evitar órdenes accidentales.", flush=True)
                    with self.state_lock:
                        if "system_info" not in self.state: self.state["system_info"] = {}
                        self.state["system_info"]["status"] = "stopped (paused)"
                        self._save_state_locked()
                    sys.exit(0)
                
                # Recargar estado con bloqueo para evitar pisar cambios de hilos
                with self.state_lock:
                    new_state = self._load_state()
                    # Fusionar solo lo necesario o recargar si no hay hilos activos
                    # Por simplicidad y seguridad, si hay hilos activos, solo actualizamos lo que el web_server pudo cambiar
                    if not self.active_sl_threads:
                        self.state = new_state
                    else:
                        # Si hay hilos, solo actualizamos posiciones/config que pudieron venir de afuera
                        self.state["positions"] = new_state.get("positions", self.state["positions"])
                        self.state["history"] = new_state.get("history", self.state["history"])

                self.watchlist = self.config.get("watchlist", [])
                
                # VALIDACIÓN DE INSTANCIA AUTORIZADA
                my_id = os.getenv("INSTANCE_NAME", "UNKNOWN")
                authorized_id = self.config.get("authorized_instance", "UNKNOWN")
                
                if my_id != authorized_id:
                    print(f"⚠️ INSTANCIA NO AUTORIZADA: Yo soy '{my_id}' pero la autorizada es '{authorized_id}'.")
                    print("🛑 Entrando en modo OBSERVADOR. No se realizarán operaciones ni logins.")
                    with self.state_lock:
                        self.state["last_error"] = f"Modo Observador: Instancia autorizada es {authorized_id}"
                    time.sleep(30) # Esperar antes de re-chequear
                    continue # Saltarse el ciclo de trading/login

                self.trading_enabled = self.can_trade()
                
                # SEGURIDAD: Validar login antes de intentar sincronizar
                if not self.iol.access_token:
                    if not self.iol.login():
                        print("❌ FALLA DE AUTENTICACIÓN: Pausando bot para evitar bloqueo de cuenta.")
                        with open("config.json", "r") as f:
                            cfg = json.load(f)
                        cfg["trading_paused"] = True
                        with open("config.json", "w") as f:
                            json.dump(cfg, f, indent=4)
                        self.trading_enabled = False
                        with self.state_lock:
                            self.state["last_error"] = "Error de Login (401). Trading Pausado."
                        return # Abortar ciclo
                
                self._sync_portfolio()
                
                try:
                    balances = self.iol.get_balances_all()
                    oficial = self.iol.get_official_rate()
                    balances["oficial"] = oficial
                    
                    # Valorización en USD Oficial (Hoy)
                    balances["total_usd"] = balances.get("total_pesos", 0) / oficial
                    
                    current_val = balances.get("total_pesos", 0)
                    
                    # Detección de saltos de capital (+1M) para depósitos
                    if self.last_valuation > 0 and (current_val - self.last_valuation) >= 1000000:
                        msg = f"🚨 *SALTO DE CAPITAL DETECTADO*\n"
                        msg += f"Se detectó un incremento de ${current_val - self.last_valuation:,.2f} en la cartera.\n"
                        msg += f"Si realizaste un depósito, por favor pásame el Excel con el detalle de movimientos para actualizar la inversión total."
                        self.telegram.send_message(msg)
                    
                    self.last_valuation = current_val
                    self._record_equity_snapshot(current_val)
                    
                    with self.state_lock:
                        self.state["balance"] = balances["t0"]
                        self.state["balances"] = balances
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loop: Trading Enabled={self.trading_enabled} | Valuación Pesos: ${balances.get('total_pesos', 0):,.2f}", flush=True)
                except Exception as e:
                    print(f"Error updating balances: {e}")
                
                # Resumen de cartera en logs
                for symbol, pos in self.state["positions"].items():
                    val = pos.get("current_price", pos["entry_price"]) * pos["qty"]
                    print(f"  - {symbol}: ${val:,.0f} (P: {pos.get('profit_pct', 0):.2f}%)", flush=True)

                # Procesar símbolos en paralelo para eliminar latencia de API acumulada
                from concurrent.futures import ThreadPoolExecutor
                all_symbols = list(self.state["positions"].keys()) + self.watchlist
                unique_symbols = list(set(all_symbols))
                
                with ThreadPoolExecutor(max_workers=10) as executor:
                    executor.map(self._process_symbol, unique_symbols)

                # Chequeo de liquidación al cierre (16:50)
                self._check_eod_liquidation()

                self._save_state()
                time.sleep(2 if self.trading_enabled else 30)
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(10)

    def _process_symbol(self, symbol):
        pos = self.state["positions"].get(symbol)
        quote = self.iol.get_quote(symbol, plazo="t0")
        if not quote: return
        current_price = quote['ultimoPrecio']
        
        strategy = StrategyAgent(symbol)
        decision = strategy.get_decision()
        
        # Actualizar siempre el Radar con el precio y score más reciente, se tenga o no la posición
        if decision and "final_score" in decision:
            self.state["opportunities"][symbol] = {
                "score": decision["final_score"], "metrics": decision["metrics"],
                "price": current_price, "timestamp": datetime.now().strftime("%H:%M:%S")
            }

        if pos:
            pos['current_price'] = current_price
            if decision and "technical_details" in decision: pos['technical'] = decision["technical_details"]
            pos['profit_pct'] = ((current_price / pos['entry_price']) - 1) * 100
            
            if self.trading_enabled:
                if self.trailing.check_exit(current_price, pos['sl']):
                    if symbol not in self.active_sl_threads:
                        threading.Thread(target=self._execute_sl_worker, args=(symbol, pos, current_price), daemon=True).start()
                else:
                    if pos.get('pending_sl'):
                        pos['pending_sl'] = False
                        if 'sl_countdown' in pos: del pos['sl_countdown']
                    
                    # Sincronización dinámica de niveles iniciales (Step 0) ante cambios de modo en el panel
                    if pos.get('step', 0) == 0:
                        initial_sl_pct = self.config["strategy"].get("initial_sl_pct", 0.99)
                        new_sl = pos['entry_price'] * initial_sl_pct
                        if abs(new_sl - pos['sl']) > 0.1: # Evitar micro-ajustes por redondeo
                            print(f"🔄 [MODO] Ajustando SL inicial de {symbol}: ${pos['sl']:.2f} -> ${new_sl:.2f}", flush=True)
                            pos['sl'] = new_sl
                            
                        initial_tp_pct = self.config["strategy"].get("initial_tp_pct", 1.015)
                        new_tp = pos['entry_price'] * initial_tp_pct
                        if abs(new_tp - pos['tp']) > 0.1:
                            print(f"🔄 [MODO] Ajustando TP inicial de {symbol}: ${pos['tp']:.2f} -> ${new_tp:.2f}", flush=True)
                            pos['tp'] = new_tp

                    # Priorizar valores globales del config para permitir ajustes en vivo sobre posiciones abiertas
                    tsl_val = self.config["strategy"].get("trailing_sl_pct", pos.get('strategy_snapshot', {}).get('trailing_sl_pct', 0.988))
                    ttp_val = self.config["strategy"].get("trailing_tp_pct", pos.get('strategy_snapshot', {}).get('trailing_tp_pct', 1.01))
                    
                    update = self.trailing.calculate_new_levels(current_price, pos['sl'], pos['tp'], pos['step'], tsl_val, ttp_val)
                    if update['updated']:
                        old_sl = pos['sl']
                        pos['sl'], pos['tp'], pos['step'] = update['sl'], update['tp'], update['step']
                        print(f"📈 ESCALÓN en {symbol}: SL subió de ${old_sl:.2f} a ${pos['sl']:.2f} (Usando Trailing SL: {tsl_val})", flush=True)
                        self._save_state()
                        self.telegram.send_message(f"📈 *ESCALÓN* {symbol}: SL ${pos['sl']:.2f}")
        else:
            if self.trading_enabled and self.config.get("auto_buy", True) and decision and decision['decision'] == "BUY":
                excluded = self.state.get("excluded_symbols", [])
                if symbol not in excluded:
                    self._execute_buy(symbol, decision, current_price)
                else:
                    print(f"⏩ {symbol} está excluido por hoy. Ignorando compra.")
            self._save_state()

    def _execute_sl_worker(self, symbol, pos, current_price):
        self.active_sl_threads.add(symbol)
        try:
            pos['pending_sl'] = True
            self._save_state()
            
            for i in range(3, -1, -1):
                # Recargar configuración para chequear pausa en cada iteración del countdown
                self.config = self._load_config()
                if self.config.get("trading_paused", False):
                    print(f"⏸️ Venta de {symbol} pausada por el usuario.")
                    pos['pending_sl'] = False
                    if 'sl_countdown' in pos: del pos['sl_countdown']
                    self._save_state()
                    return

                temp_state = self._load_state()
                if symbol not in temp_state["positions"] or not temp_state["positions"][symbol].get("pending_sl"):
                    return
                pos['sl_countdown'] = i
                print(f"⏳ Confirmando SL en {symbol}: {i}s...", flush=True)
                self._save_state()
                if i > 0: time.sleep(1)
            
            # Doble chequeo final de pausa antes de disparar al broker
            self.config = self._load_config()
            if self.config.get("trading_paused", False):
                print(f"🚫 ABORTANDO ORDEN: El bot se pausó justo antes de enviar la orden de {symbol}")
                pos['pending_sl'] = False
                return

            # Usar Precio de Mercado (0) para asegurar la venta inmediata en SL
            log_trade(symbol, "VENTA", pos['qty'], current_price, f"STOP LOSS / EXIT alcanzado. SL: ${pos['sl']}")
            res = self.iol.place_order(symbol, pos['qty'], current_price, action="vender", validity="t0", order_type_str="market")
            
            # Si falla T0 (plazo no disponible), probamos T2
            if isinstance(res, dict) and "error" in res:
                print(f"⚠️ T0 failed for {symbol}, retrying MARKET in T2...", flush=True)
                res = self.iol.place_order(symbol, pos['qty'], current_price, action="vender", validity="t2", order_type_str="market")

            if isinstance(res, dict) and "numeroOperacion" in res:
                with self.state_lock:
                    profit_amount = (current_price - pos['entry_price']) * pos['qty']
                    self.state["history"].append({
                        "symbol": symbol, "type": "SELL", "entry_price": pos['entry_price'],
                        "exit_price": current_price, "qty": pos['qty'], "profit_pct": pos['profit_pct'],
                        "profit_amount": profit_amount, "steps": pos.get('step', 0),
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    if symbol in self.state["positions"]: del self.state["positions"][symbol]
                self._save_state()
                self.telegram.send_message(f"🛑 *VENTA EJECUTADA* {symbol} a ${current_price}")
            else:
                # Si fallaron ambos intentos, liberamos el estado de alerta para que el usuario pueda ver el error en consola
                print(f"❌ CRITICAL: Venta fallida para {symbol}. Detalle: {res}", flush=True)
                pos['pending_sl'] = False
                if 'sl_countdown' in pos: del pos['sl_countdown']
                self._save_state()
        finally:
            self.active_sl_threads.remove(symbol)

    def _execute_buy(self, symbol, decision, current_price):
        # Recargar config para estar seguro del estado de pausa
        self.config = self._load_config()
        if self.config.get("trading_paused", False):
            print(f"⏸️ Compra de {symbol} cancelada: Bot pausado.")
            return

        min_score = self.config["strategy"]["min_buy_score"]
        if decision['final_score'] >= min_score:
            balance = self.iol.get_balance()
            
            fixed_amount = self.config["strategy"].get("fixed_investment_amount", 0)
            risk_pct = self.config["strategy"].get("risk_balance_pct", 0.1)
            
            if fixed_amount > 0:
                target_amount = fixed_amount
            else:
                target_amount = balance * risk_pct

            # El monto final es el objetivo, limitado solo por el saldo real disponible (con 2% de margen para comisiones)
            amount = min(target_amount, balance * 0.98)
            
            qty = int(amount / current_price)
            if qty > 0:
                # Determinar precio basado en configuración (Mercado o Límite)
                order_type = self.config.get("strategy", {}).get("buy_order_type", "limit")
                
                if order_type == "market":
                    buy_price = 0
                    log_trade(symbol, "COMPRA", qty, current_price, f"MERCADO | Score: {decision['score']}")
                else:
                    # Round to integer for safety in BYMA for prices > 100
                    buy_price = int(current_price) if current_price > 100 else round(current_price, 2)
                    log_trade(symbol, "COMPRA", qty, buy_price, f"LÍMITE | Score: {decision['score']}")

                res = self.iol.place_order(symbol, qty, current_price if buy_price == 0 else buy_price, action="comprar", validity="t0", order_type_str=order_type)
                if isinstance(res, dict) and "numeroOperacion" in res:
                    with self.state_lock:
                        strategy_params = self.config["strategy"].copy()
                        self.state["positions"][symbol] = {
                            "entry_price": current_price,
                            "qty": qty,
                            "step": 0,
                            "sl": current_price * strategy_params.get("initial_sl_pct", 0.99),
                            "tp": current_price * strategy_params.get("initial_tp_pct", 1.02),
                            "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "buy_score": decision['final_score'],
                            "strategy_snapshot": {
                                "initial_sl_pct": strategy_params.get("initial_sl_pct", 0.99),
                                "initial_tp_pct": strategy_params.get("initial_tp_pct", 1.02),
                                "trailing_sl_pct": strategy_params.get("trailing_sl_pct", 0.988),
                                "trailing_tp_pct": strategy_params.get("trailing_tp_pct", 1.01)
                            }
                        }
                        # También guardar en historial para auditoría
                        self.state["history"].append({
                            "symbol": symbol,
                            "type": "COMPRA (BOT)",
                            "entry_price": current_price,
                            "exit_price": 0,
                            "qty": qty,
                            "score": decision['final_score'],
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    self._save_state()
                    self.telegram.send_message(f"🎯 *COMPRA EJECUTADA* {symbol}\n💰 Precio: ${current_price}\n📊 Score: *{decision['final_score']}* (Mín: {min_score})")
                else:
                    print(f"❌ Compra fallida {symbol}: {res}", flush=True)

if __name__ == "__main__":
    Orchestrator().run()
