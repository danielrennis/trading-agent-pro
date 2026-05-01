
import sys
import os
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.iol_client import IOLClient
from datetime import datetime, timedelta

client = IOLClient()
if client.login():
    date_from = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    url_ops = f"{client.base_url}/api/v2/operaciones?fechaDesde={date_from}"
    res_ops = requests.get(url_ops, headers=client.get_headers())
    ops = res_ops.json()
    
    # Buscar tipos inusuales
    tipos = set([o.get('tipo') for o in ops])
    print(f"Tipos en el último año: {tipos}")
    
    # Buscar "Ingreso" o similares
    deposits = [o for o in ops if o.get('tipo') not in ['Compra', 'Venta']]
    print(f"Encontrados {len(deposits)} movimientos que no son compra/venta.")
    if deposits:
        print(json.dumps(deposits[:5], indent=4))
