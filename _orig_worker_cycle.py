"""
Utility to resume a Prefect work pool, start a run-once worker, then pause the pool.

This copy lives next to the Railway Dockerfile so the build context stays self-contained
while sharing the same behaviour as scripts/prefect_worker_cycle.py.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping, Sequence

from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterState,
    FlowRunFilterStateType,
    WorkPoolFilter,
    WorkPoolFilterName,
)


def getenv_bool(name: str, default: bool) -> bool:
    """Read an environment variable as a boolean."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in ("", "0", "false", "no", "off")


def _resolve_log_level(name: str | None) -> int:
    if not name:
        return logging.INFO
    level = getattr(logging, name.upper(), None)
    if isinstance(level, int):
        return level
    return logging.INFO


def _configure_logger() -> logging.Logger:
    level = _resolve_log_level(os.getenv("PREFECT_WORKER_CYCLE_LOG_LEVEL"))
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    logging.captureWarnings(True)
    return logging.getLogger("prefect_worker_cycle")


LOGGER = _configure_logger()


POOL_NAME = os.getenv("PREFECT_WORK_POOL", "default-agent-pool")
WORKER_NAME = os.getenv("PREFECT_WORKER_NAME", "scheduled-default-agent")
WORKER_TYPE = os.getenv("PREFECT_WORKER_TYPE", "process")
PREFETCH_SECONDS = os.getenv("PREFECT_WORKER_PREFETCH_SECONDS", "120")
CONCURRENCY_LIMIT = os.getenv("PREFECT_WORKER_FLOW_LIMIT", "5")
RUN_FOREVER = getenv_bool("PREFECT_WORKER_RUN_FOREVER", False)
TRIGGER_DEPLOYMENTS = [
    part.strip()
    for part in os.getenv("PREFECT_TRIGGER_DEPLOYMENTS", "").split(",")
    if part.strip()
]
WAIT_FOR_COMPLETION = getenv_bool(
    "PREFECT_WAIT_FOR_COMPLETION", not RUN_FOREVER
)
WAIT_TIMEOUT = int(os.getenv("PREFECT_WAIT_TIMEOUT_SECONDS", "0"))
WAIT_POLL_INTERVAL = int(os.getenv("PREFECT_WAIT_POLL_SECONDS", "30"))
ACTIVE_STATE_TYPES = [
    state.strip().upper()
    for state in os.getenv(
        "PREFECT_ACTIVE_STATE_TYPES", "PENDING,RUNNING"
    ).split(",")
    if state.strip()
]
AUTO_PAUSE = getenv_bool("PREFECT_AUTO_PAUSE", not RUN_FOREVER)
REPOSITORY_URL = os.getenv(
    "PREFECT_WORKER_REPOSITORY", "https://github.com/monuit/truecivic.git"
)
REPOSITORY_BRANCH = os.getenv("PREFECT_WORKER_BRANCH", "main")
VERIFY_REPOSITORY = getenv_bool("PREFECT_WORKER_VERIFY_REPOSITORY", True)
CODE_DIRECTORY = Path(
    os.getenv("TRUECIVIC_CODE_DIR", "/opt/truecivic")
).resolve()
os.environ["TRUECIVIC_CODE_DIR"] = str(CODE_DIRECTORY)
INSTALL_REQUIREMENTS = getenv_bool("TRUECIVIC_INSTALL_REQUIREMENTS", True)
REQUIREMENTS_FILE = os.getenv("TRUECIVIC_REQUIREMENTS_FILE", "requirements.txt")
INSTALL_EDITABLE = getenv_bool("TRUECIVIC_INSTALL_EDITABLE", False)
PRIMARY_DATABASE_URL = os.getenv("DATABASE_URL")
SECONDARY_DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")
PRIMARY_DATABASE_URL = os.getenv("DATABASE_URL")
SECONDARY_DATABASE_URL = os.getenv("DATABASE_PUBLIC_URL")


def _format_command(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def run(
    cmd: Sequence[str],
    *,
    context: str | None = None,
    cwd: Path | str | None = None,
    extra_env: Mapping[str, str] | None = None,
) -> None:
    """Run a subprocess command and log stdout/stderr output."""
    command_str = _format_command(cmd)
    if cwd:
        command_str = f"(cd {shlex.quote(str(cwd))}) {command_str}"
    if context:
        LOGGER.info("%s", context)
    LOGGER.info("Executing: %s", command_str)

    if extra_env:
        merged_env = os.environ.copy()
        merged_env.update(extra_env)
    else:
        merged_env = None

    try:
        result = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
        )
    except OSError as exc:
        LOGGER.exception("Failed to launch command: %s", command_str)
        raise RuntimeError(f"Unable to launch command: {command_str}") from exc

    if result.stdout:
        for line in result.stdout.splitlines():
            LOGGER.info("[stdout] %s", line)
    if result.stderr:
        for line in result.stderr.splitlines():
            LOGGER.error("[stderr] %s", line)

    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {command_str}")

    LOGGER.info("Command succeeded: %s", command_str)


