import oracledb
import pandas as pd
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from app.db.models import Query, QueryStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import logging
from app.services.file_transfer import file_transfer_service
from app.core.config import settings

# Configure to use thin mode (no Oracle Client required)
oracledb.defaults.thin = True

logger = logging.getLogger(__name__)

class QueryExecutor:
    def __init__(self, query: Query, db: AsyncSession):
        self.query = query
        self.db = db
        self.connection = None

    async def connect(self) -> bool:
        try:
            # Create connection using thin mode
            self.connection = oracledb.connect(
                user=self.query.db_username,
                password=self.query.db_password,
                dsn=self.query.db_tns,
                encoding="UTF-8"
            )
            return True
        except Exception as e:
            await self._update_query_status(
                QueryStatus.FAILED,
                error_message=f"Connection error: {str(e)}"
            )
            return False

    async def execute(self) -> bool:
        try:
            await self._update_query_status(QueryStatus.RUNNING)
            
            # Execute query
            cursor = self.connection.cursor()
            cursor.execute(self.query.query_text)
            
            # Fetch results
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=columns)
            
            # Generate temporary file path
            filename = f"query_{self.query.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            export_type = self.query.export_type.lower() if self.query.export_type else "csv"
            
            if export_type == "csv":
                filename += ".csv"
            elif export_type == "excel":
                filename += ".xlsx"
            elif export_type == "json":
                filename += ".json"
                
            tmp_file_path = file_transfer_service.get_tmp_path(filename)
            
            # Export to temporary location
            if export_type == "csv":
                df.to_csv(tmp_file_path, index=False)
            elif export_type == "excel":
                df.to_excel(tmp_file_path, index=False)
            elif export_type == "json":
                df.to_json(tmp_file_path, orient="records")
            
            # Prepare metadata
            metadata = {
                "rows": len(df),
                "columns": len(df.columns),
                "file_size": os.path.getsize(tmp_file_path)
            }
            
            # Transfer file to user's export location
            export_path = self.query.export_location or os.path.join("exports", str(self.query.user_id))
            remote_file_path = os.path.join(export_path, filename)
            
            transfer_success = await file_transfer_service.transfer_file(
                tmp_file_path,
                remote_file_path,
                str(self.query.user_id)
            )
            
            if transfer_success:
                metadata["file_path"] = remote_file_path
                await self._update_query_status(
                    QueryStatus.COMPLETED,
                    result_metadata=metadata
                )
                # Clean up temporary file
                file_transfer_service.cleanup_tmp_file(tmp_file_path)
                return True
            else:
                await self._update_query_status(
                    QueryStatus.FAILED,
                    error_message="Failed to transfer results file"
                )
                return False
            
        except Exception as e:
            await self._update_query_status(
                QueryStatus.FAILED,
                error_message=str(e)
            )
            return False
            
        finally:
            if self.connection:
                self.connection.close()

    async def _update_query_status(
        self,
        status: QueryStatus,
        error_message: Optional[str] = None,
        result_metadata: Optional[Dict[str, Any]] = None
    ):
        self.query.status = status
        if error_message:
            self.query.error_message = error_message
        if result_metadata:
            self.query.result_metadata = result_metadata
        
        if status == QueryStatus.RUNNING:
            self.query.started_at = datetime.utcnow()
        elif status in [QueryStatus.COMPLETED, QueryStatus.FAILED]:
            self.query.completed_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(self.query) 