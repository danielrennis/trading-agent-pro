
import sys
import os
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.iol_client import IOLClient

client = IOLClient()
if client.login():
    url_ops = f"{client.base_url}/api/v2/operaciones?fechaDesde=2010-01-01"
    res_ops = requests.get(url_ops, headers=client.get_headers())
    ops = res_ops.json()
    
    # Ver si hay algo que no sea Compra/Venta
    unique_types = set([o.get('tipo') for o in ops])
    print(f"Tipos desde el inicio: {unique_types}")
    
    # Buscar depósitos en el texto de la descripción si existe
    # o si el símbolo es vacío
    for o in ops:
        if o.get('tipo') not in ['Compra', 'Venta']:
            print(f"MOVIMIENTO: {o}")
