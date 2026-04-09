from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from database import Base

class ChatSession(Base):
    """
    Stores the memory/context for a specific user (WhatsApp ChatId)
    """
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    whatsapp_chat_id = Column(String, unique=True, index=True) # Phone number like '79991234567@c.us'
    crm_lead_id = Column(Integer, nullable=True, index=True)
    
    # Store history as a JSON list: [{"role": "user", "text": "..."}, {"role": "model", "text": "..."}]
    history_json = Column(JSON, default=list) 
    
    # AI state flags
    is_qualified = Column(Boolean, default=False)
    needs_human = Column(Boolean, default=False)
    
    # Lifecycle tracking [NEW]
    booked_at = Column(DateTime(timezone=True), nullable=True) # When the MC happens
    followup_count = Column(Integer, default=0) # Number of reactivation touches sent
    is_feedback_sent = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_interaction_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now())
