import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db, Base
from app.models.user import User
from app.models.conversation import Conversation, ConversationMember
from app.models.message import Message, get_utc_now
from app.schemas.message import MessageResponse
from app.routes.auth import router as auth_router
from app.routes.conversations import router as conversations_router
from app.websocket.manager import manager
from app.auth.dependencies import get_current_user_from_ws

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Lightweight Private Messaging API with Direct and Group Chats",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.onrender\.com|https://.*\.vercel\.app|http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    """Ensure all API responses prevent browser/proxy caching for real-time consistency."""
    response = await call_next(request)
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Mount API Routers
app.include_router(auth_router)
app.include_router(conversations_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_user_shared_contact_ids(user_id: str, db: Session) -> Set[str]:
    """Find all unique user IDs who share at least one conversation with this user."""
    # Find all conversation IDs user belongs to
    my_conv_ids = [
        m.conversation_id
        for m in db.query(ConversationMember.conversation_id)
        .filter(ConversationMember.user_id == user_id)
        .all()
    ]
    if not my_conv_ids:
        return set()

    # Find other members in those conversations
    other_members = (
        db.query(ConversationMember.user_id)
        .filter(
            ConversationMember.conversation_id.in_(my_conv_ids),
            ConversationMember.user_id != user_id,
        )
        .distinct()
        .all()
    )
    return {m[0] for m in other_members}


@app.websocket("/ws/chat")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time chat routed by conversation_id,
    supporting direct chats, group chats, delivery/read receipts, and typing.
    """
    user = get_current_user_from_ws(websocket, db)
    if not user:
        logger.warning("Rejected unauthorized WebSocket connection.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = user.id
    username = user.username

    await manager.connect(user_id, websocket)

    now = get_utc_now()
    user.last_seen = now
    db.commit()

    # Notify all users who share a conversation with this user
    contact_ids = get_user_shared_contact_ids(user_id, db)
    if contact_ids:
        await manager.broadcast_to_users(
            list(contact_ids),
            {
                "type": "user_status",
                "user_id": user_id,
                "username": username,
                "is_online": True,
                "last_seen": now.isoformat(),
            },
        )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "send_message":
                conv_id = data.get("conversation_id")
                content = data.get("content", "").strip()

                if not conv_id or not content or len(content) > 4000:
                    await websocket.send_json(
                        {"type": "error", "message": "Invalid message payload or length."}
                    )
                    continue

                # Verify sender belongs to conversation
                membership = (
                    db.query(ConversationMember)
                    .filter(
                        ConversationMember.conversation_id == conv_id,
                        ConversationMember.user_id == user_id,
                    )
                    .first()
                )
                if not membership:
                    await websocket.send_json(
                        {"type": "error", "message": "You are not a member of this conversation."}
                    )
                    continue

                # Get all members of conversation
                all_members = (
                    db.query(ConversationMember.user_id)
                    .filter(ConversationMember.conversation_id == conv_id)
                    .all()
                )
                member_uids = [m[0] for m in all_members]

                # Check if any recipient is online
                any_other_online = any(
                    manager.is_user_online(uid) for uid in member_uids if uid != user_id
                )

                msg_now = get_utc_now()
                new_msg = Message(
                    conversation_id=conv_id,
                    sender_id=user_id,
                    content=content,
                    created_at=msg_now,
                    delivered_at=msg_now if any_other_online else None,
                )
                db.add(new_msg)
                db.commit()
                db.refresh(new_msg)

                msg_dict = MessageResponse.from_orm_model(
                    new_msg,
                    sender_username=username,
                    current_user_id=user_id,
                ).model_dump(mode="json")

                # Broadcast to all conversation members (including sender)
                await manager.broadcast_to_users(
                    member_uids,
                    {
                        "type": "new_message",
                        "conversation_id": conv_id,
                        "message": msg_dict,
                    },
                )

            elif msg_type == "mark_read":
                conv_id = data.get("conversation_id")
                message_ids = data.get("message_ids", [])

                if not conv_id:
                    continue

                query = db.query(Message).filter(
                    Message.conversation_id == conv_id,
                    Message.sender_id != user_id,
                    Message.read_at.is_(None),
                )
                if message_ids:
                    query = query.filter(Message.id.in_(message_ids))

                unread = query.all()
                if unread:
                    read_now = get_utc_now()
                    read_ids = []
                    for m in unread:
                        m.read_at = read_now
                        if m.delivered_at is None:
                            m.delivered_at = read_now
                        read_ids.append(m.id)
                    db.commit()

                    all_members = (
                        db.query(ConversationMember.user_id)
                        .filter(ConversationMember.conversation_id == conv_id)
                        .all()
                    )
                    member_uids = [m[0] for m in all_members]

                    await manager.broadcast_to_users(
                        member_uids,
                        {
                            "type": "messages_read",
                            "conversation_id": conv_id,
                            "message_ids": read_ids,
                            "read_at": read_now.isoformat(),
                        },
                    )

            elif msg_type == "typing":
                conv_id = data.get("conversation_id")
                is_typing = bool(data.get("is_typing", False))

                if conv_id:
                    all_members = (
                        db.query(ConversationMember.user_id)
                        .filter(ConversationMember.conversation_id == conv_id)
                        .all()
                    )
                    recipient_uids = [m[0] for m in all_members if m[0] != user_id]

                    await manager.broadcast_to_users(
                        recipient_uids,
                        {
                            "type": "typing",
                            "conversation_id": conv_id,
                            "user_id": user_id,
                            "username": username,
                            "is_typing": is_typing,
                        },
                    )

    except WebSocketDisconnect:
        is_offline = manager.disconnect(user_id, websocket)
        if is_offline:
            off_now = get_utc_now()
            user.last_seen = off_now
            db.commit()
            contact_ids = get_user_shared_contact_ids(user_id, db)
            if contact_ids:
                await manager.broadcast_to_users(
                    list(contact_ids),
                    {
                        "type": "user_status",
                        "user_id": user_id,
                        "username": username,
                        "is_online": False,
                        "last_seen": off_now.isoformat(),
                    },
                )
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        is_offline = manager.disconnect(user_id, websocket)
        if is_offline:
            off_now = get_utc_now()
            user.last_seen = off_now
            db.commit()
            contact_ids = get_user_shared_contact_ids(user_id, db)
            if contact_ids:
                await manager.broadcast_to_users(
                    list(contact_ids),
                    {
                        "type": "user_status",
                        "user_id": user_id,
                        "username": username,
                        "is_online": False,
                        "last_seen": off_now.isoformat(),
                    },
                )
