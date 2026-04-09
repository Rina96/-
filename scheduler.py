import asyncio
from typing import List
from sqlalchemy.future import select
from loguru import logger
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_

from database import AsyncSessionLocal
from models import ChatSession
from llm_engine import llm
from green_api import wa_client

# Static thresholds
PRE_EVENT_REMINDER_MINUTES = 120  # 2 hours
POST_EVENT_FEEDBACK_MINUTES = 180  # 3 hours

async def check_all_proactive_tasks():
    """Main loop for the proactive agent engine."""
    logger.info("Running proactive engine cycle...")
    async with AsyncSessionLocal() as db:
        await handle_sunday_broadcast(db)
        await handle_pre_event_reminders(db)
        await handle_post_event_feedback(db)
        await handle_reactivations(db)

async def handle_sunday_broadcast(db):
    """Sends a warm broadcast every Sunday at 11:00 AM to paid attendees of THAT day."""
    now = datetime.now()
    # Check if Sunday and around 11:00
    if now.weekday() == 6 and now.hour == 11 and now.minute < 30:
        today_str = now.strftime("%Y-%m-%d")
        
        query = select(ChatSession).where(
            ChatSession.booked_date == today_str,
            ChatSession.is_paid == True,
            ChatSession.last_interaction < now - timedelta(minutes=60) # Don't interrupt active chat
        )
        result = await db.execute(query)
        sessions = result.scalars().all()
        
        for session in sessions:
            logger.info(f"Sending Sunday Broadcast to {session.whatsapp_chat_id}")
            msg = f"Доброе утро, {session.client_name or ''}! ☀️ Ждем вас сегодня на мастер-классе в школе Го. Будет очень интересно!"
            await wa_client.send_message(session.whatsapp_chat_id, msg)
        
        await db.commit()

async def handle_pre_event_reminders(db):
    """Reminds users 2 hours before their specific booked_at time."""
    now = datetime.now()
    reminder_threshold = now + timedelta(minutes=PRE_EVENT_REMINDER_MINUTES)
    
    query = select(ChatSession).where(
        ChatSession.booked_at <= reminder_threshold,
        ChatSession.booked_at > now,
        ChatSession.is_paid == True,
        ChatSession.is_reminder_sent == False
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    for session in sessions:
        logger.info(f"Reminder (2h) for {session.whatsapp_chat_id}")
        msg = "Напоминаю, что ваш мастер-класс начнется через 2 часа! Ждем вас! ☕️"
        await wa_client.send_message(session.whatsapp_chat_id, msg)
        session.is_reminder_sent = True
    
    await db.commit()

async def handle_post_event_feedback(db):
    """Requests feedback 3 hours after the masterclass."""
    now = datetime.now()
    feedback_threshold = now - timedelta(minutes=POST_EVENT_FEEDBACK_MINUTES)
    
    query = select(ChatSession).where(
        ChatSession.booked_at <= feedback_threshold,
        ChatSession.is_paid == True,
        ChatSession.is_reminder_sent == True, # Only if they were reminded/attended
        ChatSession.is_feedback_sent == False
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    for session in sessions:
        logger.info(f"Feedback request for {session.whatsapp_chat_id}")
        msg = "Надеюсь, вам понравился наш мастер-класс! Поделитесь, пожалуйста, вашими впечатлениями? Что было самым запоминающимся?"
        await wa_client.send_message(session.whatsapp_chat_id, msg)
        session.is_feedback_sent = True
        
    await db.commit()

async def handle_reactivations(db):
    """Gently nudges leads who stopped responding."""
    now = datetime.now()
    threshold = now - timedelta(hours=24)
    
    query = select(ChatSession).where(
        ChatSession.is_qualified == False,
        ChatSession.last_interaction < threshold,
        ChatSession.followup_count < 2
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    for session in sessions:
        logger.info(f"Reactivating lead {session.whatsapp_chat_id}")
        prompt = "Клиент замолчал 24 часа назад. Напиши одну короткую и очень вежливую фразу, чтобы узнать, не передумали ли они насчет школы Го."
        ai_resp = llm.generate_response(prompt, session.history_json)
        await wa_client.send_message(session.whatsapp_chat_id, ai_resp.reply_text)
        session.followup_count += 1
    
    await db.commit()

async def scheduler_loop():
    """Infinite loop for the scheduler tracker."""
    while True:
        try:
            await check_all_proactive_tasks()
        except Exception as e:
            logger.error(f"Scheduler Loop Error: {e}")
        await asyncio.sleep(1800) # Run every 30 minutes
