from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.models.user import User
from app.models.message import Message, get_utc_now
from app.schemas.message import (
    MessageCreateRequest,
    MessageResponse,
    MarkReadRequest,
    ConversationInfo,
)
from app.auth.dependencies import get_current_user, get_partner_user
from app.websocket.manager import manager

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.get("", response_model=List[MessageResponse])
def get_messages(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetch chronological message history between the two users.
    Automatically marks undelivered incoming messages as delivered.
    """
    partner = get_partner_user(current_user, db)
    if not partner:
        return []

    # Query all messages exchanged between current_user and partner
    messages = (
        db.query(Message)
        .filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == partner.id),
                and_(Message.sender_id == partner.id, Message.receiver_id == current_user.id),
            )
        )
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Automatically mark incoming undelivered messages as delivered
    now = get_utc_now()
    updated = False
    newly_delivered_ids = []

    for msg in messages:
        if msg.receiver_id == current_user.id and msg.delivered_at is None:
            msg.delivered_at = now
            updated = True
            newly_delivered_ids.append(msg.id)

    if updated:
        db.commit()
        # Notify sender that their messages were delivered
        import asyncio
        if newly_delivered_ids:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    for mid in newly_delivered_ids:
                        asyncio.create_task(
                            manager.send_to_user(
                                partner.id,
                                {
                                    "type": "message_delivered",
                                    "message_id": mid,
                                    "delivered_at": now.isoformat(),
                                },
                            )
                        )
            except Exception:
                pass

    return [MessageResponse.from_orm_model(msg, current_user.id) for msg in messages]


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    payload: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Send a message to the partner.
    Persists to database and delivers via WebSocket in real-time.
    """
    partner = get_partner_user(current_user, db)
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your chat partner has not registered yet. Please wait for them to join.",
        )

    now = get_utc_now()
    partner_online = manager.is_user_online(partner.id)

    new_message = Message(
        sender_id=current_user.id,
        receiver_id=partner.id,
        content=payload.content,
        created_at=now,
        delivered_at=now if partner_online else None,
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    msg_resp = MessageResponse.from_orm_model(new_message, current_user.id)
    msg_dict = msg_resp.model_dump(mode="json")

    # Broadcast to recipient in real time
    await manager.send_to_user(
        partner.id,
        {
            "type": "new_message",
            "message": msg_dict,
        },
    )

    # Also broadcast to sender (useful for multi-tab sync)
    await manager.send_to_user(
        current_user.id,
        {
            "type": "new_message",
            "message": msg_dict,
        },
    )

    return msg_resp


@router.post("/mark-read")
async def mark_messages_read(
    payload: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark messages from partner as read.
    Updates database and broadcasts read receipts.
    """
    partner = get_partner_user(current_user, db)
    if not partner:
        return {"read_count": 0}

    now = get_utc_now()
    query = db.query(Message).filter(
        Message.receiver_id == current_user.id,
        Message.sender_id == partner.id,
        Message.read_at.is_(None),
    )

    if payload.message_ids:
        query = query.filter(Message.id.in_(payload.message_ids))

    unread_messages = query.all()
    if not unread_messages:
        return {"read_count": 0}

    read_ids = []
    for msg in unread_messages:
        msg.read_at = now
        if msg.delivered_at is None:
            msg.delivered_at = now
        read_ids.append(msg.id)

    db.commit()

    # Broadcast read receipt to sender
    await manager.send_to_user(
        partner.id,
        {
            "type": "messages_read",
            "message_ids": read_ids,
            "read_at": now.isoformat(),
        },
    )

    return {"read_count": len(read_ids), "message_ids": read_ids}


@router.patch("/{message_id}/read", response_model=MessageResponse)
async def mark_single_message_read(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single message as read by receiver."""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if msg.receiver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot mark messages as read for another user")

    now = get_utc_now()
    if msg.read_at is None:
        msg.read_at = now
        if msg.delivered_at is None:
            msg.delivered_at = now
        db.commit()
        db.refresh(msg)

        # Broadcast read receipt
        await manager.send_to_user(
            msg.sender_id,
            {
                "type": "messages_read",
                "message_ids": [msg.id],
                "read_at": now.isoformat(),
            },
        )

    return MessageResponse.from_orm_model(msg, current_user.id)


@router.get("/conversation-summary", response_model=Optional[ConversationInfo])
def get_conversation_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get sidebar preview information about the 1-to-1 conversation."""
    partner = get_partner_user(current_user, db)
    if not partner:
        return None

    unread_count = (
        db.query(Message)
        .filter(
            Message.receiver_id == current_user.id,
            Message.sender_id == partner.id,
            Message.read_at.is_(None),
        )
        .count()
    )

    last_msg = (
        db.query(Message)
        .filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == partner.id),
                and_(Message.sender_id == partner.id, Message.receiver_id == current_user.id),
            )
        )
        .order_by(Message.created_at.desc())
        .first()
    )

    last_msg_resp = (
        MessageResponse.from_orm_model(last_msg, current_user.id) if last_msg else None
    )

    return ConversationInfo(
        partner_id=partner.id,
        partner_username=partner.username,
        partner_is_online=manager.is_user_online(partner.id),
        partner_last_seen=partner.last_seen,
        unread_count=unread_count,
        last_message=last_msg_resp,
    )
