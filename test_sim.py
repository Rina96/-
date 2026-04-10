import asyncio
import httpx
from main import app
from fastapi.testclient import TestClient

def test_webhook_simulation():
    print("\n--- 🧪 ТЕСТ-СИМУЛЯЦИЯ ВЕБХУКА ---")
    client = TestClient(app)
    
    # Имитируем структуру Green API
    payload = {
        "body": {
            "typeWebhook": "incomingMessageReceived",
            "senderData": {
                "chatId": "79123456789@c.us"
            },
            "messageData": {
                "typeMessage": "textMessage",
                "textMessageData": {
                    "textMessage": "Тестовое сообщение для Юлии"
                }
            }
        }
    }
    
    print("📡 Отправка фейкового вебхука...")
    response = client.post("/webhook/green-api", json=payload)
    
    print(f"✅ Статус ответа сервера: {response.status_code}")
    print(f"📄 Ответ: {response.json()}")
    
    print("\n⚠️ ВНИМАНИЕ: Если сервер ответил 'ok', значит Julia приняла задачу.")
    print("Теперь проверьте логи в терминале (если вы запустите сервер локально).")
    print("--- 🏁 ТЕСТ ЗАВЕРШЕН ---\n")

if __name__ == "__main__":
    test_webhook_simulation()
