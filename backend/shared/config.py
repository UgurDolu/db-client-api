from typing import Optional
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "db_client"
    _SQLALCHEMY_DATABASE_URI: Optional[str] = None

    def get_database_uri(self) -> str:
        """Get the database URI."""
        if self._SQLALCHEMY_DATABASE_URI:
            return self._SQLALCHEMY_DATABASE_URI
        
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

# Create a singleton instance
db_settings = DatabaseSettings() 