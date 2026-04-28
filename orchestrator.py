import time
import json
import os
import threading
from datetime import datetime, time as dtime
from agents.strategy_agent import StrategyAgent
from core.iol_client import IOLClient
from core.trailing_engine import TrailingEngine
from core.telegram_client import TelegramClient

class Orchestrator:
    def __init__(self, symbols=None):
        self.config_file = "config.json"
        self.config = self._load_config()
        self.symbols = symbols if symbols else self.config.get("symbols", ["NVDA", "AMD"])
        self.iol = IOLClient()
        self.trailing = TrailingEngine()
        self.telegram = TelegramClient()
        self.state_file = "state.json"
        self.state = self._load_state()
        self.state_lock = threading.Lock()
        self.active_sl_threads = set()

    def _load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def _load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                if "history" not in state: state["history"] = []
                if "opportunities" not in state: state["opportunities"] = {}
                if "excluded_symbols" not in state: state["excluded_symbols"] = []
                return state
        return {"positions": {}, "history": [], "opportunities": {}, "excluded_symbols": []}

    def _save_state(self):
        with self.state_lock:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=4)

    def can_trade(self):
        now = datetime.now().time()
        is_market_open = dtime(11, 0) <= now <= dtime(17, 0)
        is_paused = self.config.get("trading_paused", False)
        return is_market_open and not is_paused

    def _sync_portfolio(self):
        try:
            portfolio = self.iol.get_portfolio()
            if not portfolio or "activos" not in portfolio: return
            
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
                to_remove = [sym for sym in state_pos if sym not in real_positions]
                for sym in to_remove:
                    if sym not in self.active_sl_threads:
                        del state_pos[sym]
                    
                for sym, act in real_positions.items():
                    if sym not in state_pos:
                        avg_price = act.get("ppc", act.get("ultimoPrecio", 0))
                        isl_pct = self.config.get("strategy", {}).get("initial_sl_pct", 0.99)
                        itp_pct = self.config.get("strategy", {}).get("initial_tp_pct", 1.02)
                        
                        state_pos[sym] = {
                            "entry_price": avg_price, "current_price": act.get("ultimoPrecio", avg_price),
                            "qty": act["cantidad"], "sl": avg_price * isl_pct, "tp": avg_price * itp_pct,
                            "step": 0, "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    else:
                        state_pos[sym]["qty"] = act["cantidad"]
                        if "ultimoPrecio" in act: state_pos[sym]["current_price"] = act["ultimoPrecio"]
                self.state["positions"] = state_pos
        except Exception as e: print(f"Error syncing portfolio: {e}")

    def run(self):
        print("🚀 Starting Trading Orchestrator...", flush=True)
        while True:
            try:
                self.config = self._load_config()
                self.state = self._load_state()
                self.watchlist = self.config.get("watchlist", [])
                self.trading_enabled = self.can_trade()
                self._sync_portfolio()
                
                try:
                    balances = self.iol.get_balances_all()
                    self.state["balance"] = balances["t0"]
                    self.state["balances"] = balances
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Loop: Trading Enabled={self.trading_enabled} | Saldo CI (T0): ${balances['t0']:,.2f} | T+1: ${balances['t1']:,.2f}", flush=True)
                except:
                    pass
                
                # Resumen de cartera en logs
                for symbol, pos in self.state["positions"].items():
                    val = pos.get("current_price", pos["entry_price"]) * pos["qty"]
                    print(f"  - {symbol}: ${val:,.0f} (P: {pos.get('profit_pct', 0):.2f}%)", flush=True)

                for symbol in list(self.state["positions"].keys()):
                    self._process_symbol(symbol)

                for symbol in self.watchlist:
                    if symbol not in self.state["positions"]:
                        self._process_symbol(symbol)

                self._save_state()
                time.sleep(10 if self.trading_enabled else 60)
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
                    
                    tsl_val = 1 - (self.config["strategy"]["trailing_sl_pct"] / 100)
                    ttp_val = 1 + (self.config["strategy"]["trailing_tp_pct"] / 100)
                    update = self.trailing.calculate_new_levels(current_price, pos['sl'], pos['tp'], pos['step'], tsl_val, ttp_val)
                    if update['updated']:
                        pos['sl'], pos['tp'], pos['step'] = update['sl'], update['tp'], update['step']
                        self.telegram.send_message(f"📈 *ESCALÓN* {symbol}: SL ${pos['sl']:.2f}")
        else:
            if decision and "final_score" in decision:
                self.state["opportunities"][symbol] = {
                    "score": decision["final_score"], "metrics": decision["metrics"],
                    "price": current_price, "timestamp": datetime.now().strftime("%H:%M:%S")
                }
                if self.trading_enabled and decision['decision'] == "BUY":
                    excluded = self.state.get("excluded_symbols", [])
                    if symbol not in excluded:
                        self._execute_buy(symbol, decision, current_price)
                    else:
                        print(f"⏩ {symbol} está excluido por hoy. Ignorando compra.")

    def _execute_sl_worker(self, symbol, pos, current_price):
        self.active_sl_threads.add(symbol)
        try:
            pos['pending_sl'] = True
            self._save_state()
            
            for i in range(10, -1, -1):
                temp_state = self._load_state()
                if symbol not in temp_state["positions"] or not temp_state["positions"][symbol].get("pending_sl"):
                    return
                pos['sl_countdown'] = i
                self._save_state()
                if i > 0: time.sleep(1)
            
            # Usar Precio de Mercado (0) para asegurar la venta inmediata en SL
            print(f"🛑 Attempting MARKET SELL for {symbol}...", flush=True)
            res = self.iol.place_order(symbol, pos['qty'], 0, action="vender", validity="t0")
            
            # Si falla T0 (plazo no disponible), probamos T2
            if isinstance(res, dict) and "error" in res:
                print(f"⚠️ T0 failed for {symbol}, retrying MARKET in T2...", flush=True)
                res = self.iol.place_order(symbol, pos['qty'], 0, action="vender", validity="t2")

            if isinstance(res, dict) and "numeroOperacion" in res:
                with self.state_lock:
                    profit_amount = (current_price - pos['entry_price']) * pos['qty']
                    self.state["history"].append({
                        "symbol": symbol, "type": "SELL", "entry_price": pos['entry_price'],
                        "exit_price": current_price, "qty": pos['qty'], "profit_pct": pos['profit_pct'],
                        "profit_amount": profit_amount, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        min_score = self.config["strategy"]["min_buy_score"]
        if decision['final_score'] >= min_score:
            balance = self.iol.get_balance()
            
            # Calcular Equidad Total (Efectivo + Valor de Acciones) para un riesgo real
            total_equity = balance
            for s, p in self.state.get("positions", {}).items():
                total_equity += p["qty"] * p.get("current_price", p["entry_price"])
            
            risk_pct = self.config["strategy"]["risk_balance_pct"]
            target_amount = total_equity * risk_pct
            
            # El monto real de compra no puede exceder el efectivo disponible (menos margen para comisiones)
            amount = min(target_amount, balance * 0.95)
            
            qty = int(amount / current_price)
            if qty > 0:
                # Round to integer for safety in BYMA for prices > 100
                buy_price = int(current_price) if current_price > 100 else round(current_price, 2)
                res = self.iol.place_order(symbol, qty, buy_price, action="comprar", validity="t0")
                if isinstance(res, dict) and "numeroOperacion" in res:
                    with self.state_lock:
                        self.state["positions"][symbol] = {
                            "entry_price": current_price, "qty": qty, "step": 0,
                            "sl": current_price * self.config["strategy"]["initial_sl_pct"],
                            "tp": current_price * self.config["strategy"]["initial_tp_pct"],
                            "buy_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    self._save_state()
                    self.telegram.send_message(f"🎯 *COMPRA EJECUTADA* {symbol} a ${current_price}")
                else:
                    print(f"❌ Compra fallida {symbol}: {res}", flush=True)

if __name__ == "__main__":
    Orchestrator().run()
