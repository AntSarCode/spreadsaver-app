from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, AliasChoices


# ---------------------------------------------------------------------------
# Base config
# ---------------------------------------------------------------------------
class ORMBase(BaseModel):
    """Base schema with ORM compatibility for SQLAlchemy models (Pydantic v2)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# ---------------------------------------------------------------------------
# User Schemas (pydantic v2)
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    tier: Optional[str] = None
    is_admin: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class UserTierUpdate(BaseModel):
    tier: str

class LoginRequest(BaseModel):
    username_or_email: str = Field(validation_alias=AliasChoices("username_or_email", "username", "email"))
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Badge Schemas (matches Badge, UserBadge, and BadgeAssignRequest models)
# ---------------------------------------------------------------------------
class BadgeBase(ORMBase):
    title: str
    description: Optional[str] = None
    icon_url: Optional[str] = None  # path or URL to PNG/SVG in your assets store
    criteria: Optional[dict] = None  # JSON criteria (e.g., {"spent_over": 500, "category": "Food"})


class BadgeCreate(BadgeBase):
    pass


class BadgeUpdate(ORMBase):
    title: Optional[str] = None
    description: Optional[str] = None
    icon_url: Optional[str] = None
    criteria: Optional[dict] = None


class BadgeRead(BadgeBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UserBadgeBase(ORMBase):
    user_id: int
    badge_id: int
    notes: Optional[str] = None
    source: Optional[str] = None  # e.g., "system", "admin", or a job name


class UserBadgeCreate(UserBadgeBase):
    pass


class UserBadgeRead(UserBadgeBase):
    id: int
    unlocked_at: datetime
    badge: Optional[BadgeRead] = None

    model_config = {"from_attributes": True}

class UserBadgeUpdate(BaseModel):
    unlocked_at: Optional[datetime] = None
    badge_id: Optional[int] = None

class BadgeAssignRequest(ORMBase):
    """Request body for assigning a badge to a user (admin/service action)."""
    user_id: int
    badge_id: int
    reason: Optional[str] = None

class BadgeAssignResult(BaseModel):
    new_badges: list[UserBadgeRead] = Field(default_factory=list)
    message: str = "Badges evaluated and assigned successfully."

    model_config = {"from_attributes": True}

# ---------------------------------------------------------------------------
# Common utility schemas
# ---------------------------------------------------------------------------
class MessageResponse(ORMBase):
    message: str


class Pagination(ORMBase):
    page: int = 1
    size: int = 25


__all__ = [
    # Base
    "ORMBase",
    # Badge
    "BadgeBase",
    "BadgeCreate",
    "BadgeUpdate",
    "BadgeRead",
    # User
    "UserCreate",
    "UserRead",
    "UserTierUpdate",
    "LoginRequest",
    "Token",
    # UserBadge
    "UserBadgeBase",
    "UserBadgeCreate",
    "UserBadgeRead",
    # Requests
    "BadgeAssignRequest",
    "BadgeAssignResult",
    # Utilities
    "MessageResponse",
    "Pagination",
]
