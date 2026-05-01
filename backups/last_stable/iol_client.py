import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

class IOLClient:
    def __init__(self):
        self.base_url = "https://api.invertironline.com"
        self.username = os.getenv("IOL_USERNAME")
        self.password = os.getenv("IOL_PASSWORD")
        self.token = None
        self.refresh_token = None
        self.token_expiry = 0

    def login(self):
        """Authenticate with IOL and get access token."""
        url = f"{self.base_url}/token"
        data = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password"
        }
        try:
            response = requests.post(url, data=data)
            if response.status_code == 200:
                res_data = response.json()
                self.token = res_data["access_token"]
                self.refresh_token = res_data["refresh_token"]
                self.token_expiry = time.time() + res_data.get("expires_in", 3600)
                print("Login successful.")
                return True
            else:
                print(f"Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error during login: {e}")
            return False

    def _ensure_token(self):
        """Ensure token is still valid, refresh if necessary."""
        if not self.token or time.time() > self.token_expiry - 60:
            return self.login()
        return True

    def get_headers(self, force_refresh=False):
        if force_refresh:
            self.login()
        else:
            self._ensure_token()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_balances_all(self):
        """Fetch all available balances and calculate total valuation in Pesos."""
        url_acc = f"{self.base_url}/api/v2/estadocuenta"
        url_port = f"{self.base_url}/api/v2/portafolio/argentina"
        balances = {"t0": 0, "t1": 0, "t2": 0, "total": 0, "total_pesos": 0, "activos_valorizados": 0}
        
        try:
            # 1. Obtener saldos de efectivo (Cash)
            res_acc = requests.get(url_acc, headers=self.get_headers())
            if res_acc.status_code == 200:
                data = res_acc.json()
                max_disponible = 0
                for item in data.get("cuentas", []):
                    if item.get("moneda") == "peso_Argentino":
                        saldos = item.get("saldos", [])
                        for s in saldos:
                            liq = s.get("liquidacion")
                            disp = s.get("disponibleOperar", 0)
                            # El disponible total es lo que el broker permite operar (usualmente el máximo entre plazos)
                            if disp > max_disponible: max_disponible = disp
                            
                            if liq == "inmediato": balances["t0"] = disp
                            elif liq == "hrs24": balances["t1"] = disp
                            elif liq == "hrs48": balances["t2"] = disp
                balances["disponible_total"] = max_disponible
            
            # 2. Obtener valorización de activos (Stocks/Cedears)
            res_port = requests.get(url_port, headers=self.get_headers())
            total_assets_pesos = 0
            if res_port.status_code == 200:
                port = res_port.json()
                for asset in port.get("activos", []):
                    # Solo sumamos activos en Argentina (valen ARS)
                    total_assets_pesos += asset.get("valorizado", 0)
            
            balances["activos_valorizados"] = total_assets_pesos
            # CRITERIO HUGO: Disponible + Activos (Ignoramos el Saldo Total de IOL que incluye T+1/T+2 proyectado)
            balances["total_pesos"] = balances.get("disponible_total", 0) + total_assets_pesos
            
            return balances
        except Exception as e:
            print(f"Error fetching balances and valuation: {e}")
            return balances

    def get_balance(self):
        """Fetch available cash balance specifically for Contado Inmediato (T0)."""
        balances = self.get_balances_all()
        return balances["t0"]

    def get_portfolio(self):
        """Fetch current portfolio."""
        url = f"{self.base_url}/api/v2/portafolio/argentina"
        try:
            response = requests.get(url, headers=self.get_headers())
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error fetching portfolio: {e}")
            return None

    def get_quote(self, symbol, market="bcba", plazo="t2"):
        """Fetch real-time quote for a symbol."""
        url = f"{self.base_url}/api/v2/{market}/Titulos/{symbol}/Cotizacion?plazo={plazo}"
        try:
            response = requests.get(url, headers=self.get_headers())
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
            return None

    def place_order(self, symbol, quantity, price, action="Comprar", validity="t0", market="bCBA", retry=True):
        """Place a buy/sell order based on official documentation."""
        import datetime
        action_url = action.capitalize()
        url = f"{self.base_url}/api/v2/operar/{action_url}"
        
        # Fecha de validez: Hoy al final del día
        validez = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime("%Y-%m-%dT23:59:59Z")
        
        data = {
            "mercado": market,
            "simbolo": symbol,
            "cantidad": int(quantity),
            "precio": int(price) if price == int(price) else float(price),
            "plazo": validity,
            "validez": validez,
            "tipoOrden": "precioMercado" if price == 0 else "precioLimite"
        }
        
        try:
            print(f"DEBUG: Enviando orden a IOL (DOC FORM) -> {data}")
            response = requests.post(url, json=data, headers=self.get_headers())
            
            if response.status_code == 401 and retry:
                print("⚠️ Authorization denied. Retrying login and order...")
                response = requests.post(url, json=data, headers=self.get_headers(force_refresh=True))
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Order Failed: {response.status_code} - {response.text}")
                return {"error": response.status_code, "message": response.text}
        except Exception as e:
            print(f"Error placing order: {e}")
            return None
    def get_operations(self, state="terminadas"):
        """Fetch operation history from IOL (last 7 days)."""
        import datetime
        date_from = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        url = f"{self.base_url}/api/v2/operaciones?estado={state}&fechaDesde={date_from}"
        try:
            response = requests.get(url, headers=self.get_headers())
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            print(f"Error fetching operations: {e}")
            return []

    def get_official_rate(self):
        """Fetch current Dolar Oficial rate from DolarApi."""
        try:
            res = requests.get("https://dolarapi.com/v1/cotizaciones/oficial")
            if res.status_code == 200:
                return res.json().get("venta", 1415)
        except:
            pass
        return 1415 # Fallback para Mayo 2026

if __name__ == "__main__":
    client = IOLClient()
    if client.login():
        print(client.get_portfolio())
