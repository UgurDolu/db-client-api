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

class QueueManager:
    def __init__(self):
        self._running_queries: Dict[int, List[int]] = {}  # user_id -> list of query IDs
        self._queued_queries: Dict[int, List[int]] = {}   # user_id -> list of query IDs
        self._lock = asyncio.Lock()

    async def add_query(self, query: Query, db: AsyncSession) -> None:
        async with self._lock:
            user_id = query.user_id
            query_id = query.id
            
            # Initialize user queues if not exists
            if user_id not in self._running_queries:
                self._running_queries[user_id] = []
            if user_id not in self._queued_queries:
                self._queued_queries[user_id] = []
            
            # Get user settings
            result = await db.execute(
                select(UserSettings).where(UserSettings.user_id == user_id)
            )
            settings = result.scalar_one_or_none()
            max_parallel = settings.max_parallel_queries if settings else 3
            
            # Check if can execute immediately or need to queue
            if len(self._running_queries[user_id]) < max_parallel:
                self._running_queries[user_id].append(query_id)
                asyncio.create_task(self._execute_query(query_id))
            else:
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
                self._queued_queries[user_id].append(query_id)

    async def _execute_query(self, query_id: int) -> None:
        # Create a new session for query execution
        async with AsyncSessionLocal() as db:
            async with db.begin():
                # Get fresh copy of the query
                result = await db.execute(
                    select(Query).where(Query.id == query_id)
                )
                query = result.scalar_one()
                
                executor = QueryExecutor(query, db)
                
                try:
                    if await executor.connect():
                        await executor.execute()
                except Exception as e:
                    logger.error(f"Error executing query {query_id}: {str(e)}")
                finally:
                    async with self._lock:
                        user_id = query.user_id
                        self._running_queries[user_id].remove(query_id)
                        
                        # Process next query in queue if exists
                        if self._queued_queries[user_id]:
                            next_query_id = self._queued_queries[user_id].pop(0)
                            self._running_queries[user_id].append(next_query_id)
                            asyncio.create_task(self._execute_query(next_query_id))

    async def get_queue_position(self, query_id: int, user_id: int) -> Optional[int]:
        async with self._lock:
            if user_id in self._queued_queries:
                try:
                    return self._queued_queries[user_id].index(query_id) + 1
                except ValueError:
                    return None
        return None

    async def get_running_queries_count(self, user_id: int) -> int:
        async with self._lock:
            return len(self._running_queries.get(user_id, []))

    async def get_queued_queries_count(self, user_id: int) -> int:
        async with self._lock:
            return len(self._queued_queries.get(user_id, []))

# Global queue manager instance
queue_manager = QueueManager() 