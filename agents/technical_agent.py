import yfinance as yf
import pandas as pd
import numpy as np
import ta
import time

class TechnicalAgent:
    def __init__(self, symbol: str):
        self.symbol = symbol
        
    def _fetch_data(self, interval: str, period: str = "60d"):
        """Fetch historical data using yfinance with robust fallbacks."""
        yf_symbols_to_try = []
        
        # Estrategia de búsqueda de símbolos
        if self.symbol in ["MSFT", "AAPL", "AMZN", "META", "GOOGL", "TSLA", "MELI", "KO", "PYPL", "BABA", "NVDA", "AMD"]:
            yf_symbols_to_try.append(self.symbol + ".BA") # Primero el CEDEAR
            yf_symbols_to_try.append(self.symbol)         # Luego el original de USA
        elif not self.symbol.endswith(".BA") and len(self.symbol) > 3:
            yf_symbols_to_try.append(self.symbol + ".BA")
            yf_symbols_to_try.append(self.symbol)
        else:
            yf_symbols_to_try.append(self.symbol)

        for yf_symbol in yf_symbols_to_try:
            try:
                # Pequeña espera para evitar bloqueos de Yahoo
                time.sleep(0.5)
                df = yf.download(yf_symbol, period=period, interval=interval, progress=False, threads=False)
                
                if df is not None and not df.empty and len(df) > 10:
                    # Reset index and ensure columns are flat and lowercase
                    df = df.copy()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    
                    df.columns = [str(c).lower() for c in df.columns]
                    df.index.name = 'datetime'
                    df.dropna(inplace=True)
                    
                    if len(df) > 10:
                        return df
            except Exception as e:
                print(f"⚠️ Error fetching {yf_symbol}: {e}")
                continue
                
        return None

    def _add_indicators(self, df: pd.DataFrame):
        """Add EMAs and StochRSI to the dataframe."""
        df = df.copy()
        
        # EMAs
        df['ema20'] = ta.trend.ema_indicator(df['close'], window=20)
        df['ema50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['ema200'] = ta.trend.ema_indicator(df['close'], window=200)
        
        # Stochastic RSI
        stoch_rsi = ta.momentum.StochRSIIndicator(close=df['close'], window=14, smooth1=3, smooth2=3)
        df['stoch_rsi_k'] = stoch_rsi.stochrsi_k() * 100 
        df['stoch_rsi_d'] = stoch_rsi.stochrsi_d() * 100
        
        # Standard RSI
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        
        # Volume moving average
        df['vol_ma20'] = df['volume'].rolling(window=20).mean()
        
        # Support / Resistance
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        df.dropna(inplace=True)
        return df

    def analyze(self):
        """
        Analyze 1D for master trend and 1H for actionable triggers.
        """
        # 1. Diario (Tendencia)
        df_1d = self._fetch_data("1d", period="2y")
        if df_1d is None or len(df_1d) < 50:
            return {"error": f"Not enough Daily data for {self.symbol}"}
        
        df_1d_ind = self._add_indicators(df_1d)
        last_1d = df_1d_ind.iloc[-1]
        
        # EMA200 o EMA50 como fallback
        ema_trend = last_1d.get('ema200', last_1d.get('ema50'))
        daily_bullish = last_1d['close'] > ema_trend if ema_trend is not None else True
        daily_trend_str = "BULLISH" if daily_bullish else "BEARISH"

        # 2. Horario (Triggers)
        df_1h = self._fetch_data("1h", period="60d")
        if df_1h is None or len(df_1h) < 20:
            return {"error": f"Not enough 1H data for {self.symbol}"}
            
        df_1h_ind = self._add_indicators(df_1h)
        last_1h = df_1h_ind.iloc[-1]
        prev_1h = df_1h_ind.iloc[-2]
        
        score = 5.0
        
        # Lógica de Puntaje
        if last_1h['close'] > last_1h['ema20'] > last_1h['ema50']: score += 2.0
        elif last_1h['close'] < last_1h['ema20'] < last_1h['ema50']: score -= 2.0
            
        if last_1h['rsi'] > 50: score += 1.0 
        if last_1h['rsi'] < 30: score += 1.5 
        elif last_1h['rsi'] > 70: score -= 1.5 
            
        if prev_1h['stoch_rsi_k'] < 20 and last_1h['stoch_rsi_k'] > last_1h['stoch_rsi_d']: score += 1.5 
        elif prev_1h['stoch_rsi_k'] > 80 and last_1h['stoch_rsi_k'] < last_1h['stoch_rsi_d']: score -= 1.5 

        if last_1h['volume'] > last_1h['vol_ma20']:
            if last_1h['close'] > last_1h['open']: score += 1.0
            else: score -= 1.0

        if daily_bullish: score += 1.0 
        else:
            if score > 5.0: score = 5.0 
            score -= 2.0 

        score = max(0, min(10, score))
        
        if score >= 7.5: signal = "STRONG_BUY"
        elif score >= 6.5: signal = "BUY"
        elif score <= 2.5: signal = "STRONG_SELL"
        elif score <= 4.0: signal = "SELL"
        else: signal = "NEUTRAL"

        return {
            "symbol": self.symbol,
            "score": round(score, 1),
            "signal": signal,
            "daily_trend": daily_trend_str,
            "price": round(last_1h['close'], 2),
            "1h_rsi": round(last_1h['rsi'], 1),
            "1h_stoch": round(last_1h['stoch_rsi_k'], 1)
        }
