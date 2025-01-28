import asyncio
import logging
from app.core.config import settings
from app.services.query_executor import QueryExecutor
from app.db.session import dispose_engine
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan():
    # Startup
    logger.info("Starting up processor service...")
    executor = QueryExecutor()
    task = asyncio.create_task(executor.process_queries())
    yield
    # Shutdown
    logger.info("Shutting down processor service...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    # Cleanup database connections
    await dispose_engine()
    logger.info("Processor service shutdown complete")

def main():
    executor = QueryExecutor()
    try:
        asyncio.run(executor.process_queries())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Ensure connection pool is cleaned up
        asyncio.run(dispose_engine())

if __name__ == "__main__":
    main() 