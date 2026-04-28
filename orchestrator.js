// core/orchestrator.js
// Cerebro del sistema: coordina los 3 agentes y ejecuta operaciones

import 'dotenv/config'
import cron from 'node-cron'
import chalk from 'chalk'
import { ASSETS, TRADING, SCORING } from '../config/settings.js'
import { loadState, getState, getConfig, updatePosition, addPnL, hasOpenPosition, getPosition } from './state.js'
import { getQuote, getBalance, placeOrder } from './iol-client.js'
import { initTrailing, updateTrailing, calcPnL } from './trailing.js'
import { runTechnicalAgent } from '../agents/technical.js'
import { runNewsAgent } from '../agents/news.js'
import { combineScores, selectBestAsset, makeDecision } from '../agents/strategy.js'
import { sendTelegram } from './telegram.js'
import { startPanel } from './panel-server.js'

// Cache de noticias (se actualizan cada 30 min)
let newsCache = {}
let lastNewsUpdate = 0

// ── Helpers de tiempo ────────────────────────────────────────────────────────
function isMarketOpen() {
  const now = new Date()
  const tz  = new Intl.DateTimeFormat('es-AR', {
    timeZone: TRADING.timezone,
    hour: '2-digit', minute: '2-digit', hour12: false
  }).format(now)
  const [h, m] = tz.split(':').map(Number)
  const mins = h * 60 + m
  const open  = 10 * 60 + 30   // 10:30
  const close = 16 * 60 + 45   // 16:45
  const day = now.toLocaleDateString('es-AR', { timeZone: TRADING.timezone, weekday: 'short' })
  if (['sáb', 'dom'].includes(day)) return false
  return mins >= open && mins <= close
}

function shouldForceClose() {
  const now = new Date()
  const tz  = new Intl.DateTimeFormat('es-AR', {
    timeZone: TRADING.timezone,
    hour: '2-digit', minute: '2-digit', hour12: false
  }).format(now)
  const [h, m] = tz.split(':').map(Number)
  return h === 16 && m >= 40
}

// ── Actualizar noticias (cada 30 min) ────────────────────────────────────────
async function refreshNews() {
  const now = Date.now()
  if (now - lastNewsUpdate < TRADING.newsIntervalMs) return
  console.log(chalk.cyan('\n[orquestador] Actualizando noticias...'))
  for (const symbol of ASSETS) {
    newsCache[symbol] = await runNewsAgent(symbol)
  }
  lastNewsUpdate = now
}

