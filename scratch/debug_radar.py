
import sys
import os
sys.path.append(os.getcwd())
from agents.strategy_agent import StrategyAgent
from core.iol_client import IOLClient

iol = IOLClient()
iol.login()

for symbol in ["AAPL", "AMZN", "META", "MELI"]:
    print(f"\n--- Analyzing {symbol} ---")
    strategy = StrategyAgent(symbol)
    decision = strategy.get_decision()
    print(decision)
