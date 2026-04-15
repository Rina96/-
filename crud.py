from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import ChatSession, Company
from loguru import logger
import datetime

# sliding window size
MAX_HISTORY_LENGTH = 15

class CRUD:
    """Production-grade DAL with explicit transaction protection."""

    async def get_or_create_session(self, db: AsyncSession, chat_id: str, company_id: int = 1) -> ChatSession:
        """Retrieves or creates a session with rollback protection.

        Args:
            db: Database session
            chat_id: WhatsApp chat ID
            company_id: Company ID (defaults to 1 for backward compatibility)
        """
        try:
            result = await db.execute(
                select(ChatSession).where(
                    (ChatSession.whatsapp_chat_id == chat_id) &
                    (ChatSession.company_id == company_id)
                )
            )
            session = result.scalar_one_or_none()

            if not session:
                logger.info(f"🆕 Creating NEW ChatSession for {chat_id} (company_id={company_id})")
                session = ChatSession(
                    company_id=company_id,
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
            await db.rollback() # Block 4: CRITICAL ROLLBACK
            raise

    async def get_company(self, db: AsyncSession, company_id: int) -> Company:
        """Get company by ID."""
        try:
            result = await db.execute(
                select(Company).where(Company.id == company_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ DB ERROR in get_company: {e}")
            await db.rollback()
            return None

    async def get_company_by_name(self, db: AsyncSession, name: str) -> Company:
        """Get company by name."""
        try:
            result = await db.execute(
                select(Company).where(Company.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ DB ERROR in get_company_by_name: {e}")
            await db.rollback()
            return None

    async def create_company(self, db: AsyncSession, name: str, crm_type: str, crm_config: dict) -> Company:
        """Create new company with CRM configuration."""
        try:
            company = Company(
                name=name,
                crm_type=crm_type,
                crm_config=crm_config,
                is_active=True
            )
            db.add(company)
            await db.commit()
            await db.refresh(company)
            logger.success(f"✅ Company created: {name} (CRM: {crm_type})")
            return company
        except Exception as e:
            logger.error(f"❌ DB ERROR in create_company: {e}")
            await db.rollback()
            return None

    async def add_message_to_history(self, db: AsyncSession, session: ChatSession, role: str, text: str):
        """Adds message and updates timestamp with rollback protection."""
        try:
            history = list(session.history_json) if session.history_json else []
            history.append({"role": role, "text": text})
            
            if len(history) > MAX_HISTORY_LENGTH * 2:
                history = history[-(MAX_HISTORY_LENGTH * 2):]

            session.history_json = history
            session.last_interaction = datetime.datetime.utcnow()
            
            await db.commit()
            await db.refresh(session)
        except Exception as e:
            logger.error(f"❌ DB ERROR in add_message_to_history: {e}")
            await db.rollback() # Block 4: CRITICAL ROLLBACK

    async def update_session_state(self, db: AsyncSession, session: ChatSession, updates: dict):
        """Updates session metadata with rollback protection."""
        try:
            for key, value in updates.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            
            await db.commit()
        except Exception as e:
            logger.error(f"❌ DB ERROR in update_session_state: {e}")
            await db.rollback() # Block 4: CRITICAL ROLLBACK

# Singleton access
crud = CRUD()
