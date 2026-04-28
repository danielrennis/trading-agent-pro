from core.iol_client import IOLClient
import os
from dotenv import load_dotenv

load_dotenv()
iol = IOLClient()
iol.login()
print("Quote NVDA:", iol.get_quote("NVDA"))
