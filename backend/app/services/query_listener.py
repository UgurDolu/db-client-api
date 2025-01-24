import asyncio
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Query, QueryStatus
from app.db.session import AsyncSessionLocal
from app.services.queue_manager import queue_manager
from app.core.config import settings

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, settings.QUERY_LISTENER_LOG_LEVEL))

class QueryListener:
    def __init__(self):
        self._running = False
        self._check_interval = settings.QUERY_LISTENER_CHECK_INTERVAL
        self._last_check_time = None
        self._total_queries_processed = 0
        logger.info(f"Query Listener initialized with check interval: {self._check_interval} seconds")

    async def start(self):
        """Start the query listener."""
        logger.info("Starting Query Listener service")
        self._running = True
        self._last_check_time = datetime.utcnow()
        
        while self._running:
            try:
                start_time = datetime.utcnow()
                queries_found = await self._check_queries()
                end_time = datetime.utcnow()
                
                # Log performance metrics
                processing_time = (end_time - start_time).total_seconds()
                if queries_found > 0:
                    logger.info(
                        f"Processed {queries_found} queries in {processing_time:.2f} seconds "
                        f"(avg: {processing_time/queries_found:.2f} sec/query)"
                    )
                
                # Log periodic stats
                time_since_last_check = (end_time - self._last_check_time).total_seconds()
                if time_since_last_check >= 60:  # Log stats every minute
                    logger.info(
                        f"Listener Stats: Total Queries Processed: {self._total_queries_processed}, "
                        f"Uptime: {(end_time - self._last_check_time).total_seconds():.0f} seconds"
                    )
                    self._last_check_time = end_time
                
            except Exception as e:
                logger.error(f"Error in query listener: {str(e)}", exc_info=True)
            finally:
                await asyncio.sleep(self._check_interval)

    async def stop(self):
        """Stop the query listener."""
        logger.info("Stopping Query Listener service")
        self._running = False
        logger.info(f"Final Stats - Total Queries Processed: {self._total_queries_processed}")

    async def _check_queries(self) -> int:
        """Check for new or unstarted queries and add them to the queue.
        Returns the number of queries processed."""
        queries_processed = 0
        
        async with AsyncSessionLocal() as db:
            try:
                # Find queries that are in PENDING status
                result = await db.execute(
                    select(Query)
                    .where(Query.status == QueryStatus.PENDING.value)
                    .order_by(Query.created_at.asc())
                )
                pending_queries = result.scalars().all()
                
                if pending_queries:
                    logger.info(f"Found {len(pending_queries)} pending queries")

                # Process each pending query
                for query in pending_queries:
                    try:
                        logger.debug(
                            f"Processing query {query.id} "
                            f"(created: {query.created_at.isoformat()})"
                        )
                        
                        # Add query to queue manager
                        await queue_manager.add_query(query, db)
                        queries_processed += 1
                        self._total_queries_processed += 1
                        
                        logger.info(
                            f"Successfully queued query {query.id} "
                            f"(user: {query.user_id}, db: {query.db_tns})"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error processing query {query.id}: {str(e)}", 
                            exc_info=True
                        )
                        
            except Exception as e:
                logger.error(f"Database error in check_queries: {str(e)}", exc_info=True)
                
        return queries_processed

# Create a singleton instance
query_listener = QueryListener() 