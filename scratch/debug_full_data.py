
import sys
import os
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.iol_client import IOLClient

client = IOLClient()
if client.login():
    # 1. Estado de cuenta
    url_acc = f"{client.base_url}/api/v2/estadocuenta"
    res_acc = requests.get(url_acc, headers=client.get_headers())
    print("--- ESTADO DE CUENTA ---")
    print(json.dumps(res_acc.json(), indent=4))
    
    # 2. Portafolio
    url_port = f"{client.base_url}/api/v2/portafolio/argentina"
    res_port = requests.get(url_port, headers=client.get_headers())
    print("\n--- PORTAFOLIO ---")
    print(json.dumps(res_port.json(), indent=4))

    # 3. Operaciones (para depósitos)
    # Buscamos depósitos en el historial de operaciones
    url_ops = f"{client.base_url}/api/v2/operaciones?estado=terminadas"
    res_ops = requests.get(url_ops, headers=client.get_headers())
    print("\n--- OPERACIONES ---")
    print(json.dumps(res_ops.json(), indent=4))
