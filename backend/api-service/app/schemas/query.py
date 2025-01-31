from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from shared.models import QueryStatus

class QueryBase(BaseModel):
    query_text: str
    db_username: str
    db_password: str
    db_tns: str
    export_location: Optional[str] = None
    export_type: Optional[str] = None
    export_filename: Optional[str] = None  # Optional custom filename for exported file
    ssh_hostname: Optional[str] = None  # Optional SSH hostname for remote execution

class QueryCreate(QueryBase):
    pass

class QueryUpdate(BaseModel):
    query_text: Optional[str] = None
    db_username: Optional[str] = None
    db_password: Optional[str] = None
    db_tns: Optional[str] = None
    export_location: Optional[str] = None
    export_type: Optional[str] = None
    export_filename: Optional[str] = None
    ssh_hostname: Optional[str] = None
    status: Optional[QueryStatus] = None
    error_message: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None

class Query(QueryBase):
    id: int
    user_id: int
    status: QueryStatus = QueryStatus.pending
    error_message: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

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
    export_filename: Optional[str] = None
    ssh_hostname: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class QueryBatchDelete(BaseModel):
    query_ids: List[int]

class QueryBatchRerun(BaseModel):
    query_ids: List[int]

class BatchOperationResponse(BaseModel):
    message: str
    successful_ids: List[int]
    failed_ids: Optional[Dict[int, str]] = None

class QueryStats(BaseModel):
    running_queries: int
    queued_queries: int 