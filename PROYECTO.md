# 💹 TRADING BOT PRO - Memoria del Proyecto

## 📌 Estado Actual (01/05/2026)
El sistema se encuentra operativo y optimizado para el mercado de Argentina (IOL), con foco en la precisión bimonetaria y la mitigación de riesgos por volatilidad nocturna (Overnight Gaps).

## 🎮 Modos de Operación (Presets)
El bot soporta 3 perfiles tácticos seleccionables desde el Dashboard:
- **🚀 AGRESIVO:** SL 1% | TP 1.5% | Trailing SL 0.5%. (Para scalping en mercados alcistas).
- **⚖️ NORMAL:** SL 2% | TP 3% | Trailing SL 1.2%. (Estrategia equilibrada).
- **🛡️ CONSERVADOR:** SL 4% | TP 8% | Trailing SL 3%. (Para capturar tendencias largas en mercados volátiles).

---

## 🏆 PROTOCOLO DE SEGURIDAD (Blindaje de Oro)
1. **Regla de Diamante (NUEVA):** Todo cambio exitoso confirmado por el usuario se guarda mediante `git commit`. Es la base inamovible para el siguiente paso.
2. **Rollback Instantáneo:** Ante cualquier error o disconformidad, se ejecuta `git checkout .` para volver al último estado de "Oro".
3. **Diseño Financiero:** Los montos siempre alineados a la **derecha** (`text-right`) y los u$d en **verde esmeralda** (`text-emerald-400`).

---

## 🛠️ Configuración del Motor (Estrategia)
Los parámetros activos son gestionables desde el Dashboard y se persisten en `config.json`.

### 1. Gestión de Salida (Trailing Engine)
- **Stop Loss Inicial:** 2.0% (Protección base al comprar).
- **Take Profit Inicial:** 1.5% (Objetivo de ganancia base).
- **Trailing Stop Loss:** 1.2% (Distancia del SL dinámico).
- **Trailing Take Profit:** 1.0% (Distancia del TP dinámico).

### 2. Gestión de Riesgo y Capital
- **Riesgo por Operación:** 10% del patrimonio total por cada activo.
- **Monto Fijo:** Configurado en $1.000.000 para estandarizar entradas.
- **Inversión Total Detectada (Histórica):** $12.300.000.
- **Criterio de Valorización:** `Disponible para Operar + Activos Valorizados` (Ignora saldos proyectados de IOL).

### 3. Protección EOD (End Of Day) - *NUEVO*
Implementado para evitar pérdidas por malas noticias internacionales fuera de hora (Gap-down de Meta/MSFT).
- **Modos:**
    - `selective`: Liquida posiciones con ganancia > 1.5% a las 16:50 hs.
    - `full`: Liquida toda la cartera a las 16:50 hs para dormir 100% en efectivo.
    - `off`: Mantenimiento de posiciones.

---

## 📊 Auditoría y Rendimiento
- **Profit Real Total:** ~$1.4M (11.35% de rendimiento global en 4 días).
- **Costo Operativo (Comisiones):** ~$406k (Representa el 3.2% del volumen movido).
- **Conversión Bimonetaria:** Basada en **Dólar Oficial Real** (Fuente Ámbito/DolarApi) para cálculos históricos rigurosos.

---

## 🚀 Próximos Pasos
1.  **Refinamiento de Señales:** Analizar por qué el bot dio compra en META a $41.9k justo antes de la caída.
2.  **Optimización de Comisiones:** Si se logra bajar la comisión al 0.1%, el ahorro proyectado es del 61% de los gastos actuales.
3.  **UI Avanzada:** Dashboard con controles totales de variables de estrategia.

---
*Ultima actualización: 01/05/2026 11:45 AR*
