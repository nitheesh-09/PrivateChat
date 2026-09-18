from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, ConversationMember
from app.models.message import Message, get_utc_now
from app.schemas.conversation import (
    ConversationCreateDirect,
    ConversationCreateGroup,
    AddMembersRequest,
    MemberResponse,
    ConversationResponse,
)
from app.schemas.message import MessageCreateRequest, MessageResponse, MarkReadRequest
from app.auth.dependencies import get_current_user
from app.websocket.manager import manager

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


def format_conversation_response(
    conv: Conversation,
    current_user_id: str,
    db: Session,
) -> ConversationResponse:
    """Helper to assemble a rich ConversationResponse for a given user."""
    members_list: List[MemberResponse] = []
    other_username = ""

    for m in conv.members:
        is_online = manager.is_user_online(m.user.id)
        if m.user.id != current_user_id:
            other_username = m.user.username

        members_list.append(
            MemberResponse(
                id=m.user.id,
                username=m.user.username,
                is_online=is_online,
                last_seen=m.user.last_seen,
                joined_at=m.joined_at,
            )
        )

    # Calculate display name
    if conv.type == "group":
        display_name = conv.name or "Unnamed Group"
    else:
        display_name = other_username or "Direct Chat"

    # Get last message
    last_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.desc())
        .first()
    )
    last_msg_resp = (
        MessageResponse.from_orm_model(last_msg, current_user_id=current_user_id)
        if last_msg
        else None
    )

    # Calculate unread count
    unread_count = (
        db.query(Message)
        .filter(
            Message.conversation_id == conv.id,
            Message.sender_id != current_user_id,
            Message.read_at.is_(None),
        )
        .count()
    )

    return ConversationResponse(
        id=conv.id,
        type=conv.type,
        name=conv.name,
        display_name=display_name,
        created_at=conv.created_at,
        created_by=conv.created_by,
        members=members_list,
        last_message=last_msg_resp,
        unread_count=unread_count,
    )


def verify_conversation_membership(
    conversation_id: str,
    user_id: str,
    db: Session,
) -> Conversation:
    """Verify that a user is an authorized member of the conversation."""
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    is_member = (
        db.query(ConversationMember)
        .filter(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.user_id == user_id,
        )
        .first()
    )
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this conversation.",
        )

    return conv


@router.get("", response_model=List[ConversationResponse])
def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all direct and group conversations the user belongs to."""
    # Find all conversation IDs current user belongs to
    member_conv_ids = [
        m.conversation_id
        for m in db.query(ConversationMember.conversation_id)
        .filter(ConversationMember.user_id == current_user.id)
        .all()
    ]

    if not member_conv_ids:
        return []

    conversations = (
        db.query(Conversation)
        .filter(Conversation.id.in_(member_conv_ids))
        .all()
    )

    results = [
        format_conversation_response(c, current_user.id, db)
        for c in conversations
    ]

    # Sort conversations by latest message timestamp or conversation created_at descending
    def get_sort_key(resp: ConversationResponse):
        if resp.last_message and resp.last_message.created_at:
            return resp.last_message.created_at
        return resp.created_at

    results.sort(key=get_sort_key, reverse=True)
    return results


@router.post("/direct", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_or_get_direct_conversation(
    payload: ConversationCreateDirect,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start or retrieve an existing 1-to-1 direct conversation with another user.
    Reuses existing direct conversations instead of duplicating.
    """
    if payload.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot start a direct conversation with yourself.")

    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found.")

    # Check if a direct conversation already exists between both users
    user_a_conv_ids = db.query(ConversationMember.conversation_id).filter(
        ConversationMember.user_id == current_user.id
    )
    user_b_conv_ids = db.query(ConversationMember.conversation_id).filter(
        ConversationMember.user_id == target_user.id
    )

    existing_conv = (
        db.query(Conversation)
        .filter(
            Conversation.type == "direct",
            Conversation.id.in_(user_a_conv_ids),
            Conversation.id.in_(user_b_conv_ids),
        )
        .first()
    )

    if existing_conv:
        response.status_code = status.HTTP_200_OK
        return format_conversation_response(existing_conv, current_user.id, db)

    # Create new direct conversation
    new_conv = Conversation(
        type="direct",
        name=None,
        created_by=current_user.id,
    )
    db.add(new_conv)
    db.flush()

    # Add both members
    mem1 = ConversationMember(conversation_id=new_conv.id, user_id=current_user.id)
    mem2 = ConversationMember(conversation_id=new_conv.id, user_id=target_user.id)
    db.add_all([mem1, mem2])
    db.commit()
    db.refresh(new_conv)

    # Notify target user over WebSocket in real-time
    await manager.broadcast_to_users(
        [target_user.id],
        {
            "type": "conversation_created",
            "conversation_id": new_conv.id,
        },
    )

    return format_conversation_response(new_conv, current_user.id, db)


