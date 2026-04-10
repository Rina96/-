import asyncio
from typing import List
from sqlalchemy.future import select
from loguru import logger
from datetime import datetime, timedelta
from database import AsyncSessionLocal
from models import ChatSession
from llm_engine import llm
from green_api import wa_client

async def check_all_proactive_tasks():
    """Execute all maintenance tasks with Block 7 protection."""
    try:
        async with AsyncSessionLocal() as db:
            await handle_sunday_broadcast(db)
            await handle_pre_event_reminders(db)
            await handle_post_event_feedback(db)
            await handle_reactivations(db)
    except Exception as e:
        logger.error(f"❌ SCHEDULER DB ERROR: {e}")
        # Implicitly handled by the outer loop's try-except

async def handle_sunday_broadcast(db):
    try:
        now = datetime.now()
        if now.weekday() == 6 and now.hour == 11 and now.minute < 30:
            today_str = now.strftime("%Y-%m-%d")
            query = select(ChatSession).where(
                ChatSession.booked_date == today_str,
                ChatSession.is_paid == True
            )
            result = await db.execute(query)
            for session in result.scalars().all():
                msg = f"Доброе утро, {session.client_name or ''}! ☀️ Ждем вас сегодня на мастер-классе!"
                await wa_client.send_message(session.whatsapp_chat_id, msg)
            await db.commit()
    except Exception as e:
        logger.error(f"Sunday Broadcast Error: {e}")
        await db.rollback()

async def handle_pre_event_reminders(db):
    try:
        now = datetime.now()
        threshold = now + timedelta(minutes=120)
        query = select(ChatSession).where(
            ChatSession.booked_at <= threshold,
            ChatSession.booked_at > now,
            ChatSession.is_paid == True,
            ChatSession.is_reminder_sent == False
        )
        result = await db.execute(query)
        for session in result.scalars().all():
            await wa_client.send_message(session.whatsapp_chat_id, "Напоминаю, что ваш мастер-класс начнется через 2 часа! ☕️")
            session.is_reminder_sent = True
        await db.commit()
    except Exception as e:
        logger.error(f"Pre-event Reminder Error: {e}")
        await db.rollback()

async def handle_post_event_feedback(db):
    try:
        now = datetime.now()
        threshold = now - timedelta(minutes=180)
        query = select(ChatSession).where(
            ChatSession.booked_at <= threshold,
            ChatSession.is_paid == True,
            ChatSession.is_feedback_sent == False
        )
        result = await db.execute(query)
        for session in result.scalars().all():
            await wa_client.send_message(session.whatsapp_chat_id, "Надеемся, вам понравился мастер-класс! Поделитесь впечатлениями? 😊")
            session.is_feedback_sent = True
        await db.commit()
    except Exception as e:
        logger.error(f"Post-event Feedback Error: {e}")
        await db.rollback()

async def handle_reactivations(db):
    try:
        now = datetime.now()
        threshold = now - timedelta(hours=24)
        query = select(ChatSession).where(
            ChatSession.is_qualified == False,
            ChatSession.last_interaction < threshold,
            ChatSession.followup_count < 2
        )
        result = await db.execute(query)
        for session in result.scalars().all():
            prompt = "Клиент замолчал 24 часа назад. Коротко и вежливо уточни, актуально ли ещё обучение в школе Го."
            ai_resp = llm.generate_response(prompt, session.history_json)
            await wa_client.send_message(session.whatsapp_chat_id, ai_resp.reply_text)
            session.followup_count += 1
        await db.commit()
    except Exception as e:
        logger.error(f"Reactivation Error: {e}")
        await db.rollback()

async def scheduler_loop():
    """Block 6: Robust Scheduler protection (Anti-Crash)."""
    while True:
        try:
            await check_all_proactive_tasks()
        except Exception as e:
            logger.error(f"🚨 CRITICAL SCHEDULER FAILURE: {e}")
        
        await asyncio.sleep(1800) # Run every 30 minutes
