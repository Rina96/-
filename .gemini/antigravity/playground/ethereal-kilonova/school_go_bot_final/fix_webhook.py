import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

GREEN_API_HOST = os.getenv("GREEN_API_HOST", "https://api.green-api.com")
ID_INSTANCE = os.getenv("GREEN_API_ID_INSTANCE")
API_TOKEN = os.getenv("GREEN_API_API_TOKEN_INSTANCE")
CORRECT_WEBHOOK_URL = "https://school-go-whatsapp-bot.onrender.com/webhook/green-api"

async def fix_webhook():
    print(f"\n--- 🛠 ИСПРАВЛЕНИЕ ВЕБХУКА ---")
    url = f"{GREEN_API_HOST}/waInstance{ID_INSTANCE}/setSettings/{API_TOKEN}"
    
    payload = {
        "webhookUrl": CORRECT_WEBHOOK_URL,
        "incomingWebhook": "yes",
        "stateInstanceWebhook": "yes",
        "outgoingWebhook": "no",
        "outgoingMessageWebhook": "no"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(url, json=payload, timeout=10.0)
            if r.status_code == 200:
                print(f"✅ УСПЕХ: Новый адрес вебхука установлен: {CORRECT_WEBHOOK_URL}")
            else:
                print(f"❌ ОШИБКА: Не удалось обновить настройки: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
    
    print("--- 🏁 ИСПРАВЛЕНИЕ ЗАВЕРШЕНО ---\n")

if __name__ == "__main__":
    asyncio.run(fix_webhook())
