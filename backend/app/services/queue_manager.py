import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Query, QueryStatus, User, UserSettings
from app.services.query_executor import QueryExecutor
from app.db.session import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set to INFO level for development

class QueueManager:
    def __init__(self):
        self._running_queries: Dict[int, List[int]] = {}  # user_id -> list of query IDs
        self._queued_queries: Dict[int, List[int]] = {}   # user_id -> list of query IDs
        self._lock = asyncio.Lock()
        logger.info("Queue Manager initialized")

    async def add_query(self, query: Query, db: AsyncSession) -> None:
        logger.info(f"Adding query {query.id} to queue for user {query.user_id}")
        async with self._lock:
            user_id = query.user_id
            query_id = query.id
            
            # Initialize user queues if not exists
            if user_id not in self._running_queries:
                self._running_queries[user_id] = []
                logger.info(f"Initialized running queries list for user {user_id}")
            if user_id not in self._queued_queries:
                self._queued_queries[user_id] = []
                logger.info(f"Initialized queued queries list for user {user_id}")
            
            # Get user settings
            logger.info(f"Getting user settings for user {user_id}")
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none()
            max_parallel = settings.max_parallel_queries if settings else 3
            logger.info(f"Max parallel queries for user {user_id}: {max_parallel}")
            
            # Check if can execute immediately or need to queue
            current_running = len(self._running_queries[user_id])
            logger.info(f"Current running queries for user {user_id}: {current_running}")
            
            if current_running < max_parallel:
                logger.info(f"Starting query {query_id} immediately")
                self._running_queries[user_id].append(query_id)
                asyncio.create_task(self._execute_query(query_id))
            else:
                logger.info(f"Queueing query {query_id} for later execution")
                # Create a new session for updating query status
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        # Get fresh copy of the query
                        result = await session.execute(
                            select(Query).where(Query.id == query_id)
                        )
                        query = result.scalar_one()
                        query.status = QueryStatus.QUEUED
                        await session.commit()
                        logger.info(f"Updated query {query_id} status to QUEUED")
                self._queued_queries[user_id].append(query_id)

    async def _execute_query(self, query_id: int) -> None:
        logger.info(f"Starting execution of query {query_id}")
        try:
            # Create a new session for query execution
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    # Get fresh copy of the query
                    result = await db.execute(
                        select(Query).where(Query.id == query_id)
                    )
                    query = result.scalar_one()
                    logger.info(f"Retrieved fresh copy of query {query_id}")
                    
                    executor = QueryExecutor(query, db)
                    
                    logger.info(f"Attempting to connect for query {query_id}")
                    if await executor.connect():
                        logger.info(f"Connection successful, executing query {query_id}")
                        await executor.execute()
                    else:
                        logger.error(f"Connection failed for query {query_id}")
        except Exception as e:
            logger.error(f"Error executing query {query_id}: {str(e)}", exc_info=True)
        finally:
            async with self._lock:
                # Get user_id from running queries since query object might be detached
                user_id = next(uid for uid, qids in self._running_queries.items() if query_id in qids)
                logger.info(f"Removing query {query_id} from running queries for user {user_id}")
                self._running_queries[user_id].remove(query_id)
                
                # Process next query in queue if exists
                if self._queued_queries[user_id]:
                    next_query_id = self._queued_queries[user_id].pop(0)
                    logger.info(f"Starting next queued query {next_query_id} for user {user_id}")
                    self._running_queries[user_id].append(next_query_id)
                    asyncio.create_task(self._execute_query(next_query_id))

    async def get_queue_position(self, query_id: int, user_id: int) -> Optional[int]:
        async with self._lock:
            if user_id in self._queued_queries:
                try:
                    position = self._queued_queries[user_id].index(query_id) + 1
                    logger.info(f"Query {query_id} is at position {position} in queue for user {user_id}")
                    return position
                except ValueError:
                    logger.info(f"Query {query_id} not found in queue for user {user_id}")
                    return None
        return None

    async def get_running_queries_count(self, user_id: int) -> int:
        async with self._lock:
            count = len(self._running_queries.get(user_id, []))
            logger.info(f"User {user_id} has {count} running queries")
            return count

    async def get_queued_queries_count(self, user_id: int) -> int:
        async with self._lock:
            count = len(self._queued_queries.get(user_id, []))
            logger.info(f"User {user_id} has {count} queued queries")
            return count

# Global queue manager instance
queue_manager = QueueManager() 