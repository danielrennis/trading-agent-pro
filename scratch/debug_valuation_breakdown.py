
import sys
import os
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.iol_client import IOLClient

client = IOLClient()
if client.login():
    url_acc = f"{client.base_url}/api/v2/estadocuenta"
    url_port = f"{client.base_url}/api/v2/portafolio/argentina"
    
    # 1. Cash
    res_acc = requests.get(url_acc, headers=client.get_headers())
    data_acc = res_acc.json()
    print("--- CASH BREAKDOWN (PESOS) ---")
    cash_pesos = 0
    for item in data_acc.get("cuentas", []):
        if item.get("moneda") == "peso_Argentino":
            for s in item.get("saldos", []):
                print(f"Liquidez {s.get('liquidacion')}: Saldo={s.get('saldo')}, Disponible={s.get('disponibleOperar')}")
                cash_pesos += s.get('saldo', 0)
    print(f"TOTAL CASH PESOS: {cash_pesos}")

    # 2. Assets
    res_port = requests.get(url_port, headers=client.get_headers())
    data_port = res_port.json()
    print("\n--- ASSET BREAKDOWN (PESOS) ---")
    assets_pesos = 0
    for asset in data_port.get("activos", []):
        if asset.get("moneda") == "peso_Argentino":
            print(f"{asset.get('simbolo')}: {asset.get('valorizado')}")
            assets_pesos += asset.get('valorizado', 0)
    print(f"TOTAL ASSETS PESOS: {assets_pesos}")
    
    print(f"\nGRAND TOTAL PESOS (CASH + ASSETS): {cash_pesos + assets_pesos}")
    print(f"IOL 'totalEnPesos' (Global): {data_acc.get('totalEnPesos')}")
