from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from app.db.models import QueryStatus

class QueryBase(BaseModel):
    db_username: str
    db_password: str
    db_tns: str
    query_text: str
    export_location: Optional[str] = None
    export_type: Optional[str] = None

class QueryCreate(QueryBase):
    pass

class QueryUpdate(BaseModel):
    status: Optional[QueryStatus] = None
    error_message: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None

class Query(QueryBase):
    id: int
    user_id: int
    status: QueryStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class QueryStatusResponse(BaseModel):
    query_id: int
    status: QueryStatus
    position: Optional[int] = None
    estimated_time: Optional[int] = None  # in seconds
    error_message: Optional[str] = None

class QueryResult(BaseModel):
    query_id: int
    status: QueryStatus
    export_location: Optional[str] = None
    export_type: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class QueryBatchDelete(BaseModel):
    query_ids: list[int]

class QueryBatchRerun(BaseModel):
    query_ids: list[int]

class BatchOperationResponse(BaseModel):
    message: str
    successful_ids: list[int]
    failed_ids: Optional[Dict[int, str]] = None

class QueryStats(BaseModel):
    running_queries: int
    queued_queries: int 