from pydantic_settings import BaseSettings
from typing import Optional, Any, Dict, Union, List, ClassVar
import secrets
from pydantic import validator
import os
import sys


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "DB Client Processor Service"
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "db_client"
    _SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # Queue Settings
    DEFAULT_MAX_PARALLEL_QUERIES: int = 3
    GLOBAL_MAX_PARALLEL_QUERIES: int = 50  # Maximum total parallel queries across all users
    DEFAULT_QUEUE_TIMEOUT: int = 3600  # 1 hour
    
    # Export Settings
    VALID_EXPORT_TYPES: ClassVar[List[str]] = ["csv", "excel", "json", "feather"]
    DEFAULT_EXPORT_TYPE: str = "csv"
    DEFAULT_EXPORT_LOCATION: str = "./exports"
    TMP_EXPORT_LOCATION: str = "./tmp/exports"  # Temporary storage for query results
    
    # SSH Settings
    SSH_HOST: str = "localhost"
    SSH_PORT: int = 2222
    SSH_USERNAME: str = "testuser"
    SSH_PASSWORD: str = "testpass"
    SSH_KEY_FILE: Optional[str] = None  # Path to private key file for SSH authentication
    SSH_KEY_PASSPHRASE: Optional[str] = None  # Optional passphrase for SSH key
    SSH_KEY: Optional[str] = None  # SSH key content as string
    SSH_KNOWN_HOSTS: Optional[str] = None  # Path to known_hosts file
    SSH_TIMEOUT: int = 30  # Connection timeout in seconds
    SSH_KEEPALIVE_INTERVAL: int = 30  # Keepalive interval in seconds

    # Query Listener Settings
    QUERY_LISTENER_CHECK_INTERVAL: int = 60  # seconds
    QUERY_LISTENER_LOG_LEVEL: str = "INFO"
    
    @validator("ACCESS_TOKEN_EXPIRE_MINUTES", pre=True)
    def parse_token_expire(cls, value: Union[str, int]) -> int:
        if isinstance(value, str):
            # Remove comments and convert to int
            clean_value = value.split('#')[0].strip()
            return int(clean_value)
        return value

    def get_database_uri(self) -> str:
        if self._SQLALCHEMY_DATABASE_URI:
            return self._SQLALCHEMY_DATABASE_URI
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"  # Allow extra fields in the settings


settings = Settings() 