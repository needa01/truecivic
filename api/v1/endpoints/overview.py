"""Overview endpoints for aggregate statistics."""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db


router = APIRouter()


class OverviewStatsResponse(BaseModel):
    """Aggregate counts for high-level dashboard metrics."""

    bills: int = Field(..., description="Total number of bills available")
    politicians: int = Field(..., description="Total number of politicians available")
    votes: int = Field(..., description="Total number of votes available")
    debates: int = Field(..., description="Total number of debates available")
    committees: int = Field(..., description="Total number of committees available")
    generated_at: datetime = Field(..., description="Timestamp when these statistics were generated")


# MARK: Helpers --------------------------------------------------------------

async def _fetch_scalar(session: AsyncSession, query: str) -> int:
    """Execute a scalar SQL query and return an integer result."""

    result = await session.execute(text(query))
    value = result.scalar() or 0
    return int(value)


async def _collect_counts(session: AsyncSession) -> Dict[str, int]:
    """Collect counts for key entities used on the dashboard."""

    queries = {
        "bills": "SELECT COUNT(*) FROM bills",
        "politicians": "SELECT COUNT(*) FROM politicians",
        "votes": "SELECT COUNT(*) FROM votes",
        "debates": "SELECT COUNT(*) FROM debates",
        "committees": "SELECT COUNT(*) FROM committees",
    }

    results: Dict[str, int] = {}
    for key, sql in queries.items():
        results[key] = await _fetch_scalar(session, sql)
    return results


# MARK: Routes ---------------------------------------------------------------

@router.get(
    "/overview/stats",
    response_model=OverviewStatsResponse,
    summary="Get aggregate counts for dashboard",
    tags=["overview"],
)
async def get_overview_stats(session: AsyncSession = Depends(get_db)) -> OverviewStatsResponse:
    """Return high-level aggregate counts for the public dashboard."""

    counts = await _collect_counts(session)
    return OverviewStatsResponse(
        generated_at=datetime.utcnow(),
        **counts,
    )
