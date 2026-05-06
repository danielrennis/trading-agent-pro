import requests
import os
import time
from dotenv import load_dotenv
from core.api_logger import log_api_call, log_generic

load_dotenv()

class IOLClient:
    def __init__(self):
        self.base_url = "https://api.invertironline.com"
        self.username = os.getenv("IOL_USERNAME")
        self.password = os.getenv("IOL_PASSWORD")
        self.access_token = None
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
                log_generic("Login exitoso en IOL.")
                return True
            else:
                log_generic(f"Error en login: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            log_generic(f"Excepción en login: {e}")
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
        balances = {"t0": 0, "t1": 0, "t2": 0, "total": 0, "total_pesos": 0, "activos_valorizados": 0, "disponible_total": 0}
        
        try:
            headers = self.get_headers()
            # 1. Obtener saldos de efectivo (Cash)
            res_acc = requests.get(url_acc, headers=headers)
            if res_acc.status_code == 200:
                data = res_acc.json()
                max_disponible = 0
                for item in data.get("cuentas", []):
                    moneda = item.get("moneda", "").lower()
                    if "peso" in moneda:
                        saldos = item.get("saldos", [])
                        for s in saldos:
                            liq = s.get("liquidacion", "").lower()
                            disp = s.get("disponibleOperar", 0)
                            if disp > max_disponible: max_disponible = disp
                            if "inmediato" in liq or "t0" in liq: balances["t0"] = disp
                            elif "24" in liq or "t1" in liq: balances["t1"] = disp
                            elif "48" in liq or "t2" in liq: balances["t2"] = disp
                balances["disponible_total"] = max_disponible
            
            # 2. Obtener valorización de activos (Stocks/Cedears)
            res_port = requests.get(url_port, headers=headers)
            total_assets_pesos = 0
            if res_port.status_code == 200:
                port = res_port.json()
                activos = port.get("activos", [])
                
                # DEBUG LOG
                with open("api_debug.log", "a") as f:
                    from datetime import datetime
                    f.write(f"[{datetime.now()}] Portafolio fetched: {len(activos)} activos found.\n")
                
                for asset in activos:
                    # Fallback robusto para valorización
                    val = asset.get("valorizado", 0)
                    if val == 0:
                        # Si 'valorizado' no existe o es 0, calculamos: ultimoPrecio * cantidad
                        # IOL a veces usa 'precioPropio' o 'ultimoPrecio'
                        precio = asset.get("ultimoPrecio", asset.get("precioPropio", 0))
                        cant = asset.get("cantidad", 0)
                        val = precio * cant
                    
                    total_assets_pesos += val
            
            balances["activos_valorizados"] = total_assets_pesos
            balances["total_pesos"] = balances["disponible_total"] + total_assets_pesos
            
            # Fallback final si todo falla pero sabemos que hay activos (usando state)
            if balances["total_pesos"] == 0:
                # Intentamos leer el último estado guardado para no mostrar 0 si la API falló momentáneamente
                try:
                    if os.path.exists("state.json"):
                        with open("state.json", "r") as f:
                            s = json.load(f)
                            # Si en el state tenemos posiciones, calculamos una valoración rápida
                            temp_total = 0
                            for symbol, p in s.get("positions", {}).items():
                                temp_total += p.get("current_price", p.get("entry_price", 0)) * p.get("qty", 0)
                            if temp_total > 0:
                                balances["total_pesos"] = temp_total + balances["disponible_total"]
                except: pass

            return balances
        except Exception as e:
            with open("api_debug.log", "a") as f:
                f.write(f"[{datetime.now()}] Error in get_balances_all: {e}\n")
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
            if response.status_code == 200:
                log_generic("Sincronización de Portafolio exitosa.")
                return response.json()
            else:
                log_generic(f"Falla sincronización portafolio: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching portfolio: {e}")
            return None

    def get_quote(self, symbol, market="bcba", plazo="t2"):
        """Fetch real-time quote for a symbol."""
        url = f"{self.base_url}/api/v2/{market}/Titulos/{symbol}/Cotizacion?plazo={plazo}"
        try:
            response = requests.get(url, headers=self.get_headers())
            res = response.json() if response.status_code == 200 else None
            if res:
                log_generic(f"Consulta Cotización: {symbol} ({plazo}) -> ${res.get('ultimoPrecio')}")
            return res
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
            return None

    def place_order(self, symbol, quantity, price, action="Comprar", validity="t0", market="BCBA", order_type_str=None, retry=True):
        """Place a buy/sell order based on official documentation."""
        import datetime
        action_name = action.capitalize()
        url = f"{self.base_url}/api/v2/operar/{action_name}"
        
        # Fecha de validez: Hoy al final del día
        validez = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime("%Y-%m-%dT23:59:59Z")
        
        # Determinar tipo de orden
        if order_type_str:
            tipo_orden = "precioMercado" if order_type_str.lower() == "market" else "precioLimite"
        else:
            tipo_orden = "precioMercado" if price == 0 else "precioLimite"
        
        # Obtener precio de referencia para cálculos o límite
        send_price = price
        if send_price == 0:
            quote = self.get_quote(symbol, plazo=validity)
            if quote:
                send_price = quote.get("ultimoPrecio", 0)

        # IOL API Rules: 
        # IOL NO PERMITE órdenes a mercado ("precioMercado") en Contado Inmediato (t0) para Acciones/CEDEARs.
        # Por lo tanto, si estamos en t0 o el usuario pidió market, forzamos "precioLimite" con el precio actual.
        if validity.lower() == "t0" and tipo_orden == "precioMercado":
            tipo_orden = "precioLimite"

        # Armar el payload estándar (cantidad y precio son obligatorios para precioLimite)
        data = {
            "mercado": market,
            "simbolo": symbol,
            "cantidad": int(quantity),
            "precio": round(float(send_price), 2),
            "plazo": validity,
            "validez": validez,
            "tipoOrden": tipo_orden
        }
        
        try:
            print(f"🌐 [IOL API] Enviando {action_name} {symbol} | Cant: {quantity} | Precio: {price} | Tipo: {tipo_orden}", flush=True)
            response = requests.post(url, json=data, headers=self.get_headers())
            
            if response.status_code == 401 and retry:
                print("⚠️ Token vencido. Re-autenticando...", flush=True)
                response = requests.post(url, json=data, headers=self.get_headers(force_refresh=True))
            
            res_data = response.json() if response.status_code in [200, 201, 400] else {"error": response.status_code, "message": response.text}
            
            # Registrar en el log de actividad
            log_api_call(action_name, symbol, quantity, price, validity, res_data)
            
            if response.status_code in [200, 201]:
                return res_data
            else:
                print(f"❌ Orden Fallida: {response.status_code} - {response.text}", flush=True)
                return res_data
        except Exception as e:
            err_msg = f"Error fatal en place_order: {e}"
            print(f"❌ {err_msg}", flush=True)
            log_api_call(action_name, symbol, quantity, price, validity, {"error": "EXCEPTION", "message": str(e)})
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

