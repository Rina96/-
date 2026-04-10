from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import ChatSession
from loguru import logger
import datetime

# Maximum number of dialogue turns (User + Assistant) to keep in the context window
MAX_HISTORY_LENGTH = 15

class CRUD:
    """Production-grade DAL (Data Access Layer) for AI Sales Agent."""

    async def get_or_create_session(self, db: AsyncSession, chat_id: str) -> ChatSession:
        """
        Block 6: Logic for single-point session retrieval/creation.
        Ensures the agent always has a context to work with.
        """
        try:
            result = await db.execute(
                select(ChatSession).where(ChatSession.whatsapp_chat_id == chat_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                logger.info(f"🆕 Creating NEW Production ChatSession for {chat_id}")
                session = ChatSession(
                    whatsapp_chat_id=chat_id,
                    history_json=[],
                    last_interaction=datetime.datetime.utcnow()
                )
                db.add(session)
                await db.commit()
                await db.refresh(session)
            
            return session
        except Exception as e:
            logger.error(f"❌ DB ERROR in get_or_create_session: {e}")
            await db.rollback()
            raise

    async def add_message_to_history(self, db: AsyncSession, session: ChatSession, role: str, text: str):
        """
        Adds a message and updates the 'last_interaction' timestamp.
        Uses a sliding window for context management.
        """
        try:
            history = list(session.history_json) if session.history_json else []
            history.append({"role": role, "text": text})
            
            # Context Management: Keep only most recent messages
            if len(history) > MAX_HISTORY_LENGTH * 2:
                history = history[-(MAX_HISTORY_LENGTH * 2):]

            session.history_json = history
            # The 'onupdate' in models.py handles last_interaction, but we can force it here for visibility
            session.last_interaction = datetime.datetime.utcnow()
            
            await db.commit()
            await db.refresh(session)
        except Exception as e:
            logger.error(f"❌ DB ERROR in add_message_to_history: {e}")
            await db.rollback()

    async def update_session_state(self, db: AsyncSession, session: ChatSession, updates: dict):
        """Generic updater for AI flags and CRM data."""
        try:
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            await db.commit()
        except Exception as e:
            logger.error(f"❌ DB ERROR in update_session_state: {e}")
            await db.rollback()

# Singleton access
crud = CRUD()
