from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import JWTError, jwt
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.models import User
from app.utils.hash import get_password_hash, verify_password

# ---------------------------------------------------------------------------
# Settings shortcuts
# ---------------------------------------------------------------------------
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
SECRET_KEY = settings.SECRET_KEY
REFRESH_SECRET_KEY = settings.REFRESH_SECRET_KEY


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def get_user_by_identifier(db: Session, identifier: str) -> Optional[User]:
    """Fetch a user by case-insensitive username or email."""
    ident = (identifier or "").strip().lower()
    if not ident:
        return None
    return (
        db.query(User)
        .filter(
            or_(
                func.lower(User.username) == ident,
                func.lower(User.email) == ident,
            )
        )
        .first()
    )


def register_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    tier: str = "Free",
    is_admin: bool = False,
) -> User:
    """Register a new user with uniqueness checks and hashed password."""
    username_norm = (username or "").strip()
    email_norm = (email or "").strip().lower()

    if not username_norm or not email_norm or not password:
        raise ValueError("username, email, and password are required")

    # Uniqueness
    if db.query(User).filter(func.lower(User.username) == username_norm.lower()).first():
        raise ValueError("Username already registered")
    if db.query(User).filter(func.lower(User.email) == email_norm).first():
        raise ValueError("Email already registered")

    hashed = get_password_hash(password)
    user = User(
        username=username_norm,
        email=email_norm,
        hashed_password=hashed,
        tier=tier,
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, identifier: str, password: str) -> Optional[User]:
    """Return user if credentials are valid; otherwise None."""
    user = get_user_by_identifier(db, identifier)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _encode_jwt(payload: dict, *, key: str, expires_delta: timedelta) -> str:
    data = payload.copy()
    data.update({"exp": datetime.now(timezone.utc) + expires_delta})
    return jwt.encode(data, key, algorithm=ALGORITHM)


def create_access_token(*, subject: str, expires_minutes: Optional[int] = None) -> str:
    """Create a short-lived access token for `subject` (username)."""
    minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    return _encode_jwt({"sub": subject}, key=SECRET_KEY, expires_delta=timedelta(minutes=minutes))


def create_refresh_token(*, subject: str, expires_days: Optional[int] = None) -> str:
    """Create a longer-lived refresh token for `subject`."""
    days = expires_days or REFRESH_TOKEN_EXPIRE_DAYS
    return _encode_jwt({"sub": subject}, key=REFRESH_SECRET_KEY, expires_delta=timedelta(days=days))


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def issue_token_pair(user: User) -> Tuple[str, str]:
    """Convenience: return (access_token, refresh_token) for a user."""
    access = create_access_token(subject=user.username)
    refresh = create_refresh_token(subject=user.username)
    return access, refresh


__all__ = [
    # users
    "get_user_by_identifier",
    "register_user",
    "authenticate_user",
    # tokens
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    "issue_token_pair",
]
# /backend/app/services/auth_service.py
# Centralized auth logic for SpreadSaver
# - Token creation/decoding
# - User lookup / registration / authentication
# Routes in app/routes/auth.py should call into these helpers.

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from jose import JWTError, jwt
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.models import User
from app.utils.hash import get_password_hash, verify_password

# ---------------------------------------------------------------------------
# Settings shortcuts
# ---------------------------------------------------------------------------
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS
SECRET_KEY = settings.SECRET_KEY
REFRESH_SECRET_KEY = settings.REFRESH_SECRET_KEY


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def get_user_by_identifier(db: Session, identifier: str) -> Optional[User]:
    """Fetch a user by case-insensitive username or email."""
    ident = (identifier or "").strip().lower()
    if not ident:
        return None
    return (
        db.query(User)
        .filter(
            or_(
                func.lower(User.username) == ident,
                func.lower(User.email) == ident,
            )
        )
        .first()
    )


def register_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    tier: str = "Free",
    is_admin: bool = False,
) -> User:
    """Register a new user with uniqueness checks and hashed password."""
    username_norm = (username or "").strip()
    email_norm = (email or "").strip().lower()

    if not username_norm or not email_norm or not password:
        raise ValueError("username, email, and password are required")

    # Uniqueness
    if db.query(User).filter(func.lower(User.username) == username_norm.lower()).first():
        raise ValueError("Username already registered")
    if db.query(User).filter(func.lower(User.email) == email_norm).first():
        raise ValueError("Email already registered")

    hashed = get_password_hash(password)
    user = User(
        username=username_norm,
        email=email_norm,
        hashed_password=hashed,
        tier=tier,
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, identifier: str, password: str) -> Optional[User]:
    """Return user if credentials are valid; otherwise None."""
    user = get_user_by_identifier(db, identifier)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _encode_jwt(payload: dict, *, key: str, expires_delta: timedelta) -> str:
    data = payload.copy()
    data.update({"exp": datetime.now(timezone.utc) + expires_delta})
    return jwt.encode(data, key, algorithm=ALGORITHM)


def create_access_token(*, subject: str, expires_minutes: Optional[int] = None) -> str:
    """Create a short-lived access token for `subject` (username)."""
    minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    return _encode_jwt({"sub": subject}, key=SECRET_KEY, expires_delta=timedelta(minutes=minutes))


def create_refresh_token(*, subject: str, expires_days: Optional[int] = None) -> str:
    """Create a longer-lived refresh token for `subject`."""
    days = expires_days or REFRESH_TOKEN_EXPIRE_DAYS
    return _encode_jwt({"sub": subject}, key=REFRESH_SECRET_KEY, expires_delta=timedelta(days=days))


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def issue_token_pair(user: User) -> Tuple[str, str]:
    """Convenience: return (access_token, refresh_token) for a user."""
    access = create_access_token(subject=user.username)
    refresh = create_refresh_token(subject=user.username)
    return access, refresh


__all__ = [
    # users
    "get_user_by_identifier",
    "register_user",
    "authenticate_user",
    # tokens
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    "issue_token_pair",
]
