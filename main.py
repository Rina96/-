import asyncio
import time
from typing import Optional, List
from loguru import logger
from fastapi import FastAPI, Request
from database import Base, engine, AsyncSessionLocal
from crud import crud
from llm_engine import llm
from green_api import wa_client
from integrations import alfa_crm
from scheduler import scheduler_loop
from contextlib import asynccontextmanager
from models import ChatSession, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Print is used for "Loud" logging in Render console
    print("🚀 JULIA 4.6 STARTING...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ DATABASE INITIALIZED")
    except Exception as e:
        print(f"❌ DATABASE ERROR: {e}")
    
    asyncio.create_task(scheduler_loop())
    yield
    print("🔌 JULIA SHUTTING DOWN...")

app = FastAPI(lifespan=lifespan)

async def process_incoming_message(chat_id: str, text: str, incoming_ts: int, image_url: Optional[str] = None):
    """
    SWISS WATCH CORE: Resilient Message Pipeline 4.6 (NO DELAY TEST)
    """
    try:
        # HUMAN DELAY REMOVED FOR DEBUGGING
        print(f"⚡️ [1/7] Processing message for {chat_id} WITHOUT DELAY...")
        
        # Check Human Takeover (Still keep logic but no sleep)
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
            # CRM CONTEXT
            crm_lead = await alfa_crm.get_customer_by_phone(chat_id)
            crm_name = crm_lead.get("name", "WA Lead") if crm_lead else "WA Lead"
            crm_id = crm_lead.get("id") if crm_lead else None
            
            # DB & History
            session = await crud.get_or_create_session(db, chat_id)
            if crm_id: session.crm_lead_id = str(crm_id)
            await crud.add_message_to_history(db, session, role="user", text=text)

            # AI Thinking
            print(f"🤖 [4/7] Generating AI response for {chat_id}...")
            ai_response = llm.generate_response(
                user_message=text, 
                chat_history=cloud_history if cloud_history else session.history_json, 
                image_url=image_url,
                metadata={"client_name": crm_name, "crm_status": "existing" if crm_id else "new"}
            )
            
            print(f"💬 [5/7] Sending response to {chat_id}...")
            await crud.add_message_to_history(db, session, role="assistant", text=ai_response.reply_text)
            
            success = await wa_client.send_message(chat_id, ai_response.reply_text)
            
            if success:
                print(f"📈 [6/7] Updating CRM for {chat_id}...")
                if ai_response.is_paid_detected and crm_id:
                    asyncio.create_task(alfa_crm.set_status(int(crm_id), alfa_crm.STATUS_PAID))
                elif not crm_id:
                    asyncio.create_task(alfa_crm.sync_customer(chat_id, crm_name))

            await db.commit()
            print(f"✅ [7/7] Finished processing {chat_id}")

    except Exception as e:
        print(f"🚨 CRITICAL WORKER ERROR: {e}")

@app.post("/webhook/green-api")
async def webhook(request: Request):
    """
    Block 6: Defensive parsing logic + LOUD DEBUGGING
    """
    try:
        # LOUD DEBUG: Print immediately
        raw_body = await request.body()
        print(f"DEBUG: WEBHOOK ARRIVED! Raw Body: {raw_body.decode()[:200]}")
        
        data = await request.json()
        body = data.get("body", {})
        
        if body.get("typeWebhook") == "incomingMessageReceived":
            chat_id = body.get("senderData", {}).get("chatId")
            incoming_ts = body.get("timestamp", int(time.time()))
            msg_data = body.get("messageData", {})
            text = msg_data.get("textMessageData", {}).get("textMessage", "")
            
            if chat_id and text:
                print(f"📩 RELEVANT MESSAGE from {chat_id}: '{text[:20]}'")
                asyncio.create_task(process_incoming_message(chat_id, text, incoming_ts))
            else:
                print(f"⚠️ IGNORED: Empty message or non-text in {chat_id}")
        
        return {"status": "ok"}
    except Exception as e:
        print(f"🚨 WEBHOOK ERROR: {e}")
        return {"status": "error"}

@app.get("/health")
async def health(): return {"status": "active"}

@app.api_route("/{full_path:path}")
async def catch_all(request: Request, full_path: str = ""):
    return {"status": "ok", "message": f"Path /{full_path} handled by Julia 4.6"}