// ── Tick principal (cada 1 minuto) ───────────────────────────────────────────
async function tick() {
  if (!isMarketOpen()) return

  const config = getConfig()
  if (config.paused) {
    console.log(chalk.yellow('[orquestador] Sistema pausado'))
    return
  }

  console.log(chalk.bold(`\n[${new Date().toLocaleTimeString('es-AR')}] ── TICK ──────────────────`))

  try {
    // 1. Actualizar noticias si corresponde
    await refreshNews()

    // 2. Correr agente técnico para todos los activos
    const technicalScores = await Promise.all(
      ASSETS.map(s => runTechnicalAgent(s))
    )

    // 3. Combinar scores con noticias
    const allScores = technicalScores.map(tech => {
      const news    = newsCache[tech.symbol] ?? { score: 5, sentiment: 0, summary: '', critical: false, avoid: false }
      const combined = combineScores(tech, news)
      return { symbol: tech.symbol, combined, technical: tech, news }
    })

    // 4. Verificar posiciones abiertas → trailing
    for (const { symbol, combined, technical } of allScores) {
      if (!hasOpenPosition(symbol)) continue

      const quote    = await getQuote(symbol)
      const trailing = updateTrailing(symbol, quote.price)
      const pos      = getPosition(symbol)

      console.log(chalk.blue(`[${symbol}] precio: $${quote.price.toFixed(2)} | step: ${trailing.step} | P&L: ${(trailing.pnlPct * 100).toFixed(2)}%`))

      // Cierre forzado al final del día
      if (shouldForceClose()) {
        console.log(chalk.red(`[orquestador] Cierre forzado fin de día → ${symbol}`))
        await executeSell(symbol, quote.price, pos, 'Cierre forzado 16:40')
        continue
      }

      if (trailing.action === 'sell') {
        await executeSell(symbol, quote.price, pos, trailing.reason)
      } else if (trailing.action === 'advance') {
        await sendTelegram(`📈 *${symbol}* escalón ${trailing.step} | nuevo SL: $${trailing.newSL?.toFixed(2)} | TP: $${trailing.newTP?.toFixed(2)} | P&L: +${(trailing.pnlPct * 100).toFixed(2)}%`)
      }
    }

    // 5. Seleccionar mejor activo para nueva entrada
    const openPositions = ASSETS.filter(s => hasOpenPosition(s))
    if (openPositions.length < TRADING.maxActiveAssets) {
      const best = selectBestAsset(allScores)
      if (best && !hasOpenPosition(best.symbol)) {
        const decision = makeDecision({
          symbol:   best.symbol,
          combined: best.combined,
          technical: best.technical,
          news:      best.news,
          position:  null
        })
        if (decision.action === 'buy') {
          const quote   = await getQuote(best.symbol)
          const balance = await getBalance()
          const amount  = Math.floor(balance.ars * config.capitalPct)
          if (amount > 5000) {
            await executeBuy(best.symbol, quote.price, amount, decision.reason)
          } else {
            console.log(chalk.yellow(`[orquestador] Saldo insuficiente: $${balance.ars}`))
          }
        } else {
          console.log(chalk.gray(`[orquestador] ${best?.symbol ?? 'N/A'} → ${decision.action}: ${decision.reason}`))
        }
      }
    }

  } catch (e) {
    console.error(chalk.red('[orquestador] Error en tick:'), e.message)
  }
}

// ── Ejecutar compra ──────────────────────────────────────────────────────────
async function executeBuy(symbol, price, amount, reason) {
  console.log(chalk.green(`\n[orquestador] COMPRANDO ${symbol} | $${amount} ARS | razón: ${reason}`))
  try {
    const order = await placeOrder({ symbol, side: 'buy', amount })
    initTrailing(symbol, price)
    updatePosition(symbol, { orderId: order.numero, amount })
    const config = getConfig()
    const sl = price * (1 + config.sl)
    const tp = price * (1 + config.tp)
    await sendTelegram(`🟢 *COMPRA* ${symbol}\nPrecio: $${price.toFixed(2)}\nMonto: $${amount.toLocaleString()} ARS\nSL: $${sl.toFixed(2)} | TP: $${tp.toFixed(2)}\nRazón: ${reason}`)
  } catch (e) {
    console.error(chalk.red(`[orquestador] Error comprando ${symbol}:`), e.message)
  }
}

// ── Ejecutar venta ───────────────────────────────────────────────────────────
async function executeSell(symbol, price, position, reason) {
  console.log(chalk.red(`\n[orquestador] VENDIENDO ${symbol} | razón: ${reason}`))
  try {
    const amount = position.amount ?? 0
    const pnl    = calcPnL(symbol, price, amount)
    await placeOrder({ symbol, side: 'sell', amount })
    addPnL(pnl)
    updatePosition(symbol, null)
    const pnlPct = ((price - position.entryPrice) / position.entryPrice * 100).toFixed(2)
    await sendTelegram(`🔴 *VENTA* ${symbol}\nPrecio: $${price.toFixed(2)}\nP&L: ${pnlPct}% ($${pnl.toFixed(0)} ARS)\nRazón: ${reason}`)
  } catch (e) {
    console.error(chalk.red(`[orquestador] Error vendiendo ${symbol}:`), e.message)
  }
}

// ── Inicio ───────────────────────────────────────────────────────────────────
async function main() {
  console.log(chalk.bold.green('\n🤖 Trading Agent iniciando...\n'))
  loadState()
  startPanel()

  // Loop cada 1 minuto en horario de mercado
  cron.schedule('* * * * *', tick, {
    timezone: TRADING.timezone
  })

  // Primera ejecución inmediata
  await tick()
  console.log(chalk.bold('\n✅ Agente corriendo. Panel en http://localhost:3001\n'))
}

main().catch(console.error)
