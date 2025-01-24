from pydantic_settings import BaseSettings
from typing import Optional, Any, Dict, Union
import secrets
from pydantic import validator
import os
import sys


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "DB Client API"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "db_client"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # Queue Settings
    DEFAULT_MAX_PARALLEL_QUERIES: int = 3
    DEFAULT_QUEUE_TIMEOUT: int = 3600  # 1 hour
    
    # Export Settings
    DEFAULT_EXPORT_TYPE: str = "csv"
    DEFAULT_EXPORT_LOCATION: str = "./exports"
    TMP_EXPORT_LOCATION: str = "./tmp/exports"  # Temporary storage for query results
    
    # SCP Settings
    SCP_HOST: str = "localhost"
    SCP_PORT: int = 22
    SCP_USER: str = ""
    SCP_PASSWORD: str = ""
    SCP_KEY_FILE: Optional[str] = None  # Path to private key file for SSH authentication

    # Query Listener Settings
    QUERY_LISTENER_CHECK_INTERVAL: int = 5  # seconds
    QUERY_LISTENER_LOG_LEVEL: str = "INFO"
    
    @validator("ACCESS_TOKEN_EXPIRE_MINUTES", pre=True)
    def parse_token_expire(cls, value: Union[str, int]) -> int:
        if isinstance(value, str):
            # Remove comments and convert to int
            clean_value = value.split('#')[0].strip()
            return int(clean_value)
        return value

    @property
    def get_database_url(self) -> str:
        if self.SQLALCHEMY_DATABASE_URI:
            return self.SQLALCHEMY_DATABASE_URI
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings() 