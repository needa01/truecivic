"""
Prefect flow wrapper around the 2025 backfill helper.

Provides a deployment-friendly interface so we can trigger the backfill from
Prefect Cloud / Railway workers with custom limits.
"""

from argparse import Namespace
from typing import Optional

from prefect import flow

from scripts.backfill_2025_sample import backfill_2025


@flow(name="backfill-2025")
async def backfill_2025_flow(
    bill_limit: Optional[int] = None,
    vote_limit: Optional[int] = None,
    debate_limit: Optional[int] = None,
    committee_limit: Optional[int] = None,
    meetings_limit: Optional[int] = None,
    parliament: Optional[int] = None,
    session: Optional[int] = None,
    full: bool = True,
):
    """
    Prefect flow entrypoint for the 2025 backfill.

    Args mirror the CLI helper so we can reuse logic across both entrypoints.
    """
    args = Namespace(
        bill_limit=bill_limit,
        vote_limit=vote_limit,
        debate_limit=debate_limit,
        committee_limit=committee_limit,
        meetings_limit=meetings_limit,
        parliament=parliament,
        session=session,
        full=full,
    )
    return await backfill_2025(args)