def verify_repository_access() -> None:
    """Ensure the worker can reach the configured git repository before starting."""
    if not VERIFY_REPOSITORY:
        LOGGER.info("Skipping repository connectivity check.")
        return

    context = (
        f"Checking git repository reachability ({REPOSITORY_URL} @ {REPOSITORY_BRANCH})."
    )
    try:
        run(
            [
                "git",
                "ls-remote",
                "--heads",
                REPOSITORY_URL,
                REPOSITORY_BRANCH,
            ],
            context=context,
        )
    except RuntimeError:
        LOGGER.error(
            "Repository check failed; aborting worker start until connectivity is fixed."
        )
        raise


def sync_repository() -> None:
    """Clone or update the repository into CODE_DIRECTORY."""
    CODE_DIRECTORY.parent.mkdir(parents=True, exist_ok=True)

    if not CODE_DIRECTORY.exists():
        run(
            [
                "git",
                "clone",
                "--branch",
                REPOSITORY_BRANCH,
                "--depth",
                "1",
                REPOSITORY_URL,
                str(CODE_DIRECTORY),
            ],
            context=f"Cloning repository into {CODE_DIRECTORY}.",
        )
    else:
        run(
            ["git", "fetch", "--tags", "--prune", "--prune-tags"],
            context="Fetching latest changes.",
            cwd=CODE_DIRECTORY,
        )
        run(
            ["git", "reset", "--hard", f"origin/{REPOSITORY_BRANCH}"],
            context=f"Resetting repository to origin/{REPOSITORY_BRANCH}.",
            cwd=CODE_DIRECTORY,
        )
        run(
            ["git", "clean", "-fdx"],
            context="Removing untracked files after reset.",
            cwd=CODE_DIRECTORY,
        )

    run(
        ["git", "rev-parse", "HEAD"],
        context="Repository HEAD after sync.",
        cwd=CODE_DIRECTORY,
    )


def _resolve_database_url() -> str | None:
    primary = (PRIMARY_DATABASE_URL or "").strip()
    secondary = (SECONDARY_DATABASE_URL or "").strip()
    if primary:
        return primary
    if secondary:
        return secondary
    return None


def check_database_connectivity() -> None:
    """Attempt a simple connection to the configured database."""
    db_url = _resolve_database_url()
    if not db_url:
        LOGGER.warning("No DATABASE_URL or DATABASE_PUBLIC_URL available; skipping database connectivity check.")
        return
    try:
        import asyncpg  # type: ignore
    except Exception:
        LOGGER.info("asyncpg not installed; skipping database connectivity check.")
        return

    async def _ping() -> None:
        LOGGER.info("Checking database connectivity using configured URL.")
        conn = await asyncpg.connect(db_url, timeout=10)
        try:
            await conn.fetchval("SELECT 1")
        finally:
            await conn.close()

    try:
        asyncio.run(_ping())
        LOGGER.info("Database connectivity check succeeded.")
    except Exception as exc:
        LOGGER.exception("Database connectivity check failed: %s", exc)


def install_dependencies(python_exe: str) -> None:
    """Install project dependencies after syncing the repository."""
    if not INSTALL_REQUIREMENTS and not INSTALL_EDITABLE:
        LOGGER.info("Skipping dependency installation step.")
        return

    if INSTALL_REQUIREMENTS:
        requirements_path = CODE_DIRECTORY / REQUIREMENTS_FILE
        if requirements_path.exists():
            run(
                [
                    python_exe,
                    "-m",
                    "pip",
                    "install",
                    "--no-cache-dir",
                    "-r",
                    str(requirements_path),
                ],
                context=f"Installing requirements from {requirements_path}.",
                cwd=CODE_DIRECTORY,
            )
        else:
            LOGGER.warning(
                "Requested requirements installation but %s not found.",
                requirements_path,
            )

    if INSTALL_EDITABLE:
        run(
            [python_exe, "-m", "pip", "install", "--no-cache-dir", "-e", "."],
            context="Installing project in editable mode.",
            cwd=CODE_DIRECTORY,
        )


