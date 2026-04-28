// backtest/runner.js
// Simula 6 meses de operaciones con la lógica del agente

import 'dotenv/config'
import yahooFinance from 'yahoo-finance2'
import { EMA, StochasticRSI } from 'technicalindicators'
import chalk from 'chalk'

const SYMBOLS    = ['NVDA', 'AMD']
const COMMISSION = 0.011   // 1.1% ida+vuelta
const INITIAL_SL = -0.010
const INITIAL_TP = +0.021
const TRAILING_SL = -0.010
const TRAILING_STEP = +0.011
const MIN_SCORE  = 7

// ── Obtener datos históricos ──────────────────────────────────────────────────
async function fetchHistory(symbol) {
  const result = await yahooFinance.chart(symbol, { interval: '1h', range: '6mo' })
  return result.quotes
    .filter(q => q.close != null)
    .map(q => ({ time: new Date(q.date), open: q.open, high: q.high, low: q.low, close: q.close, volume: q.volume }))
}

// ── Score técnico simplificado para backtesting ──────────────────────────────
function calcScore(candles) {
  if (candles.length < 55) return 5
  const closes  = candles.map(c => c.close)
  const volumes = candles.map(c => c.volume)
  const ema20   = EMA.calculate({ period: 20, values: closes })
  const ema50   = EMA.calculate({ period: 50, values: closes })
  const srsi    = StochasticRSI.calculate({ values: closes, rsiPeriod: 14, stochasticPeriod: 14, kPeriod: 3, dPeriod: 3 })

  const price   = closes.at(-1)
  const e20     = ema20.at(-1)
  const e50     = ema50.at(-1)
  const k       = srsi.at(-1)?.k ?? 50
  const vol     = volumes.at(-1)
  const volAvg  = volumes.slice(-20).reduce((a, b) => a + b, 0) / 20

  let score = 5
  if (price > e20) score += 0.8; else score -= 0.8
  if (price > e50) score += 0.6; else score -= 0.6
  if (e20 > e50)   score += 0.5; else score -= 0.5
  if (k < 20)      score += 1.2
  else if (k > 80) score -= 1.2
  else if (k > 50) score += 0.3; else score -= 0.3
  if (vol > volAvg * 1.3 && price > e20) score += 0.5

  return Math.max(0, Math.min(10, score))
}

// ── Simular trailing escalonado ───────────────────────────────────────────────
function simulateTrailing(entryPrice, futureCandles) {
  let sl   = entryPrice * (1 + INITIAL_SL)
  let tp   = entryPrice * (1 + INITIAL_TP)
  let step = 0
  let peak = entryPrice

  for (const candle of futureCandles) {
    const price = candle.close
    peak = Math.max(peak, price)

    if (price <= sl) {
      const pnl = (price - entryPrice) / entryPrice - COMMISSION
      return { exitPrice: price, pnl, step, reason: 'stop_loss', candles: futureCandles.indexOf(candle) }
    }
    if (price >= tp) {
      step++
      sl = tp * (1 + TRAILING_SL)
      tp = tp * (1 + TRAILING_STEP)
    }
  }
  // Cierre forzado al final
  const exitPrice = futureCandles.at(-1)?.close ?? entryPrice
  const pnl = (exitPrice - entryPrice) / entryPrice - COMMISSION
  return { exitPrice, pnl, step, reason: 'forced_close', candles: futureCandles.length }
}

