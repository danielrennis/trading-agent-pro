
import sys
import os
import json
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

# Añadir el directorio raíz al path para importar los módulos del bot
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orchestrator import Orchestrator
from scratch.mock_iol import MockIOLClient

def setup_simulation_files():
    config = {
        "strategy": {
            "initial_sl_pct": 0.98,
            "initial_tp_pct": 1.02,
            "trailing_sl_pct": 0.99,
            "trailing_tp_pct": 1.01,
            "risk_balance_pct": 0.1,
            "min_buy_score": 9.0,
            "fixed_investment_amount": 1000000
        },
        "symbols": ["SIMUL"],
        "watchlist": ["SIMUL"],
        "trading_paused": False
    }
    with open("config_sim.json", "w") as f:
        json.dump(config, f, indent=4)
    
    state = {"positions": {}, "history": [], "opportunities": {}, "excluded_symbols": [], "system_info": {}}
    with open("state_sim.json", "w") as f:
        json.dump(state, f, indent=4)

def create_orch_sim():
    # Parcheamos los nombres de archivo antes de instanciar
    with patch('orchestrator.Orchestrator._load_config', return_value={}), \
         patch('orchestrator.Orchestrator._load_state', return_value={}):
        orch = Orchestrator()
    
    orch.config_file = "config_sim.json"
    orch.state_file = "state_sim.json"
    # Recargamos ahora que los paths son correctos
    orch.config = orch._load_config()
    orch.state = orch._load_state()
    orch.trading_enabled = True
    orch.watchlist = ["SIMUL"]
    return orch

def run_simulation():
    print("--- INICIANDO SIMULACIÓN COMPLETA ---")
    setup_simulation_files()
    
    mock_iol = MockIOLClient()
    mock_iol.set_price("SIMUL", 100.0)
    
    # Parchear dependencias
    with patch('orchestrator.IOLClient', return_value=mock_iol), \
         patch('orchestrator.TelegramClient', return_value=MagicMock()), \
         patch('orchestrator.StrategyAgent') as MockStrategy:
        
        # Mock de Estrategia: Decisión de COMPRA inicial
        mock_strategy_inst = MockStrategy.return_value
        mock_strategy_inst.get_decision.return_value = {
            "decision": "BUY",
            "final_score": 9.8,
            "metrics": {"trend": "Strong Bullish"},
            "technical_details": {"daily_trend": "BULLISH"}
        }
        
        orch = create_orch_sim()
        
        # 1. EJECUCIÓN INICIAL (Detección y Compra)
        print("\n[Paso 1] Detectando oportunidad y ejecutando compra...")
        orch._process_symbol("SIMUL")
        
        with open("state_sim.json", "r") as f:
            state = json.load(f)
        
        if "SIMUL" in state["positions"]:
            pos = state["positions"]["SIMUL"]
            print(f"✅ Compra exitosa. Precio: {pos['entry_price']}, SL: {pos['sl']}, TP: {pos['tp']}")
        else:
            print("❌ Error: La compra no se registró en el estado.")
            return

        # 2. SIMULAR SUBIDA DE PRECIO (Primer Salto / Escalón)
        print("\n[Paso 2] Subiendo precio para disparar escalón (TP hit)...")
        mock_iol.set_price("SIMUL", 102.5) # TP era 102 (100 * 1.02)
        orch._process_symbol("SIMUL")
        
        # Recargar estado del disco para verificar persistencia real
        with open("state_sim.json", "r") as f:
            state = json.load(f)
        pos = state["positions"]["SIMUL"]
        print(f"✅ Escalón 1 completado. Nuevo SL: {pos['sl']:.2f} (Step: {pos['step']})")
        if pos['step'] != 1: 
            print(f"❌ Error: El contador de saltos debería ser 1, es {pos['step']}")
            return

        # 3. SIMULAR REINICIO DE SISTEMA
        print("\n[Paso 3] Simulando reinicio del sistema (Persistencia)...")
        orch_restarted = create_orch_sim()
        
        pos_restarted = orch_restarted.state["positions"]["SIMUL"]
        if pos_restarted['sl'] == pos['sl'] and pos_restarted['step'] == 1:
            print("✅ Persistencia verificada. Los niveles de SL y pasos se mantuvieron.")
        else:
            print(f"❌ Error: Los datos no persistieron. SL esperado: {pos['sl']}, real: {pos_restarted['sl']}")

        # 4. SIMULAR SEGUNDO SALTO (Escalón 2)
        print("\n[Paso 4] Subiendo precio para disparar segundo escalón...")
        # Nuevo TP era 102.5 * 1.01 = 103.525
        mock_iol.set_price("SIMUL", 104.0)
        orch_restarted._process_symbol("SIMUL")
        
        with open("state_sim.json", "r") as f:
            state = json.load(f)
        pos = state["positions"]["SIMUL"]
        print(f"✅ Escalón 2 completado. Nuevo SL: {pos['sl']:.2f} (Step: {pos['step']})")

        # 5. SIMULAR CAÍDA Y STOP LOSS (Disparo de Venta)
        print("\n[Paso 5] Bajando precio para disparar STOP LOSS...")
        # SL actual es 104 * 0.99 = 102.96
        mock_iol.set_price("SIMUL", 102.0)
        
        # Mock de pausa: verificar que no venda si pausamos
        print("   -> Probando pausa durante caída...")
        orch_restarted.config["trading_paused"] = True
        with open("config_sim.json", "w") as f: json.dump(orch_restarted.config, f, indent=4)
        
        # En la simulación, llamamos al worker directamente para controlar el flujo
        # orch_restarted._process_symbol("SIMUL") 
        orch_restarted._execute_sl_worker("SIMUL", pos, 102.0)
        
        with open("state_sim.json", "r") as f:
            state = json.load(f)
        if "SIMUL" in state["positions"]:
            print("✅ Pausa respetada: La posición NO se vendió estando pausado.")
        else:
            print("❌ Error: Se ejecutó la venta a pesar de estar pausado.")

        # 6. REANUDAR Y EJECUTAR VENTA FINAL
        print("\n[Paso 6] Reanudando y ejecutando venta por SL...")
        orch_restarted.config["trading_paused"] = False
        with open("config_sim.json", "w") as f: json.dump(orch_restarted.config, f, indent=4)
        
        # Usar la posición real vinculada al estado del orquestador
        pos_actual = orch_restarted.state["positions"]["SIMUL"]
        orch_restarted._execute_sl_worker("SIMUL", pos_actual, 102.0)
        
        with open("state_sim.json", "r") as f:
            state = json.load(f)
        if "SIMUL" not in state["positions"]:
            print("✅ Venta por SL ejecutada correctamente.")
            history = state["history"][-1]
            print(f"📊 Historial: Símbolo {history['symbol']}, Profit: {history['profit_pct']:.2f}%, Saltos: {history['steps']}")
        else:
            print("❌ Error: La posición debería haber sido cerrada.")

    print("\n--- SIMULACIÓN FINALIZADA ---")

if __name__ == "__main__":
    run_simulation()
