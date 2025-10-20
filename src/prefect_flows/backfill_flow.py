"""
Prefect flow wrapper around the 2025 backfill helper.

Provides a deployment-friendly interface so we can trigger the backfill from
Prefect Cloud / Railway workers with custom limits.
"""

from argparse import Namespace
from typing import Any, Optional

from prefect import flow, get_run_logger

from scripts.backfill_2025_sample import backfill_2025


@flow(name="backfill-2025")
async def backfill_2025_flow(
    bill_limit: Optional[int] = None,
    vote_limit: Optional[int] = None,
    debate_limit: Optional[int] = None,
    committee_limit: Optional[int] = None,
    meetings_limit: Optional[int] = None,
    parliament: Any = None,
    session: Any = None,
    full: bool = True,
):
    """
    Prefect flow entrypoint for the 2025 backfill.

    Args mirror the CLI helper so we can reuse logic across both entrypoints.
    """
    logger = get_run_logger()

    def _coerce_to_int(name: str, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned == "":
                logger.warning("Backfill parameter %s was an empty string; treating as None", name)
                return None
            try:
                return int(cleaned)
            except ValueError:
                logger.warning("Backfill parameter %s='%s' is not an integer; treating as None", name, value)
                return None
        logger.warning("Backfill parameter %s of type %s is unsupported; treating as None", name, type(value))
        return None

    sanitized_parliament = _coerce_to_int("parliament", parliament)
    sanitized_session = _coerce_to_int("session", session)

    logger.info(
        "Starting 2025 backfill with parameters: full=%s, bill_limit=%s, vote_limit=%s, debate_limit=%s, "
        "committee_limit=%s, meetings_limit=%s, parliament=%s, session=%s",
        full,
        bill_limit,
        vote_limit,
        debate_limit,
        committee_limit,
        meetings_limit,
        sanitized_parliament,
        sanitized_session,
    )

    args = Namespace(
        bill_limit=bill_limit,
        vote_limit=vote_limit,
        debate_limit=debate_limit,
        committee_limit=committee_limit,
        meetings_limit=meetings_limit,
        parliament=sanitized_parliament,
        session=sanitized_session,
        full=full,
    )
    return await backfill_2025(args)
