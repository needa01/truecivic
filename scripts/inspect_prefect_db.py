"""Utility to inspect Prefect database metadata."""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Iterable

import asyncpg
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
COLUMN_CACHE: dict[tuple[str, tuple[str, ...]], str] = {}


async def resolve_column_name(
    conn: asyncpg.Connection, table: str, candidates: Iterable[str]
) -> str:
    """Return the first column in *candidates* that exists on *table*."""

    cache_key = (table, tuple(candidates))
    if cache_key in COLUMN_CACHE:
        return COLUMN_CACHE[cache_key]

    rows = await conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        """,
        table,
    )
    available = {row["column_name"] for row in rows}

    for candidate in candidates:
        if candidate in available:
            COLUMN_CACHE[cache_key] = candidate
            return candidate

    raise RuntimeError(
        f"None of the candidate columns {candidates} exist on table '{table}'."
    )


def load_env(env: str | None) -> None:
    env = (env or "production").lower()
    candidates = {
        "production": [ROOT_DIR / ".env.production"],
        "local": [ROOT_DIR / ".env.local", ROOT_DIR / ".env"],
    }

    for path in candidates.get(env, []) + [ROOT_DIR / ".env"]:
        if path.exists():
            load_dotenv(path)
            return

    load_dotenv()


def normalize_connection(url: str) -> str:
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "")
    return url


async def list_tables(conn: asyncpg.Connection) -> Iterable[str]:
    rows = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """
    )
    return [row["table_name"] for row in rows]


async def resolve_flow_ids(conn: asyncpg.Connection, name_filter: str | None) -> list[str]:
    if not name_filter:
        return []

    rows = await conn.fetch(
        """
        SELECT id
        FROM flow
        WHERE name ILIKE $1
        ORDER BY created DESC
        """,
        name_filter,
    )
    return [row["id"] for row in rows]


async def fetch_child_flow_runs(conn: asyncpg.Connection, task_run_id: str) -> list[dict[str, object]]:
    rows = await conn.fetch(
        """
        SELECT id, name, state_type, state_name, start_time, end_time
        FROM flow_run
        WHERE parent_task_run_id = $1
        ORDER BY start_time DESC NULLS LAST
        """,
        task_run_id,
    )
    return [dict(row) for row in rows]


async def print_task_runs(conn: asyncpg.Connection, flow_run_id: str, depth: int = 0, max_depth: int = 1) -> None:
    rows = await conn.fetch(
        """
        SELECT tr.id,
               tr.name,
               tr.task_key,
               tr.state_type,
               tr.state_name,
               trs.timestamp,
               trs.message
        FROM task_run tr
        LEFT JOIN LATERAL (
            SELECT task_run_id, timestamp, message
            FROM task_run_state
            WHERE task_run_id = tr.id
            ORDER BY timestamp DESC
            LIMIT 1
        ) AS trs ON TRUE
        WHERE tr.flow_run_id = $1
        ORDER BY tr.created DESC
        """,
        flow_run_id,
    )

    if not rows:
        print("No task runs found for flow run", flow_run_id)
        return

    indent = "  " * depth
    print(f"{indent}Task runs:")
    for row in rows:
        log_excerpt = ""
        if row["state_type"] == "FAILED":
            logs = await conn.fetch(
                """
                SELECT message, timestamp
                FROM log
                WHERE task_run_id = $1
                ORDER BY timestamp DESC
                LIMIT 3
                """,
                row["id"],
            )
            if logs:
                latest_log = logs[0]["message"] or ""
                log_excerpt = latest_log.split("\n")[0][:160]

        line = (
            f"{indent}- {row['name']} (id={row['id']}, key={row['task_key']}, "
            f"state={row['state_type']}/{row['state_name']}, latest={row['timestamp']}, "
            f"message={(row['message'] or '').split('\n')[0]})"
        )
        if log_excerpt:
            line += f"\n{indent}    log: {log_excerpt}"
        print(line)

        if depth + 1 <= max_depth:
            child_runs = await fetch_child_flow_runs(conn, row["id"])
            for child in child_runs:
                print(
                    f"{indent}  ↳ Subflow {child['name']} (id={child['id']}, "
                    f"state={child['state_type']}/{child['state_name']}, "
                    f"start={child['start_time']}, end={child['end_time']})"
                )
                await print_task_runs(conn, child["id"], depth + 1, max_depth)


