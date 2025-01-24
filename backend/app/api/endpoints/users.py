from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.user import User, UserSettings
from app.db.models import User as UserModel, UserSettings as UserSettingsModel
from app.api.endpoints.auth import get_current_user
from sqlalchemy import select

router = APIRouter()

@router.get("/me", response_model=User)
async def read_user_me(current_user: UserModel = Depends(get_current_user)):
    return current_user

@router.get("/me/settings", response_model=UserSettings)
async def read_user_settings(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserSettingsModel).where(UserSettingsModel.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settings not found"
        )
    return settings

@router.put("/me/settings", response_model=UserSettings)
async def update_user_settings(
    settings_update: UserSettings,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(UserSettingsModel).where(UserSettingsModel.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settings not found"
        )
    
    # Update settings
    for field, value in settings_update.dict(exclude_unset=True).items():
        setattr(settings, field, value)
    
    await db.commit()
    await db.refresh(settings)
    return settings 