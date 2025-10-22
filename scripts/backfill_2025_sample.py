"""
Configurable backfill runner for OpenParliament-sourced datasets.

By default fetches a bounded slice of data (bills, votes, debates, committees)
for verification before turning on the full pipelines. Pass --full to pull the
entire dataset for the configured calendar year window (defaults to 2025).

Usage:
    PYTHONIOENCODING=utf-8 python scripts/backfill_2025_sample.py [--full]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

import httpx

from dotenv import load_dotenv

# Ensure database credentials / API keys are loaded before importing project modules
load_dotenv(".env.production")

# Ensure local imports resolve when running as a script
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.prefect_flows.bill_flows import fetch_bills_flow
from src.prefect_flows.vote_with_records_flow import fetch_votes_with_records_flow
from src.prefect_flows.debate_flow import (
    fetch_debates_with_speeches_flow,
    fetch_recent_debates_flow,
)
from src.prefect_flows.committee_flow import (
    fetch_all_committees_flow,
    fetch_committee_meetings_flow,
)
from src.prefect_flows.politician_flow import fetch_politicians_flow
from src.db.session import async_session_factory
from src.db.repositories.committee_repository import CommitteeRepository


# Default backfill window (can be overridden via CLI/Prefect parameters)
DEFAULT_START_YEAR = 2025
DEFAULT_END_YEAR = 2025

# Parliament and session defaults can be overridden via CLI flags or Prefect parameters.
PARLIAMENT_FALLBACK = 45
SESSION_FALLBACK: Optional[int] = 1

OPENPARLIAMENT_BASE_URL = "https://api.openparliament.ca"

SAMPLE_LIMITS = {
    "bills": 10,
    "votes": 10,
    "debates": 10,
    "committees": 10,
    "meetings": 5,
    "politicians": 100,
}

FULL_YEAR_LIMITS = {
    "bills": 2000,
    "votes": 1500,
    "debates": 750,
    "committees": 250,
    "meetings": 200,
    "politicians": 600,
}


async def _resolve_committee_targets(
    *, full_run: bool, committee_limit: int
) -> List[str]:
    """
    Determine which committees to target for meeting backfill.

    Returns a list of committee identifiers (codes/slugs).
    """
    if not full_run:
        return [
            "FINA",
            "HUMA",
            "JUST",
            "HESA",
            "PROC",
            "ETHI",
            "ENVI",
        ]

    async with async_session_factory() as session:
        repo = CommitteeRepository(session)
        committees = await repo.get_all(
            jurisdiction="ca",
            limit=max(committee_limit, FULL_YEAR_LIMITS["committees"]),
        )

        identifiers = sorted(
            {
                committee.committee_code
                for committee in committees
                if committee.committee_code
            }
        )

        if not identifiers:
            # Fallback to the curated list to avoid returning an empty set.
            return [
                "FINA",
                "HUMA",
                "JUST",
                "HESA",
                "PROC",
                "ETHI",
                "ENVI",
            ]

        return identifiers


def _resolve_limit(
    requested: int | None,
    *,
    full_run: bool,
    domain: str,
    year_span: int = 1,
) -> int:
    """Resolve an effective limit for a particular domain."""
    base_map = FULL_YEAR_LIMITS if full_run else SAMPLE_LIMITS
    base_value = base_map[domain]

    if full_run:
        base_value *= max(1, year_span)

    if requested is not None and requested > 0:
        return max(requested, base_value)

    return base_value


def _resolve_window(args: argparse.Namespace) -> tuple[datetime, datetime, int]:
    start_year = getattr(args, "start_year", None) or DEFAULT_START_YEAR
    end_year = getattr(args, "end_year", None) or DEFAULT_END_YEAR

    if start_year > end_year:
        start_year, end_year = end_year, start_year

    window_start = datetime(start_year, 1, 1)
    window_end = datetime(end_year, 12, 31, 23, 59, 59)
    span_years = end_year - start_year + 1

    return window_start, window_end, span_years

async def _fetch_latest_parliament_session(
    logger: logging.Logger,
) -> Tuple[int, Optional[int]]:
    """Fetch the most recent parliament/session from OpenParliament."""

    async with httpx.AsyncClient(
        timeout=15.0,
        headers={
            "User-Agent": "ParliamentExplorer/1.0 (backfill-test)",
            "Accept": "application/json",
        },
    ) as client:
        try:
            response = await client.get(
                f"{OPENPARLIAMENT_BASE_URL}/debates/",
                params={
                    "format": "json",
                    "limit": 1,
                    "order_by": "-date",
                },
            )
            response.raise_for_status()
            payload = response.json()
            objects = payload.get("objects") or []
            if not objects:
                raise ValueError("No debates returned for auto-detection")

            detail_path = objects[0].get("url")
            if not detail_path:
                raise ValueError("Latest debate missing detail URL")

            detail_response = await client.get(
                f"{OPENPARLIAMENT_BASE_URL}{detail_path}",
                params={"format": "json"},
            )
            detail_response.raise_for_status()
            detail_payload = detail_response.json()

            session_raw = detail_payload.get("session")
            parliament: Optional[int] = None
            session_num: Optional[int] = None

            if isinstance(session_raw, dict):
                parliament = session_raw.get("parliament")
                session_num = session_raw.get("session")
            elif isinstance(session_raw, str):
                parts = session_raw.split("-", 1)
                if parts and parts[0].isdigit():
                    parliament = int(parts[0])
                if len(parts) > 1 and parts[1].isdigit():
                    session_num = int(parts[1])

            if parliament is None:
                raise ValueError(f"Unable to parse parliament from session value {session_raw!r}")

            logger.info(
                "Auto-detected parliament/session from OpenParliament: parliament=%s session=%s",
                parliament,
                session_num,
            )
            return parliament, session_num

        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning(
                "Falling back to static parliament/session defaults due to detection error: %s",
                exc,
            )
            return PARLIAMENT_FALLBACK, SESSION_FALLBACK


async def backfill_2025(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Run a bounded backfill across the requested calendar year window.

    Returns:
        Aggregated results keyed by data domain.
    """

    logger = logging.getLogger("backfill_2025")
    results: Dict[str, Any] = {}
    full_run = bool(getattr(args, "full", False))

    window_start, window_end, span_years = _resolve_window(args)
    logger.info(
        "Resolved backfill window: start=%s end=%s span_years=%s",
        window_start.date(),
        window_end.date(),
        span_years,
    )

    parliament_input = getattr(args, "parliament", None)
    if isinstance(parliament_input, str):
        cleaned = parliament_input.strip()
        parliament_input = int(cleaned) if cleaned.isdigit() else None

    session_input = getattr(args, "session", None)
    if isinstance(session_input, str):
        cleaned = session_input.strip()
        session_input = int(cleaned) if cleaned.isdigit() else None

    auto_parliament: Optional[int] = None
    auto_session: Optional[int] = None
    if parliament_input is None or session_input is None:
        auto_parliament, auto_session = await _fetch_latest_parliament_session(logger)

    parliament = parliament_input if parliament_input is not None else (
        auto_parliament if auto_parliament is not None else PARLIAMENT_FALLBACK
    )
    session = session_input if session_input is not None else auto_session

    logger.info(
        "Resolved backfill settings: parliament=%s session=%s full=%s "
        "(requested limits: bills=%s votes=%s debates=%s committees=%s meetings=%s politicians=%s)",
        parliament,
        session,
        full_run,
        args.bill_limit,
        args.vote_limit,
        args.debate_limit,
        args.committee_limit,
        args.meetings_limit,
        getattr(args, "politician_limit", None),
    )

    politician_limit = _resolve_limit(
        getattr(args, "politician_limit", None),
        full_run=full_run,
        domain="politicians",
        year_span=span_years,
    )
    results["politicians"] = await fetch_politicians_flow(
        limit=politician_limit,
        current_only=True,
    )

    # Bills (limit to 2025 introductions)
    bill_limit = _resolve_limit(
        args.bill_limit,
        full_run=full_run,
        domain="bills",
        year_span=span_years,
    )
    results["bills"] = await fetch_bills_flow(
        parliament=None,
        session=None,
        limit=bill_limit,
        introduced_after=window_start,
        introduced_before=window_end,
    )

    # Votes (limit to 2025 vote dates)
    vote_limit = _resolve_limit(
        args.vote_limit,
        full_run=full_run,
        domain="votes",
        year_span=span_years,
    )
    results["votes"] = await fetch_votes_with_records_flow(
        parliament=parliament,
        session=session,
        limit=vote_limit,
        fetch_records=True,
        start_date=window_start,
    )

    # Debates (latest few batches scoped to current parliament/session)
    debate_limit = _resolve_limit(
        args.debate_limit,
        full_run=full_run,
        domain="debates",
        year_span=span_years,
    )
    results["debates"] = await fetch_debates_with_speeches_flow(
        limit=debate_limit,
        parliament=parliament,
        session=session,
    )

    # The helper flow above stores debates. We can optionally sweep a smaller
    # batch without speeches (keeps behaviour closer to incremental run).
    results["debates_recent"] = await fetch_recent_debates_flow(
        limit=min(debate_limit, 50 if full_run else 25)
    )

    # Committees are mostly static, but we fetch a fresh snapshot plus
    # key committee meetings for the same parliament/session.
    committee_limit = _resolve_limit(
        args.committee_limit,
        full_run=full_run,
        domain="committees",
        year_span=span_years,
    )
    results["committees"] = await fetch_all_committees_flow(limit=committee_limit)

    meeting_limit = _resolve_limit(
        args.meetings_limit,
        full_run=full_run,
        domain="meetings",
        year_span=span_years,
    )

    committee_targets = await _resolve_committee_targets(
        full_run=full_run,
        committee_limit=committee_limit,
    )

    results["committee_meetings"] = await fetch_committee_meetings_flow(
        committee_identifiers=committee_targets,
        limit_per_committee=meeting_limit,
        parliament=parliament,
        session=session,
    )
    # Annotate with the number of committees requested for transparency.
    if isinstance(results["committee_meetings"], dict):
        results["committee_meetings"].setdefault("metadata", {})
        results["committee_meetings"]["metadata"]["committees_requested"] = len(
            committee_targets
        )

    return results


