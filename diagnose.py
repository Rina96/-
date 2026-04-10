import asyncio
import httpx
from config import settings
from llm_engine import llm
from green_api import wa_client
from database import engine, Base
from loguru import logger

async def run_diagnostics():
    print("\n--- 🩺 КРИТИЧЕСКАЯ ДИАГНОСТИКА ЮЛИИ ---")
    
    # 1. Проверка Базы Данных
    try:
        async with engine.connect() as conn:
            print("✅ БД: Соединение установлено.")
    except Exception as e:
        print(f"❌ БД: ОШИБКА СОЕДИНЕНИЯ: {e}")

    # 2. Проверка Green API (Статус инстанции)
    try:
        url = f"{settings.GREEN_API_HOST}/waInstance{settings.GREEN_API_ID_INSTANCE}/getStateInstance/{settings.GREEN_API_API_TOKEN_INSTANCE}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            state = r.json().get("stateInstance")
            print(f"📡 WhatsApp: Статус инстанции = {state}")
            if state != "authorized":
                print("⚠️ ВНИМАНИЕ: Инстанция не авторизована! Нужно заново сканировать QR-код.")
    except Exception as e:
        print(f"❌ WhatsApp: Ошибка проверки статуса: {e}")

    # 3. Проверка Вебхука (Куда Green API шлет сообщения)
    try:
        url = f"{settings.GREEN_API_HOST}/waInstance{settings.GREEN_API_ID_INSTANCE}/getSettings/{settings.GREEN_API_API_TOKEN_INSTANCE}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            webhook_url = r.json().get("webhookUrl")
            print(f"🔗 Webhook: Текущий адрес в Green API = {webhook_url}")
            if "school-go-whatsapp-bot.onrender.com" not in str(webhook_url):
                print(f"⚠️ ВНИМАНИЕ: Адрес вебхука МОЖЕТ БЫТЬ НЕВЕРНЫМ или устаревшим!")
    except Exception as e:
        print(f"❌ Webhook: Ошибка проверки настроек: {e}")

    # 4. Проверка OpenAI
    try:
        print("🤖 ИИ: Проверка интеллекта (GPT-4o)...")
        resp = llm.generate_response("Привет, это тест системы. Ответь одним словом: 'ОК'.", [])
        print(f"✅ ИИ: Ответ получен = {resp.reply_text}")
    except Exception as e:
        print(f"❌ ИИ: ОШИБКА OpenAI: {e}")

    print("--- 🏁 ДИАГНОСТИКА ЗАВЕРШЕНА ---\n")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())
