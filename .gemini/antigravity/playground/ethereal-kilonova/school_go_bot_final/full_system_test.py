import asyncio
from llm_engine import llm
from integrations_mock import get_upcoming_weekend_dates

async def run_simulation():
    print("--- ЗАПУСК ФИНАЛЬНОГО ТЕСТА СИСТЕМЫ (ШКОЛА ГО) ---")
    
    dates = get_upcoming_weekend_dates()
    print(f"Актуальные даты бота: {dates['saturday']} и {dates['sunday']}")

    # Сценарий 1: Родитель + Ребенок
    print("\n[Сценарий 1: Родитель и Ребенок]")
    history = []
    messages = [
        "Здравствуйте! А вы кто? Что за Го?",
        "Я Олег. Хочу сына 8 лет привести. Чему научите?",
        "А сколько стоит вдвоем прийти? Мы с ним вместе хотим.",
        "Окей, давайте на субботу. Что от меня нужно?"
    ]
    
    for msg in messages:
        print(f"КЛИЕНТ: {msg}")
        resp = llm.generate_response(msg, history)
        print(f"ЮЛИЯ: {resp.reply_text}")
        print(f"DEBUG: Name={resp.extracted_name}, Audience={resp.audience}, Adult={resp.adult_count}, Child={resp.child_count}, Qualified={resp.is_qualified}")
        history.append({"role": "user", "text": msg})
        history.append({"role": "model", "text": resp.reply_text})
        
        if resp.is_qualified:
            total = (resp.adult_count * 5000) + (resp.child_count * 2000)
            print(f"--- СИСТЕМА: Выставлен счет на {total} тг ---")

    print("\n--- ТЕСТ ЗАВЕРШЕН УСПЕШНО ---")

if __name__ == "__main__":
    asyncio.run(run_simulation())
