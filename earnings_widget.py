import webview
import yfinance as yf
import threading
import json
import os
from datetime import datetime
import webbrowser

WATCHLIST = {
    "Tech/Growth": ["AAPL", "TSLA", "NVDA", "AMZN", "AMD", "META", "MSFT", "GOOG", "INTC", "ORCL", "BABA"],
    "Fintech/Latam": ["NU", "MELI", "GGAL"],
    "Energía/Comm": ["YPF", "PBR", "VIST", "PAM"],
    "Consumo/Índices": ["KO", "PEP", "SPY"],
    "Locales (ARG)": ["ALUA.BA", "TGNO4.BA"]
}

CACHE_FILE = "earnings_cache.json"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body { 
            background-color: #121212; color: #e0e0e0; 
            font-family: 'Inter', sans-serif; margin: 0; padding: 20px;
            user-select: none;
        }
        h2 { text-align: center; font-size: 18px; margin-bottom: 20px; letter-spacing: 1px; color: #fff; }
        .ticker-list { display: flex; flex-direction: column; gap: 8px; }
        .ticker-card {
            background: #1e1e1e; border-radius: 8px; padding: 12px 15px;
            display: flex; justify-content: space-between; align-items: center;
            border-left: 4px solid #444; transition: transform 0.2s; cursor: pointer;
        }
        .ticker-card:hover { background: #252525; transform: scale(1.02); }
        .ticker-name { font-weight: bold; font-size: 14px; }
        .ticker-date { font-size: 12px; }
        .urgency-red { border-left-color: #ff5252; color: #ff5252; }
        .urgency-orange { border-left-color: #ffab40; color: #ffab40; }
        .urgency-green { border-left-color: #69f0ae; color: #69f0ae; }
        .status { 
            position: fixed; bottom: 0; left: 0; width: 100%; 
            background: #1a1a1a; font-size: 10px; color: #888; 
            padding: 5px 20px; border-top: 1px solid #333;
        }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }
    </style>
</head>
<body>
    <h2>🗓️ EARNINGS CALENDAR</h2>
    <div id="list" class="ticker-list">
        <p style="text-align:center; color:#888;">Sincronizando con IOL/Yahoo...</p>
    </div>
    <div class="status" id="status">Iniciando...</div>

    <script>
        function updateList(data) {
            const listDiv = document.getElementById('list');
            listDiv.innerHTML = '';
            
            // Ordenar
            const sorted = Object.keys(data).sort((a, b) => {
                const dA = data[a].date === 'N/A' ? '9999-12-31' : data[a].date;
                const dB = data[b].date === 'N/A' ? '9999-12-31' : data[b].date;
                return dA.localeCompare(dB);
            });

            sorted.forEach(ticker => {
                const info = data[ticker];
                const card = document.createElement('div');
                card.className = 'ticker-card';
                
                let urgency = '';
                if (info.date !== 'N/A') {
                    const diff = Math.floor((new Date(info.date) - new Date()) / (1000*60*60*24));
                    if (diff <= 1) urgency = 'urgency-red';
                    else if (diff <= 7) urgency = 'urgency-orange';
                    else urgency = 'urgency-green';
                }
                
                card.classList.add(urgency);
                card.onclick = () => pywebview.api.open_chart(ticker);
                card.onmouseenter = () => document.getElementById('status').innerText = ticker + ' - Est. EPS: ' + info.eps;
                
                card.innerHTML = `
                    <span class="ticker-name">${ticker}</span>
                    <span class="ticker-date">${info.date === 'N/A' ? 'TBA' : info.date}</span>
                `;
                listDiv.appendChild(card);
            });
        }

        function setStatus(msg) {
            document.getElementById('status').innerText = msg;
        }
    </script>
</body>
</html>
"""

class API:
    def __init__(self):
        self.window = None

    def open_chart(self, ticker):
        symbol = ticker.split('.')[0]
        webbrowser.open(f"https://www.tradingview.com/symbols/{symbol}/")

def fetch_data(window):
    all_tickers = [t for sub in WATCHLIST.values() for t in sub]
    data = {}
    
    # Intentar cargar cache primero
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                if data and list(data.values())[0].get('updated') == datetime.now().strftime("%Y-%m-%d"):
                    window.evaluate_js(f"updateList({json.dumps(data)})")
                    window.evaluate_js("setStatus('Datos de caché actualizados')")
                    # No retornamos, queremos refrescar igual si es necesario, 
                    # pero ya mostramos algo
        except: pass

    # Fetch real
    current_data = {}
    for i, ticker in enumerate(all_tickers):
        window.evaluate_js(f"setStatus('Consultando {ticker} ({i+1}/{len(all_tickers)})...')")
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            e_date, eps = "N/A", "N/A"
            if cal and isinstance(cal, dict):
                dates = cal.get('Earnings Date', [])
                if dates:
                    d = dates[0]
                    e_date = d.strftime("%Y-%m-%d") if hasattr(d, 'strftime') else str(d)
                eps = cal.get('Earnings Average', "N/A")
            
            current_data[ticker] = {"date": e_date, "eps": eps, "updated": datetime.now().strftime("%Y-%m-%d")}
            # Actualizar progresivamente
            window.evaluate_js(f"updateList({json.dumps(current_data)})")
        except:
            current_data[ticker] = {"date": "N/A", "eps": "N/A", "updated": datetime.now().strftime("%Y-%m-%d")}
    
    with open(CACHE_FILE, "w") as f:
        json.dump(current_data, f)
    window.evaluate_js("setStatus('Sincronización completa')")

if __name__ == "__main__":
    api = API()
    window = webview.create_window(
        'Earnings Calendar Pro', 
        html=HTML_TEMPLATE, 
        width=380, height=650, 
        on_top=True, 
        js_api=api,
        background_color='#121212'
    )
    api.window = window
    
    # Iniciar fetch en un hilo separado
    threading.Thread(target=fetch_data, args=(window,), daemon=True).start()
    
    webview.start(debug=False)
