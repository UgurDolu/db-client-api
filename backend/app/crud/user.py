from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.db.models import User, UserSettings
from app.core.auth import get_password_hash
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Get user by email."""
    try:
        result = await db.execute(
            select(User)
            .options(selectinload(User.settings))
            .where(User.email == email)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting user by email: {str(e)}")
        return None

async def create_user(db: AsyncSession, email: str, password: str) -> User:
    """Create a new user."""
    try:
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create default settings for the user
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        await db.commit()
        
        return user
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise

async def get_user_settings(db: AsyncSession, user_id: int) -> Optional[UserSettings]:
    """Get user settings."""
    try:
        result = await db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error getting user settings: {str(e)}")
        return None

async def update_user_settings(
    db: AsyncSession,
    user_id: int,
    settings_update: Dict[str, Any]
) -> Optional[UserSettings]:
    """Update user settings."""
    try:
        # Get existing settings
        settings = await get_user_settings(db, user_id)
        if not settings:
            # Create settings if they don't exist
            settings = UserSettings(user_id=user_id)
            db.add(settings)
        
        # Update settings
        for field, value in settings_update.items():
            setattr(settings, field, value)
        
        await db.commit()
        await db.refresh(settings)
        return settings
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user settings: {str(e)}")
        raise 