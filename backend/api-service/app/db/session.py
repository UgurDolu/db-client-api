from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
from app.core.config import settings
import logging
import asyncio

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log the database URI being used (with password masked)
db_uri = settings.get_database_uri()
masked_uri = db_uri.replace(settings.DB_POSTGRES_PASSWORD, "****")
logger.info(f"Connecting to database with URI: {masked_uri}")

# Create the async engine with the database URI
engine = create_async_engine(
    settings.get_database_uri(),
    pool_pre_ping=True,
    echo=True,  # Enable SQL logging
    echo_pool=True,  # Enable connection pool logging
    # Increase pool size and overflow
    pool_size=5,  # Start with a smaller pool
    max_overflow=10,  # Limit overflow
    # Add pool recycling to prevent stale connections
    pool_recycle=3600,  # Recycle connections after 1 hour
    # Increase timeout for operations
    pool_timeout=30,  # Wait up to 30 seconds for a connection
    # Add connect args for asyncpg
    connect_args={
        "server_settings": {
            "application_name": "db_client_api",
            "client_encoding": "utf8"
        },
        "command_timeout": 60,
        "ssl": False,  # Disable SSL for Docker internal communication
        "host": settings.DB_POSTGRES_SERVER  # Explicitly set the host
    }
)

# Add engine event listeners for debugging
@event.listens_for(engine.sync_engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    logger.info("New database connection established")

@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    logger.info("Database connection checked out from pool")

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            logger.info("Creating new database session")
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            logger.info("Closing database session")
            await session.close()

async def dispose_engine():
    logger.info("Disposing database engine")
    await engine.dispose() 