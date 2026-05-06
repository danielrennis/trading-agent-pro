import os
from core.iol_client import IOLClient
from dotenv import load_dotenv

load_dotenv()

client = IOLClient()
if client.login():
    print("✅ Login exitoso")
    portfolio = client.get_portfolio()
    if portfolio:
        print("✅ Portafolio obtenido correctamente")
        print(f"Total activos: {len(portfolio.get('activos', []))}")
else:
    print("❌ Error en el login")
