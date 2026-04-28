from core.iol_client import IOLClient
import requests

iol = IOLClient()
iol.login()
url_t0 = f"{iol.base_url}/api/v2/bcba/Titulos/MSFT/Cotizacion?plazo=t0"
res_t0 = requests.get(url_t0, headers=iol.get_headers()).json()

url_t2 = f"{iol.base_url}/api/v2/bcba/Titulos/MSFT/Cotizacion?plazo=t2"
res_t2 = requests.get(url_t2, headers=iol.get_headers()).json()

print(f"T0: Ultimo Precio = {res_t0.get('ultimoPrecio')}, Fecha/Hora = {res_t0.get('fechaHora')}")
print(f"T2: Ultimo Precio = {res_t2.get('ultimoPrecio')}, Fecha/Hora = {res_t2.get('fechaHora')}")
