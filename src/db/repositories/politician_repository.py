"""
Repository for politician database operations.

Handles CRUD operations and efficient batch upserts for politicians sourced
from external APIs (OpenParliament, OurCommons, etc.).

Responsibility: Data access layer for the ``politicians`` table.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.sql import Select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import PoliticianModel

logger = logging.getLogger(__name__)


def _parse_datetime(value: Any) -> datetime:
    """
    Best-effort conversion to ``datetime``.

    The OpenParliament adapter emits ISO8601 strings. We normalise everything
    to ``datetime`` objects before persisting.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            logger.debug("Unable to parse datetime string %s", value)
    return datetime.utcnow()


class PoliticianRepository:
    """Repository encapsulating persistence for ``PoliticianModel`` records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, politician_id: int) -> Optional[PoliticianModel]:
        """Fetch a single politician by primary key."""
        stmt: Select[PoliticianModel] = select(PoliticianModel).where(
            PoliticianModel.id == politician_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 50) -> List[PoliticianModel]:
        """Return the most recently updated politician records."""
        stmt: Select[PoliticianModel] = (
            select(PoliticianModel)
            .order_by(PoliticianModel.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure payload conforms to ORM requirements."""
        data = dict(payload)

        if "id" not in data or data["id"] is None:
            raise ValueError("politician payload missing required 'id'")

        # Core name fields
        data.setdefault("name", data.get("display_name") or "")

        # Ensure JSON serialisable structures
        if "memberships" in data and data["memberships"] is None:
            data["memberships"] = []

        last_fetched = data.get("last_fetched_at") or data.get("fetched_at")
        data["last_fetched_at"] = _parse_datetime(last_fetched)

        # Remove transient ingestion-only keys that do not map to ORM columns.
        data.pop("fetched_at", None)
        data.pop("source", None)

        now = datetime.utcnow()
        data.setdefault("created_at", now)
        data["updated_at"] = now

        return data

    async def upsert(self, payload: Dict[str, Any]) -> PoliticianModel:
        """Insert or update a single politician record."""
        normalized = await self._normalize_payload(payload)
        politician_id: int = int(normalized["id"])

        existing = await self.get_by_id(politician_id)
        if existing:
            for key, value in normalized.items():
                if key in {"id", "created_at"}:
                    continue
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await self.session.flush()
            logger.debug("Updated politician %s", politician_id)
            return existing

        model = PoliticianModel(**normalized)
        self.session.add(model)
        await self.session.flush()
        logger.debug("Inserted politician %s", politician_id)
        return model

    async def upsert_many(self, payloads: Iterable[Dict[str, Any]]) -> List[PoliticianModel]:
        """
        Efficiently upsert a list of politician dictionaries.

        Uses ``ON CONFLICT`` when backed by PostgreSQL. Falls back to per-row
        upserts otherwise.
        """
        payload_list = [await self._normalize_payload(item) for item in payloads]
        if not payload_list:
            return []

        try:
            dialect = self.session.bind.dialect.name  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - fallback for tests
            dialect = "sqlite"

        if dialect == "postgresql":
            stmt = pg_insert(PoliticianModel).values(payload_list)
            update_columns = {
                "name": stmt.excluded.name,
                "given_name": stmt.excluded.given_name,
                "family_name": stmt.excluded.family_name,
                "gender": stmt.excluded.gender,
                "email": stmt.excluded.email,
                "image_url": stmt.excluded.image_url,
                "current_party": stmt.excluded.current_party,
                "current_riding": stmt.excluded.current_riding,
                "current_role": stmt.excluded.current_role,
                "memberships": stmt.excluded.memberships,
                "parl_mp_id": stmt.excluded.parl_mp_id,
                "last_fetched_at": stmt.excluded.last_fetched_at,
                "updated_at": stmt.excluded.updated_at,
            }
            stmt = stmt.on_conflict_do_update(
                index_elements=[PoliticianModel.id],
                set_=update_columns,
            )
            await self.session.execute(stmt)
            await self.session.flush()

            ids = [int(item["id"]) for item in payload_list]
            stmt_fetch = select(PoliticianModel).where(
                PoliticianModel.id.in_(ids)
            )
            result = await self.session.execute(stmt_fetch)
            models = list(result.scalars().all())
            logger.info("Upserted %s politician records (bulk)", len(models))
            return models

        # Fallback path: sequential upserts
        models: List[PoliticianModel] = []
        for payload in payload_list:
            model = await self.upsert(payload)
            models.append(model)

        logger.info("Upserted %s politician records (sequential)", len(models))
        return models
