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
        self.export_type = query.export_type.lower() if query.export_type else "csv"
        logger.info(f"Initialized QueryExecutor for query {self.query_id} with export type: {self.export_type}")

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
            if self.connection:
                try:
                    self.connection.close()
                except:
                    pass
            return False

    async def execute(self) -> bool:
        cursor = None
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
            
            # Save results using the _save_results method
            logger.info(f"Saving results for query {self.query_id} with export type: {self.export_type}")
            tmp_file_path = await self._save_results(df)
            logger.info(f"Saved query results to temporary file: {tmp_file_path}")
            
            # Prepare metadata
            file_size = os.path.getsize(tmp_file_path)
            logger.info(f"File size: {file_size} bytes")
            metadata = {
                "rows": len(df),
                "columns": len(df.columns),
                "file_size": file_size,
                "tmp_file_path": tmp_file_path
            }
            logger.info(f"Prepared metadata: {metadata}")
            
            # Create final export directory if it doesn't exist
            export_path = os.path.join("exports", str(self.user_id))
            os.makedirs(export_path, exist_ok=True)
            
            # Use the same filename but in the exports directory
            filename = os.path.basename(tmp_file_path)
            remote_file_path = os.path.join(export_path, filename)
            logger.info(f"Using export path: {remote_file_path}")
            
            logger.info(f"Starting file transfer from {tmp_file_path} to {remote_file_path}")
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
                # Clean up temporary file
                try:
                    os.remove(tmp_file_path)
                    logger.info(f"Cleaned up temporary file: {tmp_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {tmp_file_path}: {str(e)}")
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
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if self.connection:
                try:
                    self.connection.close()
                except:
                    pass

    async def _update_query_status(
        self,
        status: QueryStatus,
        error_message: Optional[str] = None,
        result_metadata: Optional[Dict[str, Any]] = None
    ):
        logger.info(f"Updating status for query {self.query_id} to {status}")
        try:
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
        except Exception as e:
            logger.error(f"Error updating query status: {str(e)}", exc_info=True)
            # If we can't update the status, we should still try to proceed
            # The query might complete but the status update failed 

    async def _save_results(self, df: pd.DataFrame) -> str:
        """Save DataFrame to file based on export type"""
        try:
            # Create temp directory for exports
            temp_dir = os.path.join("tmp", "exports", str(self.user_id))
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use correct file extension for Excel
            if self.export_type == 'excel':
                extension = 'xlsx'
            else:
                extension = self.export_type
            filename = f"query_{self.query_id}_{timestamp}.{extension}"
            filepath = os.path.join(temp_dir, filename)
            
            # Save based on export type
            if self.export_type == 'csv':
                df.to_csv(filepath, index=False)
            elif self.export_type == 'excel':
                try:
                    df.to_excel(filepath, index=False, engine='openpyxl')
                except ImportError:
                    logger.error("openpyxl not installed. Required for Excel export.")
                    raise ValueError("Excel export requires openpyxl to be installed")
            elif self.export_type == 'json':
                df.to_json(filepath, orient='records')
            elif self.export_type == 'feather':
                df.to_feather(filepath)
            
            # Get file size in bytes
            file_size = os.path.getsize(filepath)
            
            # Update query with result metadata
            self.query.result_metadata = {
                'file_path': filepath,
                'file_size': file_size,  # in bytes
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': list(df.columns)
            }
            
            logger.info(f"Saved query results to {filepath}")
            logger.info(f"Result metadata: {self.query.result_metadata}")
            
            return filepath
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}", exc_info=True)
            raise 