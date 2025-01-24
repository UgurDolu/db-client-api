import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Query, QueryStatus, User, UserSettings
from app.services.query_executor import QueryExecutor
from app.db.session import AsyncSessionLocal
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set to INFO level for development

class QueueManager:
    def __init__(self):
        self.queued_queries = asyncio.Queue()
        self.running_queries = set()
        self.all_tracked_queries = set()  # Track all queries that are either queued or running
        self.max_parallel_queries = getattr(settings, 'DEFAULT_MAX_PARALLEL_QUERIES', 3)
        self._processing = False
        self._lock = asyncio.Lock()
        logger.info(f"Initialized QueueManager with max parallel queries: {self.max_parallel_queries}")

    async def add_query(self, query_id: int, user_id: int):
        """Add a query to the queue if it's not already being processed"""
        async with self._lock:
            # Check if query is already being tracked
            if query_id in self.all_tracked_queries:
                logger.warning(f"Query {query_id} is already in queue or running, skipping")
                return
            
            # Add to tracking set and queue
            self.all_tracked_queries.add(query_id)
            logger.info(f"Adding query {query_id} to queue for user {user_id}")
            await self.queued_queries.put((query_id, user_id))
            
            # Start processing if not already running
            if not self._processing:
                asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """Process queries in the queue"""
        async with self._lock:
            if self._processing:
                logger.debug("Queue processing already running")
                return
            self._processing = True

        try:
            logger.info("Starting queue processing")
            while True:
                # Check if we can run more queries
                if len(self.running_queries) >= self.max_parallel_queries:
                    logger.debug(f"Max parallel queries ({self.max_parallel_queries}) reached, waiting...")
                    await asyncio.sleep(1)
                    continue

                # Try to get a query from the queue
                try:
                    query_id, user_id = await asyncio.wait_for(
                        self.queued_queries.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    if len(self.running_queries) == 0 and self.queued_queries.empty():
                        logger.debug("No queries to process, stopping queue processor")
                        break
                    continue

                logger.info(f"Processing query {query_id} for user {user_id}")
                
                # Start query execution in background
                self.running_queries.add(query_id)
                asyncio.create_task(self._execute_query(query_id, user_id))
                
                # Update query status to QUEUED
                try:
                    async with AsyncSessionLocal() as db:
                        async with db.begin():
                            result = await db.execute(
                                select(Query).where(Query.id == query_id)
                            )
                            query = result.scalar_one_or_none()
                            if query:
                                query.status = "queued"
                                await db.commit()
                                logger.info(f"Updated query {query_id} status to queued")
                except Exception as e:
                    logger.error(f"Error updating query {query_id} status: {str(e)}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in queue processor: {str(e)}", exc_info=True)
        finally:
            async with self._lock:
                self._processing = False
            logger.info("Queue processor stopped")

    async def _execute_query(self, query_id: int, user_id: int):
        """Execute a single query"""
        logger.info(f"Starting execution of query {query_id}")
        try:
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    # Get fresh copy of query
                    result = await db.execute(
                        select(Query).where(Query.id == query_id)
                    )
                    query = result.scalar_one_or_none()
                    
                    if not query:
                        logger.error(f"Query {query_id} not found")
                        return
                    
                    # Execute query
                    executor = QueryExecutor(query, db)
                    if await executor.connect():
                        await executor.execute()
                    
        except Exception as e:
            logger.error(f"Error executing query {query_id}: {str(e)}", exc_info=True)
        finally:
            # Remove from running queries set and tracking set
            self.running_queries.discard(query_id)
            self.all_tracked_queries.discard(query_id)
            logger.info(f"Completed execution of query {query_id}")
            
            # Check if we need to restart queue processing
            if not self._processing and not self.queued_queries.empty():
                asyncio.create_task(self._process_queue())

    async def get_queue_position(self, query_id: int, user_id: int) -> Optional[int]:
        """Get the position of a query in the queue"""
        position = 1
        async for queued_query_id, _ in self._iterate_queue():
            if queued_query_id == query_id:
                return position
            position += 1
        return None

    async def _iterate_queue(self):
        """Helper to iterate through queue without modifying it"""
        # Create a copy of the queue
        temp_queue = asyncio.Queue()
        items = []
        
        try:
            while not self.queued_queries.empty():
                item = await self.queued_queries.get()
                items.append(item)
                await temp_queue.put(item)
        finally:
            # Restore all items to the original queue
            for item in items:
                await self.queued_queries.put(item)
            
        for item in items:
            yield item

    async def get_running_queries_count(self, user_id: int) -> int:
        """Get count of currently running queries for a user"""
        return len(self.running_queries)

    async def get_queued_queries_count(self, user_id: int) -> int:
        """Get count of queued queries for a user"""
        return self.queued_queries.qsize()

# Create a singleton instance
queue_manager = QueueManager() 