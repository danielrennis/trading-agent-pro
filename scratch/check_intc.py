import sys
import os
sys.path.append(os.getcwd())

from core.iol_client import IOLClient
import json
from datetime import datetime

iol = IOLClient()
if iol.login():
    ops = iol.get_operations(state="terminadas")
    # Filtrar solo por hoy
    today = datetime.now().strftime("%Y-%m-%d")
    intc_ops = [op for op in ops if op.get('simbolo') == 'INTC']
    print(json.dumps(intc_ops, indent=4))
else:
    print("Error login")
