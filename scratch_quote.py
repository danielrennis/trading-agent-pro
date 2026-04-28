from core.iol_client import IOLClient
import json

iol = IOLClient()
iol.login()
print("--- DEFAULT QUOTE ---")
res = iol.get_quote("MSFT")
print(json.dumps(res, indent=2))
