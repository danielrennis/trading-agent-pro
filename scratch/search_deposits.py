
import sys
import os
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.iol_client import IOLClient

client = IOLClient()
if client.login():
    url_ops = f"{client.base_url}/api/v2/operaciones?fechaDesde=2024-01-01"
    res_ops = requests.get(url_ops, headers=client.get_headers())
    ops = res_ops.json()
    
    for op in ops:
        # Buscar el texto que dijo el usuario
        op_str = json.dumps(op)
        if "Depósito" in op_str or "Transferencia" in op_str or "Fondo" in op_str:
            print(f"ENCONTRADO: {op_str}")
