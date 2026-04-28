import yfinance as yf
import pandas as pd
import numpy as np

def run_simulation(symbol="NVDA", days=60):
    print(f"--- SIMULADOR DE 4 ESTRATEGIAS: {symbol} ---")
    
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{days}d", interval="1h")
    if df.empty:
        print("No data found.")
        return

    # Buscamos un punto de entrada alcista
    best_entry_idx = 0
    max_upside = 0
    for i in range(len(df) - 50):
        price_now = df.iloc[i]['Close']
        max_future = df.iloc[i:i+50]['High'].max()
        upside = (max_future / price_now) - 1
        if upside > max_upside:
            max_upside = upside
            best_entry_idx = i

    entry_price = df.iloc[best_entry_idx]['Close']
    df_sim = df.iloc[best_entry_idx:]

    print(f"Entrada: {df_sim.index[0]} a ${entry_price:.2f} | Upside: {max_upside*100:.2f}%\n")

    # --- A: Actual (Escalones fijos cada TP) ---
    curr_sl_a = entry_price * 0.99
    curr_tp_a = entry_price * 1.021
    active_a, exit_a, reason_a = True, 0, ""

    # --- C: TRAILING CONTINUO (Persiguiendo el precio) ---
    highest_price = entry_price
    curr_sl_c = entry_price * 0.99
    active_c, exit_c, reason_c = True, 0, ""

    # --- D: ESCALONES SIMÉTRICOS (Tu nueva propuesta 2% / 1%) ---
    curr_sl_d = entry_price * 0.99
    curr_tp_d = entry_price * 1.02
    active_d, exit_d, reason_d = True, 0, ""

    for _, row in df_sim.iterrows():
        high, low, close = row['High'], row['Low'], row['Close']

        # Sim A
        if active_a:
            if low <= curr_sl_a: exit_a = curr_sl_a; reason_a = "SL"; active_a = False
            elif high >= curr_tp_a:
                curr_sl_a = curr_tp_a * 0.988
                curr_tp_a = curr_tp_a * 1.01

        # Sim C (Trailing Continuo)
        if active_c:
            if low <= curr_sl_c: exit_c = curr_sl_c; reason_c = "SL"; active_c = False
            else:
                if high > highest_price:
                    highest_price = high
                    curr_sl_c = highest_price * 0.99

        # Sim D (Escalones 2% / 1%)
        if active_d:
            if low <= curr_sl_d: exit_d = curr_sl_d; reason_d = "SL"; active_d = False
            elif high >= curr_tp_d:
                # Al tocar el TP del 2%, el nuevo SL es 1% abajo del TP
                curr_sl_d = curr_tp_d * 0.99
                # Y el nuevo TP es 2% arriba del actual
                curr_tp_d = curr_tp_d * 1.02

    if active_a: exit_a = close; reason_a = "OPEN"
    if active_c: exit_c = close; reason_c = "OPEN"
    if active_d: exit_d = close; reason_d = "OPEN"

    def get_p(p): return ((p/entry_price)-1)*100

    print(f"RESULTADO A (Actual):    {get_p(exit_a):.2f}%")
    print(f"RESULTADO C (Continuo):  {get_p(exit_c):.2f}%")
    print(f"RESULTADO D (Propuesta): {get_p(exit_d):.2f}% 🔥")

if __name__ == "__main__":
    run_simulation("NVDA", 60)
    print("\n" + "="*40 + "\n")
    run_simulation("META", 60)
    print("\n" + "="*40 + "\n")
    run_simulation("TSLA", 60)
