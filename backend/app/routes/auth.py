from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    AuthResponse,
)
from app.schemas.conversation import UserSimpleResponse
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user
from app.websocket.manager import manager

router = APIRouter(prefix="/api", tags=["Authentication & Users"])


def normalize_username(username: str) -> str:
    """Consistently normalize username (stripped and lowercased)."""
    return username.strip().lower()


def build_user_response(user: User) -> UserResponse:
    """Helper to convert ORM User to UserResponse with real-time online status."""
    return UserResponse(
        id=user.id,
        username=user.username,
        created_at=user.created_at,
        last_seen=user.last_seen,
        is_online=manager.is_user_online(user.id),
    )


def set_auth_cookie(response: Response, token: str):
    """Set the HttpOnly JWT access token cookie."""
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


def clear_auth_cookie(response: Response):
    """Clear the HttpOnly authentication cookie."""
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        domain=settings.COOKIE_DOMAIN,
        path="/",
        samesite=settings.COOKIE_SAMESITE,
    )


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, response: Response, db: Session = Depends(get_db)):
    """
    Register a new user account with username and password only.
    Enforces uniqueness using both application-level validation and a UNIQUE database constraint.
    Usernames are normalized case-insensitively.
    """
    normalized_username = normalize_username(payload.username)

    # 1. Application-level validation
    existing_user = (
        db.query(User)
        .filter(func.lower(User.username) == normalized_username)
        .first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists. Please choose another username.",
        )

    # 2. Database-level UNIQUE constraint / index enforcement
    new_user = User(
        username=normalized_username,
        hashed_password=hash_password(payload.password),
    )
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists. Please choose another username.",
        )

    token = create_access_token(new_user.id)
    set_auth_cookie(response, token)

    return AuthResponse(
        user=build_user_response(new_user),
        message="Registration successful.",
    )


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: UserLoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    Authenticate a user with username and password only.
    Sets HttpOnly cookie upon success.
    Returns a generic error without revealing whether username exists.
    """
    normalized_username = normalize_username(payload.username)
    user = (
        db.query(User)
        .filter(func.lower(User.username) == normalized_username)
        .first()
    )
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = create_access_token(user.id)
    set_auth_cookie(response, token)

    return AuthResponse(
        user=build_user_response(user),
        message="Login successful.",
    )


@router.post("/auth/logout")
def logout(response: Response):
    """Log out current user by clearing the HttpOnly cookie."""
    clear_auth_cookie(response)
    return {"message": "Logged out successfully."}


@router.get("/auth/me", response_model=AuthResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve profile of the authenticated user."""
    return AuthResponse(
        user=build_user_response(current_user),
        message="Session active.",
    )


@router.get("/users", response_model=List[UserSimpleResponse])
def get_registered_users(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all registered users excluding current authenticated user.
    Strictly determined by authenticated session, never accepting client parameters.
    Prevents HTTP caching so fresh database records are always returned.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    users = (
        db.query(User)
        .filter(
            User.id != current_user.id,
            func.lower(User.username) != func.lower(current_user.username),
        )
        .order_by(User.username.asc())
        .all()
    )
    return [
        UserSimpleResponse(
            id=u.id,
            username=u.username,
            is_online=manager.is_user_online(u.id),
            last_seen=u.last_seen,
        )
        for u in users
    ]


@router.get("/users/search", response_model=List[UserSimpleResponse])
def search_users(
    response: Response,
    q: Optional[str] = Query(None, description="Username search query"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search registered users by username query using normalized logic.
    Always excludes the authenticated user.
    If query is empty or omitted, returns all discoverable users.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    query = db.query(User).filter(
        User.id != current_user.id,
        func.lower(User.username) != func.lower(current_user.username),
    )

    if q and q.strip():
        normalized_q = normalize_username(q)
        query = query.filter(func.lower(User.username).contains(normalized_q))

    users = query.order_by(User.username.asc()).limit(50).all()

    return [
        UserSimpleResponse(
            id=u.id,
            username=u.username,
            is_online=manager.is_user_online(u.id),
            last_seen=u.last_seen,
        )
        for u in users
    ]
