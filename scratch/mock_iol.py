
import json
import os
from datetime import datetime

class MockIOLClient:
    def __init__(self):
        self.prices = {}
        self.orders = []
        self.balance = 10000000  # 10M for simulation
        self.portfolio = {"activos": []}

    def set_price(self, symbol, price):
        self.prices[symbol] = price

    def get_quote(self, symbol, plazo="t0"):
        if symbol in self.prices:
            return {"ultimoPrecio": self.prices[symbol], "simbolo": symbol}
        return None

    def get_balances_all(self):
        return {"t0": self.balance, "t1": self.balance, "t2": self.balance}

    def get_balance(self):
        return self.balance

    def get_portfolio(self):
        return self.portfolio

    def place_order(self, symbol, qty, price, action, validity="t0"):
        order = {
            "numeroOperacion": len(self.orders) + 1000,
            "symbol": symbol,
            "qty": qty,
            "price": price if price > 0 else self.prices.get(symbol, 0),
            "action": action,
            "date": datetime.now().isoformat()
        }
        self.orders.append(order)
        
        # Update mock portfolio
        if action == "comprar":
            self.balance -= order["price"] * qty
            found = False
            for act in self.portfolio["activos"]:
                if act["titulo"]["simbolo"] == symbol:
                    act["cantidad"] += qty
                    found = True
                    break
            if not found:
                self.portfolio["activos"].append({
                    "titulo": {"simbolo": symbol},
                    "cantidad": qty,
                    "ppc": order["price"],
                    "ultimoPrecio": order["price"]
                })
        elif action == "vender":
            self.balance += order["price"] * qty
            for i, act in enumerate(self.portfolio["activos"]):
                if act["titulo"]["simbolo"] == symbol:
                    act["cantidad"] -= qty
                    if act["cantidad"] <= 0:
                        self.portfolio.pop("activos")[i]
                    break
        return order

    def login(self):
        return True
