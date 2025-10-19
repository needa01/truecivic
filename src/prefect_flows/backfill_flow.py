"""
Prefect flow wrapper around the 2025 backfill helper.

Provides a deployment-friendly interface so we can trigger the backfill from
Prefect Cloud / Railway workers with custom limits.
"""

from argparse import Namespace

from prefect import flow

from scripts.backfill_2025_sample import backfill_2025


@flow(name="backfill-2025")
async def backfill_2025_flow(
    bill_limit: int = 10,
    vote_limit: int = 10,
    debate_limit: int = 10,
    committee_limit: int = 10,
    meetings_limit: int = 5,
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
    )
    return await backfill_2025(args)
