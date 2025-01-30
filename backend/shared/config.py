from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import os

class BaseSettingsModel(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )

class DatabaseSettings(BaseSettingsModel):
    POSTGRES_SERVER: str = os.getenv("DB_POSTGRES_SERVER", "postgres")  # Default to service name
    POSTGRES_PORT: int = int(os.getenv("DB_POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("DB_POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("DB_POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("DB_POSTGRES_DB", "dbclient")
    _SQLALCHEMY_DATABASE_URI: Optional[str] = None

    def get_database_uri(self) -> str:
        """Get the database URI."""
        if self._SQLALCHEMY_DATABASE_URI:
            return self._SQLALCHEMY_DATABASE_URI
        
        # Print debug information
        print(f"Database Connection Info:")
        print(f"Server: {self.POSTGRES_SERVER}")
        print(f"Port: {self.POSTGRES_PORT}")
        print(f"Database: {self.POSTGRES_DB}")
        print(f"User: {self.POSTGRES_USER}")
        
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = ConfigDict(
        env_prefix="DB_POSTGRES_",
        case_sensitive=True,
        extra="allow"
    )

class SecuritySettings(BaseSettingsModel):
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 days

    model_config = ConfigDict(
        env_prefix="SECURITY_",
        case_sensitive=True,
        extra="allow"
    )

class QuerySettings(BaseSettingsModel):
    GLOBAL_MAX_PARALLEL_QUERIES: int = 50
    QUERY_LISTENER_CHECK_INTERVAL: int = 10
    QUERY_LISTENER_LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(
        env_prefix="QUERY_",
        case_sensitive=True,
        extra="allow"
    )

class SCPSettings(BaseSettingsModel):
    SCP_HOST: str = "localhost"
    SCP_PORT: int = 22
    SCP_USER: str = ""
    SCP_PASSWORD: str = ""

    model_config = ConfigDict(
        env_prefix="SCP_",
        case_sensitive=True,
        extra="allow"
    )

class Settings(BaseSettingsModel):
    db: DatabaseSettings = DatabaseSettings()
    security: SecuritySettings = SecuritySettings()
    query: QuerySettings = QuerySettings()
    scp: SCPSettings = SCPSettings()

    def get_database_uri(self) -> str:
        return self.db.get_database_uri()

# Create singleton instances
settings = Settings()
db_settings = settings.db 