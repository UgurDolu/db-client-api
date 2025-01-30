from pydantic_settings import BaseSettings
from typing import Optional, Any, Dict, Union, List, ClassVar
import secrets
from pydantic import ConfigDict
import os
import sys
from shared.config import settings as shared_settings


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "DB Client Processor Service"
    
    # Database settings from shared config
    POSTGRES_SERVER: str = shared_settings.db.POSTGRES_SERVER
    POSTGRES_USER: str = shared_settings.db.POSTGRES_USER
    POSTGRES_PASSWORD: str = shared_settings.db.POSTGRES_PASSWORD
    POSTGRES_DB: str = shared_settings.db.POSTGRES_DB
    POSTGRES_PORT: int = shared_settings.db.POSTGRES_PORT
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    def get_database_uri(self) -> str:
        """Get the database URI."""
        if self.SQLALCHEMY_DATABASE_URI:
            return self.SQLALCHEMY_DATABASE_URI
        return shared_settings.get_database_uri()

    # Security settings from shared config
    SECRET_KEY: str = shared_settings.security.SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = shared_settings.security.ACCESS_TOKEN_EXPIRE_MINUTES
    
    # Queue Settings
    DEFAULT_MAX_PARALLEL_QUERIES: int = 3
    GLOBAL_MAX_PARALLEL_QUERIES: int = shared_settings.query.GLOBAL_MAX_PARALLEL_QUERIES
    DEFAULT_QUEUE_TIMEOUT: int = 3600  # 1 hour
    
    # Export Settings
    VALID_EXPORT_TYPES: ClassVar[List[str]] = ["csv", "excel", "json", "feather"]
    DEFAULT_EXPORT_TYPE: str = "csv"
    DEFAULT_EXPORT_LOCATION: str = "./exports"
    TMP_EXPORT_LOCATION: str = "./tmp/exports"
    
    # SSH Settings
    SSH_HOST: str = shared_settings.scp.SCP_HOST
    SSH_PORT: int = shared_settings.scp.SCP_PORT
    SSH_USERNAME: str = shared_settings.scp.SCP_USER
    SSH_PASSWORD: str = shared_settings.scp.SCP_PASSWORD
    SSH_KEY_FILE: Optional[str] = None
    SSH_KEY_PASSPHRASE: Optional[str] = None
    SSH_KEY: Optional[str] = None
    SSH_KNOWN_HOSTS: Optional[str] = None
    SSH_TIMEOUT: int = 30
    SSH_KEEPALIVE_INTERVAL: int = 30

    # Query Listener Settings
    QUERY_LISTENER_CHECK_INTERVAL: int = shared_settings.query.QUERY_LISTENER_CHECK_INTERVAL
    QUERY_LISTENER_LOG_LEVEL: str = shared_settings.query.QUERY_LISTENER_LOG_LEVEL

    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )


settings = Settings() 