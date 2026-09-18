from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class MessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty or whitespace only")
        return v


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    sender_username: str
    content: str
    created_at: datetime
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    status: str = "sent"

    @classmethod
    def from_orm_model(cls, message, sender_username: str = "", current_user_id: Optional[str] = None):
        status = "sent"
        if message.read_at is not None:
            status = "read"
        elif message.delivered_at is not None:
            status = "delivered"

        username = sender_username
        if not username and getattr(message, "sender", None):
            username = message.sender.username

        return cls(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_username=username,
            content=message.content,
            created_at=message.created_at,
            delivered_at=message.delivered_at,
            read_at=message.read_at,
            status=status,
        )

    model_config = {"from_attributes": True}


class MarkReadRequest(BaseModel):
    message_ids: List[str] = Field(default_factory=list)
