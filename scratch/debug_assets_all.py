
import sys
import os
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.iol_client import IOLClient

client = IOLClient()
if client.login():
    url_port = f"{client.base_url}/api/v2/portafolio/argentina"
    res_port = requests.get(url_port, headers=client.get_headers())
    data_port = res_port.json()
    print("--- ALL ASSETS ---")
    for asset in data_port.get("activos", []):
        print(f"{asset.get('simbolo')} | Moneda: {asset.get('moneda')} | Valorizado: {asset.get('valorizado')}")