def _format_summary(
    results: Dict[str, Any], *, start_year: int, end_year: int
) -> str:
    """Pretty-print a condensed summary to stdout."""
    lines: List[str] = []
    lines.append(
        f"\n=== BACKFILL SUMMARY ({start_year}-{end_year}) ==="
    )
    for domain, payload in results.items():
        status = "unknown"
        counts: List[str] = []
        if isinstance(payload, dict):
            status = payload.get("status", "unknown")
            counts = [
                f"{k}={v}"
                for k, v in payload.items()
                if isinstance(v, (int, float)) and k.endswith(("fetched", "stored", "created", "updated"))
            ]
        lines.append(f"- {domain}: {status} {'; '.join(counts)}")
    lines.append("====================================\n")
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run a bounded backfill against pgvector (sample by default, full dataset with --full)."
        )
    )
    parser.add_argument("--bill-limit", type=int, default=None, help="Number of bills to fetch")
    parser.add_argument("--vote-limit", type=int, default=None, help="Number of votes to fetch")
    parser.add_argument("--debate-limit", type=int, default=None, help="Number of debates to fetch")
    parser.add_argument("--committee-limit", type=int, default=None, help="Number of committees to fetch")
    parser.add_argument(
        "--meetings-limit",
        type=int,
        default=None,
        help="Number of meetings per committee to fetch",
    )
    parser.add_argument(
        "--politician-limit",
        type=int,
        default=None,
        help="Number of politicians to fetch",
    )
    parser.add_argument(
        "--parliament",
        type=int,
        default=None,
        help=(
            "Parliament number to target (default: auto-detected; fallback to "
            f"{PARLIAMENT_FALLBACK})"
        ),
    )
    parser.add_argument(
        "--session",
        type=int,
        default=None,
        help="Session number to target (default: auto/all sessions).",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help=(
            "First calendar year to include (default: 2025; accepts values as far back as OpenParliament allows)."
        ),
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help=(
            "Final calendar year to include (default: start year)."
        ),
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Fetch the full dataset for the specified year window (overrides default sample limits).",
    )
    args = parser.parse_args()

    results = await backfill_2025(args)
    start_dt, end_dt, _ = _resolve_window(args)
    print(_format_summary(results, start_year=start_dt.year, end_year=end_dt.year))


if __name__ == "__main__":
    asyncio.run(main())
