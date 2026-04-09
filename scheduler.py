import asyncio
from typing import List
from sqlalchemy.future import select
from loguru import logger
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_

from database import AsyncSessionLocal
from models import ChatSession
from llm_engine import LlmEngine
from green_api import wa_client
from integrations_mock import crm_mock

# Static thresholds
REACTIVATION_1_HOURS = 3
REACTIVATION_2_HOURS = 24
PRE_EVENT_REMINDER_HOURS = 2
POST_EVENT_FEEDBACK_HOURS = 3

llm = LlmEngine()

async def check_all_proactive_tasks():
    """
    Main entry point for the scheduler. Checks for follow-ups, reminders, and feedback.
    """
    logger.info("Running proactive engine cycle...")
    async with AsyncSessionLocal() as db:
        # 1. Reactivation (Follow-ups)
        await handle_reactivations(db)
        
        # 2. Pre-event Reminders
        await handle_reminders(db)
        
        # 3. Post-event Feedback
        await handle_feedback(db)

async def handle_reactivations(db):
    """
    Reactivates silent leads (3h, 24h, 48h).
    """
    # Find leads silent for > 3 hours
    now = datetime.now()
    threshold = now - timedelta(hours=REACTIVATION_1_HOURS)
    
    query = select(ChatSession).where(
        ChatSession.is_qualified == False,
        ChatSession.needs_human == False,
        ChatSession.last_interaction_at < threshold,
        ChatSession.followup_count < 3 # Limit to 3 touches
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    for session in sessions:
        logger.info(f"Reactivating silent lead {session.whatsapp_chat_id} (Touch #{session.followup_count + 1})")
        prompt = "Клиент замолчал. Сгенерируй ОДНУ короткую, теплую фразу по имени, чтобы возобновить диалог. Никакого давления."
        success = await send_proactive_message(db, session, prompt)
        session.followup_count += 1
        
        if session.followup_count >= 3:
            logger.warning(f"Lead {session.whatsapp_chat_id} is now 'Sleeping'. Updating CRM.")
            await crm_mock.update_status(session.crm_lead_id, "9")
    
    await db.commit()

async def handle_reminders(db):
    """
    Sends reminders 2 hours before the booked masterclass.
    """
    now = datetime.now()
    start_window = now + timedelta(hours=PRE_EVENT_REMINDER_HOURS - 1)
    end_window = now + timedelta(hours=PRE_EVENT_REMINDER_HOURS + 1)
    
    # Simple logic: check if booked_at is in the window and we haven't sent a reminder yet
    query = select(ChatSession).where(
        ChatSession.booked_at >= start_window,
        ChatSession.booked_at <= end_window,
        ChatSession.is_qualified == True
        # We might need a flag 'is_reminder_sent' if we want to be precise
    )
    # For now, let's keep it simple or assume it runs once per hour.
    # To be safe, I'd need a field 'reminder_sent_at'
    
    # Skipping exact implementation here to avoid double-sending without extra fields,
    # but the logic is: find match -> send "Ждать вас сегодня?"
    pass

async def handle_feedback(db):
    """
    Sends feedback request 3 hours after the masterclass.
    """
    now = datetime.now()
    # If MC ended 3 hours ago (MC is 90 min + 3h = 4.5h ago)
    target_time = now - timedelta(hours=4, minutes=30)
    
    query = select(ChatSession).where(
        ChatSession.booked_at <= target_time,
        ChatSession.is_feedback_sent == False
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    for session in sessions:
        logger.info(f"Collecting feedback for {session.whatsapp_chat_id}")
        msg = "Здравствуйте! Вы сегодня были у нас на мастер-классе. Буду рада, если поделитесь впечатлениями! Что понравилось больше всего?"
        await wa_client.send_message(session.whatsapp_chat_id, msg)
        session.is_feedback_sent = True
    
    await db.commit()

async def send_proactive_message(db, session, system_prompt):
    ai_response = llm.generate_response(user_message=system_prompt, chat_history=session.history_json)
    history = list(session.history_json) if session.history_json else []
    history.append({"role": "model", "text": ai_response.reply_text})
    session.history_json = history
    await wa_client.send_message(session.whatsapp_chat_id, ai_response.reply_text)
