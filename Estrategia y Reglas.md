  Estrategia y Reglas de Oro - Trading Bot Pro

Este documento sirve como la "Constitución" del bot. Cualquier cambio en el código debe respetar estas reglas fundamentales.

## 1. Reglas de Operación Híbrida
*   **Modo Manual prioritario:** Cuando el bot está en modo manual, tiene prohibido iniciar nuevas posiciones. Solo se encarga de vigilar las salidas.
*   **Monitoreo de Alta Frecuencia:** El ciclo de revisión no debe superar los 3 segundos (actualmente configurado en 2s).
*   **Confirmación de SL:** Ante una ruptura de Stop Loss, el bot tiene un máximo de 3 segundos para confirmar y ejecutar la orden de venta.

## 2. Gestión de Salida y Ganancias
*   **Trailing Stop Loss:** La salida es dinámica. Por cada "salto" de precio a favor, el SL debe subir para asegurar el nuevo piso de ganancias.
*   **Regla del 2% (EOD):** A las 16:50, cualquier posición con una ganancia actual > 2% debe ser liquidada inmediatamente para cerrar el día "en verde".
*   **Protección de Capital:** El sistema de SL debe ser la máxima prioridad. Nunca se debe pausar el monitoreo de SL mientras haya posiciones abiertas.

## 3. Visualización y Transparencia
*   **Métrica ARS Pura:** La valorización se calcula sumando exclusivamente el Disponible para Operar (ARS) y el valor de los Activos en el mercado local.
*   **Referencia de Depósitos:** El rendimiento se calcula contra el `total_invested` declarado, que debe coincidir con la suma de depósitos reales.

## 4. Parámetros Críticos (Base)
*   **Score de Compra Mínimo:** 9.5 (Muy conservador).
*   **Riesgo por Operación:** ~10% del balance disponible (configurable).
