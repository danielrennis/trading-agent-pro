# Roadmap: Pendientes y Mejoras

Lista de tareas y evoluciones para el Trading Bot Pro.

## 🔴 Prioridad Alta (Próximos Pasos)
- [ ] **Detección Proactiva de Depósitos:** Implementar lógica en el orquestador que detecte saltos >$1,000,000 en la valorización total (no explicados por ventas). Ante un salto, el bot enviará una alerta pidiendo el Excel de "Detalle de Movimientos" para procesarlo y actualizar la inversión total.
- [ ] **Rotación de Logs:** Implementar un sistema de rotación para `orchestrator.log` y `web_server.log` para evitar que ocupen demasiado espacio en disco.
- [ ] **Validación de Alertas Telegram:** Realizar una prueba de mercado real para confirmar que las notificaciones de "Cierre EOD" llegan correctamente.

## 🟡 Prioridad Media
- [ ] **Refinamiento de Indicadores:** Optimizar el peso de la EMA200 y el RSI en el cálculo del `buy_score`.
- [ ] **Panel de Estadísticas Históricas:** Crear una pestaña en la UI para ver gráficamente el crecimiento de la cuenta (Equity Curve).
- [ ] **Soporte Multi-Cuenta:** Estructurar el código para poder manejar más de una cuenta de IOL simultáneamente.

## 🟢 Mejoras de UX/UI
- [ ] **Modo Oscuro/Luz Toggle:** Permitir cambiar el tema desde el panel.
- [ ] **Sonidos de Alerta Personalizados:** Diferenciar el sonido de "Venta por SL" del de "Compra Exitosa".
- [ ] **Editor de Configuración en UI:** Permitir editar todos los parámetros del `config.json` directamente desde un formulario en el panel, sin tocar el archivo.

---
**Actualizado:** 2026-05-01
