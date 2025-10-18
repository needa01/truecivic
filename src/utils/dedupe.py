"""
Utility helpers for deduplicating ETL records.

Responsibility: Provide reusable utilities to drop duplicate records by a key
function and capture statistics about removed duplicates.
"""

from __future__ import annotations

from typing import Callable, Iterable, List, Tuple, TypeVar

T = TypeVar("T")
K = TypeVar("K")


def dedupe_by_key(
    records: Iterable[T],
    key_fn: Callable[[T], K],
) -> Tuple[List[T], int]:
    """
    Remove duplicate records using a key function.

    Args:
        records: Iterable of records to deduplicate.
        key_fn: Function used to compute the deduplication key.

    Returns:
        Tuple of (unique_records, duplicate_count).
    """
    seen: dict[K, T] = {}
    duplicates = 0

    for record in records:
        key = key_fn(record)
        if key is None:
            continue
        if key in seen:
            duplicates += 1
            continue
        seen[key] = record

    return list(seen.values()), duplicates
