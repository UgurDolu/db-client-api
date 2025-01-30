from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(
    settings.get_database_uri(),
    pool_pre_ping=True,
    echo=False,
    # Increase pool size and overflow
    pool_size=20,  # Default is 5
    max_overflow=30,  # Default is 10
    # Add pool recycling to prevent stale connections
    pool_recycle=3600,  # Recycle connections after 1 hour
    # Increase timeout for operations
    pool_timeout=60,  # Wait up to 60 seconds for a connection
    # Enable connection debugging
    echo_pool=False
)

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
            yield session
        finally:
            await session.close()

# Add a function to properly dispose of the connection pool
async def dispose_engine():
    await engine.dispose() 