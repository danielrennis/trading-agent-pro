# 🤖 Trading Agent — Multi-agente para CEDEARs en IOL

Sistema de trading automático anti-emocional para operar CEDEARs en BCBA vía IOL Invertironline.

## Arquitectura

```
Agente Técnico      → EMA 20/50/200 · Stoch RSI · Volumen · Patrones (corre cada 1 min)
Agente Noticias     → Yahoo Finance + Claude API para clasificar sentimiento (cada 30 min)
Agente Estratega    → Pondera señales, decide qué activo operar
Trailing Engine     → Escalones dinámicos SL/TP sin intervención humana
Orquestador         → Coordina todo, ejecuta en IOL
Panel Web           → Control en tiempo real desde browser o celular (misma red WiFi)
Telegram            → Notificaciones instantáneas de cada operación
```

## Instalación rápida

```bash
chmod +x setup.sh
./setup.sh
```

## Configuración

Editá `.env`:
```
IOL_USER=tu_usuario
IOL_PASS=tu_contraseña
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
```

## Uso

```bash
# 1. Backtesting (OBLIGATORIO antes de operar real)
npm run backtest

# 2. Arrancar agente
npm start

# 3. Panel de control
# Abrí en el browser: http://localhost:3001/panel
# Desde el celular (misma WiFi): http://<IP-MAC>:3001/panel
```

## Lógica de trading

### Scoring combinado
- **Técnico 40%**: EMA 20/50/200 · Stoch RSI · Volumen · Patrones de velas
- **Noticias 30%**: Sentimiento de headlines últimas 24h via Claude API
- **Estratega 30%**: Alineación de señales · penalización por eventos críticos

### Trailing escalonado
```
Entrada → SL: -1% | TP: +2.1% (= +1% neto)
Precio toca TP → nuevo SL: TP anterior -1% | nuevo TP: TP anterior +1.1%
Precio toca SL → VENDE automáticamente
Repite hasta que el precio se dé vuelta 1% desde un máximo
```

### Protecciones
- Pérdida máxima diaria: -0.5% del capital total
- Cierre forzado a las 16:40 (5 min antes del cierre BCBA)
- Máximo 1 posición abierta por vez
- No opera si hay earnings o evento crítico (score penalizado)
- Rotación automática: si NVDA está bajista → analiza AMD

## Panel de control

Desde el panel podés en tiempo real:
- Ver P&L del día, scores y posición abierta con escalones
- Ajustar SL/TP con sliders → se aplica inmediatamente
- Pausar/reanudar el agente
- Cambiar los activos monitoreados
- Ver análisis de noticias por activo

## Horario de operación

Lunes a viernes · 10:30 – 16:40 (hora Argentina)
La Mac debe estar encendida y conectada a internet en ese horario.

```bash
# Mantener Mac despierta en horario de mercado:
caffeinate -i -t 22500 &
```

## Activos soportados

NVDA · AMD · MSFT · INTC · META · AAPL (todos como CEDEARs en BCBA)

Configurables desde el panel en tiempo real.

## Estructura de archivos

```
trading-agent/
├── config/settings.js      → Parámetros centrales
├── core/
│   ├── orchestrator.js     → Loop principal
│   ├── iol-client.js       → API de IOL
│   ├── state.js            → Estado global persistido
│   ├── trailing.js         → Motor de trailing escalonado
│   ├── panel-server.js     → API REST + WebSocket
│   └── telegram.js         → Notificaciones
├── agents/
│   ├── technical.js        → Agente técnico
│   ├── news.js             → Agente noticias
│   └── strategy.js         → Agente estratega
├── backtest/runner.js      → Simulación 6 meses
├── panel/index.html        → Dashboard web
├── logs/state.json         → Estado persistido (auto-generado)
└── .env                    → Credenciales (no commitear)
```
