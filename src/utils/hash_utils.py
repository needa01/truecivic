"""Utility helpers for generating deterministic content hashes.

Provides stable hashing for domain models to support deduplication
and change detection during ETL processes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Iterable, TypeVar

from ..models.bill import Bill

# Fields that should not influence bill content hashing because they
# represent volatile metadata captured during each fetch cycle.
_BILL_HASH_EXCLUDE_FIELDS: set[str] = {
    "last_fetched_at",
    "last_enriched_at",
}


def _normalized_json(payload: Any) -> str:
    """Serialize payload to a deterministic JSON string."""
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def calculate_hash(payload: Any) -> str:
    """Produce a SHA-256 hash for the given payload."""
    normalized = _normalized_json(payload)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_bill_hash(bill: Bill) -> str:
    """Compute a deterministic content hash for a bill record."""
    payload = bill.model_dump(mode="json", exclude=_BILL_HASH_EXCLUDE_FIELDS)
    return calculate_hash(payload)


T = TypeVar("T")


def deduplicate_by_hash(items: Iterable[T], hash_func: Callable[[T], str]) -> tuple[list[T], int]:
    """Remove duplicates from an iterable using the provided hash function."""
    seen_hashes: set[str] = set()
    unique_items: list[T] = []
    duplicates = 0

    for item in items:
        item_hash = hash_func(item)
        if item_hash in seen_hashes:
            duplicates += 1
            continue
        seen_hashes.add(item_hash)
        unique_items.append(item)

    return unique_items, duplicates
