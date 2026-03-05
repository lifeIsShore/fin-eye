"""
app/services/auth_service.py
Business logic for user registration and authentication.
"""
import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    name: Optional[str] = None,
) -> User:
    """
    Create a new user. Raises ValueError if email already registered.
    """
    existing = await get_user_by_email(db, email)
    if existing:
        raise ValueError("Email already registered.")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        name=name,
    )
    db.add(user)
    await db.flush()   # get the id without committing
    await db.refresh(user)
    logger.info("Created user id=%s email=%s", user.id, user.email)
    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> Optional[User]:
    """
    Return the User if credentials are valid, else None.
    """
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user