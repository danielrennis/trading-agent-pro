
import pandas as pd

def clean_iol_monto(val):
    if pd.isna(val) or val == "" or val == "-": return 0.0
    s = str(val).strip()
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    else:
        try: return float(s) / 100.0
        except: return 0.0

try:
    df = pd.read_html("MovimientosHistoricos.xls")[0]
    df = df[df['Tipo Cuenta'].str.contains("Pesos", na=False)]
    
    # Limpiar
    df['Monto_N'] = df['Monto'].apply(clean_iol_monto)
    df['Comis_N'] = df['Comis.'].apply(clean_iol_monto)
    df['Iva_N'] = df['Iva Com.'].apply(clean_iol_monto)
    df['Imp_N'] = df['Otros Imp.'].apply(clean_iol_monto)
    
    # Filtrar solo operativas
    ops = df[df['Tipo Mov.'].str.contains("Compra|Venta", case=False, na=False)].copy()
    
    # Calcular Monto Bruto (sin comisiones)
    # Compra: Monto es negativo. Bruto = abs(Monto) - (Comis+Iva+Imp)
    # Venta: Monto es positivo. Bruto = Monto + (Comis+Iva+Imp)
    def calc_bruto(row):
        total_fees = row['Comis_N'] + row['Iva_N'] + row['Imp_N']
        if "Compra" in row['Tipo Mov.']:
            return abs(row['Monto_N']) - total_fees
        else:
            return row['Monto_N'] + total_fees
            
    ops['Bruto'] = ops.apply(calc_bruto, axis=1)
    
    # Simulación 0.1%
    ops['Sim_Comis'] = ops['Bruto'] * 0.001
    ops['Sim_Iva'] = ops['Sim_Comis'] * 0.21
    ops['Sim_Total_Fees'] = ops['Sim_Comis'] + ops['Sim_Iva'] + ops['Imp_N']
    
    actual_total_fees = ops['Comis_N'].sum() + ops['Iva_N'].sum() + ops['Imp_N'].sum()
    simulated_total_fees = ops['Sim_Total_Fees'].sum()
    ahorro = actual_total_fees - simulated_total_fees
    
    print("--- SIMULACIÓN DE COMISIONES (0.5% vs 0.1%) ---")
    print(f"Volumen Operado Total (Bruto): ${ops['Bruto'].sum():,.2f}")
    print("-" * 45)
    print(f"GASTOS ACTUALES (0.5% + Imp):  ${actual_total_fees:,.2f}")
    print(f"GASTOS SIMULADOS (0.1% + Imp): ${simulated_total_fees:,.2f}")
    print("-" * 45)
    print(f"AHORRO POTENCIAL:             ${ahorro:,.2f}")
    print(f"Reducción de costos:          {(ahorro/actual_total_fees)*100:.2f}%")
    
    # Comparativa de Profit
    realized_profit_actual = ops[ops['Tipo Mov.'].str.contains("Venta")]['Monto_N'].sum() + ops[ops['Tipo Mov.'].str.contains("Compra")]['Monto_N'].sum()
    # Profit simulado = (Ventas Brutas - Sim Fees) - (Compras Brutas + Sim Fees)
    # Es equivalente a: Profit Actual + Ahorro
    realized_profit_sim = realized_profit_actual + ahorro
    
    print("\n--- IMPACTO EN PROFIT REALIZADO ---")
    print(f"Profit Realizado Actual:      ${realized_profit_actual:,.2f}")
    print(f"Profit Realizado con 0.1%:    ${realized_profit_sim:,.2f}")

except Exception as e:
    print(f"Error: {e}")
