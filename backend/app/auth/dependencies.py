from typing import Optional
from fastapi import Depends, HTTPException, Request, WebSocket, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.auth.security import decode_access_token


def extract_token_from_request(request: Request) -> Optional[str]:
    """Extract JWT token from HttpOnly cookie or Authorization header."""
    # 1. Check HttpOnly cookie first (primary auth)
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        return token

    # 2. Check Authorization header (Bearer token fallback)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """Dependency to retrieve and validate the authenticated user from request."""
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )

    return user


def get_current_user_from_ws(
    websocket: WebSocket,
    db: Session,
) -> Optional[User]:
    """Authenticate a WebSocket handshake via query token or cookie."""
    # 1. Check explicit query parameter first
    token = websocket.query_params.get("token")

    # 2. Fallback to cookie sent during WebSocket handshake
    if not token:
        token = websocket.cookies.get(settings.COOKIE_NAME)

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    user_id = payload["sub"]
    return db.query(User).filter(User.id == user_id).first()
