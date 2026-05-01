
import sys
import os
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.iol_client import IOLClient

client = IOLClient()
if client.login():
    url_ops = f"{client.base_url}/api/v2/operaciones"
    res_ops = requests.get(url_ops, headers=client.get_headers())
    ops = res_ops.json()
    tipos = set([o.get('tipo') for o in ops])
    print(f"Tipos encontrados: {tipos}")
    
    # Imprimir ejemplos de cada tipo que no sea Compra/Venta
    for t in tipos:
        if t not in ['Compra', 'Venta']:
            example = [o for o in ops if o.get('tipo') == t][0]
            print(f"Ejemplo de {t}: {json.dumps(example, indent=4)}")
