"""
Repository for FetchLog database operations.

Handles CRUD operations for fetch operation logs, used for monitoring
pipeline health and performance.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import FetchLogModel
from src.db.session import Database


class FetchLogRepository:
    """Repository for fetch log operations."""
    
    def __init__(self, db: Database):
        """
        Initialize repository with database instance.
        
        Args:
            db: Database instance
        """
        self.db = db
    
    async def create_log(
        self,
        source: str,
        status: str,
        records_attempted: int,
        records_succeeded: int,
        records_failed: int,
        duration_seconds: float,
        fetch_params: Optional[dict] = None,
        error_count: int = 0,
        error_summary: Optional[str] = None,
    ) -> FetchLogModel:
        """
        Create a new fetch log entry.
        
        Args:
            source: Source of the fetch operation (e.g., "OpenParliament", "LEGISinfo")
            status: Status of the operation ("success", "partial", "error")
            records_attempted: Number of records attempted to fetch
            records_succeeded: Number of records successfully processed
            records_failed: Number of records that failed
            duration_seconds: Duration of the operation in seconds
            fetch_params: Optional parameters used for the fetch
            error_count: Number of errors encountered
            error_summary: Optional summary of errors
            
        Returns:
            Created FetchLogModel instance
        """
        async with self.db.get_session() as session:
            log = FetchLogModel(
                source=source,
                status=status,
                records_attempted=records_attempted,
                records_succeeded=records_succeeded,
                records_failed=records_failed,
                duration_seconds=duration_seconds,
                fetch_params=fetch_params,
                error_count=error_count,
                error_summary=error_summary,
            )
            
            session.add(log)
            await session.commit()
            await session.refresh(log)
            
            return log
    
    async def get_logs_since(
        self,
        cutoff_time: datetime,
        source: Optional[str] = None,
    ) -> List[FetchLogModel]:
        """
        Get all logs since a specific datetime.
        
        Args:
            cutoff_time: Datetime to filter logs from
            source: Optional source filter
            
        Returns:
            List of FetchLogModel instances
        """
        async with self.db.get_session() as session:
            query = select(FetchLogModel).where(
                FetchLogModel.created_at >= cutoff_time
            )
            
            if source:
                query = query.where(FetchLogModel.source == source)
            
            query = query.order_by(FetchLogModel.created_at.desc())
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_recent_logs(
        self,
        limit: int = 100,
        source: Optional[str] = None,
    ) -> List[FetchLogModel]:
        """
        Get most recent fetch logs.
        
        Args:
            limit: Maximum number of logs to return
            source: Optional source filter
            
        Returns:
            List of FetchLogModel instances
        """
        async with self.db.get_session() as session:
            query = select(FetchLogModel)
            
            if source:
                query = query.where(FetchLogModel.source == source)
            
            query = query.order_by(FetchLogModel.created_at.desc()).limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
