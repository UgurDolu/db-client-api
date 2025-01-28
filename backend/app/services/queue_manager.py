import asyncio
from asyncio import Queue, Lock
from typing import Dict, Set, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import Query, UserSettings
from app.services.query_executor import QueryExecutor
from app.core.config import settings

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self):
        self.queued_queries: Queue = Queue()
        self.running_queries: Set[int] = set()
        self.all_tracked_queries: Set[int] = set()
        self._lock = Lock()
        self._processing = False
        # Track running queries per user
        self.user_running_queries: Dict[int, Set[int]] = {}
        # Global limit from settings
        self.global_max_parallel = getattr(settings, 'GLOBAL_MAX_PARALLEL_QUERIES', 50)
        
    async def add_query(self, query_id: int, user_id: int):
        """Add a query to the processing queue."""
        logger.info(f"Adding query {query_id} for user {user_id} to queue")
        if query_id in self.all_tracked_queries:
            logger.warning(f"Query {query_id} is already in the queue or running")
            return
            
        self.all_tracked_queries.add(query_id)
        await self.queued_queries.put((query_id, user_id))
        
        if not self._processing:
            asyncio.create_task(self._process_queue())
            
    async def get_user_parallel_limit(self, db: AsyncSession, user_id: int) -> int:
        """Get user's max parallel queries limit from settings."""
        try:
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            user_settings = result.scalar_one_or_none()
            if user_settings and user_settings.max_parallel_queries:
                return user_settings.max_parallel_queries
        except Exception as e:
            logger.error(f"Error getting user settings: {str(e)}")
        
        return settings.DEFAULT_MAX_PARALLEL_QUERIES

    async def can_start_query(self, db: AsyncSession, user_id: int) -> bool:
        """Check if a new query can be started based on limits."""
        # Check global limit
        if len(self.running_queries) >= self.global_max_parallel:
            logger.info(f"Global parallel query limit ({self.global_max_parallel}) reached")
            return False
            
        # Check user limit
        user_limit = await self.get_user_parallel_limit(db, user_id)
        user_running = len(self.user_running_queries.get(user_id, set()))
        
        if user_running >= user_limit:
            logger.info(f"User {user_id} parallel query limit ({user_limit}) reached")
            return False
            
        return True

    async def _process_queue(self):
        """Process queries in the queue respecting limits."""
        async with self._lock:
            if self._processing:
                return
            self._processing = True
        
        try:
            while not self.queued_queries.empty():
                async with AsyncSessionLocal() as db:
                    query_id, user_id = await self.queued_queries.get()
                    
                    if not await self.can_start_query(db, user_id):
                        # Put the query back in the queue if limits are reached
                        await self.queued_queries.put((query_id, user_id))
                        logger.info(f"Query {query_id} requeued due to limits")
                        await asyncio.sleep(1)  # Prevent tight loop
                        continue
                    
                    # Start the query
                    self.running_queries.add(query_id)
                    if user_id not in self.user_running_queries:
                        self.user_running_queries[user_id] = set()
                    self.user_running_queries[user_id].add(query_id)
                    
                    # Update query status to QUEUED
                    try:
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
                        logger.error(f"Error updating query {query_id} status: {str(e)}")
                    
                    # Execute query
                    asyncio.create_task(self._execute_query(query_id, user_id))

        except Exception as e:
            logger.error(f"Error in queue processor: {str(e)}")
        finally:
            async with self._lock:
                self._processing = False
            logger.info("Queue processor stopped")

    async def _execute_query(self, query_id: int, user_id: int):
        """Execute a single query and update tracking."""
        logger.info(f"Starting execution of query {query_id}")
        try:
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    result = await db.execute(
                        select(Query).where(Query.id == query_id)
                    )
                    query = result.scalar_one_or_none()
                    
                    if not query:
                        logger.error(f"Query {query_id} not found")
                        return
                    
                    executor = QueryExecutor(query, db)
                    if await executor.connect():
                        await executor.execute()
                    
        except Exception as e:
            logger.error(f"Error executing query {query_id}: {str(e)}")
        finally:
            # Remove from running queries set and user tracking
            self.running_queries.discard(query_id)
            if user_id in self.user_running_queries:
                self.user_running_queries[user_id].discard(query_id)
                if not self.user_running_queries[user_id]:
                    del self.user_running_queries[user_id]
            
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