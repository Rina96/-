"""
🩺 ПОЛНАЯ ДИАГНОСТИКА ЮЛИИ 4.7
Запустить: python3 check_julia.py

Проверяет каждое звено цепочки:
1. Render (сервер живой?)
2. Green API (инстанция авторизована?)
3. Webhook URL (правильный адрес?)
4. OpenAI (ключ рабочий, есть деньги?)
5. Database (URL и формат корректны?)
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────
RENDER_URL      = "https://school-go-whatsapp-bot.onrender.com"
GREEN_HOST      = os.getenv("GREEN_API_HOST", "https://api.green-api.com")
ID_INSTANCE     = os.getenv("GREEN_API_ID_INSTANCE", "")
API_TOKEN       = os.getenv("GREEN_API_API_TOKEN_INSTANCE", "")
OPENAI_KEY      = os.getenv("OPENAI_API_KEY", "")
DATABASE_URL    = os.getenv("DATABASE_URL", "")
CORRECT_WEBHOOK = f"{RENDER_URL}/webhook/green-api"

OK  = "✅"
ERR = "❌"
WRN = "⚠️ "

results = []

def log(icon, title, detail=""):
    line = f"  {icon} {title}"
    if detail:
        line += f"\n       → {detail}"
    print(line)
    results.append((icon, title))

# ─── CHECKS ──────────────────────────────────────────────────────────────────

async def check_render():
    print("\n📡 [1/5] ПРОВЕРКА СЕРВЕРА (Render)")
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{RENDER_URL}/health", timeout=10.0)
            if r.status_code == 200:
                log(OK, "Сервер отвечает", f"Status: {r.json()}")
            else:
                log(WRN, f"Сервер отвечает, но со статусом {r.status_code}", r.text[:100])
    except httpx.ConnectTimeout:
        log(ERR, "Сервер НЕ отвечает (таймаут)", "Render может быть в режиме сна или упал. Зайдите в дашборд Render и проверьте статус деплоя.")
    except Exception as e:
        log(ERR, f"Ошибка подключения: {e}")


async def check_green_api_auth():
    print("\n📱 [2/5] ПРОВЕРКА АВТОРИЗАЦИИ WhatsApp (Green API)")
    if not ID_INSTANCE or not API_TOKEN:
        log(ERR, "GREEN_API_ID_INSTANCE или GREEN_API_API_TOKEN_INSTANCE не заданы в .env")
        return
    try:
        url = f"{GREEN_HOST}/waInstance{ID_INSTANCE}/getStateInstance/{API_TOKEN}"
        async with httpx.AsyncClient() as c:
            r = await c.get(url, timeout=8.0)
            state = r.json().get("stateInstance", "unknown")
            if state == "authorized":
                log(OK, f"WhatsApp авторизован", f"State: {state}")
            else:
                log(ERR, f"WhatsApp НЕ авторизован! State = '{state}'",
                    "Зайдите на greenapi.com → ваша инстанция → сканируйте QR-код заново.")
    except Exception as e:
        log(ERR, f"Ошибка запроса к Green API: {e}")


async def check_webhook_url():
    print("\n🔗 [3/5] ПРОВЕРКА АДРЕСА ВЕБХУКА (Green API Settings)")
    if not ID_INSTANCE or not API_TOKEN:
        log(ERR, "Невозможно проверить — ключи не заданы")
        return
    try:
        url = f"{GREEN_HOST}/waInstance{ID_INSTANCE}/getSettings/{API_TOKEN}"
        async with httpx.AsyncClient() as c:
            r = await c.get(url, timeout=8.0)
            webhook_url = r.json().get("webhookUrl", "")
            if CORRECT_WEBHOOK in str(webhook_url):
                log(OK, "Адрес вебхука правильный", webhook_url)
            else:
                log(ERR, "Адрес вебхука НЕВЕРНЫЙ!", 
                    f"Сейчас: '{webhook_url}'\nДолжен быть: '{CORRECT_WEBHOOK}'\nЯ исправлю это автоматически...")
                # Auto-fix
                fix_url = f"{GREEN_HOST}/waInstance{ID_INSTANCE}/setSettings/{API_TOKEN}"
                fix_payload = {
                    "webhookUrl": CORRECT_WEBHOOK,
                    "incomingWebhook": "yes",
                    "outgoingWebhook": "no",
                    "stateInstanceWebhook": "yes"
                }
                fix_r = await c.post(fix_url, json=fix_payload, timeout=8.0)
                if fix_r.status_code == 200:
                    log(OK, "Адрес вебхука ИСПРАВЛЕН автоматически!", CORRECT_WEBHOOK)
                else:
                    log(ERR, f"Не удалось исправить автоматически: {fix_r.status_code}")
    except Exception as e:
        log(ERR, f"Ошибка проверки настроек: {e}")


async def check_openai():
    print("\n🤖 [4/5] ПРОВЕРКА OPENAI (ключ и баланс)")
    if not OPENAI_KEY:
        log(ERR, "OPENAI_API_KEY не задан в .env!")
        return
    try:
        headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Ответь одним словом: ОК"}],
            "max_tokens": 5
        }
        async with httpx.AsyncClient() as c:
            r = await c.post("https://api.openai.com/v1/chat/completions",
                             headers=headers, json=payload, timeout=15.0)
            if r.status_code == 200:
                reply = r.json()["choices"][0]["message"]["content"]
                log(OK, f"OpenAI работает", f"Ответ: '{reply}'")
            elif r.status_code == 401:
                log(ERR, "OpenAI: НЕВЕРНЫЙ КЛЮЧ (401 Unauthorized)",
                    "Проверьте OPENAI_API_KEY в .env и в настройках Render.")
            elif r.status_code == 429:
                log(ERR, "OpenAI: ЛИМИТ ИСЧЕРПАН (429 Rate Limit)",
                    "Проверьте баланс на platform.openai.com/usage")
            else:
                log(ERR, f"OpenAI вернул неожиданный статус: {r.status_code}", r.text[:200])
    except Exception as e:
        log(ERR, f"Ошибка подключения к OpenAI: {e}")


async def check_database():
    print("\n🗄️  [5/5] ПРОВЕРКА БАЗЫ ДАННЫХ")
    if not DATABASE_URL:
        log(WRN, "DATABASE_URL не задан — используется SQLite (локально)", 
            "На Render нужен PostgreSQL URL в переменных окружения.")
        return
    if "postgres" in DATABASE_URL:
        log(OK, "DATABASE_URL указывает на PostgreSQL", DATABASE_URL[:40] + "...")
    elif "sqlite" in DATABASE_URL:
        log(WRN, "DATABASE_URL указывает на SQLite",
            "SQLite на Render не сохраняется между перезапусками. Нужен PostgreSQL.")
    else:
        log(WRN, f"Неизвестный формат DATABASE_URL: {DATABASE_URL[:40]}")


# ─── SUMMARY ─────────────────────────────────────────────────────────────────

def print_summary():
    print("\n" + "="*50)
    print("  📊 ИТОГ ДИАГНОСТИКИ")
    print("="*50)
    errors = [r for r in results if ERR in r[0]]
    warnings = [r for r in results if WRN in r[0]]
    ok_count = len([r for r in results if OK in r[0]])

    print(f"\n  ✅ Работает: {ok_count}/{len(results)}")
    if errors:
        print(f"\n  ❌ КРИТИЧЕСКИЕ ОШИБКИ ({len(errors)}):")
        for _, title in errors:
            print(f"     • {title}")
    if warnings:
        print(f"\n  ⚠️  Предупреждения ({len(warnings)}):")
        for _, title in warnings:
            print(f"     • {title}")
    if not errors and not warnings:
        print("\n  🎉 ВСЕ СИСТЕМЫ РАБОТАЮТ НОРМАЛЬНО!")
        print("  Попробуйте написать Юлии в WhatsApp.")
    print("="*50 + "\n")


async def main():
    print("\n🔬 ДИАГНОСТИКА ЮЛИИ 4.7 — ПОЛНАЯ ПРОВЕРКА")
    print("="*50)
    await check_render()
    await check_green_api_auth()
    await check_webhook_url()
    await check_openai()
    await check_database()
    print_summary()

if __name__ == "__main__":
    asyncio.run(main())
