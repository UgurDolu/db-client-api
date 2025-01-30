import os
import sys
import asyncio
from contextlib import asynccontextmanager

# Add the backend directory to the Python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.services.query_executor import QueryExecutor
from app.db.session import dispose_engine
from app.core.logger import Logger

# Initialize logger
logger = Logger("main").get_logger()

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