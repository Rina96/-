import asyncio
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
import models

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.success("✅ Database Ready (Swiss Watch Foundation)")
    except Exception as e:
        logger.error(f"❌ DB Init Fail: {e}")
    
    loop_task = asyncio.create_task(scheduler_loop())
    yield
    loop_task.cancel()

app = FastAPI(lifespan=lifespan)

async def process_incoming_message(chat_id: str, text: str, image_url: Optional[str] = None):
    """
    SWISS WATCH CORE: Resilient Message Pipeline 4.5
    """
    try:
        # 1. 15s Delay for Human
        await asyncio.sleep(15)
        
        # 2. Check Human Takeover
        recent_wa = await wa_client.get_chat_history(chat_id, count=1)
        if recent_wa and recent_wa[0].get("role") == "assistant":
            logger.info(f"🛡 Human agent responded in {chat_id}. Юлия отключается.")
            return

        async with AsyncSessionLocal() as db:
            # 3. CRM CONTEXT (SAFE LOOKUP)
            crm_lead = await alfa_crm.get_customer_by_phone(chat_id)
            crm_name = crm_lead.get("name", "WhatsApp Lead") if crm_lead else "WhatsApp Lead"
            crm_id = crm_lead.get("id") if crm_lead else None
            
            # 4. CLOUD HISTORY (DEEP MEMORY)
            cloud_history = await wa_client.get_chat_history(chat_id, count=10)
            
            # 5. DB SESSION
            session = await crud.get_or_create_session(db, chat_id)
            if crm_id: session.crm_lead_id = str(crm_id)
            
            # Update local history
            await crud.add_message_to_history(db, session, role="user", text=text)

            # 6. AI REASONING (SUPER CONTEXT)
            final_history = cloud_history if cloud_history else session.history_json
            
            ai_response = llm.generate_response(
                user_message=text, 
                chat_history=final_history, 
                image_url=image_url,
                metadata={"client_name": crm_name, "crm_status": "existing" if crm_id else "new"}
            )
            
            # 7. RESPONSE & CRM LOG
            await crud.add_message_to_history(db, session, role="assistant", text=ai_response.reply_text)
            
            # Send to Client
            success = await wa_client.send_message(chat_id, ai_response.reply_text)
            
            # Async CRM Update
            if success:
                if ai_response.is_paid_detected and crm_id:
                    asyncio.create_task(alfa_crm.set_status(int(crm_id), alfa_crm.STATUS_PAID))
                    asyncio.create_task(alfa_crm.add_comment(int(crm_id), "Оплата подтверждена ИИ."))
                elif not crm_id:
                    asyncio.create_task(alfa_crm.sync_customer(chat_id, crm_name))

            await db.commit()
            logger.success(f"✅ Swiss Watch Core processing completed for {chat_id}")

    except Exception as e:
        logger.error(f"🚨 SWISS WATCH CORE FAIL: {e}")

@app.post("/webhook/green-api")
async def webhook(request: Request):
    try:
        data = await request.json()
        body = data.get("body", {})
        if body.get("typeWebhook") == "incomingMessageReceived":
            chat_id = body.get("senderData", {}).get("chatId")
            msg_data = body.get("messageData", {})
            text = msg_data.get("textMessageData", {}).get("textMessage", "")
            if chat_id and text:
                asyncio.create_task(process_incoming_message(chat_id, text))
        return {"status": "ok"}
    except:
        return {"status": "error"}

@app.get("/health")
async def health(): return {"status": "active"}

@app.route("/{full_path:path}")
async def catch_all(request: Request, full_path: str):
    return {"status": "ok", "message": f"Path /{full_path} handles by Julia 4.5"}
