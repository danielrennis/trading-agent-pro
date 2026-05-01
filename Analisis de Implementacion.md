# Análisis Técnico de Implementación - Trading Bot Pro

Este documento detalla la arquitectura y el estado actual del bot de trading tras la última fase de optimización y refinamiento.

## 1. Arquitectura del Sistema
El bot opera bajo una estructura de **tres capas** diseñada para alta frecuencia y resiliencia:

*   **Orquestador (`orchestrator.py`):** El motor central. Gestiona el bucle de monitoreo cada **2 segundos**. Utiliza procesamiento paralelo (`ThreadPoolExecutor`) para consultar cotizaciones simultáneamente, eliminando la latencia de la API de IOL.
*   **Servidor Web (`web_server.py`):** Expone una API para el control en tiempo real. Gestiona la configuración dinámicamente y permite la interacción desde el panel.
*   **Panel de Control (`panel/index.html`):** Interfaz premium construida en React con estética "Bento" y actualizaciones automáticas.

## 2. Modo Híbrido (Auto/Manual)
Se ha implementado un control granular sobre la ejecución de órdenes:
*   **Flag `auto_buy`:** Permite alternar entre trading 100% autónomo y un modo de "Asistente de Salida".
*   **Comportamiento Manual:** En este modo, el bot **no inicia nuevas posiciones**. Sin embargo, mantiene activas todas las protecciones de las posiciones abiertas (SL, TP y Trailing).

## 3. Gestión de Riesgo y Trailing Stop
El bot utiliza un motor de **Trailing Stop Loss dinámico**:
*   **Escalamiento (Saltos):** Cada vez que la acción sube un escalón definido, el bot actualiza el SL para asegurar ganancias.
*   **Persistencia Atómica:** Todos los niveles de SL/TP y la cantidad de "saltos" se guardan inmediatamente en `state.json`. Esto permite reiniciar el sistema sin perder el rastro de la estrategia.
*   **Confirmación Rápida:** El tiempo de ejecución tras detectar una ruptura de SL se ha reducido a **3 segundos**.

## 4. Lógica de Valorización Patrimonial
Se ha refinado la integración con IOL para reflejar la realidad del usuario en Argentina:
*   **Métrica Solo Pesos:** El bot desglosa la cuenta para mostrar únicamente activos y efectivo denominados en `peso_Argentino`. Excluye conversiones de dólares para evitar ruido por tipo de cambio.
*   **Fórmula:** `Total Patrimonio = Disponible para Operar (Max Liquidez) + Activos Valorizados (Portafolio AR)`.

## 5. Funcionalidades Especiales
*   **Liquidación EOD (Cierre de Jornada):** Entre las 16:50 y 17:00, el bot liquida automáticamente posiciones que tengan una ganancia actual mayor al **2%**, asegurando el cierre del día con saldo positivo.
*   **Seguridad de Pausa:** Implementación de "Kill Switch" que detiene procesos de forma segura y garantiza que no se ejecuten órdenes accidentales mientras el sistema está en pausa.

## 6. Estado de Archivos Clave
*   `config.json`: Contiene parámetros de estrategia (`min_buy_score`, `total_invested`, `auto_buy`).
*   `state.json`: Base de datos de posiciones activas, historiales y oportunidades detectadas.
*   `core/iol_client.py`: Versión optimizada del cliente IOL con manejo de tokens y errores de conexión.

---
**Última Actualización:** 2026-05-01
**Estado Operativo:** Activo / Sincronizado
