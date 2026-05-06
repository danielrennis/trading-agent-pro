from core.iol_client import IOLClient
import json

client = IOLClient()
if client.login():
    port = client.get_portfolio()
    print(json.dumps(port, indent=2))
else:
    print("Login failed")
