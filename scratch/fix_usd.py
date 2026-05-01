import pandas as pd
import json
import os

file_path = "MovimientosHistoricos.xls"
config_file = "config.json"

try:
    dfs = pd.read_html(file_path)
    df = dfs[0]
    
    mask = (df['Tipo Mov.'].str.contains("Depósito|Transferencia", case=False, na=False)) & \
           (df['Tipo Cuenta'].str.contains("Pesos", case=False, na=False))
    depositos = df[mask]
    
    total_ars = 0
    total_usd_hist = 0
    for _, row in depositos.iterrows():
        monto_raw = str(row['Monto']).replace(".", "").replace(",", ".")
        monto = float(monto_raw)
        total_ars += monto
        
        fecha = str(row['Concert.'])
        # Tasas históricas de Abril 2026 (según registro de chat anterior)
        rate = 1415 # Default
        if "12/04" in fecha: rate = 1398
        elif "14/04" in fecha: rate = 1400
        elif "24/04" in fecha: rate = 1410
        elif "29/04" in fecha: rate = 1414
        elif "30/04" in fecha: rate = 1415
        total_usd_hist += monto / rate

    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        if "strategy" not in config: config["strategy"] = {}
        config["strategy"]["total_invested"] = total_ars
        config["strategy"]["total_invested_usd"] = total_usd_hist
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"ARS: {total_ars}")
        print(f"USD: {total_usd_hist}")
except Exception as e:
    print(f"Error: {e}")
