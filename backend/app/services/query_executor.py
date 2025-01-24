import oracledb
import pandas as pd
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from app.db.models import Query, QueryStatus, UserSettings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from pathlib import Path
import logging
from app.services.file_transfer import file_transfer_service
from app.core.config import settings

# Configure to use thin mode (no Oracle Client required)
oracledb.defaults.thin = True

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # Set to INFO level for development

class QueryExecutor:
    def __init__(self, query: Query, db: AsyncSession):
        self.query = query
        self.db = db
        self.connection = None
        self.user_settings = None
        # Store query attributes locally
        self.query_id = query.id
        self.user_id = query.user_id
        self.db_username = query.db_username
        self.db_password = query.db_password
        self.db_tns = query.db_tns
        self.query_text = query.query_text
        logger.info(f"Initialized QueryExecutor for query {self.query_id}")

    async def connect(self) -> bool:
        try:
            logger.info(f"Getting user settings for query {self.query_id}")
            # Get user settings
            result = await self.db.execute(
                select(UserSettings).where(UserSettings.user_id == self.user_id)
            )
            self.user_settings = result.scalar_one_or_none()
            logger.info(f"User settings retrieved for query {self.query_id}")
            
            logger.info(f"Connecting to Oracle for query {self.query_id} with DSN: {self.db_tns}")
            # Create connection using thin mode
            self.connection = oracledb.connect(
                user=self.db_username,
                password=self.db_password,
                dsn=self.db_tns
            )
            logger.info(f"Successfully connected to Oracle for query {self.query_id}")
            return True
        except Exception as e:
            logger.error(f"Connection error for query {self.query_id}: {str(e)}", exc_info=True)
            await self._update_query_status(
                QueryStatus.FAILED,
                error_message=f"Connection error: {str(e)}"
            )
            return False

    async def execute(self) -> bool:
        try:
            logger.info(f"Starting execution of query {self.query_id}")
            await self._update_query_status(QueryStatus.RUNNING)
            
            # Execute query
            logger.info(f"Creating cursor for query {self.query_id}")
            cursor = self.connection.cursor()
            
            logger.info(f"Executing SQL for query {self.query_id}: {self.query_text[:100]}...")
            cursor.execute(self.query_text)
            logger.info(f"SQL executed successfully for query {self.query_id}")
            
            # Fetch results
            logger.info(f"Fetching column descriptions for query {self.query_id}")
            columns = [col[0] for col in cursor.description]
            logger.info(f"Columns: {columns}")
            
            logger.info(f"Fetching rows for query {self.query_id}")
            rows = cursor.fetchall()
            logger.info(f"Fetched {len(rows)} rows for query {self.query_id}")
            
            # Convert to DataFrame
            logger.info(f"Converting to DataFrame for query {self.query_id}")
            df = pd.DataFrame(rows, columns=columns)
            logger.info(f"DataFrame created with {len(df)} rows and {len(df.columns)} columns")
            
            # Generate temporary file path with timestamp and query ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"query_{self.query_id}_{timestamp}.csv"
            logger.info(f"Generated filename: {filename}")
            
            # Get tmp path (this will create the directory if needed)
            tmp_file_path = file_transfer_service.get_tmp_path(filename)
            logger.info(f"Using temporary path: {tmp_file_path}")
            
            # Save as CSV
            logger.info(f"Saving DataFrame to CSV for query {self.query_id}")
            df.to_csv(tmp_file_path, index=False)
            logger.info(f"Saved query results to: {tmp_file_path}")
            
            # Prepare metadata
            file_size = os.path.getsize(tmp_file_path)
            logger.info(f"File size: {file_size} bytes")
            metadata = {
                "rows": len(df),
                "columns": len(df.columns),
                "file_size": file_size,
                "tmp_file_path": tmp_file_path  # Include tmp path in metadata for development
            }
            logger.info(f"Prepared metadata: {metadata}")
            
            # Use default export location for development
            export_path = os.path.join("exports", str(self.user_id))
            remote_file_path = os.path.join(export_path, filename)
            logger.info(f"Using export path: {remote_file_path}")
            
            logger.info(f"Starting file transfer for query {self.query_id}")
            transfer_success = await file_transfer_service.transfer_file(
                tmp_file_path,
                remote_file_path,
                str(self.user_id)
            )
            
            if transfer_success:
                logger.info(f"File transfer successful for query {self.query_id}")
                metadata["file_path"] = remote_file_path
                await self._update_query_status(
                    QueryStatus.COMPLETED,
                    result_metadata=metadata
                )
                # Don't clean up tmp file in development
                # file_transfer_service.cleanup_tmp_file(tmp_file_path)
                return True
            else:
                logger.error(f"File transfer failed for query {self.query_id}")
                await self._update_query_status(
                    QueryStatus.FAILED,
                    error_message="Failed to transfer results file"
                )
                return False
            
        except Exception as e:
            logger.error(f"Error executing query {self.query_id}: {str(e)}", exc_info=True)
            await self._update_query_status(
                QueryStatus.FAILED,
                error_message=str(e)
            )
            return False
            
        finally:
            if self.connection:
                logger.info(f"Closing Oracle connection for query {self.query_id}")
                self.connection.close()

    async def _update_query_status(
        self,
        status: QueryStatus,
        error_message: Optional[str] = None,
        result_metadata: Optional[Dict[str, Any]] = None
    ):
        logger.info(f"Updating status for query {self.query_id} to {status}")
        # Create a new session for this update
        async with AsyncSession(self.db.bind) as session:
            async with session.begin():
                # Get fresh copy of the query
                result = await session.execute(
                    select(Query).where(Query.id == self.query_id)
                )
                query = result.scalar_one()
                
                # Update query object
                query.status = status
                if error_message:
                    query.error_message = error_message
                if result_metadata:
                    query.result_metadata = result_metadata
                
                if status == QueryStatus.RUNNING:
                    query.started_at = datetime.utcnow()
                elif status in [QueryStatus.COMPLETED, QueryStatus.FAILED]:
                    query.completed_at = datetime.utcnow()
                
                await session.commit()
                logger.info(f"Status updated successfully for query {self.query_id}")
                
                # Update our reference
                self.query = query 