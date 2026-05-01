
import sys
import os
import requests
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.iol_client import IOLClient

client = IOLClient()
if client.login():
    url = f"{client.base_url}/api/v2/movimientos"
    response = requests.get(url, headers=client.get_headers())
    print(json.dumps(response.json(), indent=4))
