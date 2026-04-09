import asyncio
import os
from typing import Optional
from loguru import logger
from fastapi import FastAPI, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, Base, get_db_session
from crud import crud
from llm_engine import llm
from green_api import wa_client
from config import settings
from integrations_mock import crm_mock, kaspi_mock

app = FastAPI()

async def process_incoming_message(chat_id: str, text: str, db: AsyncSession, image_url: Optional[str] = None):
    """Elite background worker with Vision and Voice support."""
    logger.info(f"🚀 Обработка: {text[:30]} | Фото: {bool(image_url)}")
    
    session = await crud.get_or_create_session(db, chat_id)
    await crud.add_message_to_history(db, session, role="user", text=text)
    
    # 1. AI Thinking (GPT-4o Vision + Multi-agent logic)
    ai_response = llm.generate_response(user_message=text, chat_history=session.history_json, image_url=image_url)
    
    # 2. Обновление памяти
    await crud.add_message_to_history(db, session, role="assistant", text=ai_response.reply_text)
    
    # 3. Ответ: Голос или Текст?
    if ai_response.voice_response_needed and settings.VOICE_ENABLED:
        logger.info(f"🎙 Генерация ГОЛОСОВОГО ответа для {chat_id}")
        audio_bytes = await llm.generate_voice(ai_response.reply_text)
        temp_path = f"voice_{chat_id}.ogg"
        with open(temp_path, "wb") as f:
            f.write(audio_bytes)
        
        await wa_client.send_file(chat_id, temp_path)
        os.remove(temp_path)
    else:
        # Стандартный текст кусками
        chunks = [c.strip() for c in ai_response.reply_text.split("\n\n") if c.strip()][:2]
        for i, chunk in enumerate(chunks):
            if i > 0: await asyncio.sleep(4)
            await wa_client.send_message(chat_id, chunk)

    # 4. Выставление счета, если клиент готов
    if ai_response.is_qualified:
        total_price = (ai_response.adult_count * 5000) + (ai_response.child_count * 2000)
        invoice_url = await kaspi_mock.create_invoice(chat_id, amount=total_price)
        invoice_msg = f"Оплатите, пожалуйста, счет на сумму {total_price} тг по ссылке: {invoice_url}"
        await wa_client.send_message(chat_id, invoice_msg)

    logger.success(f"✅ Цикл обработки завершен для {chat_id}")

@app.post("/webhook/green-api")
async def webhook(request: Request, db: AsyncSession = Depends(get_db_session)):
    # Legacy logic for standalone server if needed
    data = await request.json()
    logger.debug(f"Webhook data: {data}")
    body = data.get("body", {})
    if body.get("typeWebhook") == "incomingMessageReceived":
        chat_id = body.get("senderData", {}).get("chatId")
        text = body.get("messageData", {}).get("textMessageData", {}).get("textMessage", "")
        if chat_id and text:
            asyncio.create_task(process_incoming_message(chat_id, text, db))
    return {"status": "ok"}
