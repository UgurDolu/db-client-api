import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager

# Add the backend directory to the Python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.core.config import settings
from app.services.query_executor import QueryExecutor
from app.db.session import dispose_engine

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