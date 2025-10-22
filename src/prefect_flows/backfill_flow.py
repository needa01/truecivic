"""
Prefect flow wrapper around the 2025 backfill helper.

Provides a deployment-friendly interface so we can trigger the backfill from
Prefect Cloud / Railway workers with custom limits.
"""

import logging
from argparse import Namespace
from typing import Any, Optional

from prefect import flow, get_run_logger

from scripts.backfill_2025_sample import backfill_2025


def _coerce_to_int(logger: logging.Logger, name: str, value: Any) -> Optional[int]:
    """Best-effort conversion of dynamic Prefect parameters to integers."""
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


def _build_args(
    logger: logging.Logger,
    *,
    bill_limit: Any,
    vote_limit: Any,
    debate_limit: Any,
    committee_limit: Any,
    meetings_limit: Any,
    politician_limit: Any,
    parliament: Any,
    session: Any,
    full: bool,
    start_year: Any,
    end_year: Any,
) -> Namespace:
    return Namespace(
        bill_limit=_coerce_to_int(logger, "bill_limit", bill_limit),
        vote_limit=_coerce_to_int(logger, "vote_limit", vote_limit),
        debate_limit=_coerce_to_int(logger, "debate_limit", debate_limit),
        committee_limit=_coerce_to_int(logger, "committee_limit", committee_limit),
        meetings_limit=_coerce_to_int(logger, "meetings_limit", meetings_limit),
        politician_limit=_coerce_to_int(logger, "politician_limit", politician_limit),
        parliament=_coerce_to_int(logger, "parliament", parliament),
        session=_coerce_to_int(logger, "session", session),
        full=bool(full),
        start_year=_coerce_to_int(logger, "start_year", start_year),
        end_year=_coerce_to_int(logger, "end_year", end_year),
    )


@flow(name="backfill-2025")
async def backfill_2025_flow(
    bill_limit: Optional[int] = None,
    vote_limit: Optional[int] = None,
    debate_limit: Optional[int] = None,
    committee_limit: Optional[int] = None,
    meetings_limit: Optional[int] = None,
    politician_limit: Optional[int] = None,
    parliament: Any = None,
    session: Any = None,
    full: bool = True,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
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

    logger.info(
        "Starting backfill with parameters: full=%s, start_year=%s, end_year=%s, bill_limit=%s, "
        "vote_limit=%s, debate_limit=%s, committee_limit=%s, meetings_limit=%s, politician_limit=%s, "
        "parliament=%s, session=%s",
        full,
        start_year,
        end_year,
        bill_limit,
        vote_limit,
        debate_limit,
        committee_limit,
        meetings_limit,
        politician_limit,
        parliament,
        session,
    )

    args = _build_args(
        logger,
        bill_limit=bill_limit,
        vote_limit=vote_limit,
        debate_limit=debate_limit,
        committee_limit=committee_limit,
        meetings_limit=meetings_limit,
        politician_limit=politician_limit,
        parliament=parliament,
        session=session,
        full=full,
        start_year=start_year,
        end_year=end_year,
    )

    logger.info(
        "Sanitized backfill args: full=%s, start_year=%s, end_year=%s, bill_limit=%s, vote_limit=%s, "
        "debate_limit=%s, committee_limit=%s, meetings_limit=%s, politician_limit=%s, parliament=%s, session=%s",
        args.full,
        args.start_year,
        args.end_year,
        args.bill_limit,
        args.vote_limit,
        args.debate_limit,
        args.committee_limit,
        args.meetings_limit,
        args.politician_limit,
        args.parliament,
        args.session,
    )
    return await backfill_2025(args)


@flow(name="backfill-decade")
async def backfill_decade_flow(
    bill_limit: Optional[int] = None,
    vote_limit: Optional[int] = None,
    debate_limit: Optional[int] = None,
    committee_limit: Optional[int] = None,
    meetings_limit: Optional[int] = None,
    politician_limit: Optional[int] = None,
    parliament: Any = None,
    session: Any = None,
):
    """Convenience wrapper to backfill the last decade (2015-2025)."""

    logger = get_run_logger()
    logger.info("Launching decade backfill (2015-2025) with full dataset mode enabled")

    args = _build_args(
        logger,
        bill_limit=bill_limit,
        vote_limit=vote_limit,
        debate_limit=debate_limit,
        committee_limit=committee_limit,
        meetings_limit=meetings_limit,
        politician_limit=politician_limit,
        parliament=parliament,
        session=session,
        full=True,
        start_year=2015,
        end_year=2025,
    )

    logger.info(
        "Sanitized decade backfill args: bill_limit=%s, vote_limit=%s, debate_limit=%s, committee_limit=%s, "
        "meetings_limit=%s, politician_limit=%s, parliament=%s, session=%s",
        args.bill_limit,
        args.vote_limit,
        args.debate_limit,
        args.committee_limit,
        args.meetings_limit,
        args.politician_limit,
        args.parliament,
        args.session,
    )

    return await backfill_2025(args)
