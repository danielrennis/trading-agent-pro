from core.iol_client import IOLClient
iol = IOLClient()
iol.login()
res = iol.place_order("TLCPO", 1000000, 164000, action="vender") # Not enough qty, should fail
print("Response:", res)
