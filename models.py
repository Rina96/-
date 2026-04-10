from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class ChatSession(Base):
    """Production-grade model for storing AI sales funnel state."""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    whatsapp_chat_id = Column(String, unique=True, index=True, nullable=False) # Block 8: UNIQUE constraint
    history_json = Column(JSON, default=[]) # Block 5: Dialogue memory
    
    # AI State Flags
    is_qualified = Column(Boolean, default=False)
    needs_human = Column(Boolean, default=False)
    crm_lead_id = Column(String, nullable=True) # Mapping to AlfaCRM ID
    
    # Booking & Funnel Progression
    booked_at = Column(DateTime, nullable=True)
    booked_date = Column(String, nullable=True) # Readable date like "14.04 (воскресенье)"
    
    # Proactive Engine Markers
    is_paid = Column(Boolean, default=False) # Block 5
    is_reminder_sent = Column(Boolean, default=False) # Block 5
    is_feedback_sent = Column(Boolean, default=False)
    followup_count = Column(Integer, default=0)
    
    # CRM Profile Data (Long-term memory)
    client_name = Column(String, nullable=True)
    child_age = Column(Integer, nullable=True)
    client_intent = Column(String, nullable=True) # e.g. "for self" or "for child"
    
    # Block 5: Timestamps for the Scheduler
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
