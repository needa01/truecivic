"""
Repository for debate database operations.

Persists Hansard debate metadata fetched from OpenParliament / OurCommons.

Responsibility: Data access layer for the ``debates`` table.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import and_, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import DebateModel

logger = logging.getLogger(__name__)


def _parse_parliament_session(value: Any) -> tuple[Optional[int], Optional[int]]:
    """
    Accept values like ``"45-1"`` or ``{"parliament": 45, "session": 1}``.
    Returns a tuple of integers (parliament, session).
    """
    if isinstance(value, dict):
        return value.get("parliament"), value.get("session")

    if isinstance(value, str) and "-" in value:
        parts = value.split("-", 1)
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None, None

    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return int(value[0]), int(value[1])
        except (ValueError, TypeError):
            return None, None

    return None, None


def _parse_date(value: Any) -> Optional[datetime]:
    """Convert date strings to ``datetime`` (UTC midnight)."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                return None
    return None


class DebateRepository:
    """Repository handling persistence for ``DebateModel`` records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_natural_key(
        self,
        *,
        jurisdiction: str,
        hansard_id: str,
    ) -> Optional[DebateModel]:
        """Fetch a debate by its natural key."""
        stmt = select(DebateModel).where(
            and_(
                DebateModel.jurisdiction == jurisdiction,
                DebateModel.hansard_id == hansard_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, debate_id: int) -> Optional[DebateModel]:
        """Fetch a debate by database identifier."""
        stmt = select(DebateModel).where(DebateModel.id == debate_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 25) -> List[DebateModel]:
        """Return debates ordered by newest sitting date."""
        stmt = (
            select(DebateModel)
            .order_by(DebateModel.sitting_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure payload contains all required fields for persistence."""
        data = dict(payload)

        hansard_id = data.get("hansard_id") or data.get("source_id") or data.get("id")
        if not hansard_id:
            raise ValueError("debate payload missing hansard_id/source_id")
        data["hansard_id"] = str(hansard_id)

        jurisdiction = data.get("jurisdiction") or "ca"
        data["jurisdiction"] = jurisdiction

        parliament, session = _parse_parliament_session(
            data.get("session") or data.get("parliament_session")
        )

        if data.get("parliament") is None:
            data["parliament"] = parliament
        if data.get("session") is None or isinstance(data.get("session"), str):
            data["session"] = session

        if data.get("parliament") is None or data.get("session") is None:
            raise ValueError("debate payload missing parliament/session numbers")

        sitting_date = _parse_date(data.get("sitting_date") or data.get("date"))
        if not sitting_date:
            raise ValueError("debate payload missing valid sitting_date")
        data["sitting_date"] = sitting_date

        data["chamber"] = data.get("chamber") or "House of Commons"
        data["debate_type"] = data.get("debate_type") or data.get("document_type")

        # Persist the OpenParliament document path for downstream mapping.
        source_url = data.pop("source_url", None)
        document_path = data.get("url")
        if document_path:
            data["document_url"] = document_path
        elif not data.get("document_url") and source_url:
            data["document_url"] = source_url

        timestamp = datetime.utcnow()
        data.setdefault("created_at", timestamp)
        data["updated_at"] = timestamp

        allowed_fields = {
            "jurisdiction",
            "hansard_id",
            "parliament",
            "session",
            "sitting_date",
            "chamber",
            "debate_type",
            "document_url",
            "created_at",
            "updated_at",
        }

        normalized: Dict[str, Any] = {
            key: data[key]
            for key in allowed_fields
            if key in data and data[key] is not None
        }

        required_fields = {
            "jurisdiction",
            "hansard_id",
            "parliament",
            "session",
            "sitting_date",
            "chamber",
            "created_at",
            "updated_at",
        }
        missing_required = required_fields - normalized.keys()
        if missing_required:
            raise ValueError(
                "debate payload missing required fields after normalization: "
                + ", ".join(sorted(missing_required))
            )

        return normalized

    async def map_document_urls(
        self,
        urls: Iterable[str],
        jurisdiction: str = "ca",
    ) -> Dict[str, DebateModel]:
        """Return a mapping of document_url -> DebateModel for provided URLs."""
        url_list = [u for u in set(urls) if u]
        if not url_list:
            return {}

        stmt = select(DebateModel).where(
            and_(
                DebateModel.document_url.in_(url_list),
                DebateModel.jurisdiction == jurisdiction,
            )
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return {model.document_url: model for model in models if model.document_url}

    async def upsert(self, payload: Dict[str, Any]) -> DebateModel:
        """Insert or update a single debate record."""
        normalized = await self._normalize_payload(payload)

        existing = await self.get_by_natural_key(
            jurisdiction=normalized["jurisdiction"],
            hansard_id=normalized["hansard_id"],
        )
        if existing:
            for key, value in normalized.items():
                if key in {"id", "created_at"}:
                    continue
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await self.session.flush()
            return existing

        model = DebateModel(**normalized)
        self.session.add(model)
        await self.session.flush()
        return model

    async def upsert_many(self, payloads: Iterable[Dict[str, Any]]) -> List[DebateModel]:
        """
        Batch upsert debates using ``ON CONFLICT`` on PostgreSQL.

        Falls back to sequential upserts when necessary (e.g., SQLite tests).
        """
        normalized_payloads = [
            await self._normalize_payload(item) for item in payloads
        ]
        if not normalized_payloads:
            return []

        try:
            dialect = self.session.bind.dialect.name  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - unit tests
            dialect = "sqlite"

        if dialect == "postgresql":
            stmt = pg_insert(DebateModel).values(normalized_payloads)
            stmt = stmt.on_conflict_do_update(
                index_elements=[DebateModel.jurisdiction, DebateModel.hansard_id],
                set_={
                    "parliament": stmt.excluded.parliament,
                    "session": stmt.excluded.session,
                    "sitting_date": stmt.excluded.sitting_date,
                    "chamber": stmt.excluded.chamber,
                    "debate_type": stmt.excluded.debate_type,
                    "document_url": stmt.excluded.document_url,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            await self.session.execute(stmt)
            await self.session.flush()

            keys = [
                (item["jurisdiction"], item["hansard_id"])
                for item in normalized_payloads
            ]
            stmt_fetch = select(DebateModel).where(
                tuple_(DebateModel.jurisdiction, DebateModel.hansard_id).in_(keys)  # type: ignore[name-defined]
            )
            result = await self.session.execute(stmt_fetch)
            models = list(result.scalars().all())
            logger.info("Upserted %s debates (bulk)", len(models))
            return models

        # Fallback path
        models: List[DebateModel] = []
        for payload in normalized_payloads:
            models.append(await self.upsert(payload))

        logger.info("Upserted %s debates (sequential)", len(models))
        return models
