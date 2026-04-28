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
        """Fetch all available balances by liquidation timeframe."""
        url = f"{self.base_url}/api/v2/estadocuenta"
        balances = {"t0": 0, "t1": 0, "t2": 0}
        try:
            response = requests.get(url, headers=self.get_headers())
            if response.status_code == 200:
                data = response.json()
                for item in data.get("cuentas", []):
                    if item.get("moneda") == "peso_Argentino":
                        saldos = item.get("saldos", [])
                        for s in saldos:
                            liq = s.get("liquidacion")
                            if liq == "inmediato": balances["t0"] = s.get("disponibleOperar", 0)
                            elif liq == "hrs24": balances["t1"] = s.get("disponibleOperar", 0)
                            elif liq == "hrs48": balances["t2"] = s.get("disponibleOperar", 0)
                return balances
            return balances
        except Exception as e:
            print(f"Error fetching balances: {e}")
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

if __name__ == "__main__":
    client = IOLClient()
    if client.login():
        print(client.get_portfolio())
