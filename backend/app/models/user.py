import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


def get_utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    last_seen = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now, nullable=False)

    conversation_memberships = relationship(
        "ConversationMember",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sent_messages = relationship(
        "Message",
        back_populates="sender",
        cascade="all, delete-orphan",
    )
