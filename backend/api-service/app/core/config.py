from pydantic_settings import BaseSettings
from typing import Optional, Any, Dict, Union, List, ClassVar
import secrets
from pydantic import ConfigDict
import os
import sys
import logging
from shared.config import settings as shared_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "DB Client API"
    
    # Database settings
    DB_POSTGRES_SERVER: str = "postgres"  # Use Docker service name directly
    DB_POSTGRES_USER: str = "postgres"
    DB_POSTGRES_PASSWORD: str = "postgres"
    DB_POSTGRES_DB: str = "dbclient"
    DB_POSTGRES_PORT: int = 5432

    def get_database_uri(self) -> str:
        """Get the database URI."""
        # Print debug information
        logger.info("Database Connection Info (API Service):")
        logger.info(f"Server: {self.DB_POSTGRES_SERVER}")
        logger.info(f"Port: {self.DB_POSTGRES_PORT}")
        logger.info(f"Database: {self.DB_POSTGRES_DB}")
        logger.info(f"User: {self.DB_POSTGRES_USER}")
        
        return f"postgresql+asyncpg://{self.DB_POSTGRES_USER}:{self.DB_POSTGRES_PASSWORD}@{self.DB_POSTGRES_SERVER}:{self.DB_POSTGRES_PORT}/{self.DB_POSTGRES_DB}"

    # Security settings
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days
    
    # Queue Settings
    DEFAULT_MAX_PARALLEL_QUERIES: int = 3
    GLOBAL_MAX_PARALLEL_QUERIES: int = 50
    DEFAULT_QUEUE_TIMEOUT: int = 3600  # 1 hour
    
    # Export Settings
    VALID_EXPORT_TYPES: ClassVar[List[str]] = ["csv", "excel", "json", "feather"]
    DEFAULT_EXPORT_TYPE: str = "csv"
    DEFAULT_EXPORT_LOCATION: str = "./exports"
    TMP_EXPORT_LOCATION: str = "./tmp/exports"
    
    # SSH Settings
    SSH_HOST: str = "sshtest"
    SSH_PORT: int = 22
    SSH_USERNAME: str = "testuser"
    SSH_PASSWORD: str = "testpass"
    SSH_KEY_FILE: Optional[str] = None
    SSH_KEY_PASSPHRASE: Optional[str] = None
    SSH_KEY: Optional[str] = None
    SSH_KNOWN_HOSTS: Optional[str] = None
    SSH_TIMEOUT: int = 30
    SSH_KEEPALIVE_INTERVAL: int = 30

    # Query Listener Settings
    QUERY_LISTENER_CHECK_INTERVAL: int = 10
    QUERY_LISTENER_LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="allow"
    )


settings = Settings(
    _env_file=None,  # Disable .env file loading
    DB_POSTGRES_SERVER=os.getenv("DB_POSTGRES_SERVER", "postgres"),
    DB_POSTGRES_USER=os.getenv("DB_POSTGRES_USER", "postgres"),
    DB_POSTGRES_PASSWORD=os.getenv("DB_POSTGRES_PASSWORD", "postgres"),
    DB_POSTGRES_DB=os.getenv("DB_POSTGRES_DB", "dbclient"),
    DB_POSTGRES_PORT=int(os.getenv("DB_POSTGRES_PORT", "5432"))
) 