
import pandas as pd
import sys

def clean_monto(val):
    if pd.isna(val): return 0
    if isinstance(val, str):
        # IOL format: 1.000,00
        return float(val.replace(".", "").replace(",", "."))
    return float(val)

try:
    dfs = pd.read_html("MovimientosHistoricos.xls")
    df = dfs[0]
    
    # Filtrar solo pesos
    df = df[df['Tipo Cuenta'].str.contains("Pesos", na=False)]
    
    # Limpiar columnas numéricas
    df['Monto_Num'] = df['Monto'].apply(clean_monto)
    df['Comis_Num'] = df['Comis.'].apply(clean_monto)
    df['Iva_Num'] = df['Iva Com.'].apply(clean_monto)
    df['Imp_Num'] = df['Otros Imp.'].apply(clean_monto)
    
    # Clasificar movimientos
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
    
    print("--- AUDITORÍA DE MOVIMIENTOS (IOL EXCEL) ---")
    print(f"Total Depositado:       ${total_depositos:,.2f}")
    print(f"Total en Compras:       ${abs(total_compras):,.2f}")
    print(f"Total en Ventas:        ${total_ventas:,.2f}")
    print("-" * 40)
    print(f"Comisiones (Puras):     ${total_comis:,.2f}")
    print(f"IVA Comisiones:         ${total_iva:,.2f}")
    print(f"Otros Impuestos:        ${total_imp:,.2f}")
    print(f"TOTAL GASTOS (Fees):    ${total_fees:,.2f}")
    print("-" * 40)
    
    # Profit realizado = Ventas - Compras (netas)
    # Nota: En IOL el 'Monto' de compra ya suele incluir la comisión restada o sumada?
    # Usualmente el Monto es lo que se debita o acredita.
    # Si Monto Compra = -100 y Comis = 1, entonces el costo real fue 100? O 101?
    # En IOL, el 'Monto' de una compra es el EFECTIVO TOTAL que salió (incluyendo comisiones).
    # Vamos a verificarlo con una fila.
    
    sample = compras.iloc[0]
    print(f"DEBUG COMPRA: Monto={sample['Monto_Num']}, Comis={sample['Comis_Num']}, IVA={sample['Iva_Num']}, Imp={sample['Imp_Num']}")
    
    # Profit Realizado = Suma de Ventas + Suma de Compras (que son negativas)
    # Si Ventas son +110 y Compras son -100, Profit = 10.
    realized_profit = total_ventas + total_compras 
    
    print(f"PROFIT REALIZADO NETO:  ${realized_profit:,.2f}")
    
    # Cantidad de operaciones
    print(f"Cant. Operaciones:      {len(compras) + len(ventas)} (Compras: {len(compras)}, Ventas: {len(ventas)})")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
