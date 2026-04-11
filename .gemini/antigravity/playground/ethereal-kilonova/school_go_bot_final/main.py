import asyncio
import time
import datetime
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

# CRITICAL: Import models before Base to ensure tables are registered
from models import ChatSession
from database import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 JULIA 4.7 STARTING...")
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


async def process_incoming_message(
    chat_id: str,
    text: str,
    incoming_ts: int,
    image_url: Optional[str] = None
):
    """
    SWISS WATCH CORE: Resilient Message Pipeline 4.7 (ALL BUGS FIXED)
    FIX 2: generate_response runs in thread pool (non-blocking)
    FIX 3: booked_at is set when AI detects booked_date
    FIX 1: client_name passed to AI for personalized responses
    """
    try:
        print(f"⚡️ [1/7] Processing message for {chat_id}...")

        # Check Human Takeover (timestamp-based)
        cloud_history = await wa_client.get_chat_history(chat_id, count=5)

        human_replied = any(
            msg.get("role") == "assistant" and msg.get("ts", 0) > incoming_ts
            for msg in cloud_history
        )

        if human_replied:
            print(f"🛡 Human takeover detected in {chat_id}. Julia silent.")
            return

        print(f"🧠 [2/7] Fetching context for {chat_id}...")
        async with AsyncSessionLocal() as db:
            # CRM CONTEXT (fail-safe, with name)
            crm_lead = await alfa_crm.get_customer_by_phone(chat_id)
            crm_name = crm_lead.get("name", "") if crm_lead else ""
            crm_id = crm_lead.get("id") if crm_lead else None

            # DB Session
            session = await crud.get_or_create_session(db, chat_id)
            if crm_id:
                session.crm_lead_id = str(crm_id)

            # FIX 1: Save name to DB session for future reference
            if crm_name and not session.client_name:
                session.client_name = crm_name

            await crud.add_message_to_history(db, session, role="user", text=text)

            final_history = cloud_history if cloud_history else (session.history_json or [])

            # FIX 2: Run blocking OpenAI call in thread pool — non-blocking
            print(f"🤖 [3/7] Generating AI response for {chat_id}...")
            ai_response = await asyncio.to_thread(
                llm.generate_response,
                user_message=text,
                chat_history=final_history,
                image_url=image_url,
                client_name=crm_name or session.client_name or ""
            )

            print(f"💬 [4/7] Sending response to {chat_id}: '{ai_response.reply_text[:40]}...'")
            await crud.add_message_to_history(db, session, role="assistant", text=ai_response.reply_text)

            # FIX 3: Set booked_at when AI detects booking date
            if ai_response.booked_date and not session.booked_at:
                session.booked_date = ai_response.booked_date
                session.booked_at = datetime.datetime.utcnow()
                print(f"📅 [5/7] Booking set for {chat_id}: {ai_response.booked_date}")

            # FIX 1: Save extracted name from AI if CRM didn't have one
            if ai_response.extracted_name and not session.client_name:
                session.client_name = ai_response.extracted_name

            success = await wa_client.send_message(chat_id, ai_response.reply_text)
            print(f"{'✅' if success else '❌'} [6/7] WA send status: {success}")

            # CRM SYNC: Create or update lead
            if not crm_id:
                # FIX: await directly to get the new ID and save it to session
                print(f"📋 [6/7] Creating new CRM lead for {chat_id}...")
                new_crm_id = await alfa_crm.sync_customer(
                    chat_id,
                    session.client_name or ai_response.extracted_name or "WA Lead"
                )
                if new_crm_id:
                    session.crm_lead_id = str(new_crm_id)
                    crm_id = new_crm_id
                    print(f"✅ CRM lead created: ID={new_crm_id}")
                    # Add first message as context in CRM
                    asyncio.create_task(
                        alfa_crm.add_comment(int(new_crm_id), f"Первое сообщение: {text[:100]}")
                    )
                else:
                    print(f"⚠️ CRM lead creation failed — will retry next message")

            # Update CRM status based on AI detections
            if crm_id:
                if ai_response.is_paid_detected:
                    asyncio.create_task(
                        alfa_crm.set_status(int(crm_id), alfa_crm.STATUS_PAID)
                    )
                    asyncio.create_task(
                        alfa_crm.add_comment(int(crm_id), "✅ Оплата подтверждена через WhatsApp")
                    )
                elif ai_response.booked_date:
                    asyncio.create_task(
                        alfa_crm.set_status(int(crm_id), alfa_crm.STATUS_BOOKED)
                    )
                    asyncio.create_task(
                        alfa_crm.add_comment(int(crm_id), f"📅 Записан на мастер-класс: {ai_response.booked_date}")
                    )
                elif ai_response.is_qualified:
                    asyncio.create_task(
                        alfa_crm.set_status(int(crm_id), alfa_crm.STATUS_NEW)
                    )

            await db.commit()
            print(f"✅ [7/7] Finished processing {chat_id}")
            logger.success(f"✅ Cycle complete for {chat_id}")

    except Exception as e:
        print(f"🚨 CRITICAL WORKER ERROR for {chat_id}: {e}")
        logger.error(f"🚨 Worker error: {e}")


@app.post("/webhook/green-api")
async def webhook(request: Request):
    """
    CRITICAL FIX: Green API sends fields at ROOT level, not in 'body'.
    Correct format: data["typeWebhook"], data["senderData"], data["messageData"]
    Supports both formats for compatibility.
    """
    try:
        data = await request.json()
        print(f"DEBUG: WEBHOOK ARRIVED! Keys: {list(data.keys())}")

        # Green API Webhook Endpoint format: fields at ROOT level
        # (NOT nested in "body" — that was the bug)
        type_webhook = data.get("typeWebhook", "")

        if type_webhook == "incomingMessageReceived":
            chat_id = data.get("senderData", {}).get("chatId")
            incoming_ts = data.get("timestamp", int(time.time()))
            msg_data = data.get("messageData", {})

            text = ""
            image_url = None

            if "textMessageData" in msg_data:
                text = msg_data["textMessageData"].get("textMessage", "")
            elif "extendedTextMessageData" in msg_data:
                text = msg_data["extendedTextMessageData"].get("text", "")
            elif "imageMessageData" in msg_data:
                image_url = msg_data["imageMessageData"].get("downloadUrl")
                text = msg_data["imageMessageData"].get("caption", "Image")

            if chat_id and "@c.us" in chat_id and (text or image_url):
                print(f"📩 RELEVANT MESSAGE from {chat_id}: '{text[:40]}'")
                asyncio.create_task(
                    process_incoming_message(chat_id, text, incoming_ts, image_url)
                )
            elif chat_id and "@g.us" in chat_id:
                print(f"🛡 IGNORED: Group message from {chat_id}")
            else:
                print(f"⚠️ IGNORED: Non-individual chat ({chat_id}) or no content.")
        else:
            print(f"ℹ️ NON-MESSAGE WEBHOOK: {type_webhook}")

        return {"status": "ok"}
    except Exception as e:
        print(f"🚨 WEBHOOK ERROR: {e}")
        logger.error(f"🚨 Webhook error: {e}")
        return {"status": "error", "reason": str(e)}


@app.get("/health")
async def health():
    return {"status": "active", "version": "5.1-Logged"}


@app.api_route("/{full_path:path}", methods=["GET", "POST", "HEAD"])
async def catch_all(request: Request, full_path: str = ""):
    return {"status": "ok", "path": full_path, "bot": "Julia 4.7"}
