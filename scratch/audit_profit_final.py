
import pandas as pd
import sys

def clean_iol_monto(val):
    if pd.isna(val) or val == "" or val == "-": return 0.0
    s = str(val).strip()
    if not s: return 0.0
    
    # Si tiene coma, es formato estándar 1.234,56
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    else:
        # Si NO tiene coma y es numérico, son centavos (ej: 94900 -> 949.00)
        try:
            # Si es un número muy grande pero sin puntos, es probable que sean centavos
            # Pero cuidado con montos redondos de millones.
            # Sin embargo, en IOL los centavos siempre vienen al final.
            return float(s) / 100.0
        except:
            return 0.0

try:
    dfs = pd.read_html("MovimientosHistoricos.xls")
    df = dfs[0]
    
    # Filtrar solo pesos
    df = df[df['Tipo Cuenta'].str.contains("Pesos", na=False)]
    
    # Limpiar columnas
    df['Monto_Num'] = df['Monto'].apply(clean_iol_monto)
    df['Comis_Num'] = df['Comis.'].apply(clean_iol_monto)
    df['Iva_Num'] = df['Iva Com.'].apply(clean_iol_monto)
    df['Imp_Num'] = df['Otros Imp.'].apply(clean_iol_monto)
    
    compras = df[df['Tipo Mov.'].str.contains("Compra", case=False, na=False)]
    ventas = df[df['Tipo Mov.'].str.contains("Venta", case=False, na=False)]
    depositos = df[df['Tipo Mov.'].str.contains("Depósito|Transferencia", case=False, na=False)]
    
    total_compras = compras['Monto_Num'].sum()
    total_ventas = ventas['Monto_Num'].sum()
    total_depositos = depositos['Monto_Num'].sum()
    
    total_comis = df['Comis_Num'].sum()
    total_iva = df['Iva_Num'].sum()
    total_imp = df['Imp_Num'].sum()
    total_fees = total_comis + total_iva + total_imp
    
    # El 'Monto' en IOL para compras y ventas YA INCLUYE comisiones e impuestos.
    # Es el flujo neto de caja.
    # Profit Realizado = Suma de flujos de Compras (-) y Ventas (+)
    realized_profit = total_ventas + total_compras
    
    print("--- AUDITORÍA DE MOVIMIENTOS (IOL EXCEL CORREGIDA) ---")
    print(f"Total Depositado:       ${total_depositos:,.2f}")
    print(f"Total en Compras:       ${abs(total_compras):,.2f}")
    print(f"Total en Ventas:        ${total_ventas:,.2f}")
    print("-" * 40)
    print(f"Comisiones (Puras):     ${total_comis:,.2f}")
    print(f"IVA Comisiones:         ${total_iva:,.2f}")
    print(f"Otros Impuestos:        ${total_imp:,.2f}")
    print(f"TOTAL GASTOS (Fees):    ${total_fees:,.2f}")
    print("-" * 40)
    print(f"PROFIT REALIZADO NETO:  ${realized_profit:,.2f}")
    print(f"Cant. Operaciones:      {len(compras) + len(ventas)} (C: {len(compras)}, V: {len(ventas)})")
    
    # Simulación de Cartera Actual
    # Valorización actual (según el bot)
    current_valuation = 25028510 # Valor hardcodeado del prompt para la comparativa
    
    print("\n--- BALANCE PATRIMONIAL ---")
    print(f"Total Invertido:        ${total_depositos:,.2f}")
    print(f"Valorización Actual:    ${current_valuation:,.2f}")
    print(f"PROFIT TOTAL (U+R):     ${current_valuation - total_depositos:,.2f}")
    print(f"Rendimiento Global:     {((current_valuation / total_depositos) - 1)*100:.2f}%")

except Exception as e:
    print(f"Error: {e}")
