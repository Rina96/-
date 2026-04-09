import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import ChatSession
from loguru import logger

# Maximum number of message pairs (User + Assistant) to keep in the context window
MAX_HISTORY_LENGTH = 10 

class CRUD:
    async def get_or_create_session(self, db: AsyncSession, chat_id: str) -> ChatSession:
        """Retrieves an existing chat session or creates a new one."""
        query = select(ChatSession).where(ChatSession.whatsapp_chat_id == chat_id)
        result = await db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            logger.info(f"Creating new session for {chat_id}")
            session = ChatSession(whatsapp_chat_id=chat_id, history_json=[])
            db.add(session)
            await db.commit()
            await db.refresh(session)
            
        return session

    async def add_message_to_history(self, db: AsyncSession, session: ChatSession, role: str, text: str):
        """
        Adds a single message to the history. 
        Enforces a sliding window to prevent token overflow.
        """
        history = list(session.history_json) if session.history_json else []
        history.append({"role": role, "text": text})
        
        # Sliding window logic: keep only the last N messages
        if len(history) > MAX_HISTORY_LENGTH * 2:
            # Always keep the first few sets (if they contain crucial qualification info) 
            # and slice the oldest out of the middle, or just keep the N most recent.
            history = history[-(MAX_HISTORY_LENGTH * 2):]

        session.history_json = history
        await db.commit()
        await db.refresh(session)

    async def update_session_state(self, db: AsyncSession, session: ChatSession, is_qualified: bool, needs_human: bool):
        """Updates the AI state flags derived from the LLM struct output."""
        session.is_qualified = is_qualified
        session.needs_human = needs_human
        await db.commit()

# Singleton for easy access
crud = CRUD()
