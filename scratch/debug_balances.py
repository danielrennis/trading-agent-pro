import os
import json
from core.iol_client import IOLClient
from dotenv import load_dotenv

load_dotenv()

client = IOLClient()
if client.login():
    print("✅ Login exitoso")
    balances = client.get_balances_all()
    print("Balances raw result:")
    print(json.dumps(balances, indent=4))
    
    # Debug estadocuenta
    url = f"{client.base_url}/api/v2/estadocuenta"
    import requests
    res = requests.get(url, headers=client.get_headers())
    print("\nEstadocuenta status:", res.status_code)
    if res.status_code == 200:
        print("Estadocuenta data snippet:")
        data = res.json()
        print(json.dumps(data, indent=4)[:1000]) # Solo los primeros 1000 chars
    else:
        print("Error en estadocuenta:", res.text)
else:
    print("❌ Error en el login")
