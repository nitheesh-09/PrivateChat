from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="Unique username")
    password: str = Field(..., min_length=6, max_length=100, description="Password with minimum 6 characters")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Username cannot be empty or whitespace only")
        if not cleaned.isalnum() and "_" not in cleaned and "-" not in cleaned:
            raise ValueError("Username can only contain alphanumeric characters, underscores, and hyphens")
        return cleaned


class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Username cannot be empty")
        return cleaned


class UserResponse(BaseModel):
    id: str
    username: str
    created_at: datetime
    last_seen: datetime
    is_online: bool = False

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse
    message: str
