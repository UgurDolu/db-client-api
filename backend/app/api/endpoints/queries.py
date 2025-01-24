from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.query import QueryCreate, Query, QueryStatus, QueryResult
from app.db.models import Query as QueryModel, User as UserModel
from app.api.endpoints.auth import get_current_user
from app.services.queue_manager import queue_manager
from sqlalchemy import select
from typing import List

router = APIRouter()

@router.post("/", response_model=Query)
async def create_query(
    query: QueryCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Create new query
    db_query = QueryModel(
        user_id=current_user.id,
        db_username=query.db_username,
        db_password=query.db_password,
        db_tns=query.db_tns,
        query_text=query.query_text,
        export_location=query.export_location,
        export_type=query.export_type
    )
    db.add(db_query)
    await db.commit()
    await db.refresh(db_query)
    
    # Add to queue
    await queue_manager.add_query(db_query, db)
    
    return db_query

@router.get("/", response_model=List[Query])
async def list_queries(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(QueryModel)
        .where(QueryModel.user_id == current_user.id)
        .order_by(QueryModel.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{query_id}", response_model=QueryResult)
async def get_query_status(
    query_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(QueryModel)
        .where(QueryModel.id == query_id, QueryModel.user_id == current_user.id)
    )
    query = result.scalar_one_or_none()
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    # Get queue position if query is queued
    queue_position = None
    if query.status == QueryStatus.QUEUED:
        queue_position = await queue_manager.get_queue_position(query_id, current_user.id)
    
    return QueryResult(
        query_id=query.id,
        status=query.status,
        export_location=query.export_location,
        export_type=query.export_type,
        result_metadata=query.result_metadata,
        error_message=query.error_message,
        position=queue_position
    )

@router.get("/stats/current", response_model=dict)
async def get_current_stats(
    current_user: UserModel = Depends(get_current_user)
):
    running_count = await queue_manager.get_running_queries_count(current_user.id)
    queued_count = await queue_manager.get_queued_queries_count(current_user.id)
    
    return {
        "running_queries": running_count,
        "queued_queries": queued_count
    } 