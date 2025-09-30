from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON
from database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, index=True)  # User email
    title = Column(String, index=True)  # Session title (first question or custom)
    messages = Column(JSON)  # Store entire conversation as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    message_count = Column(Integer, default=0)  # Number of messages in session