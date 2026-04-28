import yfinance as yf
import pandas as pd
from agents.technical_agent import TechnicalAgent

class Backtester:
    def __init__(self, symbols, initial_capital=100000):
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.commission = 0.0056  # 0.56% per trade (buy + sell = 1.12%)
        
    def run(self):
        print(f"🚀 Simulación de Trailing Infinito para {self.symbols}...")
        
        all_results = {}
        for symbol in self.symbols:
            print(f"\n--- Analizando {symbol} ---")
            df = yf.download(symbol, period="6mo", interval="1h", progress=False)
            if df.empty: continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df.columns = [str(c).lower() for c in df.columns]
            agent = TechnicalAgent(symbol)
            df = agent._add_indicators(df)
            
            trades = []
            capital = self.initial_capital
            in_position = False
            entry_price = 0
            sl_actual = 0
            tp_actual = 0
            shares = 0
            step_count = 0
            
            for timestamp, row in df.iterrows():
                if in_position:
                    # Check SL exit
                    if row['low'] <= sl_actual:
                        exit_price = sl_actual
                        net_profit = (exit_price - entry_price) * shares
                        commission_cost = (entry_price * shares * self.commission) + (exit_price * shares * self.commission)
                        capital += (exit_price * shares) - commission_cost
                        trades.append({"profit": net_profit - commission_cost})
                        print(f"  🛑 [{timestamp}] VENTA por Stop Loss en {symbol} a ${exit_price:.2f} | Resultado: ${net_profit-commission_cost:.2f}")
                        in_position = False
                        continue
                    
                    # Check for trailing update (ESCALÓN)
                    if row['high'] >= tp_actual:
                        step_count += 1
                        sl_actual = tp_actual * 0.99
                        tp_actual = tp_actual * 1.01
                        print(f"  📈 [{timestamp}] ¡ESCALÓN {step_count}! Nuevo SL: ${sl_actual:.2f} | Nuevo TP: ${tp_actual:.2f}")
                    
                else:
                    # Entry logic: Trend + Stoch RSI Cross-up + RSI Filter
                    if row['close'] > row['ema20'] > row['ema50'] and \
                       row['stoch_rsi_k'] < 30 and row['stoch_rsi_k'] > row['stoch_rsi_d'] and \
                       row['rsi'] > 45:
                        
                        entry_price = row['close']
                        investment = capital * 0.8
                        shares = int(investment / entry_price)
                        
                        if shares > 0:
                            sl_actual = entry_price * 0.99
                            tp_actual = entry_price * 1.021
                            capital -= (entry_price * shares)
                            in_position = True
                            step_count = 0
                            print(f"  🎯 [{timestamp}] COMPRA en {symbol} a ${entry_price:.2f} | SL: ${sl_actual:.2f} | TP: ${tp_actual:.2f}")
            
            total_profit = sum([t['profit'] for t in trades])
            print(f"\n📊 RESUMEN {symbol}: Ganancia Total: ${total_profit:.2f}")
            
        return all_results

if __name__ == "__main__":
    symbols = [
        "AMZN", "MSFT", "META", "BABA", "INTC", 
        "NVDA", "AMD", "GOOG", "AAPL", "TSLA"
    ]
    backtester = Backtester(symbols)
    backtester.run()
