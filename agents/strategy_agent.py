import yfinance as yf
from agents.technical_agent import TechnicalAgent
from agents.news_agent import NewsAgent

class StrategyAgent:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.tech_agent = TechnicalAgent(symbol)
        self.news_agent = NewsAgent(symbol)

    def get_fundamental_score(self):
        """
        Uses yfinance to get analyst consensus and price targets.
        Returns a score from 0 to 10.
        """
        try:
            ticker = yf.Ticker(self.symbol)
            info = ticker.info
            
            # 1. Recommendation Score
            rec_map = {
                "strong_buy": 10,
                "buy": 8,
                "hold": 5,
                "underperform": 2,
                "sell": 0
            }
            rec_key = info.get("recommendationKey", "hold")
            rec_score = rec_map.get(rec_key, 5)
            
            # 2. Upside Score
            current = info.get("currentPrice")
            target = info.get("targetMeanPrice")
            upside_score = 5 # Default neutral
            
            if current and target:
                upside_pct = (target - current) / current
                if upside_pct > 0.20: upside_score = 10
                elif upside_pct > 0.10: upside_score = 8
                elif upside_pct > 0: upside_score = 6
                elif upside_pct > -0.10: upside_score = 3
                else: upside_score = 0
            
            # Weighted fundamental score
            final_fund_score = (rec_score * 0.6) + (upside_score * 0.4)
            
            return {
                "score": round(final_fund_score, 1),
                "recommendation": rec_key.replace("_", " ").upper(),
                "target_upside": f"{round(((target/current)-1)*100, 1)}%" if current and target else "N/A"
            }
        except Exception as e:
            print(f"Error in fundamental analysis for {self.symbol}: {e}")
            return {"score": 5, "recommendation": "NEUTRAL", "target_upside": "N/A"}

    def get_decision(self):
        """
        Combines Technical, Fundamental (yfinance), and News analysis.
        Weights:
        - Technical: 50%
        - Fundamental: 30%
        - News: 20%
        """
        tech_result = self.tech_agent.analyze()
        if "error" in tech_result:
            return tech_result

        fund_result = self.get_fundamental_score()
        
        news_list = self.news_agent.fetch_news()
        news_result = self.news_agent.analyze_sentiment(news_list)

        tech_score = tech_result['score']
        fund_score = fund_result['score']
        news_score = news_result['score']

        # Weighted final score
        final_score = (tech_score * 0.5) + (fund_score * 0.3) + (news_score * 0.2)
        
        decision = "HOLD"
        if final_score >= 7.0:
            decision = "BUY"
        elif final_score <= 3.0:
            decision = "SELL"

        return {
            "symbol": self.symbol,
            "final_score": round(final_score, 1),
            "decision": decision,
            "metrics": {
                "technical": tech_score,
                "fundamental": fund_score,
                "news": news_score
            },
            "technical_details": {
                "daily_trend": tech_result.get('daily_trend', 'UNKNOWN'),
                "1h_rsi": tech_result.get('1h_rsi', 0),
                "1h_stoch": tech_result.get('1h_stoch', 0),
                "1d_ema200": tech_result.get('1d_ema200', 0)
            },
            "fundamental_data": {
                "consensus": fund_result['recommendation'],
                "upside": fund_result['target_upside']
            },
            "news_reason": news_result.get('reason', '')
        }

if __name__ == "__main__":
    agent = StrategyAgent("MSFT")
    print(agent.get_decision())
