import asyncio
import os
from typing import Optional
from loguru import logger
from fastapi import FastAPI, Request
from database import engine, Base, AsyncSessionLocal
from crud import crud
from llm_engine import llm
from green_api import wa_client
from config import settings
from integrations import alfa_crm
from scheduler import scheduler_loop
from contextlib import asynccontextmanager

# Block 1 CRITICAL: Models must be imported BEFORE create_all
import models

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Database Schema
    try:
        logger.info("🛠 Critical DB Initialization...")
        async with engine.begin() as conn:
            # Metadata now correctly contains ChatSession tables
            await conn.run_sync(Base.metadata.create_all)
        logger.success("✅ Database Schema Ready.")
    except Exception as e:
        logger.error(f"❌ DATABASE INIT ERROR: {e}")

    # 2. Start Scheduler 
    logger.info("📡 Starting Proactive Scheduler Loop...")
    loop_task = asyncio.create_task(scheduler_loop())
    yield
    loop_task.cancel()
    logger.info("🔌 Shutting down...")

app = FastAPI(lifespan=lifespan)

async def process_incoming_message(chat_id: str, text: str, image_url: Optional[str] = None, pdf_bytes: Optional[bytes] = None):
    """
    Block 2: Protected Background Worker (Anti-Crash)
    """
    try:
        # Human-First Delay
        await asyncio.sleep(15)
        
        # Check human takeover
        history = await wa_client.get_chat_history(chat_id, count=1)
        if history and history[0].get("type") == "outgoing":
            logger.info(f"🛡 Human takeover detected in {chat_id}. Юлия отступает.")
            return

        async with AsyncSessionLocal() as db:
            session = await crud.get_or_create_session(db, chat_id)
            await crud.add_message_to_history(db, session, role="user", text=text)

            # CRM Sync
            try:
                if not session.crm_lead_id:
                    crm_id = await alfa_crm.sync_customer(phone=chat_id, name="Lead from WA")
                    if crm_id: session.crm_lead_id = str(crm_id)
            except Exception as e:
                logger.error(f"CRM ERROR: {e}")

            # AI Thinking
            pdf_text = llm.extract_text_from_pdf(pdf_bytes) if pdf_bytes else None
            ai_response = llm.generate_response(user_message=text, chat_history=session.history_json, image_url=image_url, pdf_text=pdf_text)
            
            # Update state with safety
            updates = {
                "is_paid": ai_response.is_paid_detected or session.is_paid,
                "booked_date": ai_response.booked_date or session.booked_date,
                "is_qualified": ai_response.is_qualified,
                "needs_human": ai_response.needs_human
            }
            await crud.update_session_state(db, session, updates)

            # Output
            await crud.add_message_to_history(db, session, role="assistant", text=ai_response.reply_text)
            
            if ai_response.voice_response_needed:
                audio = await llm.generate_voice(ai_response.reply_text)
                await wa_client.send_file(chat_id, audio, "reply.ogg")
            else:
                await wa_client.send_message(chat_id, ai_response.reply_text)

            await db.commit()
            logger.success(f"✅ processed {chat_id}")
            
    except Exception as e:
        logger.error(f"❌ CRITICAL ERROR in process_incoming_message: {e}")

@app.post("/webhook/green-api")
async def webhook(request: Request):
    """
    Block 4: Defensive parsing + Block 8: Empty Data Filter
    """
    try:
        data = await request.json()
        
        # Block 8: Filter empty/invalid webhooks
        if not data or "body" not in data:
            return {"status": "empty or invalid"}

        body = data.get("body", {})
        type_webhook = body.get("typeWebhook")
        
        if type_webhook == "incomingMessageReceived":
            chat_id = body.get("senderData", {}).get("chatId")
            msg_data = body.get("messageData", {})
            
            text = ""
            image_url = None
            pdf_bytes = None
            
            if "textMessageData" in msg_data:
                text = msg_data["textMessageData"].get("textMessage", "")
            elif "imageMessageData" in msg_data:
                image_url = msg_data["imageMessageData"].get("downloadUrl")
                text = msg_data["imageMessageData"].get("caption", "Image")
            elif "fileMessageData" in msg_data:
                if msg_data["fileMessageData"].get("fileName", "").lower().endswith(".pdf"):
                    pdf_bytes = await wa_client.download_file(msg_data["fileMessageData"].get("downloadUrl"))
                    text = "PDF Check"

            if chat_id and (text or image_url or pdf_bytes):
                # Block 2: Anti-crash task execution
                asyncio.create_task(process_incoming_message(chat_id, text, image_url, pdf_bytes))
            else:
                return {"status": "no relevant content"}

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"🚨 WEBHOOK ERROR: {e}")
        return {"status": "error", "message": str(e)}

@app.head("/health")
@app.get("/health")
async def health(): return {"status": "active"}

@app.get("/")
async def root(): return {"status": "online", "bot": "Julia 4.4"}
