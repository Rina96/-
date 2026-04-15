"""
Example of updated main.py for multi-company multi-CRM support.
This shows how to integrate the new company/CRM system into message processing.

To use: Review this example, then apply changes to the actual main.py
"""

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

# CRITICAL: Import models before Base to ensure tables are registered
from models import ChatSession, Company
from database import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 JULIA WITH MULTI-CRM SUPPORT STARTING...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ DATABASE INITIALIZED")
        logger.success("✅ Database Schema Ready.")

        # Initialize default company if none exists
        async with AsyncSessionLocal() as db:
            companies = await crud.get_company(db, 1)
            if not companies:
                logger.info("🆕 Creating default company...")
                # Default to AlfaCRM for backward compatibility
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
                logger.success(f"✅ Default company created (ID: {default_company.id})")

    except Exception as e:
        print(f"❌ DATABASE ERROR: {e}")
        logger.error(f"❌ DB Init Fail: {e}")

    asyncio.create_task(scheduler_loop())
    yield
    print("🔌 JULIA SHUTTING DOWN...")


app = FastAPI(lifespan=lifespan)

# Global CRM adapters cache
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


async def process_incoming_message(
    chat_id: str,
    text: str,
    incoming_ts: int,
    company_id: int = 1,  # NEW: Company parameter
    image_url: Optional[str] = None
):
    """
    SWISS WATCH CORE: Multi-Company Resilient Message Pipeline 4.8+

    NEW FEATURES:
    - Multi-company support
    - Dynamic CRM adapter selection
    - Company-specific processing
    """
    try:
        print(f"⚡️ [1/8] Processing message for {chat_id} (Company {company_id})...")

        # Check Human Takeover (timestamp-based)
        cloud_history = await wa_client.get_chat_history(chat_id, count=5)

        human_replied = any(
            msg.get("role") == "assistant" and msg.get("ts", 0) > incoming_ts
            for msg in cloud_history
        )

        if human_replied:
            print(f"🛡 Human takeover detected in {chat_id}. Julia silent.")
            return

        print(f"🧠 [2/8] Fetching context for {chat_id}...")
        async with AsyncSessionLocal() as db:
            # NEW: Get CRM adapter for this company
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

            # Save name to DB session
            if crm_name and not session.client_name:
                session.client_name = crm_name

            await crud.add_message_to_history(db, session, role="user", text=text)

            final_history = cloud_history if cloud_history else (session.history_json or [])

            # Generate AI response
            print(f"🤖 [3/8] Generating AI response for {chat_id}...")
            ai_response = await asyncio.to_thread(
                llm.generate_response,
                user_message=text,
                chat_history=final_history,
                image_url=image_url,
                client_name=crm_name or session.client_name or ""
            )

            print(f"💬 [4/8] Sending response to {chat_id}: '{ai_response.reply_text[:40]}...'")
            await crud.add_message_to_history(db, session, role="assistant", text=ai_response.reply_text)

            # Handle booking detection
            if ai_response.booked_date:
                session.booked_date = ai_response.booked_date
                session.booked_at = datetime.datetime.utcnow()
                logger.success(f"📅 Booking detected for {chat_id}: {ai_response.booked_date}")

            # Handle qualification
            if ai_response.is_qualified:
                session.is_qualified = True
                # NEW: Update CRM using dynamic adapter
                if crm_id:
                    await crm_adapter.set_lead_status(crm_id, "qualified")
                logger.success(f"✅ Lead qualified: {chat_id}")

            await db.commit()

            # Send to WhatsApp
            print(f"📤 [5/8] Sending WhatsApp message...")
            try:
                await wa_client.send_message(chat_id, ai_response.reply_text)
                logger.success(f"✅ Message sent to {chat_id}")
            except Exception as e:
                logger.error(f"❌ WhatsApp send fail: {e}")
                return

            # Add CRM comment
            if crm_id:
                print(f"📝 [6/8] Adding CRM comment...")
                await crm_adapter.update_lead(
                    crm_id,
                    {"comment": f"Julia: {ai_response.reply_text[:100]}"}
                )

            print(f"✅ [7/8] Message processing complete for {chat_id}")

    except Exception as e:
        logger.error(f"❌ Message processing failed for {chat_id}: {e}")
        import traceback
        traceback.print_exc()


# API Endpoint Example
@app.post("/webhook/whatsapp")
async def receive_whatsapp_message(request: Request):
    """
    Example webhook endpoint for WhatsApp messages.

    Expected payload:
    {
        "chatId": "1234567890@c.us",
        "textMessage": "Hello",
        "timestamp": 1234567890,
        "companyId": 1  # NEW: Company identifier
    }
    """
    try:
        data = await request.json()

        chat_id = data.get("chatId")
        text = data.get("textMessage")
        incoming_ts = data.get("timestamp", int(time.time()))
        company_id = data.get("companyId", 1)  # Default to company 1
        image_url = data.get("imageUrl")

        if not chat_id or not text:
            return {"error": "Missing required fields"}

        # Process in background
        asyncio.create_task(
            process_incoming_message(chat_id, text, incoming_ts, company_id, image_url)
        )

        return {"status": "processing", "companyId": company_id}

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return {"error": str(e)}


@app.get("/health")
async def health_check():
    """Health check endpoint with company status."""
    async with AsyncSessionLocal() as db:
        companies = []
        # List all companies
        from sqlalchemy.future import select
        result = await db.execute(select(Company))
        company_list = result.scalars().all()

        for company in company_list:
            adapter = await get_crm_adapter(company.id)
            companies.append({
                "id": company.id,
                "name": company.name,
                "crm_type": company.crm_type,
                "active": company.is_active,
                "crm_connected": adapter is not None
            })

        return {
            "status": "healthy",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "companies": companies
        }


# Example: Add a new company via API
@app.post("/api/companies")
async def add_company(name: str, crm_type: str, config: dict):
    """
    Add a new company with CRM integration.

    Example request:
    {
        "name": "CompanyA",
        "crm_type": "bitrix24",
        "config": {"webhook_url": "https://..."}
    }
    """
    async with AsyncSessionLocal() as db:
        company = await crud.create_company(db, name, crm_type, config)
        if company:
            return {"id": company.id, "name": company.name, "crm_type": company.crm_type}
        return {"error": "Failed to create company"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
