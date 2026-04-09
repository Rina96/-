from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks, Depends
import asyncio
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import engine, Base, get_db
from crud import crud
from llm_engine import llm
from green_api import wa_client
from config import settings
from integrations_mock import crm_mock, kaspi_mock, get_upcoming_weekend_dates
import scheduler
from datetime import datetime

# Setup structured logging
logger.add("logs/app.log", rotation="50 MB", retention="10 days", level="DEBUG")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    logger.info("Initializing Database Schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database Schema Initialized.")
    
    # Start APScheduler for background proactive follow-ups
    background_scheduler = AsyncIOScheduler()
    background_scheduler.add_job(scheduler.check_silent_leads, 'interval', hours=1)
    background_scheduler.start()
    logger.info("Started Proactive Sales Scheduler.")
    
    yield
    background_scheduler.shutdown()
    logger.info("Shutting down...")
logger.add("logs/app.log", rotation="50 MB", retention="10 days", level="DEBUG")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    logger.info("Initializing Database Schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database Schema Initialized.")
    yield
    logger.info("Shutting down...")

app = FastAPI(title="AI Sales Lead Engine", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/webhook/green-api")
async def green_api_webhook(request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Webhook endpoint to receive incoming messages from WhatsApp via Green-API
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}
        
    logger.debug(f"Received Green-API Webhook.")
    
    # 1. Parse Green-API Payload
    # Extract sender info and message text (Green-API specific payload structure)
    try:
        webhook_body = payload.get("messageData", {})
        message_data = webhook_body.get("textMessageData", {}) or webhook_body.get("extendedTextMessageData", {})
        user_message = message_data.get("textMessage")
        
        sender_data = payload.get("senderData", {})
        chat_id = sender_data.get("chatId") or sender_data.get("sender")
        
        # Filter out group messages
        if chat_id and "@g.us" in chat_id:
            logger.info(f"Ignoring group message from {chat_id}")
            return {"status": "ignored", "reason": "Groups not allowed"}
            
        # Deduplication check: Green-API sends "receipt" webhooks too. Ignore them.
        type_webhook = payload.get("typeWebhook")
        if type_webhook != "incomingMessageReceived" or not user_message or not chat_id:
            return {"status": "ignored", "reason": "Not an incoming text message"}
            
    except Exception as e:
        logger.error(f"Failed to parse payload: {e}")
        return {"status": "error"}

    # 2. Add to Background Tasks to return HTTP 200 immediately to Green-API
    background_tasks.add_task(process_incoming_message, chat_id, user_message, db)
    return {"status": "received"}

async def process_incoming_message(chat_id: str, text: str, db: AsyncSession):
    """
    Background worker to process the message via SQLite and Gemini.
    """
    logger.info(f"Processing message from {chat_id}: {text[:30]}...")
    
    # 1. Retrieve or Context
    session = await crud.get_or_create_session(db, chat_id)
    
    # 2. Append User Message
    await crud.add_message_to_history(db, session, role="user", text=text)
    
    # 3. Call LLM Engine
    ai_response = llm.generate_response(user_message=text, chat_history=session.history_json)
    
    # 4. Append AI Response
    await crud.add_message_to_history(db, session, role="model", text=ai_response.reply_text)
    
    # 5. Update State and Call CRM logic
    await crud.update_session_state(db, session, ai_response.is_qualified, ai_response.needs_human)
    
    # Reset follow-up counter as user replied
    session.followup_count = 0
    
    # Save booked_at date if specified
    if ai_response.booked_date:
        dates = get_upcoming_weekend_dates()
        # Parse the string (e.g., '11.04 (суббота) в 13:00' -> datetime)
        raw_date = dates.get(ai_response.booked_date.lower())
        if raw_date:
            try:
                # Basic parsing for the day and month
                day_month = raw_date.split(" ")[0] # '11.04'
                day, month = map(int, day_month.split("."))
                year = datetime.now().year
                session.booked_at = datetime(year, month, day, 13, 0)
                logger.info(f"Saved booking date for {chat_id}: {session.booked_at}")
            except Exception as e:
                logger.error(f"Failed to parse date {raw_date}: {e}")

    await db.commit()
    message_chunks = [chunk.strip() for chunk in ai_response.reply_text.split("\n\n") if chunk.strip()]
    
    for i, chunk in enumerate(message_chunks):
        if i > 0:
            logger.info(f"Waiting 10s before next chunk for {chat_id}...")
            await asyncio.sleep(10) # Имитация набора текста
        await wa_client.send_message(chat_id=chat_id, message=chunk)
    
    # 6. Handle Mocks (Alpha CRM & Kaspi)
    if not session.crm_lead_id:
        # First time client - create alpha lead
        name = ai_response.extracted_name or "Неизвестный"
        session.crm_lead_id = await crm_mock.create_lead(name, chat_id)
        await db.commit()

    # If qualified (ready to book) - Send Kaspi Invoice
    if ai_response.is_qualified:
        # Calculate total price for all participants
        total_price = (ai_response.adult_count * 5000) + (ai_response.child_count * 2000)
        
        invoice_url = await kaspi_mock.create_invoice(chat_id, amount=total_price)
        name_str = f"{ai_response.extracted_name}, " if ai_response.extracted_name else ""
        invoice_msg = f"{name_str}для подтверждения записи на мастер-класс для всей группы ({ai_response.adult_count} взр, {ai_response.child_count} дет) оплатите, пожалуйста, счет на сумму {total_price} тг по ссылке: {invoice_url}"
        
        # Add a small delay before sending the invoice too
        await asyncio.sleep(5)
        await wa_client.send_message(chat_id, invoice_msg)
        await crm_mock.update_status(session.crm_lead_id, "3") # Статус: Записан
    
    elif ai_response.needs_human:
        await crm_mock.update_status(session.crm_lead_id, "2") # Статус: В обработке (менеджером)

    logger.success(f"Fully processed message cycle for {chat_id}")

@app.post("/webhook/alphacrm")
async def alpha_crm_webhook(request: Request, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Webhook endpoint to catch "Lead Created" from Alpha CRM
    """
    payload = await request.form()
    logger.debug(f"Received Alpha CRM Webhook: {dict(payload)}")
    
    try:
        # AmoCRM webhook payload usually arrives as x-www-form-urlencoded
        # Extracting the lead ID and the Phone number custom field (simplified)
        events = payload.get("leads[add][0][id]")
        # This is a simplification. Depending on the custom field structure, you'll extract the phone:
        phone_number = payload.get("leads[add][0][custom_fields][0][values][0][value]")
        lead_id = int(events)
        
        if phone_number and lead_id:
            # Clean number to WhatsApp format '79991234567@c.us'
            clean_phone = "".join(filter(str.isdigit, phone_number))
            wa_chat_id = f"{clean_phone}@c.us"
            
            # Initiate background task to send the FIRST qualifying message
            background_tasks.add_task(initiate_proactive_chat, wa_chat_id, lead_id, db)
            
    except Exception as e:
        logger.error(f"Failed to parse amocrm payload: {e}")
        
    return {"status": "received"}

async def initiate_proactive_chat(chat_id: str, lead_id: int, db: AsyncSession):
    """
    Called when a lead is created in CRM. The AI must message first.
    """
    logger.info(f"Initiating Proactive Chat for Lead {lead_id} -> {chat_id}")
    
    # 1. Create DB mapping locally
    session = await crud.get_or_create_session(db, chat_id)
    session.crm_lead_id = lead_id
    await db.commit()
    
    # 2. Tell LLM to generate the Hook Message based solely on the prompt "Start the conversation"
    ai_response = llm.generate_response(
        user_message="ПРОМПТ: Инициируй диалог. Поздоровайся и спроси, в силе ли их заявка на курс. (Используй знания)",
        chat_history=[]
    )
    
    # 3. Save to memory 
    await crud.add_message_to_history(db, session, "model", ai_response.reply_text)
    
    # 4. Send WA
    await wa_client.send_message(chat_id, ai_response.reply_text)
    
    # 5. Add Note/Log to CRM
    logger.info(f"[🚀 ИИ Запустил Воронку] для Лида {lead_id}")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
