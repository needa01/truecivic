"""
Utility to resume a Prefect work pool, start a run-once worker, then pause the pool.

This copy lives next to the Railway Dockerfile so the build context stays self-contained
while sharing the same behaviour as scripts/prefect_worker_cycle.py.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from typing import Sequence

from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterState,
    FlowRunFilterStateType,
    WorkPoolFilter,
    WorkPoolFilterName,
)

POOL_NAME = os.getenv("PREFECT_WORK_POOL", "default-agent-pool")
WORKER_NAME = os.getenv("PREFECT_WORKER_NAME", "scheduled-default-agent")
WORKER_TYPE = os.getenv("PREFECT_WORKER_TYPE", "process")
PREFETCH_SECONDS = os.getenv("PREFECT_WORKER_PREFETCH_SECONDS", "120")
CONCURRENCY_LIMIT = os.getenv("PREFECT_WORKER_FLOW_LIMIT", "5")
TRIGGER_DEPLOYMENTS = [
    part.strip()
    for part in os.getenv("PREFECT_TRIGGER_DEPLOYMENTS", "").split(",")
    if part.strip()
]
WAIT_FOR_COMPLETION = (
    os.getenv("PREFECT_WAIT_FOR_COMPLETION", "true").lower() != "false"
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
AUTO_PAUSE = os.getenv("PREFECT_AUTO_PAUSE", "true").lower() != "false"


def run(cmd: Sequence[str]) -> None:
    """Run a subprocess command with inherited stdio."""
    print(">>", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


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
            print(">> Work pool idle; no active flow runs remaining.", flush=True)
            return

        if deadline and time.monotonic() >= deadline:
            print(">> Timeout waiting for flow runs to finish.", flush=True)
            return

        print(
            f">> Active flow runs detected. Sleeping {WAIT_POLL_INTERVAL} seconds...",
            flush=True,
        )
        time.sleep(WAIT_POLL_INTERVAL)


def main() -> None:
    python_exe = sys.executable

    run([python_exe, "-m", "prefect", "work-pool", "resume", POOL_NAME])

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
                ]
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
        "--run-once",
        "--prefetch-seconds",
        PREFETCH_SECONDS,
        "--limit",
        CONCURRENCY_LIMIT,
    ]

    try:
        run(worker_cmd)
        wait_for_pool_to_be_idle()
    finally:
        if AUTO_PAUSE:
            run([python_exe, "-m", "prefect", "work-pool", "pause", POOL_NAME])


if __name__ == "__main__":
    main()
