"""
Prefect flow to run Alembic schema migrations.

Useful for environments (e.g., Railway) where migrations must run from inside
the application container rather than a local developer machine.
"""

from datetime import datetime
import os
from typing import Optional

from alembic import command
from alembic.config import Config
from prefect import flow, task, get_run_logger
# from prefect.task_runners import SequentialTaskRunner


def _make_alembic_config(config_path: str = "alembic.ini") -> Config:
    """
    Build an Alembic Config bound to the runtime database URL.

    Prefers DATABASE_URL / SQLALCHEMY_DATABASE_URL environment variables so
    deployments can inject credentials at runtime.
    """
    config = Config(config_path)
    database_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URL")
        or config.get_main_option("sqlalchemy.url")
    )
    if not database_url:
        raise RuntimeError(
            "No database URL configured for Alembic. Set DATABASE_URL or "
            "SQLALCHEMY_DATABASE_URL in the environment."
        )
    config.set_main_option("sqlalchemy.url", database_url)
    return config


@task(name="run_alembic_upgrade", retries=1, retry_delay_seconds=30, log_prints=True)
def run_alembic_upgrade_task(
    revision: str = "head",
    config_path: str = "alembic.ini",
    sql: bool = False,
    tag: Optional[str] = None,
) -> dict:
    """
    Execute ``alembic upgrade`` to the requested revision.
    """
    logger = get_run_logger()
    logger.info("Preparing to run Alembic upgrade to revision '%s'", revision)

    config = _make_alembic_config(config_path=config_path)

    command.upgrade(config, revision, sql=sql, tag=tag)

    logger.info("Alembic upgrade to '%s' completed successfully", revision)
    return {
        "revision": revision,
        "config_path": config_path,
        "sql_mode": sql,
        "tag": tag,
    }


@flow(
    name="alembic-upgrade",
    description="Run Alembic migrations inside the Prefect worker environment.",
    # task_runner=sequential_task_runner,
    log_prints=True,
)
def alembic_upgrade_flow(
    revision: str = "head",
    config_path: str = "alembic.ini",
    sql: bool = False,
    tag: Optional[str] = None,
) -> dict:
    """
    Prefect flow wrapper for Alembic migrations.

    Example:
        prefect deployment run alembic-upgrade --revision head
    """
    logger = get_run_logger()
    logger.info(
        "Starting Alembic upgrade flow: revision=%s, sql=%s, tag=%s, config=%s",
        revision,
        sql,
        tag,
        config_path,
    )

    start_time = datetime.utcnow()
    task_result = run_alembic_upgrade_task(
        revision=revision,
        config_path=config_path,
        sql=sql,
        tag=tag,
    )
    end_time = datetime.utcnow()

    result = {
        "status": "success",
        "revision": revision,
        "sql": sql,
        "tag": tag,
        "config_path": config_path,
        "started_at": start_time.isoformat(),
        "completed_at": end_time.isoformat(),
        "duration_seconds": (end_time - start_time).total_seconds(),
        "task_result": task_result,
    }

    logger.info("Alembic upgrade flow finished: %s", result)
    return result


if __name__ == "__main__":
    alembic_upgrade_flow()
