import asyncio
import os
from loguru import logger
from database import engine, Base, AsyncSessionLocal
from crud import crud
from llm_engine import llm
from green_api import wa_client
from amocrm import amocrm_client
import knowledge_parser

# Mock API functions so we don't need real keys
async def mock_send_message(chat_id, message):
    print(f"\n[🟢 ОТПРАВЛЕНО В WHATSAPP -> {chat_id}]:\n{message}\n")
    return True
wa_client.send_message = mock_send_message

async def mock_create_note(lead_id, text):
    print(f"[🗄️ AMOCRM ПРИМЕЧАНИЕ К ЛИДУ №{lead_id}]: {text}")
    return True
amocrm_client.create_lead_note = mock_create_note

async def mock_update_status(lead_id, status_id, pipeline_id):
    print(f"\n[🔥 AMOCRM УСПЕХ! СТАТУС ЛИДА №{lead_id} ИЗМЕНЕН НА -> {status_id}]\n")
    return True
amocrm_client.update_lead_status = mock_update_status

async def mock_create_task(lead_id, text):
    print(f"\n[⚠️ AMOCRM ЗАДАЧА НА ДОЖИМ МЕНЕДЖЕРУ -> Лид №{lead_id}]: {text}\n")
    return True
amocrm_client.create_task_for_manager = mock_create_task

async def simulate_conversation():
    print("--- ЗАПУСКАЕМ ТЕСТОВУЮ СИМУЛЯЦИЮ ИИ-ПРОДАВЦА ---")
    
    # Check if Gemini key is available for the test
    if not os.getenv("GEMINI_API_KEY"):
        print("ОШИБКА: Нет ключа GEMINI_API_KEY. Тест не запустится, ИИ не сможет отвечать.")
        return
        
    # Re-initialize the knowledge parser to load the newly created .json
    knowledge_parser.kb.load()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    chat_id = "77011234567@c.us"
    lead_id = 100500

    async with AsyncSessionLocal() as db:
        session = await crud.get_or_create_session(db, chat_id)
        session.crm_lead_id = lead_id
        await db.commit()

        # Step 1: Simulator triggers amoCRM Webhook creation
        print("\n--- ЭТАП 1: Лид оставил заявку на сайте. Система инициирует диалог. ---")
        prompt = "Инициируй диалог. Поздоровайся приветливо от имени Школы Массажа."
        ai_res = llm.generate_response(user_message=prompt, chat_history=[])
        await crud.add_message_to_history(db, session, "model", ai_res.reply_text)
        await wa_client.send_message(chat_id, ai_res.reply_text)
        await amocrm_client.create_lead_note(lead_id, f"[🚀 ИИ начал воронку]: {ai_res.reply_text}")

        # Step 2: Client replies
        client_replies = [
            "Привет. Да, хочу на базовый курс, но у меня грыжа. И мне кажется дорого...",
            "Ну вообще для себя хочу научиться делать массаж, не для работы.",
            "Хорошо, если в рассрочку от Kaspi, то я согласен оформляться."
        ]

        stage = 2
        for reply in client_replies:
            print(f"\n--- ЭТАП {stage}: Клиент пишет в WhatsApp ---")
            print(f"[👤 КЛИЕНТ {chat_id} ПОЛУЧЕНО]: {reply}")
            
            # Save user reply
            await crud.add_message_to_history(db, session, "user", reply)
            
            # AI processes reply
            ai_res = llm.generate_response(user_message=reply, chat_history=session.history_json)
            
            # Save AI reply
            await crud.add_message_to_history(db, session, "model", ai_res.reply_text)
            
            # Update state in DB
            await crud.update_session_state(db, session, ai_res.is_qualified, ai_res.needs_human)
            
            # Push to APIs
            await wa_client.send_message(chat_id, ai_res.reply_text)
            await amocrm_client.create_lead_note(lead_id, f"[ИИ]: {ai_res.reply_text}")

            if ai_res.is_qualified:
                await amocrm_client.update_lead_status(lead_id, 142, None)
                print("\n[СИМУЛЯТОР]: ИИ успешно квалифицировал сделку! Цикл продаж завершен.")
                break
            elif ai_res.needs_human:
                await amocrm_client.create_task_for_manager(lead_id, "Менеджер, перехвати диалог!")
                print("\n[СИМУЛЯТОР]: ИИ сдался и передал лид живому человеку.")
                break
                
            stage += 1

if __name__ == "__main__":
    asyncio.run(simulate_conversation())
