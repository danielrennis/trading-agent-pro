import requests
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

load_dotenv()

class NewsAgent:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.analyzer = SentimentIntensityAnalyzer()

    def fetch_news(self):
        """Fetch latest news headlines from Google News RSS."""
        url = f"https://news.google.com/rss/search?q={self.symbol}+stock&hl=en-US&gl=US&ceid=US:en"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.content, features="lxml-xml")
            items = soup.find_all('item')
            
            news_list = []
            for item in items[:10]: # Get top 10 news
                news_list.append({
                    'title': item.title.text,
                    'description': item.description.text if item.description else "",
                    'link': item.link.text
                })
            return news_list
        except Exception as e:
            print(f"Error fetching news for {self.symbol}: {e}")
            return []

    def analyze_sentiment(self, news_list):
        """Analyze sentiment of the news headlines using local VADER analysis."""
        if not news_list:
            return {"sentiment": "NEUTRAL", "score": 5, "reason": "No news found"}

        combined_text = ". ".join([n['title'] for n in news_list])
        vs = self.analyzer.polarity_scores(combined_text)
        
        # VADER compound score is -1 to 1. Map it to 0-10.
        # (compound + 1) * 5
        score = (vs['compound'] + 1) * 5
        
        sentiment = "NEUTRAL"
        if score >= 6.5: sentiment = "BULLISH"
        elif score <= 3.5: sentiment = "BEARISH"
        
        return {
            "score": round(score, 1),
            "sentiment": sentiment,
            "reason": f"Local VADER Analysis (compound: {vs['compound']})"
        }

if __name__ == "__main__":
    agent = NewsAgent("NVDA")
    news = agent.fetch_news()
    print(f"Fetched {len(news)} news items.")
    sentiment = agent.analyze_sentiment(news)
    print(sentiment)
