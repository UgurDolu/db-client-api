from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.query import (
    QueryCreate, Query as QuerySchema, QueryResult, QueryBatchDelete,
    QueryBatchRerun, BatchOperationResponse, QueryStats,
    QueryStatus
)
from shared.models import Query as QueryModel, User as UserModel
from app.api.api_v1.endpoints.auth import get_current_user
from sqlalchemy import select, update, delete, func
from typing import List, Dict
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/query", response_model=QuerySchema)
async def create_query(
    *,
    db: AsyncSession = Depends(get_db),
    query_in: QueryCreate,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Create a new query.

    - **query_text**: SQL query to execute
    - **db_username**: Database username
    - **db_password**: Database password
    - **db_tns**: Database TNS connection string
    - **export_location**: Optional custom export location
    - **export_type**: Optional export file type (csv, excel, json, feather)
    - **export_filename**: Optional custom filename for the exported file (extension will be added automatically)
    - **ssh_hostname**: Optional SSH hostname for remote execution
    """
    logger.info(f"Creating new query for user {current_user.id}")
    try:
        # Create new query with UTC timestamp
        query = QueryModel(
            **query_in.model_dump(),
            user_id=current_user.id,
            status=QueryStatus.pending.value,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(query)
        await db.commit()
        await db.refresh(query)
        logger.info(f"Created query {query.id} for user {current_user.id}")
        
        return query
            
    except Exception as e:
        logger.error(f"Error creating query: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create query: {str(e)}"
        )

@router.get("/query", response_model=List[QuerySchema])
async def list_queries(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all queries for the current user with complete information"""
    try:
        result = await db.execute(
            select(QueryModel)
            .where(QueryModel.user_id == current_user.id)
            .order_by(QueryModel.created_at.desc())
        )
        queries = result.scalars().all()
        return [
            QuerySchema(
                id=query.id,
                user_id=query.user_id,
                query_text=query.query_text,
                db_username=query.db_username,
                db_password=query.db_password,
                db_tns=query.db_tns,
                status=query.status,
                error_message=query.error_message,
                result_metadata=query.result_metadata,
                export_location=query.export_location,
                export_type=query.export_type,
                export_filename=query.export_filename,
                ssh_hostname=query.ssh_hostname,
                created_at=query.created_at,
                started_at=query.started_at,
                updated_at=query.updated_at,
                completed_at=query.completed_at
            ) for query in queries
        ]
    except Exception as e:
        logger.error(f"Error fetching queries: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch queries"
        )

@router.post("/batch/rerun", response_model=BatchOperationResponse)
async def batch_rerun_queries(
    *,
    db: AsyncSession = Depends(get_db),
    batch_data: QueryBatchRerun,
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Rerun multiple queries in batch.

    - **query_ids**: List of query IDs to rerun
    - All original query parameters will be preserved, including:
        - query_text
        - db_username
        - db_password
        - db_tns
        - export_location
        - export_type
        - export_filename
        - ssh_hostname
    """
    successful_ids = []
    failed_ids = {}

    for query_id in batch_data.query_ids:
        try:
            # Get original query
            result = await db.execute(
                select(QueryModel)
                .where(
                    QueryModel.id == query_id,
                    QueryModel.user_id == current_user.id
                )
            )
            original_query = result.scalar_one_or_none()

            if not original_query:
                failed_ids[query_id] = "Query not found or access denied"
                continue

            # Create new query with same parameters
            new_query = QueryModel(
                user_id=current_user.id,
                query_text=original_query.query_text,
                db_username=original_query.db_username,
                db_password=original_query.db_password,
                db_tns=original_query.db_tns,
                export_location=original_query.export_location,
                export_type=original_query.export_type,
                export_filename=original_query.export_filename,  # Preserve custom filename
                ssh_hostname=original_query.ssh_hostname,
                status=QueryStatus.pending.value
            )

            db.add(new_query)
            await db.commit()
            await db.refresh(new_query)
            successful_ids.append(query_id)

        except Exception as e:
            logger.error(f"Error rerunning query {query_id}: {str(e)}")
            failed_ids[query_id] = str(e)

    return {
        "message": f"Processed {len(batch_data.query_ids)} queries",
        "successful_ids": successful_ids,
        "failed_ids": failed_ids
    }

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
        export_filename=query.export_filename,
        ssh_hostname=query.ssh_hostname,
        result_metadata=query.result_metadata,
        error_message=query.error_message,
        created_at=query.created_at,
        started_at=query.started_at,
        updated_at=query.updated_at,
        completed_at=query.completed_at
    )

@router.post("/{query_id}/rerun", response_model=QuerySchema)
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
            ssh_hostname=query.ssh_hostname,
            status=QueryStatus.pending.value,
            created_at=datetime.now(timezone.utc)
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