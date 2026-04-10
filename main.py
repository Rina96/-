import asyncio
import os
from typing import Optional
from loguru import logger
from fastapi import FastAPI, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from database import engine, Base, AsyncSessionLocal # Use AsyncSessionLocal for tasks
from crud import crud
from llm_engine import llm
from green_api import wa_client
from config import settings
from integrations_mock import kaspi_mock
from scheduler import scheduler_loop
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Database Schema (Migration-on-the-fly)
    try:
        logger.info("🛠 Initializing Database Schema...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.success("✅ Database Schema Ready.")
    except Exception as e:
        logger.error(f"❌ DB Init Error: {e}")

    # 2. Start Scheduler in background
    logger.info("📡 Starting Proactive Scheduler...")
    loop_task = asyncio.create_task(scheduler_loop())
    yield
    loop_task.cancel()
    logger.info("🔌 Shutting down...")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(lifespan=lifespan)

# --- MIDDLEWARE (For Cron-job headers support) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. LIGHTWEIGHT HEALTH CHECK ---
@app.get("/")
@app.head("/")
async def root_check():
    """Wakes up the bot from the root URL."""
    return {"status": "ok", "message": "Julia is awake!"}

@app.get("/health")
@app.get("/health/")
@app.api_route("/health", methods=["GET", "HEAD", "OPTIONS"])
@app.api_route("/health/", methods=["GET", "HEAD", "OPTIONS"])
async def health_check():
    """Ultra-fast wake-up endpoint for Render & Cron-job."""
    return {"status": "ok"}

# --- 3. THE ULTIMATE CATCH-ALL (Diagnostic Tool) ---
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"])
async def catch_all(request: Request, path_name: str):
    """Intercepts ANY path to wake up the bot and log what Cron-job is hitting."""
    logger.info(f"🚩 Mystery request caught! Path: /{path_name} | Method: {request.method} | IP: {request.client.host if request.client else 'unknown'}")
    return {
        "status": "ok", 
        "message": f"Julia caught your request to /{path_name}!", 
        "path": path_name,
        "method": request.method
    }

# --- 2. ROBUST BACKGROUND WORKER ---
async def process_incoming_message(chat_id: str, text: str, image_url: Optional[str] = None, pdf_bytes: Optional[bytes] = None):
    """Elite worker with INDEPENDENT DB SESSION and error handling."""
    try:
        # 1. Human-First Delay (15 seconds)
        logger.info(f"⏳ Waiting 15s for human takeover in {chat_id}...")
        await asyncio.sleep(15)
        
        # Check if human replied in the meantime
        history = await wa_client.get_chat_history(chat_id, count=1)
        if history and history[0].get("type") == "outgoing":
            logger.info(f"🛡 Human takeover detected in {chat_id}. Юлия отступает.")
            return

        # Use independent session for background processing
        async with AsyncSessionLocal() as db:
            session = await crud.get_or_create_session(db, chat_id)
            await crud.add_message_to_history(db, session, role="user", text=text)

            # 2. PDF Processing
            pdf_text = None
            if pdf_bytes:
                logger.info(f"📄 Parsing PDF for {chat_id}")
                pdf_text = llm.extract_text_from_pdf(pdf_bytes)

            # 3. AI Thinking (Self-Reflection + Vision)
            ai_response = llm.generate_response(user_message=text, chat_history=session.history_json, image_url=image_url, pdf_text=pdf_text)
            
            # Update Database with payment status if detected
            if ai_response.is_paid_detected:
                logger.success(f"💰 Payment detected for {chat_id}!")
                session.is_paid = True
                session.booked_date = ai_response.booked_date or session.booked_date

            await crud.add_message_to_history(db, session, role="assistant", text=ai_response.reply_text)
            
            # 4. Response
            if ai_response.voice_response_needed and settings.VOICE_ENABLED:
                audio_bytes = await llm.generate_voice(ai_response.reply_text)
                temp_path = f"voice_{chat_id}.ogg"
                with open(temp_path, "wb") as f: f.write(audio_bytes)
                await wa_client.send_file(chat_id, temp_path)
                os.remove(temp_path)
            else:
                chunks = [c.strip() for c in ai_response.reply_text.split("\n\n") if c.strip()][:2]
                for i, chunk in enumerate(chunks):
                    if i > 0: await asyncio.sleep(4)
                    await wa_client.send_message(chat_id, chunk)

            await db.commit()
            logger.success(f"✅ processed {chat_id}")
            
    except Exception as e:
        logger.error(f"❌ Critical Error in background worker: {e}")

@app.post("/webhook/green-api")
async def webhook(request: Request):
    """Reliable webhook receiver that fires-and-forgets to avoid blocking."""
    try:
        data = await request.json()
        body = data.get("body", {})
        type_webhook = body.get("typeWebhook")
        
        if type_webhook == "incomingMessageReceived":
            chat_id = body.get("senderData", {}).get("chatId")
            msg_data = body.get("messageData", {})
            
            text = ""
            image_url = None
            pdf_bytes = None
            
            # Extract content types
            if "textMessageData" in msg_data:
                text = msg_data["textMessageData"].get("textMessage", "")
            elif "imageMessageData" in msg_data:
                image_url = msg_data["imageMessageData"].get("downloadUrl")
                text = msg_data["imageMessageData"].get("caption", "Скриншот")
            elif "fileMessageData" in msg_data:
                doc_url = msg_data["fileMessageData"].get("downloadUrl")
                file_name = msg_data["fileMessageData"].get("fileName", "")
                if file_name.lower().endswith(".pdf"):
                    pdf_bytes = await wa_client.download_file(doc_url)
                    text = "Прислал PDF чек"

            if chat_id:
                # Create independent task without passing the request's DB session
                asyncio.create_task(process_incoming_message(chat_id, text, image_url, pdf_bytes))
                
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error"}
