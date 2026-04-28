import yfinance as yf
import json

def test_tickers(tickers):
    results = {}
    for ticker in tickers:
        print(f"Fetching data for {ticker}...")
        t = yf.Ticker(ticker)
        
        # Get info (fundamentals)
        info = t.info
        
        # Get news
        news = t.news[:3] # Last 3 news
        
        # Get recommendations
        recommendations = t.recommendations
        
        results[ticker] = {
            "metrics": {
                "currentPrice": info.get("currentPrice"),
                "targetMeanPrice": info.get("targetMeanPrice"),
                "recommendationKey": info.get("recommendationKey"),
                "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
                "trailingPE": info.get("trailingPE"),
                "marketCap": info.get("marketCap")
            },
            "recent_news": [
                {"title": n.get("title"), "link": n.get("link")} for n in news
            ]
        }
        
    return results

if __name__ == "__main__":
    # Test with some typical CEDEARs
    my_tickers = ["MSFT", "AAPL", "NVDA"]
    data = test_tickers(my_tickers)
    print("\n--- RESULTS ---\n")
    print(json.dumps(data, indent=2))
