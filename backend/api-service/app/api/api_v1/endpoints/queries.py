from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.query import (
    QueryCreate, Query, QueryResult, QueryBatchDelete,
    QueryBatchRerun, BatchOperationResponse, QueryStats,
    QueryStatus
)
from app.db.models import Query as QueryModel, User as UserModel
from app.api.api_v1.endpoints.auth import get_current_user
from sqlalchemy import select, update, delete, func
from typing import List, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=Query)
async def create_query(
    query: QueryCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new query and submit it for processing"""
    logger.info(f"Creating new query for user {current_user.id}")
    try:
        # Create new query
        db_query = QueryModel(
            user_id=current_user.id,
            db_username=query.db_username,
            db_password=query.db_password,
            db_tns=query.db_tns,
            query_text=query.query_text,
            export_location=query.export_location,
            export_type=query.export_type,
            status=QueryStatus.pending.value
        )
        
        db.add(db_query)
        await db.commit()
        await db.refresh(db_query)
        logger.info(f"Created query {db_query.id} for user {current_user.id}")
        
        return db_query
            
    except Exception as e:
        logger.error(f"Error creating query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create query: {str(e)}"
        )

@router.get("/", response_model=List[Query])
async def list_queries(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all queries for the current user"""
    try:
        result = await db.execute(
            select(QueryModel)
            .where(QueryModel.user_id == current_user.id)
            .order_by(QueryModel.created_at.desc())
        )
        queries = result.scalars().all()
        return queries
    except Exception as e:
        logger.error(f"Error fetching queries: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch queries"
        )

@router.post("/batch/rerun", response_model=BatchOperationResponse)
async def batch_rerun_queries(
    query_ids: QueryBatchRerun,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rerun multiple queries in batch"""
    successful_ids = []
    failed_ids: Dict[int, str] = {}

    try:
        # Get all queries
        result = await db.execute(
            select(QueryModel)
            .where(
                QueryModel.id.in_(query_ids.query_ids),
                QueryModel.user_id == current_user.id
            )
        )
        queries = result.scalars().all()
        
        # Create new queries for each original query
        for query in queries:
            try:
                # Create a new query with the same parameters
                new_query = QueryModel(
                    user_id=current_user.id,
                    db_username=query.db_username,
                    db_password=query.db_password,
                    db_tns=query.db_tns,
                    query_text=query.query_text,
                    export_location=query.export_location,
                    export_type=query.export_type,
                    status=QueryStatus.pending.value,
                    created_at=datetime.utcnow()
                )
                
                db.add(new_query)
                await db.flush()  # Get the ID without committing
                successful_ids.append(query.id)
                logger.info(f"Created new query {new_query.id} as rerun of {query.id}")
                
            except Exception as e:
                logger.error(f"Failed to rerun query {query.id}: {str(e)}")
                failed_ids[query.id] = str(e)
        
        # Commit all successful queries at once
        if successful_ids:
            await db.commit()
        
        total_queries = len(query_ids.query_ids)
        success_count = len(successful_ids)
        fail_count = len(failed_ids)
        
        return BatchOperationResponse(
            message=f"Rerun operation completed. Successfully rerun {success_count} out of {total_queries} queries.",
            successful_ids=successful_ids,
            failed_ids=failed_ids if failed_ids else None
        )
            
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch rerun operation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rerun queries: {str(e)}"
        )

@router.post("/batch/delete")
async def batch_delete_queries(
    query_ids: QueryBatchDelete,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete multiple queries in batch"""
    try:
        # Get all queries to check their status
        result = await db.execute(
            select(QueryModel)
            .where(
                QueryModel.id.in_(query_ids.query_ids),
                QueryModel.user_id == current_user.id
            )
        )
        queries = result.scalars().all()
        
        # Check if any query is running or queued
        running_queries = [q.id for q in queries if q.status in [QueryStatus.running.value, QueryStatus.queued.value]]
        if running_queries:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete queries that are running or queued: {running_queries}"
            )
        
        # Delete the queries
        await db.execute(
            delete(QueryModel)
            .where(
                QueryModel.id.in_(query_ids.query_ids),
                QueryModel.user_id == current_user.id
            )
        )
        await db.commit()
        
        return {
            "message": f"Successfully deleted {len(query_ids.query_ids)} queries",
            "deleted_ids": query_ids.query_ids
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch deleting queries: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete queries: {str(e)}"
        )

@router.get("/{query_id}", response_model=QueryResult)
async def get_query_status(
    query_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the status and results of a specific query"""
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
    
    return QueryResult(
        query_id=query.id,
        status=query.status,
        export_location=query.export_location,
        export_type=query.export_type,
        result_metadata=query.result_metadata,
        error_message=query.error_message
    )

@router.post("/{query_id}/rerun", response_model=Query)
async def rerun_query(
    query_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rerun a specific query"""
    try:
        # Get the original query
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
        
        # Create a new query with the same parameters
        new_query = QueryModel(
            user_id=current_user.id,
            db_username=query.db_username,
            db_password=query.db_password,
            db_tns=query.db_tns,
            query_text=query.query_text,
            export_location=query.export_location,
            export_type=query.export_type,
            status=QueryStatus.pending.value,
            created_at=datetime.utcnow()
        )
        
        db.add(new_query)
        await db.commit()
        await db.refresh(new_query)
        
        logger.info(f"Rerun query {query_id} created new query {new_query.id}")
        return new_query
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rerunning query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rerun query: {str(e)}"
        )

@router.delete("/{query_id}")
async def delete_query(
    query_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a query if it's not running or queued"""
    try:
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
        
        if query.status in [QueryStatus.running.value, QueryStatus.queued.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete query in {query.status} status"
            )
        
        await db.execute(
            delete(QueryModel)
            .where(QueryModel.id == query_id, QueryModel.user_id == current_user.id)
        )
        await db.commit()
        
        return {"message": "Query deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete query: {str(e)}"
        )

@router.get("/stats/current", response_model=QueryStats)
async def get_current_stats(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current stats of running and queued queries"""
    try:
        # Get count of running queries
        running_result = await db.execute(
            select(func.count())
            .where(
                QueryModel.user_id == current_user.id,
                QueryModel.status == "running"
            )
        )
        running_count = running_result.scalar_one()

        # Get count of queued queries
        queued_result = await db.execute(
            select(func.count())
            .where(
                QueryModel.user_id == current_user.id,
                QueryModel.status == "queued"
            )
        )
        queued_count = queued_result.scalar_one()

        logger.info(f"Stats for user {current_user.id}: running={running_count}, queued={queued_count}")
        return QueryStats(
            running_queries=running_count,
            queued_queries=queued_count
        )
            
    except Exception as e:
        logger.error(f"Error getting query stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get query stats: {str(e)}"
        ) 