import asyncio
import httpx
import os
from dotenv import load_dotenv

# Load env from .env file
load_dotenv()

GREEN_API_HOST = os.getenv("GREEN_API_HOST", "https://api.green-api.com")
ID_INSTANCE = os.getenv("GREEN_API_ID_INSTANCE")
API_TOKEN = os.getenv("GREEN_API_API_TOKEN_INSTANCE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def run_lite_diagnostics():
    print("\n--- ⚡️ ЭКСПРЕСС-ДИАГНОСТИКА ЮЛИИ ---")
    
    # 1. Проверка Green API (Статус инстанции)
    try:
        url = f"{GREEN_API_HOST}/waInstance{ID_INSTANCE}/getStateInstance/{API_TOKEN}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10.0)
            state = r.json().get("stateInstance")
            print(f"📡 WhatsApp Instance: {state}")
            if state != "authorized":
                print("🚨 ОШИБКА: Инстанция НЕ авторизована. Бот не видит сообщения!")
            else:
                print("✅ WhatsApp Instance: OK.")
    except Exception as e:
        print(f"❌ WhatsApp: Ошибка связи: {e}")

    # 2. Проверка Webhook URL
    try:
        url = f"{GREEN_API_HOST}/waInstance{ID_INSTANCE}/getSettings/{API_TOKEN}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=10.0)
            settings = r.json()
            webhook_url = settings.get("webhookUrl")
            print(f"🔗 Webhook URL: {webhook_url}")
            if "school-go-whatsapp-bot.onrender.com" not in str(webhook_url):
                print("🚨 ВНИМАНИЕ: Адрес вебхука НЕВЕРНЫЙ! Юлия не получает уведомления.")
            else:
                print("✅ Webhook URL: OK.")
    except Exception as e:
        print(f"❌ Webhook: Ошибка настроек: {e}")

    # 3. Проверка OpenAI (Ping)
    try:
        print("🤖 ИИ: Проверка OpenAI...")
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
            payload = {"model": "gpt-4o", "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5}
            r = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10.0)
            if r.status_code == 200:
                print("✅ OpenAI: OK.")
            else:
                print(f"🚨 OpenAI Error: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"❌ OpenAI: Ошибка связи: {e}")

    print("--- 🏁 КОНЕЦ ДИАГНОСТИКИ ---\n")

if __name__ == "__main__":
    asyncio.run(run_lite_diagnostics())
