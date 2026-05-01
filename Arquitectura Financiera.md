# 💰 Arquitectura Financiera

Lógica de costos y rentabilidad aplicada al bot.

## 🏆 Categoría de Broker: BLACK (IOL)
- **Requisito:** Volumen mensual > $50,000,000.
- **Comisión Base:** 0.1%.
- **Costos Adicionales:** Derechos de Mercado (0.05%) + IVA.
- **Costo Total Roundtrip:** **0.32%** (In + Out).

## 📉 Parámetros de Trading
- **Break-even:** Punto exacto donde la operación cubre costos. Se calcula sobre un factor de 1.0032.
- **Valorización Total:** Precio de Mercado x Cantidad. El dato clave para entender la exposición nominal.
- **Equity Curve:** Evolución acumulada del profit neto, descontando comisiones de categoría [[BLACK]].

## 📋 Auditoría de Volumen
- El volumen se verifica mediante scripts de auditoría en la [[Base de Datos y Estados]] para asegurar que siempre operemos en la categoría de comisión correcta.

## 🔗 Relaciones
- Conecta con: [[Estrategia y Reglas]], [[Reglas de Oro y Contexto]].
