from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.message import MessageResponse


class ConversationCreateDirect(BaseModel):
    user_id: str = Field(..., description="Target user ID to start or open a 1-to-1 conversation with")


class ConversationCreateGroup(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Group conversation title")
    member_ids: List[str] = Field(default_factory=list, description="Initial list of member user IDs to add")


class AddMembersRequest(BaseModel):
    member_ids: List[str] = Field(..., min_length=1, description="List of user IDs to add to the group")


class MemberResponse(BaseModel):
    id: str
    username: str
    is_online: bool = False
    last_seen: datetime
    joined_at: datetime

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: str
    type: str  # "direct" or "group"
    name: Optional[str] = None
    display_name: str
    created_at: datetime
    created_by: Optional[str] = None
    members: List[MemberResponse] = Field(default_factory=list)
    last_message: Optional[MessageResponse] = None
    unread_count: int = 0

    model_config = {"from_attributes": True}


class UserSimpleResponse(BaseModel):
    id: str
    username: str
    is_online: bool = False
    last_seen: datetime

    model_config = {"from_attributes": True}
