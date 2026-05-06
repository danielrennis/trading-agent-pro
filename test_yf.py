import yfinance as yf
ticker = yf.Ticker("AAPL")
print("Calendar:")
print(ticker.calendar)
print("---")
