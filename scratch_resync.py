import json
import os
from core.iol_client import IOLClient

STATE_FILE = "state.json"

iol = IOLClient()
iol.login()
portfolio = iol.get_portfolio()

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
else:
    state = {"positions": {}, "opportunities": {}, "balance": 0, "history": []}

real_positions = {}
if portfolio and "activos" in portfolio:
    for act in portfolio["activos"]:
        sym = act["titulo"]["simbolo"]
        qty = act["cantidad"]
        if qty > 0:
            real_positions[sym] = act

# Remove positions in state that are NOT in real_positions
to_remove = [sym for sym in state.get("positions", {}) if sym not in real_positions]
for sym in to_remove:
    print(f"Removing phantom position from state: {sym}")
    del state["positions"][sym]

# Add or update positions in state from real_positions
for sym, act in real_positions.items():
    if sym not in state.get("positions", {}):
        print(f"Adding real position to state: {sym}")
        avg_price = act.get("ppc", act.get("ultimoPrecio", 0))
        state["positions"][sym] = {
            "entry_price": avg_price,
            "qty": act["cantidad"],
            "sl": avg_price * 0.99,
            "tp": avg_price * 1.021,
            "step": 0,
            "buy_time": "2026-04-24 10:00:00" # Dummy
        }
    else:
        # Just ensure qty matches
        state["positions"][sym]["qty"] = act["cantidad"]

state["balance"] = iol.get_balance()

with open(STATE_FILE, "w") as f:
    json.dump(state, f, indent=4)

print("Resync complete.")
