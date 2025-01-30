import oracledb
import pandas as pd
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from app.db.models import Query, UserSettings, QueryStatus
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, func
import os
from pathlib import Path
from app.services.file_transfer import file_transfer_service
from app.core.config import settings
from sqlalchemy.orm import selectinload
from app.services.file_transfer import FileTransferService
import asyncssh
from app.db.session import AsyncSessionLocal
from collections import defaultdict
from app.core.logger import Logger

# Configure to use thin mode (no Oracle Client required)
oracledb.defaults.thin = True

# Initialize logger
logger = Logger("query_executor").get_logger()

class QueryExecutor:
    def __init__(self):
        self.logger = Logger("QueryExecutor").get_logger()
        self.active_queries = {}  # query_id -> task
        self.user_active_queries = defaultdict(set)  # user_id -> set of query_ids
        self.running = True
        self.max_total_queries = settings.GLOBAL_MAX_PARALLEL_QUERIES
        self.check_interval = settings.QUERY_LISTENER_CHECK_INTERVAL
        self._total_queries_processed = 0
        self._start_time = datetime.now(timezone.utc)
        
        self.logger.info(
            f"Initialized QueryExecutor with:"
            f"\n - Max parallel queries: {self.max_total_queries}"
            f"\n - Check interval: {self.check_interval} seconds"
            f"\n - Start time: {self._start_time.isoformat()}"
        )

    async def get_user_query_limit(self, session: AsyncSession, user_id: int) -> int:
        """Get user's max parallel queries limit from settings"""
        try:
            result = await session.execute(
                select(UserSettings.max_parallel_queries)
                .where(UserSettings.user_id == user_id)
            )
            user_limit = result.scalar_one_or_none()
            limit = user_limit if user_limit is not None else settings.DEFAULT_MAX_PARALLEL_QUERIES
            self.logger.debug(f"User {user_id} query limit: {limit}")
            return limit
        except Exception as e:
            self.logger.error(f"Error getting user query limit for user {user_id}: {str(e)}")
            return settings.DEFAULT_MAX_PARALLEL_QUERIES

    async def get_running_queries_count(self, session: AsyncSession) -> Dict[int, int]:
        """Get count of currently running queries per user"""
        try:
            result = await session.execute(
                select(Query.user_id, func.count(Query.id))
                .where(Query.status.in_([QueryStatus.running.value, QueryStatus.transferring.value]))
                .group_by(Query.user_id)
            )
            counts = dict(result.all())
            self.logger.debug(f"Current running queries per user: {counts}")
            return counts
        except Exception as e:
            self.logger.error(f"Error getting running queries count: {str(e)}")
            return {}

    async def process_queries(self):
        """Process pending queries from the queue while respecting limits"""
        self.logger.info("Starting query processing service")
        last_stats_time = datetime.now(timezone.utc)
        
        while self.running:
            try:
                async with AsyncSessionLocal() as session:
                    # Log current system state
                    total_running = sum(len(queries) for queries in self.user_active_queries.values())
                    self.logger.info(
                        f"Checking for pending queries..."
                        f"\n - Total running queries: {total_running}/{self.max_total_queries}"
                        f"\n - Active users: {len(self.user_active_queries)}"
                    )

                    # Get all pending queries with their users' settings
                    result = await session.execute(
                        select(Query, UserSettings)
                        .join(UserSettings, Query.user_id == UserSettings.user_id)
                        .where(Query.status == QueryStatus.pending.value)
                        .order_by(Query.created_at)
                        .options(selectinload(Query.user))
                    )
                    pending_queries = result.unique().all()

                    if pending_queries:
                        self.logger.info(f"Found {len(pending_queries)} pending queries")

                    # Group queries by user
                    user_pending_queries = defaultdict(list)
                    for query, settings in pending_queries:
                        user_pending_queries[query.user_id].append((query, settings))
                        self.logger.debug(
                            f"Pending query {query.id} for user {query.user_id}:"
                            f"\n - Created at: {query.created_at}"
                            f"\n - Database: {query.db_tns}"
                        )

                    # Calculate available slots
                    total_running = sum(len(queries) for queries in self.user_active_queries.values())
                    available_slots = max(0, self.max_total_queries - total_running)

                    if available_slots > 0:
                        self.logger.info(f"Processing queries with {available_slots} available slots")
                        # Process queries for each user fairly
                        started_count = 0
                        while available_slots > started_count:
                            started_any = False
                            
                            # Try to start one query for each user that has pending queries
                            for user_id, user_queries in list(user_pending_queries.items()):
                                if not user_queries:  # Skip if user has no more pending queries
                                    continue
                                
                                current_user_queries = len(self.user_active_queries[user_id])
                                user_limit = user_queries[0][1].max_parallel_queries or settings.DEFAULT_MAX_PARALLEL_QUERIES

                                # Check if we can start a query for this user
                                if current_user_queries < user_limit:
                                    query, _ = user_queries.pop(0)  # Remove the query from pending list
                                    if query.id not in self.active_queries:
                                        self.logger.info(
                                            f"Starting query {query.id} for user {user_id}:"
                                            f"\n - Current user queries: {current_user_queries}/{user_limit}"
                                            f"\n - Total system queries: {total_running}/{self.max_total_queries}"
                                        )
                                        
                                        # Start processing the query
                                        task = asyncio.create_task(self.execute_query(query))
                                        
                                        # Add cleanup callback
                                        def cleanup_callback(task, query_id=query.id, user_id=user_id):
                                            self.active_queries.pop(query_id, None)
                                            self.user_active_queries[user_id].discard(query_id)
                                            if not self.user_active_queries[user_id]:
                                                self.user_active_queries.pop(user_id, None)
                                            self._total_queries_processed += 1
                                            self.logger.info(
                                                f"Query {query_id} completed and cleaned up:"
                                                f"\n - Total processed: {self._total_queries_processed}"
                                                f"\n - Remaining active queries: {len(self.active_queries)}"
                                            )
                                        
                                        task.add_done_callback(cleanup_callback)
                                        
                                        self.active_queries[query.id] = task
                                        self.user_active_queries[user_id].add(query.id)
                                        started_count += 1
                                        started_any = True
                                        
                                        # Break if we've used all available slots
                                        if started_count >= available_slots:
                                            break
                            
                            # If we couldn't start any queries in this round, break
                            if not started_any:
                                break

                    # Log periodic statistics (every 5 minutes)
                    current_time = datetime.now(timezone.utc)
                    if (current_time - last_stats_time).total_seconds() >= 300:
                        uptime = current_time - self._start_time
                        self.logger.info(
                            f"QueryExecutor Statistics:"
                            f"\n - Uptime: {uptime}"
                            f"\n - Total queries processed: {self._total_queries_processed}"
                            f"\n - Currently active queries: {len(self.active_queries)}"
                            f"\n - Active users: {len(self.user_active_queries)}"
                            f"\n - Available slots: {available_slots}"
                        )
                        last_stats_time = current_time

            except Exception as e:
                self.logger.error(f"Error in process_queries: {str(e)}", exc_info=True)
            
            # Use a short sleep to prevent CPU spinning
            await asyncio.sleep(self.check_interval)

    async def execute_query(self, query: Query) -> bool:
        """Execute a single query"""
        oracle_conn = None
        try:
            async with AsyncSessionLocal() as session:
                # Get user settings
                result = await session.execute(
                    select(UserSettings)
                    .where(UserSettings.user_id == query.user_id)
                    .options(selectinload(UserSettings.user))
                )
                user_settings = result.scalar_one_or_none()

                # Log transfer details
                self.logger.info(f"Query {query.id} transfer details:")
                if query.ssh_hostname:
                    self.logger.info(f"File will be transferred to host: {query.ssh_hostname}")
                elif user_settings and user_settings.ssh_hostname:
                    self.logger.info(f"File will be transferred to host: {user_settings.ssh_hostname} (from user settings)")
                else:
                    self.logger.info("Using local file transfer (no SSH hostname specified)")
                
                if query.export_location:
                    self.logger.info(f"Export location is: {query.export_location}")
                elif user_settings and user_settings.export_location:
                    self.logger.info(f"Export location is: {user_settings.export_location} (from user settings)")
                else:
                    self.logger.info(f"Using default export location: {settings.DEFAULT_EXPORT_LOCATION}")

                # Update status to running and set started_at timestamp
                await self._update_query_status(
                    query.id,
                    QueryStatus.running.value,
                    started_at=datetime.now(timezone.utc)
                )

                # Run database operations in a thread pool to avoid blocking
                def execute_oracle_query():
                    conn = oracledb.connect(
                        user=query.db_username,
                        password=query.db_password,
                        dsn=query.db_tns
                    )
                    cursor = conn.cursor()
                    cursor.execute(query.query_text)
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    return columns, rows

                # Execute in thread pool
                loop = asyncio.get_event_loop()
                columns, rows = await loop.run_in_executor(None, execute_oracle_query)
                
                # Create DataFrame
                df = pd.DataFrame(rows, columns=columns)

                # Save and transfer results
                tmp_file_path, result_metadata = await self._save_results(df, query, user_settings)
                
                # Calculate final file path based on user settings or query-specific path
                final_path = (
                    query.export_location or 
                    (user_settings.export_location if user_settings else None) or 
                    settings.DEFAULT_EXPORT_LOCATION
                )
                # Get export type from query or user settings
                export_type = query.export_type or (user_settings.export_type if user_settings else None) or 'csv'
                self.logger.info(f"Using export type: {export_type}")
                if export_type == 'excel':
                    export_type = 'xlsx'
                # Generate filename based on query settings or default format
                if query.export_filename:
                    # Use custom filename from query
                    base_filename = query.export_filename
                    if export_type and not base_filename.endswith(f".{export_type}"):
                        filename = f"{base_filename}.{export_type}"
                    else:
                        filename = base_filename
                    self.logger.info(f"Using custom filename: {filename}")
                else:
                    # Generate default filename with timestamp
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    filename = f"{query.id}_query_{timestamp}.{export_type}"
                    self.logger.info(f"Using default filename format: {filename}")

                final_file_path = os.path.join(final_path, filename).replace("\\", "/")
                result_metadata["final_file_path"] = final_file_path
                self.logger.info(f"Final file path: {final_file_path}")
                
                # Update status to transferring
                await self._update_query_status(
                    query.id,
                    QueryStatus.transferring.value,
                    result_metadata=result_metadata
                )

                # Create transfer service with user settings
                transfer_service = FileTransferService(user_settings)
                
                success = await transfer_service.transfer_file(
                    str(tmp_file_path),
                    final_file_path,
                    str(query.user_id),
                    query
                )

                if success:
                    await self._update_query_status(query.id, QueryStatus.completed.value)
                    return True
                else:
                    raise Exception("File transfer failed")

        except Exception as e:
            self.logger.error(f"Error executing query {query.id}: {str(e)}", exc_info=True)
            await self._update_query_status(
                query.id,
                QueryStatus.failed.value,
                error_message=str(e)
            )
            return False

    async def _update_query_status(
        self,
        query_id: int,
        status: str,
        error_message: Optional[str] = None,
        result_metadata: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None
    ) -> bool:
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                async with AsyncSessionLocal() as session:
                    async with session.begin():
                        result = await session.execute(
                                select(Query).where(Query.id == query_id)
                        )
                        query = result.scalar_one()
                        
                        query.status = status
                        if error_message:
                            query.error_message = error_message
                        if result_metadata:
                                existing_metadata = query.result_metadata or {}
                                existing_metadata.update(result_metadata)
                                query.result_metadata = existing_metadata
                        
                        if status == QueryStatus.running.value:
                            query.started_at = started_at or datetime.now(timezone.utc)
                        elif status in [QueryStatus.completed.value, QueryStatus.failed.value]:
                            query.completed_at = datetime.now(timezone.utc)
                        
                        await session.commit()
                        self.logger.info(f"Status updated successfully for query {query_id} to {status}")
                        return True
                        
            except Exception as e:
                    retry_count += 1
                    self.logger.error(f"Error updating query status (attempt {retry_count}): {str(e)}")
                    if retry_count < max_retries:
                        await asyncio.sleep(1)  # Wait before retrying
                    else:
                        self.logger.error(f"Failed to update status after {max_retries} attempts")
                        return False
            
        return False

    async def _save_results(self, df: pd.DataFrame, query: Query, user_settings: Optional[UserSettings]) -> tuple[Path, dict]:
        """Save DataFrame to file based on export type and return metadata"""
        try:
            # Create temp directory for exports
            temp_dir = Path("tmp/exports")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with query ID and timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            extension = 'xlsx' if query.export_type == 'excel' else (query.export_type or 'csv')
            filename = f"query_{query.id}_{timestamp}.{extension}"
            filepath = temp_dir / filename
            
            # Run file I/O operations in thread pool
            loop = asyncio.get_event_loop()
            
            async def save_dataframe():
                def _save():
                    # Save based on export type
                    if query.export_type == 'csv' or not query.export_type:
                        df.to_csv(filepath, index=False)
                    elif query.export_type == 'excel':
                        df.to_excel(filepath, index=False, engine='openpyxl')
                    elif query.export_type == 'json':
                        df.to_json(filepath, orient='records')
                    elif query.export_type == 'feather':
                        df.to_feather(filepath)
                    
                    # Calculate file size
                    return os.path.getsize(filepath)
                
                return await loop.run_in_executor(None, _save)
            
            # Execute file saving in thread pool
            file_size = await save_dataframe()
            
            # Prepare metadata
            metadata = {
                "tmp_file_path": str(filepath),
                "file_size": file_size,
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns)
            }
            
            return filepath, metadata
            
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}", exc_info=True)
            raise 