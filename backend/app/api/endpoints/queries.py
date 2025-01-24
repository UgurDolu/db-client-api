from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, AsyncSessionLocal
from app.schemas.query import QueryCreate, Query, QueryResult
from app.db.models import Query as QueryModel, User as UserModel, QueryStatus
from app.api.endpoints.auth import get_current_user
from app.services.queue_manager import queue_manager
from sqlalchemy import select, update, delete
from typing import List
from app.services.query_executor import QueryExecutor
from app.services.queue_manager import QueueManager
from app.core.logger import logger
import asyncio
import os

# Configure endpoint-specific logger
logger = logger.getChild('queries')

router = APIRouter()

@router.post("/", response_model=Query)
async def create_query(
    query: QueryCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Creating new query for user {current_user.id}")
    try:
        # Create new query using the provided session
        db_query = QueryModel(
            user_id=current_user.id,
            db_username=query.db_username,
            db_password=query.db_password,
            db_tns=query.db_tns,
            query_text=query.query_text,
            export_location=query.export_location,
            export_type=query.export_type,
            status="pending"  # Use string directly since it's stored as string in DB
        )
        
        try:
            db.add(db_query)
            await db.commit()
            await db.refresh(db_query)
            
            logger.info(f"Created query {db_query.id} for user {current_user.id}")
            
            # Start background task without passing the session
            asyncio.create_task(queue_manager.add_query(db_query.id, current_user.id))
            logger.info(f"Added query {db_query.id} to queue")
            
            return db_query
            
        except Exception as db_error:
            # Try to rollback if commit failed
            try:
                await db.rollback()
            except:
                pass
            logger.error(f"Database error while creating query: {str(db_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(db_error)}"
            )
            
    except Exception as e:
        logger.error(f"Error creating query for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create query: {str(e)}"
        )

@router.get("/", response_model=List[Query])
async def list_queries(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"Fetching queries for user {current_user.id}")
    try:
        # Use the provided session instead of creating a new one
        result = await db.execute(
            select(QueryModel)
            .where(QueryModel.user_id == current_user.id)
            .order_by(QueryModel.created_at.desc())
        )
        queries = result.scalars().all()
        logger.info(f"Found {len(queries)} queries for user {current_user.id}")
        return queries
    except Exception as e:
        logger.error(f"Error fetching queries for user {current_user.id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch queries"
        )

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
    if query.status == QueryStatus.queued.value:
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

@router.post("/{query_id}/rerun")
async def rerun_query(
    query_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rerun an existing query"""
    logger.info(f"User {current_user.id} requested to rerun query {query_id}")
    
    try:
        # Get the original query
        result = await db.execute(
            select(QueryModel)
            .where(QueryModel.id == query_id)
            .where(QueryModel.user_id == current_user.id)
        )
        query = result.scalar_one_or_none()
        
        if not query:
            logger.warning(f"Query {query_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query {query_id} not found"
            )
        
        # Create a new query with the same parameters
        new_query = QueryModel(
            user_id=current_user.id,
            query_text=query.query_text,
            db_username=query.db_username,
            db_password=query.db_password,
            db_tns=query.db_tns,
            status="pending",  # Use string directly
            export_location=query.export_location,
            export_type=query.export_type
        )
        
        db.add(new_query)
        await db.commit()
        await db.refresh(new_query)
        
        logger.info(f"Created new query {new_query.id} as rerun of {query_id} for user {current_user.id}")
        
        # Add to queue using the new interface
        asyncio.create_task(queue_manager.add_query(new_query.id, current_user.id))
        logger.info(f"Added query {new_query.id} to queue")
        
        return new_query
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rerunning query {query_id}: {str(e)}", exc_info=True)
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
    """Delete a query"""
    logger.info(f"User {current_user.id} requested to delete query {query_id}")
    
    try:
        # Check if query exists and belongs to user
        result = await db.execute(
            select(QueryModel)
            .where(QueryModel.id == query_id)
            .where(QueryModel.user_id == current_user.id)
        )
        query = result.scalar_one_or_none()
        
        if not query:
            logger.warning(f"Query {query_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Query {query_id} not found"
            )
        
        # Don't allow deletion of running or queued queries
        if query.status in ["running", "queued"]:
            logger.warning(f"Attempted to delete {query.status} query {query_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete query in {query.status} status"
            )
        
        # Delete the query
        try:
            await db.execute(
                delete(QueryModel)
                .where(QueryModel.id == query_id)
                .where(QueryModel.user_id == current_user.id)
            )
            await db.commit()
            
            # Try to delete the result file if it exists
            if query.result_metadata and "file_path" in query.result_metadata:
                file_path = query.result_metadata["file_path"]
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Deleted result file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete result file {file_path}: {str(e)}")
            
            logger.info(f"Successfully deleted query {query_id} for user {current_user.id}")
            return {"message": "Query deleted successfully"}
            
        except Exception as db_error:
            await db.rollback()
            logger.error(f"Database error while deleting query {query_id}: {str(db_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error while deleting query: {str(db_error)}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting query {query_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete query: {str(e)}"
        )

@router.delete("/batch")
async def delete_queries(
    query_ids: List[int],
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete multiple queries"""
    logger.info(f"User {current_user.id} requested to delete queries: {query_ids}")
    
    # Check if queries exist and belong to user
    result = await db.execute(
        select(QueryModel)
        .where(QueryModel.id.in_(query_ids))
        .where(QueryModel.user_id == current_user.id)
    )
    queries = result.scalars().all()
    
    if not queries:
        logger.warning(f"No queries found for batch deletion request from user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No queries found"
        )
    
    # Check for running queries
    running_queries = [q for q in queries if q.status in [QueryStatus.running.value, QueryStatus.queued.value]]
    if running_queries:
        logger.warning(f"Attempted to delete running/queued queries: {[q.id for q in running_queries]}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete queries in RUNNING or QUEUED status: {[q.id for q in running_queries]}"
        )
    
    # Delete the queries
    await db.execute(
        delete(QueryModel)
        .where(QueryModel.id.in_(query_ids))
        .where(QueryModel.user_id == current_user.id)
    )
    await db.commit()
    
    logger.info(f"Successfully deleted {len(queries)} queries for user {current_user.id}")
    return {"message": f"Successfully deleted {len(queries)} queries"}

@router.post("/batch/rerun")
async def rerun_queries(
    query_ids: List[int],
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rerun multiple queries"""
    logger.info(f"User {current_user.id} requested to rerun queries: {query_ids}")
    
    try:
        # Get the original queries
        result = await db.execute(
            select(QueryModel)
            .where(QueryModel.id.in_(query_ids))
            .where(QueryModel.user_id == current_user.id)
        )
        queries = result.scalars().all()
        
        if not queries:
            logger.warning(f"No queries found for batch rerun request from user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No queries found"
            )
        
        new_queries = []
        
        # Create new queries
        for query in queries:
            new_query = QueryModel(
                user_id=current_user.id,
                query_text=query.query_text,
                db_username=query.db_username,
                db_password=query.db_password,
                db_tns=query.db_tns,
                status="pending",  # Use string directly
                export_location=query.export_location,
                export_type=query.export_type
            )
            db.add(new_query)
            new_queries.append(new_query)
        
        await db.commit()
        
        # Add all new queries to the queue using the new interface
        for new_query in new_queries:
            await db.refresh(new_query)
            asyncio.create_task(queue_manager.add_query(new_query.id, current_user.id))
            logger.info(f"Added query {new_query.id} to queue")
        
        logger.info(f"Successfully rerun {len(queries)} queries for user {current_user.id}")
        return new_queries
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch rerun: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rerun queries: {str(e)}"
        ) 