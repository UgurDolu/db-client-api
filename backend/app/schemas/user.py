from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserLogin(UserBase):
    password: str

class UserSettings(BaseModel):
    export_location: Optional[str] = None
    export_type: Optional[str] = None
    max_parallel_queries: Optional[int] = None

    class Config:
        from_attributes = True

class User(UserBase):
    id: int
    is_active: bool
    settings: Optional[UserSettings] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None 