async def print_task_run_details(conn: asyncpg.Connection, task_run_id: str) -> None:
    print(f"\nTask run details for {task_run_id}:")
    state_type_column = await resolve_column_name(conn, "task_run_state", ("state_type", "type"))
    state_name_column = await resolve_column_name(conn, "task_run_state", ("state_name", "name"))
    states = await conn.fetch(
        f"""
        SELECT {state_type_column} AS state_type,
               {state_name_column} AS state_name,
               timestamp,
               message
        FROM task_run_state
        WHERE task_run_id = $1
        ORDER BY timestamp
        """,
        task_run_id,
    )
    for state in states:
        print(
            f"- {state['timestamp']} {state['state_type']}/{state['state_name']}: "
            f"{(state['message'] or '').split('\n')[0]}"
        )

    logs = await conn.fetch(
        """
        SELECT level, timestamp, message
        FROM log
        WHERE task_run_id = $1
        ORDER BY timestamp
        LIMIT 20
        """,
        task_run_id,
    )
    if logs:
        print("\nLog excerpts:")
        for entry in logs:
            msg = (entry["message"] or "").replace("\r", " ").replace("\n", " ")
            print(f"- {entry['timestamp']} [{entry['level']}] {msg}")
    else:
        print("\nNo logs recorded for this task run.")

    error_logs = await conn.fetch(
        """
        SELECT level, timestamp, message
        FROM log
        WHERE task_run_id = $1 AND level >= 30
        ORDER BY timestamp DESC
        LIMIT 5
        """,
        task_run_id,
    )
    if error_logs:
        print("\nRecent error logs (latest first):")
        for entry in error_logs:
            msg = (entry["message"] or "").replace("\r", " ").replace("\n", " ")
            print(f"- {entry['timestamp']} [{entry['level']}] {msg}")


async def main(
    env: str | None,
    limit: int,
    flow_run_id: str | None,
    flow_name: str | None,
    max_depth: int,
    task_run_id: str | None,
) -> None:
    load_env(env)
    url = os.getenv("PREFECT_API_DATABASE_CONNECTION_URL")
    if not url:
        raise RuntimeError("PREFECT_API_DATABASE_CONNECTION_URL is not set")

    conn = await asyncpg.connect(normalize_connection(url))

    try:
        tables = await list_tables(conn)
        print("Tables available:")
        for name in tables:
            print(f"  - {name}")

        print("\nRecent flow runs:")
        flow_ids = await resolve_flow_ids(conn, flow_name)

        if flow_name and not flow_ids:
            print(f"No flows found matching name filter '{flow_name}'.")
            return

        base_query = (
            "SELECT id, name, flow_id, state_type, state_name, created, updated, start_time, end_time "
            "FROM flow_run"
        )
        params: list[object] = [limit]

        if flow_ids:
            base_query += " WHERE flow_id = ANY($2)"
            params.append(flow_ids)

        base_query += " ORDER BY created DESC LIMIT $1"

        rows = await conn.fetch(base_query, *params)
        chosen_flow_run_id = flow_run_id or (rows[0]["id"] if rows else None)
        for idx, row in enumerate(rows, start=1):
            print(
                f"{idx}. {row['name']} (id={row['id']}, state={row['state_type']}/{row['state_name']}, "
                f"created={row['created']}, start={row['start_time']}, end={row['end_time']})"
            )

        if chosen_flow_run_id:
            print("\nInspecting task runs for:", chosen_flow_run_id)
            await print_task_runs(conn, chosen_flow_run_id, max_depth=max_depth)
        else:
            print("No flow runs available to inspect.")

        if task_run_id:
            await print_task_run_details(conn, task_run_id)
    finally:
        await conn.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect Prefect DB")
    parser.add_argument("--env", default="production", choices=("production", "local"))
    parser.add_argument("--limit", type=int, default=10, help="Number of flow runs to list")
    parser.add_argument("--flow-run-id", help="Specific flow run ID to inspect")
    parser.add_argument("--flow-name", help="Filter flow runs by flow name (supports SQL ILIKE wildcards)")
    parser.add_argument("--max-depth", type=int, default=1, help="Depth of subflow traversal")
    parser.add_argument("--task-run-id", help="Print state history and logs for a specific task run")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        main(
            args.env,
            args.limit,
            args.flow_run_id,
            args.flow_name,
            args.max_depth,
            args.task_run_id,
        )
    )
