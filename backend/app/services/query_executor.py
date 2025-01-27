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
from sqlalchemy.orm import selectinload
from app.services.file_transfer import FileTransferService
import asyncssh

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
                select(UserSettings)
                .where(UserSettings.user_id == self.user_id)
                .options(selectinload(UserSettings.user))  # Ensure we load the related user
            )
            self.user_settings = result.scalar_one_or_none()
            if self.user_settings:
                logger.info(f"User settings retrieved for query {self.query_id}")
                if self.user_settings.export_location:
                    logger.info(f"User has custom export location: {self.user_settings.export_location}")
            else:
                logger.info(f"No user settings found for query {self.query_id}")
            
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
            
            # Get fresh query with updated metadata
            async with AsyncSession(self.db.bind) as session:
                async with session.begin():
                    result = await session.execute(
                        select(Query).where(Query.id == self.query_id)
                    )
                    query = result.scalar_one()
                    metadata = query.result_metadata
            
            # Transfer file to final location
            logger.info(f"Starting file transfer from {metadata['tmp_file_path']} to {metadata['final_file_path']}")
            
            # Create FileTransferService with user settings
            transfer_service = FileTransferService(self.user_settings)
            try:
                transfer_success = await transfer_service.transfer_file(
                    metadata['tmp_file_path'],
                    metadata['final_file_path'],
                    str(self.user_id)
                )
                
                if transfer_success:
                    logger.info(f"File transfer successful for query {self.query_id}")
                    await self._update_query_status(
                        QueryStatus.COMPLETED,
                        result_metadata=metadata
                    )
                    # Clean up temporary file
                    try:
                        os.remove(metadata['tmp_file_path'])
                        logger.info(f"Cleaned up temporary file: {metadata['tmp_file_path']}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temporary file {metadata['tmp_file_path']}: {str(e)}")
                    return True
            except asyncssh.PermissionDenied as e:
                error_msg = f"SSH permission denied: {str(e)}"
                logger.error(f"{error_msg} for query {self.query_id}")
                await self._update_query_status(
                    QueryStatus.FAILED,
                    error_message=error_msg
                )
                return False
            except Exception as e:
                error_msg = f"File transfer failed: {str(e)}"
                logger.error(f"{error_msg} for query {self.query_id}")
                await self._update_query_status(
                    QueryStatus.FAILED,
                    error_message=error_msg
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
            temp_dir = os.path.join("tmp", "exports")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Use correct file extension for Excel
            if self.export_type == 'excel':
                extension = 'xlsx'
            else:
                extension = self.export_type
            filename = f"query_{timestamp}.{extension}"
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
            
            # Determine export location from user settings
            export_location = None
            if self.user_settings and self.user_settings.export_location:
                export_location = self.user_settings.export_location
                logger.info(f"Using export location from user settings: {export_location}")
            else:
                # Get fresh query object to check export location
                async with AsyncSession(self.db.bind) as session:
                    async with session.begin():
                        result = await session.execute(
                            select(Query).where(Query.id == self.query_id)
                        )
                        query = result.scalar_one()
                        export_location = query.export_location
                        if export_location:
                            logger.info(f"Using export location from query: {export_location}")

            # If no export location specified, use default shared directory
            if not export_location:
                export_location = "shared"
                logger.info("No export location specified, using default shared directory")
            
            # Create final export path - simplified structure
            final_path = os.path.join(export_location, filename)
            logger.info(f"Final export path: {final_path}")
            
            # Update query with result metadata
            metadata = {
                'tmp_file_path': filepath,
                'final_file_path': final_path,
                'file_size': file_size,
                'rows': len(df),
                'columns': len(df.columns),
                'column_names': list(df.columns)
            }
            
            # Update query metadata in database
            async with AsyncSession(self.db.bind) as session:
                async with session.begin():
                    result = await session.execute(
                        select(Query).where(Query.id == self.query_id)
                    )
                    query = result.scalar_one()
                    query.result_metadata = metadata
                    await session.commit()
            
            logger.info(f"Saved query results to temporary file: {filepath}")
            logger.info(f"Final export path will be: {final_path}")
            logger.info(f"Result metadata: {metadata}")
            
            return filepath
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}", exc_info=True)
            raise 