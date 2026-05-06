from core.iol_client import IOLClient
import json

client = IOLClient()
if client.login():
    ops = client.get_operations(state="terminadas")
    print(json.dumps(ops, indent=2))
else:
    print("Login failed")
