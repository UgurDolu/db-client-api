import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Query, QueryStatus, User, UserSettings
from app.services.query_executor import QueryExecutor
import logging

logger = logging.getLogger(__name__)

class QueueManager:
    def __init__(self):
        self._running_queries: Dict[int, List[Query]] = {}  # user_id -> list of running queries
        self._queued_queries: Dict[int, List[Query]] = {}   # user_id -> list of queued queries
        self._lock = asyncio.Lock()

    async def add_query(self, query: Query, db: AsyncSession) -> None:
        async with self._lock:
            user_id = query.user_id
            
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
                self._running_queries[user_id].append(query)
                asyncio.create_task(self._execute_query(query, db))
            else:
                query.status = QueryStatus.QUEUED
                await db.commit()
                self._queued_queries[user_id].append(query)

    async def _execute_query(self, query: Query, db: AsyncSession) -> None:
        executor = QueryExecutor(query, db)
        
        try:
            if await executor.connect():
                await executor.execute()
        except Exception as e:
            logger.error(f"Error executing query {query.id}: {str(e)}")
        finally:
            async with self._lock:
                user_id = query.user_id
                self._running_queries[user_id].remove(query)
                
                # Process next query in queue if exists
                if self._queued_queries[user_id]:
                    next_query = self._queued_queries[user_id].pop(0)
                    self._running_queries[user_id].append(next_query)
                    asyncio.create_task(self._execute_query(next_query, db))

    async def get_queue_position(self, query_id: int, user_id: int) -> Optional[int]:
        async with self._lock:
            if user_id in self._queued_queries:
                for i, query in enumerate(self._queued_queries[user_id]):
                    if query.id == query_id:
                        return i + 1
        return None

    async def get_running_queries_count(self, user_id: int) -> int:
        async with self._lock:
            return len(self._running_queries.get(user_id, []))

    async def get_queued_queries_count(self, user_id: int) -> int:
        async with self._lock:
            return len(self._queued_queries.get(user_id, []))

# Global queue manager instance
queue_manager = QueueManager() 