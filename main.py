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
from crm_factory import CRMFactory
from scheduler import scheduler_loop
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select

# CRITICAL: Import models before Base to ensure tables are registered
from models import ChatSession, Company
from database import Base
from api_routes import router as api_router


# CRM adapters cache for performance
crm_adapters_cache: dict = {}


async def get_crm_adapter(company_id: int):
    """Get or create CRM adapter for company."""
    if company_id in crm_adapters_cache:
        return crm_adapters_cache[company_id]

    async with AsyncSessionLocal() as db:
        company = await crud.get_company(db, company_id)
        if not company:
            logger.error(f"❌ Company {company_id} not found")
            return None

        adapter = await CRMFactory.create_adapter(company.crm_type, company.crm_config)
        if adapter:
            crm_adapters_cache[company_id] = adapter
            logger.success(f"✅ CRM adapter cached for company {company_id}")
        return adapter


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 JULIA 5.0 - MULTI-CRM PLATFORM STARTING...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ DATABASE INITIALIZED")
        logger.success("✅ Database Schema Ready.")

        # Initialize default company if none exists
        async with AsyncSessionLocal() as db:
            default_company = await crud.get_company(db, 1)
            if not default_company:
                logger.info("🆕 Creating default company...")
                default_company = await crud.create_company(
                    db,
                    name="Default",
                    crm_type="alfarc",
                    crm_config={
                        "base_url": "https://shkolago.s20.online",
                        "email": "schoolgoalmaty@gmail.com",
                        "api_key": "95a954c1-33e5-11f1-a996-3cecefbdd1ae",
                        "app_key": "325702e0f2a21a95b6df99e47dc82d02"
                    }
                )
                if default_company:
                    logger.success(f"✅ Default company created (ID: {default_company.id})")

    except Exception as e:
        print(f"❌ DATABASE ERROR: {e}")
        logger.error(f"❌ DB Init Fail: {e}")

    asyncio.create_task(scheduler_loop())
    yield
    print("🔌 JULIA SHUTTING DOWN...")


app = FastAPI(lifespan=lifespan)

# Add CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


async def process_incoming_message(
    chat_id: str,
    text: str,
    incoming_ts: int,
    company_id: int = 1,
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

        print(f"🧠 [2/7] Fetching context for {chat_id} (Company {company_id})...")
        async with AsyncSessionLocal() as db:
            # Get CRM adapter for this company
            crm_adapter = await get_crm_adapter(company_id)
            if not crm_adapter:
                logger.error(f"❌ No CRM adapter for company {company_id}")
                return

            # CRM CONTEXT (using dynamic adapter)
            crm_lead = await crm_adapter.get_lead_by_phone(chat_id)
            crm_name = crm_lead.name if crm_lead else ""
            crm_id = crm_lead.id if crm_lead else None

            # DB Session with company_id
            session = await crud.get_or_create_session(db, chat_id, company_id)
            if crm_id:
                session.crm_lead_id = str(crm_id)

            # Save name to DB session for future reference
            if crm_name and not session.client_name:
                session.client_name = crm_name

            await crud.add_message_to_history(db, session, role="user", text=text)

            final_history = cloud_history if cloud_history else (session.history_json or [])

            # Run blocking OpenAI call in thread pool — non-blocking
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
                print(f"📋 [6/7] Creating new CRM lead for {chat_id}...")
                new_crm_id = await crm_adapter.create_lead(
                    name=session.client_name or ai_response.extracted_name or "WA Lead",
                    phone=chat_id
                )
                if new_crm_id:
                    session.crm_lead_id = str(new_crm_id)
                    crm_id = new_crm_id
                    print(f"✅ CRM lead created: ID={new_crm_id}")
                else:
                    print(f"⚠️ CRM lead creation failed — will retry next message")

            # Update CRM status based on AI detections
            if crm_id:
                if ai_response.is_paid_detected:
                    session.is_paid = True
                    await crm_adapter.set_lead_status(crm_id, "paid")
                    await crm_adapter.update_lead(crm_id, {
                        "comment": "✅ Оплата подтверждена через WhatsApp"
                    })
                elif ai_response.booked_date:
                    session.booked_date = ai_response.booked_date
                    session.booked_at = datetime.datetime.utcnow()
                    await crm_adapter.set_lead_status(crm_id, "booked")
                    await crm_adapter.update_lead(crm_id, {
                        "comment": f"📅 Записан на мастер-класс: {ai_response.booked_date}"
                    })
                elif ai_response.is_qualified:
                    session.is_qualified = True
                    await crm_adapter.set_lead_status(crm_id, "qualified")

            await db.commit()
            print(f"✅ [7/7] Finished processing {chat_id}")
            logger.success(f"✅ Cycle complete for {chat_id}")

    except Exception as e:
        print(f"🚨 CRITICAL WORKER ERROR for {chat_id}: {e}")
        logger.error(f"🚨 Worker error: {e}")


@app.post("/webhook/green-api")
async def webhook_green_api(request: Request):
    """
    Green API webhook handler with multi-company support.
    Supports fields at ROOT level: data["typeWebhook"], data["senderData"], data["messageData"]
    """
    try:
        data = await request.json()
        print(f"DEBUG: WEBHOOK ARRIVED! Keys: {list(data.keys())}")

        # Extract company_id if provided (optional, defaults to 1)
        company_id = data.get("companyId", 1)

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
                print(f"📩 RELEVANT MESSAGE from {chat_id} (Company {company_id}): '{text[:40]}'")
                asyncio.create_task(
                    process_incoming_message(chat_id, text, incoming_ts, company_id, image_url)
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


@app.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request):
    """
    Generic WhatsApp webhook handler with company support.
    Expected payload:
    {
        "chatId": "1234567890@c.us",
        "textMessage": "Hello",
        "timestamp": 1234567890,
        "companyId": 1
    }
    """
    try:
        data = await request.json()

        chat_id = data.get("chatId")
        text = data.get("textMessage")
        incoming_ts = data.get("timestamp", int(time.time()))
        company_id = data.get("companyId", 1)
        image_url = data.get("imageUrl")

        if not chat_id or not text:
            return {"error": "Missing required fields: chatId, textMessage"}

        print(f"📩 WhatsApp message from {chat_id} (Company {company_id}): '{text[:40]}'")
        asyncio.create_task(
            process_incoming_message(chat_id, text, incoming_ts, company_id, image_url)
        )

        return {"status": "processing", "companyId": company_id}

    except Exception as e:
        print(f"🚨 WEBHOOK ERROR: {e}")
        logger.error(f"🚨 Webhook error: {e}")
        return {"status": "error", "reason": str(e)}


@app.get("/health")
async def health_check():
    """Health check with company status."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Company))
            companies = result.scalars().all()

            company_statuses = []
            for company in companies:
                adapter = await get_crm_adapter(company.id)
                is_connected = adapter is not None

                company_statuses.append({
                    "id": company.id,
                    "name": company.name,
                    "crm_type": company.crm_type,
                    "active": company.is_active,
                    "crm_connected": is_connected
                })

            return {
                "status": "healthy",
                "version": "5.0-MultiCRM",
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "companies": company_statuses,
                "total_companies": len(companies),
                "connected_companies": sum(1 for c in company_statuses if c["crm_connected"])
            }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.api_route("/{full_path:path}", methods=["GET", "POST", "HEAD"])
async def catch_all(request: Request, full_path: str = ""):
    return {"status": "ok", "path": full_path, "bot": "Julia 5.0-MultiCRM", "note": "Use /api endpoints for company management"}
