from pydantic import BaseModel, EmailStr, SecretStr
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
    ssh_username: Optional[str] = None
    ssh_password: Optional[SecretStr] = None
    ssh_key: Optional[str] = None
    ssh_key_passphrase: Optional[SecretStr] = None

    class Config:
        from_attributes = True

class SSHSettingsUpdate(BaseModel):
    ssh_username: Optional[str] = None
    ssh_password: Optional[SecretStr] = None
    ssh_key: Optional[str] = None
    ssh_key_passphrase: Optional[SecretStr] = None

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