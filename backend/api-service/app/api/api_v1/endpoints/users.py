from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.api_v1.endpoints.auth import get_current_user
from app.schemas.user import User, UserSettings, SSHSettingsUpdate
from app.crud.user import update_user_settings, get_user_settings
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class UserProfile(BaseModel):
    id: int
    email: str
    is_active: bool
    settings: UserSettings | None = None

    class Config:
        from_attributes = True

@router.get("/profile", response_model=UserProfile)
async def read_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user's profile information"""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        is_active=current_user.is_active,
        settings=current_user.settings
    )

@router.get("/settings", response_model=UserSettings)
async def read_user_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's settings"""
    settings = await get_user_settings(db, current_user.id)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings

@router.put("/settings", response_model=UserSettings)
async def update_user_settings_endpoint(
    settings: UserSettings,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user's settings"""
    try:
        # Validate export type if provided
        if settings.export_type:
            from app.core.config import settings as app_settings
            if settings.export_type not in app_settings.VALID_EXPORT_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid export type. Valid types are: {app_settings.VALID_EXPORT_TYPES}"
                )

        # Validate SSH port if provided
        if settings.ssh_port is not None and (settings.ssh_port < 1 or settings.ssh_port > 65535):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SSH port must be between 1 and 65535"
            )

        # Update settings in database
        updated_settings = await update_user_settings(
            db,
            current_user.id,
            {
                "export_type": settings.export_type,
                "export_location": settings.export_location,
                "max_parallel_queries": settings.max_parallel_queries,
                "ssh_hostname": settings.ssh_hostname,
                "ssh_port": settings.ssh_port,
                "ssh_username": settings.ssh_username,
                "ssh_password": settings.ssh_password.get_secret_value() if settings.ssh_password else None,
                "ssh_key": settings.ssh_key,
                "ssh_key_passphrase": settings.ssh_key_passphrase.get_secret_value() if settings.ssh_key_passphrase else None
            }
        )
        logger.info(f"Updated settings for user {current_user.id}")
        return updated_settings
    except Exception as e:
        logger.error(f"Failed to update user settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update settings: {str(e)}"
        ) 