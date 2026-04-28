import json
from core.iol_client import IOLClient
import requests

iol = IOLClient()
iol.login()

url1 = f"{iol.base_url}/api/v2/cuentas/estadocuenta"
resp1 = requests.get(url1, headers=iol.get_headers())
print(f"URL1 ({url1}) Status: {resp1.status_code}")

url2 = f"{iol.base_url}/api/v2/estadocuenta"
resp2 = requests.get(url2, headers=iol.get_headers())
print(f"URL2 ({url2}) Status: {resp2.status_code}")
