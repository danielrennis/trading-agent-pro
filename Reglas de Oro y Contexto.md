# ⚖️ Reglas de Oro y Contexto Operativo

Estas son las leyes fundamentales que rigen el desarrollo y la operación del [[Trading Bot Agent Pro]].

## 🇦🇷 Contexto Regional
- **Zona Horaria:** Buenos Aires, Argentina (GMT-3).
- **Lenguaje:** Técnico, directo y profesional. Sin condescendencia.
- **Mercado:** Foco en BYMA (Acciones y CEDEARs) y Obligaciones Negociables (ONs).

## 🛡️ Protocolo de Seguridad y Calidad
- **Base de Oro (Git):** Cada cambio funcional DEBE ser precedido por un commit de respaldo. Si algo rompe, se vuelve al commit anterior.
- **Sin Fragmentos:** El código se entrega siempre en archivos completos para evitar errores de integración.
- **No Suposiciones:** Ante dudas sobre datos (ej. Volumen), se ejecutan scripts de auditoría sobre [[Base de Datos y Estados]] para obtener el dato puro. No se interpretan comas o puntos a ojo.

## 🤖 Autonomía del Sistema
- **Polling Permanente:** El refresco de 5 segundos es innegociable. El bot debe ser capaz de operar sin intervención humana.
- **Consistencia:** Las listas de [[Cartera Activa]] y [[Watchlist]] deben mantenerse siempre en orden alfabético.

## 🔗 Relaciones
- Conecta con: [[Arquitectura Financiera]], [[Manual de Estilo y UX]].
