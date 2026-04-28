import requests
import os
from dotenv import load_dotenv

load_dotenv()

class TelegramClient:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str):
        """Send a message to the configured Telegram chat."""
        if not self.token or not self.chat_id:
            print("Telegram credentials missing.")
            return False
            
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False

if __name__ == "__main__":
    tg = TelegramClient()
    tg.send_message("🚀 *Trading Bot Iniciado*\nEl bot está listo para monitorear el mercado.")
