import asyncio
import httpx
import sys
import os
import time
from loguru import logger
from database import engine, Base, get_db_session
from main import process_incoming_message
from llm_engine import llm
from green_api import wa_client
from config import settings

logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>")

MESSAGE_BUFFER = {}
AGGREGATION_DELAY = 2.0
PROCESSED_MESSAGES = set()

async def process_buffer():
    while True:
        now = time.time()
        to_process = []
        for chat_id, data in list(MESSAGE_BUFFER.items()):
            if now - data["last_time"] >= AGGREGATION_DELAY:
                full_text = ". ".join(data["texts"])
                to_process.append((chat_id, full_text, data.get("image_url")))
                del MESSAGE_BUFFER[chat_id]
        
        for chat_id, text, img in to_process:
            async with get_db_session() as db:
                await process_incoming_message(chat_id, text, db, image_url=img)
        await asyncio.sleep(0.5)

async def poll_green_api():
    logger.info("🔍 ELITE MULTIMODAL AGENT IS ONLINE...")
    asyncio.create_task(process_buffer())
    
    id_instance = settings.GREEN_API_ID_INSTANCE
    api_token = settings.GREEN_API_API_TOKEN_INSTANCE
    base_url = f"{settings.GREEN_API_HOST}/waInstance{id_instance}"
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                receive_url = f"{base_url}/receiveNotification/{api_token}"
                response = await client.get(receive_url, timeout=20.0)
                
                if response.status_code == 200 and response.json():
                    data = response.json()
                    receipt_id = data.get("receiptId")
                    body = data.get("body", {})
                    type_webhook = body.get("typeWebhook")
                    
                    # Мгновенная очередь
                    await client.delete(f"{base_url}/deleteNotification/{api_token}/{receipt_id}")

                    sender_data = body.get("senderData", {})
                    chat_id = sender_data.get("chatId")
                    message_data = body.get("messageData", {})
                    
                    user_text = ""
                    image_url = None

                    # HANDLE TEXT
                    if type_webhook == "incomingMessageReceived":
                        user_text = message_data.get("textMessageData", {}).get("textMessage") or \
                                    message_data.get("extendedTextMessageData", {}).get("text", "")
                    
                    # HANDLE AUDIO (Whisper)
                    elif type_webhook == "incomingMessageReceived" and "audioMessageData" in message_data:
                        logger.info(f"🎤 Receiving voice from {chat_id}")
                        download_url = message_data["audioMessageData"]["downloadUrl"]
                        audio_bytes = await wa_client.download_file(download_url)
                        user_text = await llm.transcribe_voice(audio_bytes)
                        logger.info(f"🎤 Transcribed: {user_text}")

                    # HANDLE IMAGE (Vision)
                    elif type_webhook == "incomingMessageReceived" and "imageMessageData" in message_data:
                        logger.info(f"📸 Receiving image from {chat_id}")
                        image_url = message_data["imageMessageData"]["downloadUrl"]
                        user_text = "Клиент прислал изображение/чек."

                    if (user_text or image_url) and chat_id and "@c.us" in chat_id:
                        if chat_id not in MESSAGE_BUFFER:
                            MESSAGE_BUFFER[chat_id] = {"texts": [], "last_time": 0, "image_url": None}
                        
                        if user_text: MESSAGE_BUFFER[chat_id]["texts"].append(user_text)
                        if image_url: MESSAGE_BUFFER[chat_id]["image_url"] = image_url
                        MESSAGE_BUFFER[chat_id]["last_time"] = time.current_time() if hasattr(time, 'current_time') else time.time()
                
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"Poll Error: {e}")
                await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(poll_green_api())
