"""
Selective 2025 backfill runner.

Fetches a bounded slice of data (bills, votes, debates, committees)
for verification before turning on the full pipelines.

Usage:
    PYTHONIOENCODING=utf-8 python scripts/backfill_2025_sample.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

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


# Ensure database credentials / API keys are loaded when run locally
load_dotenv(".env.production")


START_2025 = datetime(2025, 1, 1)
END_2025 = datetime(2025, 12, 31, 23, 59, 59)

# The 44th Parliament entered its second session in September 2023 and remains
# active through 2025. Adjust these if Parliament numbers change.
PARLIAMENT = 44
SESSION = 2


async def backfill_2025(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Run a limited backfill for the 2025 calendar year.

    Returns:
        Aggregated results keyed by data domain.
    """

    results: Dict[str, Any] = {}

    # Bills (limit to 2025 introductions)
    results["bills"] = await fetch_bills_flow(
        parliament=None,
        session=None,
        limit=args.bill_limit,
        introduced_after=START_2025,
        introduced_before=END_2025,
    )

    # Votes (limit to 2025 vote dates)
    results["votes"] = await fetch_votes_with_records_flow(
        parliament=PARLIAMENT,
        session=SESSION,
        limit=args.vote_limit,
        fetch_records=True,
        start_date=START_2025,
    )

    # Debates (latest few batches scoped to current parliament/session)
    results["debates"] = await fetch_debates_with_speeches_flow(
        limit=args.debate_limit,
        parliament=PARLIAMENT,
        session=SESSION,
    )

    # The helper flow above stores debates. We can optionally sweep a smaller
    # batch without speeches (keeps behaviour closer to incremental run).
    results["debates_recent"] = await fetch_recent_debates_flow(limit=min(args.debate_limit, 25))

    # Committees are mostly static, but we fetch a fresh snapshot plus
    # key committee meetings for the same parliament/session.
    results["committees"] = await fetch_all_committees_flow(limit=args.committee_limit)

    top_committees: List[str] = [
        "FINA",
        "HUMA",
        "JUST",
        "HESA",
        "PROC",
        "ETHI",
        "ENVI",
    ]
    results["committee_meetings"] = await fetch_committee_meetings_flow(
        committee_identifiers=top_committees,
        limit_per_committee=args.meetings_limit,
        parliament=PARLIAMENT,
        session=SESSION,
    )

    return results


def _format_summary(results: Dict[str, Any]) -> str:
    """Pretty-print a condensed summary to stdout."""
    lines: List[str] = []
    lines.append("\n=== 2025 SAMPLE BACKFILL SUMMARY ===")
    for domain, payload in results.items():
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
    parser = argparse.ArgumentParser(description="Run a scoped 2025 backfill against pgvector.")
    parser.add_argument("--bill-limit", type=int, default=10, help="Number of bills to fetch (default: 10)")
    parser.add_argument("--vote-limit", type=int, default=10, help="Number of votes to fetch (default: 10)")
    parser.add_argument("--debate-limit", type=int, default=10, help="Number of debates to fetch (default: 10)")
    parser.add_argument("--committee-limit", type=int, default=10, help="Number of committees to fetch (default: 10)")
    parser.add_argument(
        "--meetings-limit",
        type=int,
        default=5,
        help="Number of meetings per committee to fetch (default: 5)",
    )
    args = parser.parse_args()

    results = await backfill_2025(args)
    print(_format_summary(results))


if __name__ == "__main__":
    asyncio.run(main())
