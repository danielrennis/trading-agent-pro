
import json
import time
import os
from datetime import datetime

STATE_FILE = "state.json"

def run_simulation():
    print("🚀 Iniciando Simulación de Funcionamiento Óptimo...")
    
    if not os.path.exists(STATE_FILE):
        print("❌ No se encontró state.json")
        return

    with open(STATE_FILE, "r") as f:
        original_state = json.load(f)

    try:
        # 1. SIMULAR OPORTUNIDAD EXPLOSIVA
        print("🔎 Simulando hallazgo de oportunidad técnica...")
        state = original_state.copy()
        state["opportunities"]["NVDA"] = {
            "score": 9.8,
            "metrics": {"technical": 10, "fundamental": 9.5, "news": 10},
            "price": 850.25,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
        time.sleep(3)

        # 2. SIMULAR STOP LOSS TRIGGERED (ALERTA ROJA + SONIDO)
        print("⚠️ SIMULANDO IMPACTO EN STOP LOSS (TSLA)...")
        if "TSLA" in state["positions"]:
            state["positions"]["TSLA"]["pending_sl"] = True
            state["positions"]["TSLA"]["sl_countdown"] = 10
            
            # Guardamos para disparar la alarma en el panel
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=4)
            
            # Cuenta regresiva simulada
            for i in range(9, -1, -1):
                time.sleep(1)
                state["positions"]["TSLA"]["sl_countdown"] = i
                with open(STATE_FILE, "w") as f:
                    json.dump(state, f, indent=4)
                print(f"   Contador: {i}s")

        print("✅ Simulación visual completada. Restaurando estado original en 5 segundos...")
        time.sleep(5)
        
    finally:
        # Restaurar estado original (limpiar alertas falsas)
        if "TSLA" in original_state["positions"]:
            if "pending_sl" in original_state["positions"]["TSLA"]:
                del original_state["positions"]["TSLA"]["pending_sl"]
            if "sl_countdown" in original_state["positions"]["TSLA"]:
                del original_state["positions"]["TSLA"]["sl_countdown"]
        
        with open(STATE_FILE, "w") as f:
            json.dump(original_state, f, indent=4)
        print("♻️ Estado restaurado.")

if __name__ == "__main__":
    run_simulation()
