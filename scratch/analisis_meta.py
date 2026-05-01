
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
    
    # Filtrar solo META
    meta = df[df['Tipo Mov.'].str.contains("META", case=False, na=False)].copy()
    meta['Total_Fees'] = meta['Comis_N'] + meta['Iva_N'] + meta['Imp_N']
    
    print(f"--- ANÁLISIS DETALLADO: META ---")
    print(f"Cant. Operaciones: {len(meta)}")
    
    total_compras_monto = meta[meta['Tipo Mov.'].str.contains("Compra")]['Monto_N'].sum()
    total_ventas_monto = meta[meta['Tipo Mov.'].str.contains("Venta")]['Monto_N'].sum()
    total_fees = meta['Total_Fees'].sum()
    
    print(f"Total Gastado en Compras: ${abs(total_compras_monto):,.2f}")
    print(f"Total Recibido en Ventas: ${total_ventas_monto:,.2f}")
    print(f"Total Comisiones e Imp.:  ${total_fees:,.2f}")
    print("-" * 40)
    print(f"PROFIT REALIZADO META:    ${total_ventas_monto + total_compras_monto:,.2f}")
    
    # Ejemplos específicos
    print("\nÚltimas Operaciones Relevantes:")
    # Tomamos las filas 29 y 31 (fueron 226 títulos)
    row_v = meta[meta['Cant. titulos'] == '226'].iloc[0] # Venta
    row_c = meta[meta['Cant. titulos'] == '226'].iloc[1] # Compra
    
    print(f"VENTA:  {row_v['Cant. titulos']} x ${row_v['Precio']} | Neto: ${row_v['Monto_N']:,.2f} | Fees: ${row_v['Total_Fees']:,.2f}")
    print(f"COMPRA: {row_c['Cant. titulos']} x ${row_c['Precio']} | Neto: ${row_c['Monto_N']:,.2f} | Fees: ${row_c['Total_Fees']:,.2f}")
    
except Exception as e:
    print(f"Error: {e}")
