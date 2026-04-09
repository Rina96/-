from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime
from config import settings

Base = declarative_base()

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True)
    whatsapp_chat_id = Column(String, unique=True, index=True)
    history_json = Column(JSON, default=[])
    is_qualified = Column(Boolean, default=False)
    needs_human = Column(Boolean, default=False)
    crm_lead_id = Column(Integer, nullable=True)
    booked_at = Column(DateTime, nullable=True)
    followup_count = Column(Integer, default=0)
    
    # NEW: Long-term profile memory
    client_name = Column(String, nullable=True)
    child_age = Column(Integer, nullable=True)
    client_intent = Column(String, nullable=True) # например, "для себя" или "для ребенка"
    last_interaction = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