// ── Main backtest ─────────────────────────────────────────────────────────────
async function runBacktest() {
  console.log(chalk.bold.cyan('\n📊 BACKTESTING — 6 meses\n'))

  const results = {}

  for (const symbol of SYMBOLS) {
    console.log(chalk.bold(`\n── ${symbol} ──────────────────────────────`))
    const candles = await fetchHistory(symbol)
    console.log(`Velas obtenidas: ${candles.length}`)

    const trades = []
    let inPosition = false
    let entryIdx   = -1

    // Simular hora por hora
    for (let i = 55; i < candles.length - 1; i++) {
      const window = candles.slice(Math.max(0, i - 100), i + 1)
      const candle = candles[i]

      // Solo operar en horario "de mercado" (simplificado: lunes-viernes)
      const day = candle.time.getDay()
      if (day === 0 || day === 6) continue

      if (!inPosition) {
        const score = calcScore(window)
        if (score >= MIN_SCORE) {
          inPosition = true
          entryIdx   = i
        }
      } else {
        // Mantener máximo 8 horas (1 día de trading)
        const hoursHeld = i - entryIdx
        if (hoursHeld >= 8 || i === candles.length - 2) {
          const future = candles.slice(entryIdx + 1, entryIdx + 1 + Math.min(8, candles.length - entryIdx - 1))
          const result = simulateTrailing(candles[entryIdx].close, future)
          trades.push({
            entry:      candles[entryIdx].close,
            exit:       result.exitPrice,
            pnl:        result.pnl,
            steps:      result.step,
            reason:     result.reason,
            date:       candles[entryIdx].time.toLocaleDateString('es-AR')
          })
          inPosition = false
        }
      }
    }

    // ── Métricas ──────────────────────────────────────────────────────────────
    if (!trades.length) { console.log('Sin trades'); continue }

    const wins       = trades.filter(t => t.pnl > 0)
    const losses     = trades.filter(t => t.pnl <= 0)
    const totalPnL   = trades.reduce((a, t) => a + t.pnl, 0)
    const avgWin     = wins.length   ? wins.reduce((a, t) => a + t.pnl, 0) / wins.length : 0
    const avgLoss    = losses.length ? losses.reduce((a, t) => a + t.pnl, 0) / losses.length : 0
    const winRate    = (wins.length / trades.length * 100).toFixed(1)
    const maxSteps   = Math.max(...trades.map(t => t.steps))
    const avgSteps   = (trades.reduce((a, t) => a + t.steps, 0) / trades.length).toFixed(1)

    // Drawdown máximo
    let peak = 0, maxDD = 0, running = 0
    for (const t of trades) {
      running += t.pnl
      if (running > peak) peak = running
      const dd = peak - running
      if (dd > maxDD) maxDD = dd
    }

    results[symbol] = { trades: trades.length, winRate, totalPnL, avgWin, avgLoss, maxDD, maxSteps, avgSteps }

    console.log(`Trades:       ${trades.length}`)
    console.log(`Win rate:     ${chalk.bold(winRate + '%')}`)
    console.log(`P&L total:    ${totalPnL > 0 ? chalk.green((totalPnL * 100).toFixed(2) + '%') : chalk.red((totalPnL * 100).toFixed(2) + '%')}`)
    console.log(`Ganancia prom: ${chalk.green((avgWin * 100).toFixed(2) + '%')}`)
    console.log(`Pérdida prom:  ${chalk.red((avgLoss * 100).toFixed(2) + '%')}`)
    console.log(`Max drawdown: ${chalk.red((maxDD * 100).toFixed(2) + '%')}`)
    console.log(`Escalones prom: ${avgSteps} | máx: ${maxSteps}`)

    // Últimos 5 trades
    console.log('\nÚltimos 5 trades:')
    trades.slice(-5).forEach(t => {
      const pnlStr = (t.pnl * 100).toFixed(2) + '%'
      const color  = t.pnl > 0 ? chalk.green : chalk.red
      console.log(`  ${t.date} | ${color(pnlStr)} | steps: ${t.steps} | ${t.reason}`)
    })
  }

  // ── Resumen final ──────────────────────────────────────────────────────────
  console.log(chalk.bold.cyan('\n\n📊 RESUMEN COMPARATIVO\n'))
  for (const [sym, r] of Object.entries(results)) {
    const rec = r.winRate > 55 && r.totalPnL > 0 ? chalk.green('✅ RECOMENDADO') : chalk.yellow('⚠️  REVISAR')
    console.log(`${sym}: win ${r.winRate}% | P&L ${(r.totalPnL*100).toFixed(1)}% | ${rec}`)
  }
  console.log()
}

runBacktest().catch(console.error)
