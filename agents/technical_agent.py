import yfinance as yf
import pandas as pd
import numpy as np
import ta

class TechnicalAgent:
    def __init__(self, symbol: str):
        self.symbol = symbol
        
    def _fetch_data(self, interval: str, period: str = "60d"):
        """Fetch historical data using yfinance."""
        try:
            # If it's a common Argentine ticker without .BA, add it for Yahoo Finance
            yf_symbol = self.symbol
            if self.symbol in ["MSFT", "AAPL", "AMZN", "META", "GOOGL", "TSLA", "MELI", "KO", "PYPL", "BABA", "NVDA", "AMD"]:
                yf_symbol = self.symbol + ".BA"
            elif not self.symbol.endswith(".BA") and len(self.symbol) > 3:
                # Potential local ticker or Cedear
                yf_symbol = self.symbol + ".BA"
                
            df = yf.download(yf_symbol, period=period, interval=interval, progress=False)
            if df.empty:
                # Fallback to original symbol if .BA failed
                df = yf.download(self.symbol, period=period, interval=interval, progress=False)
                if df.empty:
                    return None
            
            # Reset index and ensure columns are flat and lowercase
            df = df.copy()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            df.columns = [str(c).lower() for c in df.columns]
            df.index.name = 'datetime'
                
            df.dropna(inplace=True)
            return df
        except Exception as e:
            print(f"Error fetching data for {self.symbol}: {e}")
            return None

    def _add_indicators(self, df: pd.DataFrame):
        """Add EMAs and StochRSI to the dataframe."""
        df = df.copy()
        # Columns are already lowercase from _fetch_data
        
        # EMAs
        df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)
        
        # Stochastic RSI
        stoch_rsi = ta.momentum.StochRSIIndicator(close=df['close'], window=14, smooth1=3, smooth2=3)
        df['stoch_rsi_k'] = stoch_rsi.stochrsi_k() * 100 # Scale 0-100
        df['stoch_rsi_d'] = stoch_rsi.stochrsi_d() * 100
        
        # Standard RSI (14)
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        
        # Volume moving average
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
        
        # Support / Resistance (Last 20 candles)
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        df.dropna(inplace=True)
        return df

    def analyze(self):
        """
        Analyze 1D for master trend and 1H for actionable triggers.
        Score from 0-10.
        """
        # 1. Fetch Daily Data for Trend (EMA 200)
        df_1d = self._fetch_data("1d", period="2y") # 2 years to have enough data for EMA200
        if df_1d is None or len(df_1d) < 200:
            return {"error": "Not enough Daily data"}
        
        df_1d_ind = self._add_indicators(df_1d)
        last_1d = df_1d_ind.iloc[-1]
        
        # Define Daily Trend
        if 'ema200' in last_1d and not np.isnan(last_1d['ema200']):
            daily_bullish = last_1d['close'] > last_1d['ema200']
        else:
            # Fallback to EMA50 if EMA200 is missing (for newer assets)
            daily_bullish = last_1d['close'] > last_1d['ema50']
            
        daily_trend_str = "BULLISH" if daily_bullish else "BEARISH"

        # 2. Fetch 1H Data for Triggers
        df_1h = self._fetch_data("1h", period="60d")
        if df_1h is None or len(df_1h) < 50:
            return {"error": "Not enough 1H data"}
            
        df_1h_ind = self._add_indicators(df_1h)
        
        # Get latest rows
        last_1h = df_1h_ind.iloc[-1]
        prev_1h = df_1h_ind.iloc[-2]
        
        score = 5.0 # Neutral start
        
        # --- 1H Technical Triggers ---
        # EMA Cross/Alignment (1H)
        if last_1h['close'] > last_1h['ema20'] > last_1h['ema50']:
            score += 2.0
        elif last_1h['close'] < last_1h['ema20'] < last_1h['ema50']:
            score -= 2.0
            
        # RSI (1H)
        if last_1h['rsi'] > 50:
            score += 1.0 
        if last_1h['rsi'] < 30:
            score += 1.5 # Oversold bounce potential
        elif last_1h['rsi'] > 70:
            score -= 1.5 # Overbought
            
        # Stoch RSI (1H) - Cross confirmation
        if prev_1h['stoch_rsi_k'] < 20 and last_1h['stoch_rsi_k'] > last_1h['stoch_rsi_d']:
            score += 1.5 # Golden cross in oversold
        elif prev_1h['stoch_rsi_k'] > 80 and last_1h['stoch_rsi_k'] < last_1h['stoch_rsi_d']:
            score -= 1.5 # Death cross in overbought

        # Volume confirmation (1H)
        if last_1h['volume'] > last_1h['vol_ma20']:
            if last_1h['close'] > last_1h['open']:
                score += 1.0
            else:
                score -= 1.0

        # --- 1D Trend Filter (CRITICAL) ---
        if daily_bullish:
            score += 1.0 # Bonus for trend alignment
        else:
            # If daily is bearish, we cap the score to avoid buying in a downtrend
            if score > 5.0:
                score = 5.0 # Neutralize buy signals
            score -= 2.0 # Penalty for bearish daily trend

        # Cap score between 0 and 10
        score = max(0, min(10, score))
        
        # Decide action based on score
        if score >= 7.5:
            signal = "STRONG_BUY"
        elif score >= 6.5:
            signal = "BUY"
        elif score <= 2.5:
            signal = "STRONG_SELL"
        elif score <= 4.0:
            signal = "SELL"
        else:
            signal = "NEUTRAL"

        return {
            "symbol": self.symbol,
            "score": round(score, 1),
            "signal": signal,
            "daily_trend": daily_trend_str,
            "price": round(last_1h['close'], 2),
            "1h_rsi": round(last_1h['rsi'], 1),
            "1h_stoch": round(last_1h['stoch_rsi_k'], 1),
            "1d_ema200": round(last_1d['ema200'], 2)
        }

if __name__ == "__main__":
    agent = TechnicalAgent("NVDA")
    print(agent.analyze())
