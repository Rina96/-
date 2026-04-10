import asyncio
import time
from typing import Optional
from loguru import logger
from fastapi import FastAPI, Request
from database import engine, AsyncSessionLocal
from crud import crud
from llm_engine import llm
from green_api import wa_client
from integrations import alfa_crm
from scheduler import scheduler_loop
from contextlib import asynccontextmanager

# CRITICAL: Import models BEFORE Base to ensure tables are registered
from models import ChatSession
from database import Base  # Single source of truth for Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 JULIA 4.6 STARTING...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ DATABASE INITIALIZED")
        logger.success("✅ Database Schema Ready.")
    except Exception as e:
        print(f"❌ DATABASE ERROR: {e}")
        logger.error(f"❌ DB Init Fail: {e}")
    
    asyncio.create_task(scheduler_loop())
    yield
    print("🔌 JULIA SHUTTING DOWN...")

app = FastAPI(lifespan=lifespan)

async def process_incoming_message(chat_id: str, text: str, incoming_ts: int, image_url: Optional[str] = None):
    """
    SWISS WATCH CORE: Resilient Message Pipeline 4.6 (FULLY FIXED)
    """
    try:
        print(f"⚡️ [1/7] Processing message for {chat_id}...")
        
        # Check Human Takeover (with timestamp logic)
        cloud_history = await wa_client.get_chat_history(chat_id, count=5)
        
        human_replied = False
        for msg in cloud_history:
            if msg.get("role") == "assistant" and msg.get("ts", 0) > incoming_ts:
                human_replied = True
                break
        
        if human_replied:
            print(f"🛡 [2/7] Human takeover detected in {chat_id}. Julia silent.")
            return

        print(f"🧠 [3/7] Accessing context for {chat_id}...")
        async with AsyncSessionLocal() as db:
            # CRM CONTEXT (fail-safe)
            crm_lead = await alfa_crm.get_customer_by_phone(chat_id)
            crm_name = crm_lead.get("name", "WA Lead") if crm_lead else "WA Lead"
            crm_id = crm_lead.get("id") if crm_lead else None
            
            # DB & History
            session = await crud.get_or_create_session(db, chat_id)
            if crm_id:
                session.crm_lead_id = str(crm_id)
            await crud.add_message_to_history(db, session, role="user", text=text)

            # FIX #3: Correct call signature - no metadata parameter
            print(f"🤖 [4/7] Generating AI response for {chat_id}...")
            final_history = cloud_history if cloud_history else (session.history_json or [])
            ai_response = llm.generate_response(
                user_message=text,
                chat_history=final_history,
                image_url=image_url
            )
            
            print(f"💬 [5/7] Sending response to {chat_id}: '{ai_response.reply_text[:30]}...'")
            await crud.add_message_to_history(db, session, role="assistant", text=ai_response.reply_text)
            
            success = await wa_client.send_message(chat_id, ai_response.reply_text)
            print(f"{'✅' if success else '❌'} [6/7] Send status: {success}")

            # Async CRM update (non-blocking)
            if crm_id and ai_response.is_paid_detected:
                asyncio.create_task(alfa_crm.set_status(int(crm_id), alfa_crm.STATUS_PAID))
            elif not crm_id:
                asyncio.create_task(alfa_crm.sync_customer(chat_id, crm_name))

            await db.commit()
            print(f"✅ [7/7] Finished processing {chat_id}")
            logger.success(f"✅ Cycle complete for {chat_id}")

    except Exception as e:
        print(f"🚨 CRITICAL WORKER ERROR: {e}")
        logger.error(f"🚨 Worker error for {chat_id}: {e}")


@app.post("/webhook/green-api")
async def webhook(request: Request):
    """
    FIX #2: Read body only ONCE via request.json() to avoid stream exhaustion.
    """
    try:
        # FIX: Read JSON only once, do NOT call request.body() first
        data = await request.json()
        print(f"DEBUG: WEBHOOK ARRIVED! Keys: {list(data.keys())}")
        
        body = data.get("body", {})
        
        if body.get("typeWebhook") == "incomingMessageReceived":
            chat_id = body.get("senderData", {}).get("chatId")
            incoming_ts = body.get("timestamp", int(time.time()))
            msg_data = body.get("messageData", {})
            
            text = ""
            image_url = None
            
            if "textMessageData" in msg_data:
                text = msg_data["textMessageData"].get("textMessage", "")
            elif "imageMessageData" in msg_data:
                image_url = msg_data["imageMessageData"].get("downloadUrl")
                text = msg_data["imageMessageData"].get("caption", "Image")

            if chat_id and (text or image_url):
                print(f"📩 RELEVANT MESSAGE from {chat_id}: '{text[:30]}'")
                asyncio.create_task(
                    process_incoming_message(chat_id, text, incoming_ts, image_url)
                )
            else:
                print(f"⚠️ IGNORED: No usable content from {chat_id}")
        else:
            print(f"ℹ️ NON-MESSAGE WEBHOOK: {body.get('typeWebhook')}")
        
        return {"status": "ok"}
    except Exception as e:
        print(f"🚨 WEBHOOK ERROR: {e}")
        logger.error(f"🚨 Webhook error: {e}")
        return {"status": "error", "reason": str(e)}


@app.get("/health")
async def health():
    return {"status": "active", "version": "4.6"}


@app.api_route("/{full_path:path}", methods=["GET", "POST", "HEAD"])
async def catch_all(request: Request, full_path: str = ""):
    return {"status": "ok", "path": full_path, "bot": "Julia 4.6"}
