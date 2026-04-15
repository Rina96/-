from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, Text
from database import Base # CRITICAL FIX: Use the shared Base from database.py
import datetime

class Company(Base):
    """Multi-CRM company integration model."""
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)  # e.g., "ShoolaGo", "CompanyX"
    crm_type = Column(String, nullable=False, index=True)  # "amocrm", "bitrix24", "alfarc"

    # Generic CRM credentials (JSON structure varies by CRM type)
    crm_config = Column(JSON, default={})  # Stores API keys, subdomain, etc.

    # WhatsApp Integration
    whatsapp_api_id = Column(String, nullable=True)
    whatsapp_api_token = Column(String, nullable=True)

    # System
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ChatSession(Base):
    """Production-grade model for storing AI sales funnel state."""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    whatsapp_chat_id = Column(String, unique=True, index=True, nullable=False)
    history_json = Column(JSON, default=[])

    # AI State Flags
    is_qualified = Column(Boolean, default=False)
    needs_human = Column(Boolean, default=False)
    crm_lead_id = Column(String, nullable=True)

    # Booking & Funnel Progression
    booked_at = Column(DateTime, nullable=True)
    booked_date = Column(String, nullable=True)

    # Proactive Engine Markers
    is_paid = Column(Boolean, default=False)
    is_reminder_sent = Column(Boolean, default=False)
    is_feedback_sent = Column(Boolean, default=False)
    followup_count = Column(Integer, default=0)

    # CRM Profile Data
    client_name = Column(String, nullable=True)
    child_age = Column(Integer, nullable=True)
    client_intent = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
