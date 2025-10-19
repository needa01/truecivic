"""
Register the backfill-2025 deployment programmatically.

Usage:
    python scripts/register_backfill_deployment.py

Make sure PREFECT_API_KEY and PREFECT_API_URL are exported in the current
environment (e.g., source .env.production or run inside Railway where they
are already set).
"""

from __future__ import annotations

import sys
from pathlib import Path

from prefect.deployments import Deployment

# Ensure project packages are importable when the script is run directly
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from src.prefect_flows.backfill_flow import backfill_2025_flow


def main() -> None:
    deployment = Deployment.build_from_flow(
        flow=backfill_2025_flow,
        name="backfill-2025-sample",
        work_pool_name="default-agent-pool",
        parameters={
            "bill_limit": 10,
            "vote_limit": 10,
            "debate_limit": 10,
            "committee_limit": 10,
            "meetings_limit": 5,
        },
        tags=["backfill", "manual", "2025"],
        description="Run the scoped 2025 backfill (manual trigger).",
    )

    deployment.apply()
    print("✅ Prefect deployment 'backfill-2025-sample' registered successfully.")


if __name__ == "__main__":
    main()
