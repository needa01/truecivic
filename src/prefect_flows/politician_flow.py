"""
Prefect flow for ingesting politician data.

Fetches politician records from OpenParliament and persists them using the
PoliticianRepository.
"""



from __future__ import annotations

try:
    from .create_github_storage import github_block
except Exception as e:
    print("GitHub storage block not created yet:", e)
    
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from prefect import flow, task, get_run_logger

from src.db.session import async_session_factory
from src.db.repositories.politician_repository import PoliticianRepository

logger = logging.getLogger(__name__)

API_BASE = "https://api.openparliament.ca"


def _extract_numeric_id(detail: Dict[str, Any]) -> Optional[int]:
    related = detail.get("related") or {}
    activity_url = related.get("activity_rss_url")
    if not activity_url:
        return None
    parts = activity_url.strip("/").split("/")
    for part in reversed(parts):
        if part.isdigit():
            return int(part)
    return None


def _transform_politician(detail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    politician_id = _extract_numeric_id(detail)
    if politician_id is None:
        return None

    memberships_raw = detail.get("memberships") or []
    memberships: List[Dict[str, Any]] = []
    current_membership: Optional[Dict[str, Any]] = None

    for membership in memberships_raw:
        normalized_membership = {
            "party": membership.get("party", {}).get("short_name", {}).get("en"),
            "party_full": membership.get("party", {}).get("name", {}).get("en"),
            "riding": membership.get("riding", {}).get("name", {}).get("en"),
            "riding_province": membership.get("riding", {}).get("province"),
            "start_date": membership.get("start_date"),
            "end_date": membership.get("end_date"),
        }
        memberships.append(normalized_membership)
        if membership.get("end_date") is None:
            current_membership = membership

    other_info = detail.get("other_info") or {}
    parl_mp_ids = other_info.get("parl_mp_id") or []

    current_party = None
    current_riding = None
    if current_membership:
        current_party = current_membership.get("party", {}).get("short_name", {}).get("en")
        current_riding = current_membership.get("riding", {}).get("name", {}).get("en")

    return {
        "id": politician_id,
        "name": detail.get("name"),
        "given_name": detail.get("given_name"),
        "family_name": detail.get("family_name"),
        "gender": detail.get("gender"),
        "email": detail.get("email"),
        "image_url": detail.get("image"),
        "current_party": current_party,
        "current_riding": current_riding,
        "current_role": None,
        "memberships": memberships,
        "parl_mp_id": parl_mp_ids[0] if parl_mp_ids else None,
        "source": "openparliament_politicians",
        "fetched_at": datetime.utcnow().isoformat(),
    }


async def _fetch_politician_detail(client: httpx.AsyncClient, slug: str) -> Optional[Dict[str, Any]]:
    url = f"{API_BASE}/politicians/{slug}/"
    try:
        response = await client.get(url, params={"format": "json"})
        response.raise_for_status()
        detail = response.json()
        return _transform_politician(detail)
    except Exception as exc:  # pragma: no cover - logged in task
        logger.warning("Failed to fetch details for politician %s: %s", slug, exc)
        return None


@task(name="fetch_politicians", retries=2, retry_delay_seconds=30)
async def fetch_politicians_task(
    limit: int = 200,
    current_only: bool = True,
) -> List[Dict[str, Any]]:
    """
    Fetch politician records from OpenParliament.
    """
    logger_task = get_run_logger()
    logger_task.info("Fetching up to %s politicians (current_only=%s)", limit, current_only)

    slugs: List[str] = []
    url = f"{API_BASE}/politicians/"
    params: Dict[str, Any] = {
        "format": "json",
        "limit": min(limit, 100),
    }
    if current_only:
        params["current"] = "true"

    async with httpx.AsyncClient(timeout=30.0) as client:
        while url and len(slugs) < limit:
            response = await client.get(url, params=params if params else None)
            response.raise_for_status()
            payload = response.json()

            for obj in payload.get("objects", []):
                slug = (obj.get("url") or "").strip("/").split("/")[-1]
                if slug:
                    slugs.append(slug)
                if len(slugs) >= limit:
                    break

            next_url = payload.get("pagination", {}).get("next_url")
            if next_url and len(slugs) < limit:
                url = f"{API_BASE}{next_url}" if next_url.startswith("/") else next_url
                params = None
            else:
                url = None

        results: List[Dict[str, Any]] = []
        semaphore = asyncio.Semaphore(10)

        async def _fetch_with_limit(slug: str) -> Optional[Dict[str, Any]]:
            async with semaphore:
                return await _fetch_politician_detail(client, slug)

        detail_tasks = [_fetch_with_limit(slug) for slug in slugs]
        for detail in await asyncio.gather(*detail_tasks):
            if detail:
                results.append(detail)

    logger_task.info("Fetched %s politician records", len(results))
    return results


@task(name="store_politicians", retries=1)
async def store_politicians_task(politicians: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Persist politician records using the repository.
    """
    logger_task = get_run_logger()
    if not politicians:
        logger_task.info("No politicians to store")
        return {"stored": 0}

    try:
        async with async_session_factory() as session:
            repo = PoliticianRepository(session)
            stored = await repo.upsert_many(politicians)
            await session.commit()

        result = {"stored": len(stored)}
        logger_task.info("Stored %s politicians", result["stored"])
        return result
    except Exception as exc:
        logger_task.error("Error storing politicians: %s", exc, exc_info=True)
        return {"stored": 0, "error": str(exc)}


@flow(name="fetch_politicians_flow")
async def fetch_politicians_flow(
    limit: int = 200,
    current_only: bool = True,
) -> Dict[str, Any]:
    """
    Flow to fetch and store politician records.
    """
    logger.info("Starting politician ingestion flow (limit=%s, current_only=%s)", limit, current_only)
    records = await fetch_politicians_task(limit=limit, current_only=current_only)
    store_result = await store_politicians_task(records)
    result = {
        "fetched": len(records),
        **store_result,
    }
    logger.info("Completed politician ingestion flow: %s", result)
    return result


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(fetch_politicians_flow(limit=25))
