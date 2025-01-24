import cx_Oracle
import pandas as pd
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from app.db.models import Query, QueryStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import logging

logger = logging.getLogger(__name__)

class QueryExecutor:
    def __init__(self, query: Query, db: AsyncSession):
        self.query = query
        self.db = db
        self.connection = None

    async def connect(self) -> bool:
        try:
            # Create connection
            self.connection = cx_Oracle.connect(
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
            
            # Ensure export directory exists
            export_path = self.query.export_location or os.path.join("exports", str(self.query.user_id))
            os.makedirs(export_path, exist_ok=True)
            
            # Export based on type
            file_path = os.path.join(export_path, f"query_{self.query.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            export_type = self.query.export_type.lower() if self.query.export_type else "csv"
            
            if export_type == "csv":
                file_path += ".csv"
                df.to_csv(file_path, index=False)
            elif export_type == "excel":
                file_path += ".xlsx"
                df.to_excel(file_path, index=False)
            elif export_type == "json":
                file_path += ".json"
                df.to_json(file_path, orient="records")
            
            # Update query status
            metadata = {
                "rows": len(df),
                "columns": len(df.columns),
                "file_path": file_path,
                "file_size": os.path.getsize(file_path)
            }
            
            await self._update_query_status(
                QueryStatus.COMPLETED,
                result_metadata=metadata
            )
            return True
            
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