async def work_pool_has_active_runs() -> bool:
    """Return True if the work pool has flow runs in active states."""
    state_filter = FlowRunFilterState(
        type=FlowRunFilterStateType(any_=ACTIVE_STATE_TYPES)
    )
    flow_filter = FlowRunFilter(state=state_filter)

    async with get_client() as client:
        runs = await client.read_flow_runs(
            flow_run_filter=flow_filter,
            work_pool_filter=WorkPoolFilter(
                name=WorkPoolFilterName(any_=[POOL_NAME])
            ),
            limit=1,
        )
        return bool(runs)


def wait_for_pool_to_be_idle() -> None:
    """Block until the work pool has no active runs or timeout elapses."""
    if not WAIT_FOR_COMPLETION:
        return

    deadline = time.monotonic() + WAIT_TIMEOUT if WAIT_TIMEOUT > 0 else None

    while True:
        has_runs = asyncio.run(work_pool_has_active_runs())
        if not has_runs:
            LOGGER.info("Work pool idle; no active flow runs remaining.")
            return

        if deadline and time.monotonic() >= deadline:
            LOGGER.warning(
                "Timeout waiting for flow runs to finish after %s seconds.",
                WAIT_TIMEOUT,
            )
            return

        LOGGER.info(
            "Active flow runs detected. Sleeping %s seconds...", WAIT_POLL_INTERVAL
        )
        time.sleep(WAIT_POLL_INTERVAL)


def main() -> None:
    python_exe = sys.executable
    LOGGER.info(
        "Worker configuration pool=%s name=%s type=%s run_forever=%s prefetch=%s limit=%s auto_pause=%s",
        POOL_NAME,
        WORKER_NAME,
        WORKER_TYPE,
        RUN_FOREVER,
        PREFETCH_SECONDS,
        CONCURRENCY_LIMIT,
        AUTO_PAUSE,
    )
    if TRIGGER_DEPLOYMENTS:
        LOGGER.info("Triggering deployments: %s", ", ".join(TRIGGER_DEPLOYMENTS))

    # Prefer DATABASE_URL, fall back to DATABASE_PUBLIC_URL when present.
    if PRIMARY_DATABASE_URL:
        LOGGER.info("Detected DATABASE_URL; using it for flow execution.")
    elif SECONDARY_DATABASE_URL:
        os.environ["DATABASE_URL"] = SECONDARY_DATABASE_URL
        LOGGER.info(
            "DATABASE_URL not set. Falling back to DATABASE_PUBLIC_URL for flow execution."
        )
    else:
        LOGGER.warning(
            "No DATABASE_URL or DATABASE_PUBLIC_URL found in environment. "
            "Flows that access the database may fail."
        )

    verify_repository_access()
    sync_repository()
    install_dependencies(python_exe)
    check_database_connectivity()

    existing_pythonpath = os.environ.get("PYTHONPATH")
    new_pythonpath = (
        f"{CODE_DIRECTORY}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(CODE_DIRECTORY)
    )
    os.environ["PYTHONPATH"] = new_pythonpath
    LOGGER.info("PYTHONPATH set to %s", new_pythonpath)

    run(
        [python_exe, "-m", "prefect", "work-pool", "resume", POOL_NAME],
        context="Resuming work pool prior to worker start.",
    )

    if TRIGGER_DEPLOYMENTS:
        for deployment in TRIGGER_DEPLOYMENTS:
            run(
                [
                    python_exe,
                    "-m",
                    "prefect",
                    "deployment",
                    "run",
                    deployment,
                ],
                context=f"Triggering deployment {deployment}",
            )

    worker_cmd = [
        python_exe,
        "-m",
        "prefect",
        "worker",
        "start",
        "--pool",
        POOL_NAME,
        "--type",
        WORKER_TYPE,
        "--name",
        WORKER_NAME,
        "--prefetch-seconds",
        PREFETCH_SECONDS,
        "--limit",
        CONCURRENCY_LIMIT,
    ]
    if not RUN_FOREVER:
        worker_cmd.insert(worker_cmd.index("--prefetch-seconds"), "--run-once")

    try:
        run(worker_cmd, context="Starting Prefect worker.")
        wait_for_pool_to_be_idle()
    finally:
        if AUTO_PAUSE:
            run(
                [python_exe, "-m", "prefect", "work-pool", "pause", POOL_NAME],
                context="Pausing work pool after worker cycle.",
            )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.exception("Prefect worker cycle failed: %s", exc)
        sys.exit(1)
