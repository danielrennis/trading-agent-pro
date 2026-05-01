
import sys
import os
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.iol_client import IOLClient

client = IOLClient()
if client.login():
    url = f"{client.base_url}/api/v2/estadocuenta"
    # El estado de cuenta ya trae los movimientos en algunas versiones
    # O tal vez es api/v2/movimientos/pesos? No.
    
    # Voy a probar api/v2/operaciones con estado 'todas'
    url_ops = f"{client.base_url}/api/v2/operaciones?estado=todas"
    res_ops = requests.get(url_ops, headers=client.get_headers())
    print(f"Total ops: {len(res_ops.json())}")
    for op in res_ops.json()[:20]:
        print(f"{op.get('tipo')} - {op.get('simbolo')} - {op.get('montoOperado')}")
