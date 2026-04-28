from core.iol_client import IOLClient
import json
import requests

iol = IOLClient()
iol.login()
url = f"{iol.base_url}/api/v2/bcba/Titulos/MSFT/Cotizacion?plazo=t0"
res = requests.get(url, headers=iol.get_headers())
print("--- T0 QUOTE ---")
print(json.dumps(res.json(), indent=2))
