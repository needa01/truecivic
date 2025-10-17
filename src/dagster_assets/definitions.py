"""
Dagster definitions for Parliament Explorer orchestration.

This module defines:
- Asset definitions (bill fetching, monitoring)
- Job schedules (daily refreshes, hourly updates)
- Resources (database connections)
- Sensors (future: event-driven triggers)

Responsibility: Configure Dagster orchestration layer
"""

from dagster import (
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    AssetSelection,
    RunRequest,
    DefaultScheduleStatus,
)

from src.dagster_assets.bill_assets import (
    fetch_latest_bills,
    fetch_parliament_session_bills,
    monitor_fetch_operations,
)


# Define jobs (collections of assets that run together)
fetch_bills_job = define_asset_job(
    name="fetch_bills_job",
    selection=AssetSelection.assets(fetch_latest_bills),
    description="Fetch latest bills from OpenParliament and LEGISinfo",
    config={
        "ops": {
            "fetch_latest_bills": {
                "config": {
                    "limit": 50,  # Fetch 50 most recent bills
                }
            }
        }
    },
)

monitor_job = define_asset_job(
    name="monitor_job",
    selection=AssetSelection.assets(monitor_fetch_operations),
    description="Monitor fetch operations and report statistics",
    config={
        "ops": {
            "monitor_fetch_operations": {
                "config": {
                    "hours_back": 24,  # Monitor last 24 hours
                }
            }
        }
    },
)


# Define schedules
fetch_bills_hourly = ScheduleDefinition(
    name="fetch_bills_hourly",
    job=fetch_bills_job,
    cron_schedule="0 * * * *",  # Every hour at minute 0
    default_status=DefaultScheduleStatus.STOPPED,  # Start manually
    description="Fetch latest bills every hour to keep data fresh",
)

fetch_bills_daily = ScheduleDefinition(
    name="fetch_bills_daily",
    job=fetch_bills_job,
    cron_schedule="0 2 * * *",  # Daily at 2:00 AM
    default_status=DefaultScheduleStatus.STOPPED,  # Start manually
    description="Fetch latest bills daily at 2 AM",
)

monitor_daily = ScheduleDefinition(
    name="monitor_daily",
    job=monitor_job,
    cron_schedule="0 3 * * *",  # Daily at 3:00 AM (after fetch)
    default_status=DefaultScheduleStatus.STOPPED,  # Start manually
    description="Monitor fetch operations daily at 3 AM",
)


# Main Dagster definitions
defs = Definitions(
    assets=[
        fetch_latest_bills,
        fetch_parliament_session_bills,
        monitor_fetch_operations,
    ],
    jobs=[
        fetch_bills_job,
        monitor_job,
    ],
    schedules=[
        fetch_bills_hourly,
        fetch_bills_daily,
        monitor_daily,
    ],
)
