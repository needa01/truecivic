#!/usr/bin/env python3
"""
Utility to resume a Prefect work pool, start a run-once worker, then pause the pool.

Intended for automation environments (Railway cron, GitHub Actions, Task Scheduler)
to avoid keeping the worker online between batches.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence

POOL_NAME = os.getenv("PREFECT_WORK_POOL", "default-agent-pool")
WORKER_NAME = os.getenv("PREFECT_WORKER_NAME", "scheduled-default-agent")
WORKER_TYPE = os.getenv("PREFECT_WORKER_TYPE", "process")
PREFETCH_SECONDS = os.getenv("PREFECT_WORKER_PREFETCH_SECONDS", "120")
CONCURRENCY_LIMIT = os.getenv("PREFECT_WORKER_FLOW_LIMIT", "5")


def run(cmd: Sequence[str]) -> None:
    """Run a subprocess command with inherited stdio."""
    print(">>", " ".join(cmd), flush=True)
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(cmd)}")


def main() -> None:
    python_exe = sys.executable

    run([python_exe, "-m", "prefect", "work-pool", "resume", POOL_NAME])

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
    finally:
        run([python_exe, "-m", "prefect", "work-pool", "pause", POOL_NAME])


if __name__ == "__main__":
    main()
