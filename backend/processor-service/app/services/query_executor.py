import oracledb
import pandas as pd
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from app.db.models import Query, UserSettings, QueryStatus
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select
import os
from pathlib import Path
import logging
from app.services.file_transfer import file_transfer_service
from app.core.config import settings
from sqlalchemy.orm import selectinload
from app.services.file_transfer import FileTransferService
import asyncssh
from app.db.session import AsyncSessionLocal

# Configure to use thin mode (no Oracle Client required)
oracledb.defaults.thin = True

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set to INFO level for development

class QueryExecutor:
    def __init__(self):
        self.active_queries = {}
        self.running = True

    async def process_queries(self):
        """Process pending queries from the queue"""
        while self.running:
            try:
                # Get pending queries
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(Query)
                        .where(Query.status == QueryStatus.pending.value)
                        .options(selectinload(Query.user))
                        .limit(settings.DEFAULT_MAX_PARALLEL_QUERIES)
                    )
                    pending_queries = result.scalars().all()

                for query in pending_queries:
                    if query.id not in self.active_queries:
                        # Start processing the query
                        task = asyncio.create_task(self.execute_query(query))
                        self.active_queries[query.id] = task

                # Clean up completed tasks
                completed = []
                for query_id, task in self.active_queries.items():
                    if task.done():
                        completed.append(query_id)
                for query_id in completed:
                    del self.active_queries[query_id]

            except Exception as e:
                logger.error(f"Error in query processing loop: {str(e)}", exc_info=True)

            # Wait before checking for new queries
            await asyncio.sleep(settings.QUERY_LISTENER_CHECK_INTERVAL)

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

            # Connect to Oracle
            oracle_conn = oracledb.connect(
                user=query.db_username,
                password=query.db_password,
                dsn=query.db_tns
            )

            # Update status to running
            await self._update_query_status(query.id, QueryStatus.running.value)

            # Execute query and process results
            cursor = oracle_conn.cursor()
            try:
                cursor.execute(query.query_text)
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                df = pd.DataFrame(rows, columns=columns)

                # Save and transfer results
                tmp_file_path = await self._save_results(df, query, user_settings)
                
                # Update status to transferring
                await self._update_query_status(
                    query.id,
                    QueryStatus.transferring.value,
                    result_metadata={"tmp_file_path": str(tmp_file_path)}
                )

                # Transfer file
                transfer_service = FileTransferService(user_settings)
                success = await transfer_service.transfer_file(
                    str(tmp_file_path),
                    f"query_{query.id}_result.{query.export_type or 'csv'}",
                    str(query.user_id)
                )

                if success:
                    await self._update_query_status(query.id, QueryStatus.completed.value)
                    return True
                else:
                    raise Exception("File transfer failed")

            finally:
                if cursor:
                    cursor.close()

        except Exception as e:
            logger.error(f"Error executing query {query.id}: {str(e)}", exc_info=True)
            await self._update_query_status(
                query.id,
                QueryStatus.failed.value,
                error_message=str(e)
            )
            return False

        finally:
            if oracle_conn:
                try:
                    oracle_conn.close()
                except:
                    pass

    async def _update_query_status(
        self,
        query_id: int,
        status: str,
        error_message: Optional[str] = None,
        result_metadata: Optional[Dict[str, Any]] = None
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
                            query.started_at = datetime.utcnow()
                        elif status in [QueryStatus.completed.value, QueryStatus.failed.value]:
                            query.completed_at = datetime.utcnow()
                        
                        await session.commit()
                        logger.info(f"Status updated successfully for query {query_id} to {status}")
                        return True
                        
            except Exception as e:
                retry_count += 1
                logger.error(f"Error updating query status (attempt {retry_count}): {str(e)}")
                if retry_count < max_retries:
                    await asyncio.sleep(1)  # Wait before retrying
                else:
                    logger.error(f"Failed to update status after {max_retries} attempts")
                    return False
        
        return False

    async def _save_results(self, df: pd.DataFrame, query: Query, user_settings: Optional[UserSettings]) -> Path:
        """Save DataFrame to file based on export type"""
        try:
            # Create temp directory for exports
            temp_dir = Path("tmp/exports")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with query ID and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = 'xlsx' if query.export_type == 'excel' else (query.export_type or 'csv')
            filename = f"query_{query.id}_{timestamp}.{extension}"
            filepath = temp_dir / filename
            
            # Save based on export type
            if query.export_type == 'csv' or not query.export_type:
                df.to_csv(filepath, index=False)
            elif query.export_type == 'excel':
                df.to_excel(filepath, index=False, engine='openpyxl')
            elif query.export_type == 'json':
                df.to_json(filepath, orient='records')
            elif query.export_type == 'feather':
                df.to_feather(filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}", exc_info=True)
            raise 