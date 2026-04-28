import json
from core.iol_client import IOLClient

iol = IOLClient()
iol.login()
port = iol.get_portfolio()
print("--- PORTFOLIO ---")
for act in port.get("activos", []):
    sym = act["titulo"]["simbolo"]
    print(f"{sym}: qty={act['cantidad']}, ppc={act['ppc']}, ultimoPrecio(port)={act.get('ultimoPrecio')}")

print("\n--- GET QUOTE ---")
for sym in ["MSFT", "AAPL", "TSLA", "TLCPO"]:
    q = iol.get_quote(sym)
    if q:
        print(f"{sym} (t2): {q.get('ultimoPrecio')}")