@router.post("/group", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_group_conversation(
    payload: ConversationCreateGroup,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new group conversation with multiple members."""
    group_name = payload.name.strip()
    if not group_name:
        raise HTTPException(status_code=400, detail="Group name cannot be empty.")

    new_group = Conversation(
        type="group",
        name=group_name,
        created_by=current_user.id,
    )
    db.add(new_group)
    db.flush()

    # Always add creator
    members_to_add = {current_user.id}
    # Add other members
    for uid in payload.member_ids:
        user_exists = db.query(User).filter(User.id == uid).first()
        if user_exists:
            members_to_add.add(uid)

    for uid in members_to_add:
        db.add(ConversationMember(conversation_id=new_group.id, user_id=uid))

    db.commit()
    db.refresh(new_group)

    # Notify all other group members in real-time
    other_members = [uid for uid in members_to_add if uid != current_user.id]
    if other_members:
        await manager.broadcast_to_users(
            other_members,
            {
                "type": "conversation_created",
                "conversation_id": new_group.id,
            },
        )

    return format_conversation_response(new_group, current_user.id, db)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation_details(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get details of a single conversation (must be a member)."""
    conv = verify_conversation_membership(conversation_id, current_user.id, db)
    return format_conversation_response(conv, current_user.id, db)


@router.post("/{conversation_id}/members", response_model=ConversationResponse)
async def add_group_members(
    conversation_id: str,
    payload: AddMembersRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add new members to an existing group conversation."""
    conv = verify_conversation_membership(conversation_id, current_user.id, db)
    if conv.type != "group":
        raise HTTPException(status_code=400, detail="Cannot add members to a direct 1-to-1 conversation.")

    existing_uids = {m.user_id for m in conv.members}
    added_any = False

    for uid in payload.member_ids:
        if uid not in existing_uids:
            user_exists = db.query(User).filter(User.id == uid).first()
            if user_exists:
                db.add(ConversationMember(conversation_id=conv.id, user_id=uid))
                added_any = True

    if added_any:
        db.commit()
        db.refresh(conv)

        # Notify all group members (existing + newly added) in real-time
        all_members = [m.user_id for m in conv.members]
        await manager.broadcast_to_users(
            all_members,
            {
                "type": "conversation_created",
                "conversation_id": conv.id,
            },
        )

    return format_conversation_response(conv, current_user.id, db)


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
def get_conversation_messages(
    conversation_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch chronological messages for a conversation (must be a member)."""
    verify_conversation_membership(conversation_id, current_user.id, db)

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Automatically mark incoming undelivered messages as delivered
    now = get_utc_now()
    updated = False
    for msg in messages:
        if msg.sender_id != current_user.id and msg.delivered_at is None:
            msg.delivered_at = now
            updated = True

    if updated:
        db.commit()

    return [
        MessageResponse.from_orm_model(m, current_user_id=current_user.id)
        for m in messages
    ]


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_conversation_message(
    conversation_id: str,
    payload: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message to a conversation (REST fallback)."""
    conv = verify_conversation_membership(conversation_id, current_user.id, db)

    now = get_utc_now()
    member_user_ids = [m.user_id for m in conv.members]

    # Check if any other member is online
    any_other_online = any(
        manager.is_user_online(uid) for uid in member_user_ids if uid != current_user.id
    )

    new_msg = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=payload.content,
        created_at=now,
        delivered_at=now if any_other_online else None,
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)

    msg_resp = MessageResponse.from_orm_model(
        new_msg,
        sender_username=current_user.username,
        current_user_id=current_user.id,
    )
    msg_dict = msg_resp.model_dump(mode="json")

    # Broadcast to all conversation members
    await manager.broadcast_to_users(
        member_user_ids,
        {
            "type": "new_message",
            "conversation_id": conversation_id,
            "message": msg_dict,
        },
    )

    return msg_resp


@router.post("/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: str,
    payload: MarkReadRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark unread messages in a conversation as read."""
    conv = verify_conversation_membership(conversation_id, current_user.id, db)

    now = get_utc_now()
    query = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.sender_id != current_user.id,
        Message.read_at.is_(None),
    )

    if payload and payload.message_ids:
        query = query.filter(Message.id.in_(payload.message_ids))

    unread_msgs = query.all()
    if not unread_msgs:
        return {"read_count": 0}

    read_ids = []
    for m in unread_msgs:
        m.read_at = now
        if m.delivered_at is None:
            m.delivered_at = now
        read_ids.append(m.id)

    db.commit()

    # Notify all members of read event
    member_user_ids = [m.user_id for m in conv.members]
    await manager.broadcast_to_users(
        member_user_ids,
        {
            "type": "messages_read",
            "conversation_id": conversation_id,
            "message_ids": read_ids,
            "read_at": now.isoformat(),
        },
    )

    return {"read_count": len(read_ids), "message_ids": read_ids}
