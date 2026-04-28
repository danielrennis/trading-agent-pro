from core.iol_client import IOLClient
import os
from dotenv import load_dotenv

load_dotenv()
print("Testing IOL Login...")
iol = IOLClient()
if iol.login():
    print("Login SUCCESS!")
    print("Portfolio:", iol.get_portfolio())
else:
    print("Login FAILED!")
