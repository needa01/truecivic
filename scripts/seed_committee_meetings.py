"""Seed real committee meetings from the OpenParliament API.

This script loads production configuration from `.env.production`, downloads
committee metadata and meeting records from the public OpenParliament API, and
stores them in the project database. It is safe to re-run; existing committee
and meeting records will be preserved.

Environment variables:
- SEED_COMMITTEE_SLUGS: Comma-separated list of committee slugs to ingest
    (default: "environment").
- SEED_MEETING_COUNT: Maximum number of recent meetings to fetch per committee
    (default: "5").
- SEED_COMMITTEE_JURISDICTION: Jurisdiction assigned to stored committees
    (default: "ca-federal").

Usage (from project root):

        python scripts/seed_committee_meetings.py

"""

from __future__ import annotations

import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests import HTTPError, RequestException

from sqlalchemy import MetaData, Table, create_engine, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Lazy import dotenv so the script works even if python-dotenv isn't installed
try:  # pragma: no cover - optional dependency
    from dotenv import load_dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback loader
    def load_dotenv(path: Path | str, override: bool = False) -> None:
        path_obj = Path(path)
        if not path_obj.exists():
            return

        for raw_line in path_obj.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if not override and key in os.environ:
                continue

            os.environ[key] = value


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Ensure the project source directory is importable when running as a script.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.utils.committee_registry import build_committee_identifier, resolve_source_slug
ENV_FILE = PROJECT_ROOT / ".env.production"
API_BASE = "https://api.openparliament.ca"
WEB_BASE = "https://openparliament.ca"
SESSION_PATTERN = re.compile(r"(?P<parliament>\d+)-(?P<session>\d+)")
MEETING_URL_PATTERN = re.compile(r"/[^/]+/(?P<parliament>\d+)-(?P<session>\d+)/(?:\d+)/?$")


# MARK: environment helpers -------------------------------------------------


def load_environment() -> None:
    """Load environment variables from the production .env file."""
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=True)
    else:  # pragma: no cover - safety log
        raise FileNotFoundError(f"Environment file not found: {ENV_FILE}")


def resolve_database_url() -> str:
    """Resolve the synchronous PostgreSQL connection string."""
    raw_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("DATABASE_PUBLIC_URL or DATABASE_URL must be set")

    # Ensure sync driver for SQLAlchemy engine
    url = raw_url.replace("+asyncpg", "+psycopg")
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def naive_utc_now() -> datetime:
    """Return a timezone-naive UTC timestamp for legacy columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def clear_tls_env() -> None:
    """Remove TLS bundle overrides that interfere with requests."""
    for key in ("REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE"):
        if key in os.environ:
            os.environ.pop(key)


# MARK: API helpers --------------------------------------------------------

def fetch_json(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fetch JSON from the given URL, forcing `format=json`."""
    query: Dict[str, Any] = {"format": "json"}
    if params:
        query.update(params)

    response = requests.get(url, params=query, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_committee_metadata(slug: str) -> Dict[str, Any]:
    """Retrieve committee metadata for a given slug."""
    return fetch_json(f"{API_BASE}/committees/{slug}")


def fetch_meeting_summaries(slug: str, limit: int) -> List[Dict[str, Any]]:
    """Retrieve recent meeting summaries for a committee slug."""
    data = fetch_json(
        f"{API_BASE}/committees/meetings/",
        {"committee": slug, "limit": max(1, limit)},
    )
    return data.get("objects", [])


def fetch_meeting_detail(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieve detailed meeting information for a summary record."""
    meeting_path = (summary.get("url") or "").rstrip("/")
    if not meeting_path:
        return {}
    return fetch_json(f"{API_BASE}{meeting_path}")


def parse_session_parts(session_value: Optional[str], meeting_path: str) -> Tuple[int, int]:
    """Extract parliament and session numbers from API fields."""
    if session_value:
        match = SESSION_PATTERN.match(session_value)
        if match:
            return int(match.group("parliament")), int(match.group("session"))

    match = MEETING_URL_PATTERN.search(meeting_path)
    if match:
        return int(match.group("parliament")), int(match.group("session"))

    raise ValueError(f"Unable to parse parliament/session from '{meeting_path}'")


def infer_time_of_day(start_time: Optional[str]) -> Optional[str]:
    """Map a HH:MM:SS start time to a coarse time of day."""
    if not start_time:
        return None

    try:
        hour = int(start_time.split(":", 1)[0])
    except (ValueError, AttributeError):
        return None

    if hour < 12:
        return "morning"
    if hour < 17:
        return "afternoon"
    return "evening"


def build_documents(detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create a document payload list from meeting detail URLs."""
    docs: List[Dict[str, Any]] = []
    for key, title in (
        ("notice_url", "Notice"),
        ("minutes_url", "Minutes"),
        ("webcast_url", "Webcast"),
    ):
        url = detail.get(key)
        if url:
            docs.append({"title": title, "url": url, "doc_type": key.replace("_url", "")})
    return docs


def extract_title(detail: Dict[str, Any], language: str) -> Optional[str]:
    """Extract a localized title from meeting detail data."""
    title = detail.get("title")
    if isinstance(title, dict):
        return title.get(language)
    if isinstance(title, str) and language == "en":
        return title
    return None


def build_committee_payload(
    slug: str,
    committee: Dict[str, Any],
    jurisdiction: str,
) -> Dict[str, Any]:
    """Prepare a committee upsert payload."""
    now = naive_utc_now()
    names = committee.get("name") or {}
    website_path = committee.get("url") or f"/committees/{slug}/"
    parent_url = (committee.get("parent_url") or "").lower()

    acronym = committee.get("acronym")
    if isinstance(acronym, dict):
        acronym_value = acronym.get("en") or acronym.get("fr")
    else:
        acronym_value = acronym

    identifier_seed = acronym_value or slug
    identifier = build_committee_identifier(identifier_seed)

    name_en = names.get("en") if isinstance(names, dict) else names or identifier.code
    name_fr = names.get("fr") if isinstance(names, dict) else None

    chamber = "Commons"
    if "senate" in parent_url:
        chamber = "Senate"

    formatted_url = website_path if website_path.startswith("/") else f"/{website_path}"

    return {
        "jurisdiction": jurisdiction,
        "committee_code": identifier.code,
        "committee_slug": identifier.internal_slug,
        "source_slug": resolve_source_slug(slug) or identifier.source_slug,
        "name_en": name_en,
        "name_fr": name_fr,
        "chamber": chamber,
        "committee_type": committee.get("committee_type") or "standing",
        "website_url": f"{WEB_BASE}{formatted_url}",
        "created_at": now,
        "updated_at": now,
    }


def upsert_committee(engine, table: Table, payload: Dict[str, Any]) -> int:
    """Insert or update a committee record and return its database ID."""
    insert_stmt = pg_insert(table).values(payload)
    update_values = {
        "name_en": insert_stmt.excluded.name_en,
        "name_fr": insert_stmt.excluded.name_fr,
        "chamber": insert_stmt.excluded.chamber,
        "committee_type": insert_stmt.excluded.committee_type,
        "website_url": insert_stmt.excluded.website_url,
        "committee_slug": insert_stmt.excluded.committee_slug,
        "source_slug": insert_stmt.excluded.source_slug,
        "updated_at": insert_stmt.excluded.updated_at,
    }
    stmt = insert_stmt.on_conflict_do_update(
        constraint="uq_committee_natural_key",
        set_=update_values,
    ).returning(table.c.id)

    with engine.begin() as conn:
        return conn.execute(stmt).scalar_one()


def build_meeting_payload(
    committee_id: int,
    summary: Dict[str, Any],
    detail: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Combine meeting summary and detail into a database payload."""
    meeting_path = (detail.get("url") or summary.get("url") or "").rstrip("/")
    if not meeting_path:
        return None

    try:
        parliament, session = parse_session_parts(detail.get("session"), meeting_path)
    except ValueError:
        return None

    date_str = detail.get("date") or summary.get("date")
    if not date_str:
        return None

    meeting_number = detail.get("number") or summary.get("number")
    if meeting_number is None:
        return None

    try:
        meeting_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

    now = naive_utc_now()
    normalized_path = meeting_path if meeting_path.startswith("/") else f"/{meeting_path}"

    return {
        "committee_id": committee_id,
        "meeting_number": int(meeting_number),
        "parliament": parliament,
        "session": session,
        "meeting_date": meeting_date,
        "time_of_day": infer_time_of_day(detail.get("start_time")),
        "title_en": extract_title(detail, "en"),
        "title_fr": extract_title(detail, "fr"),
        "meeting_type": "in_camera" if detail.get("in_camera") else "public",
        "room": detail.get("room"),
        "witnesses": detail.get("witnesses") or [],
        "documents": build_documents(detail),
        "source_url": f"{WEB_BASE}{normalized_path}",
        "created_at": now,
        "updated_at": now,
    }


def upsert_meetings(engine, table: Table, meetings: List[Dict[str, Any]]) -> int:
    """Insert meeting payloads while ignoring duplicates."""
    if not meetings:
        return 0

    insert_stmt = (
        pg_insert(table)
        .values(meetings)
        .on_conflict_do_nothing(
            index_elements=[
                table.c.committee_id,
                table.c.meeting_number,
                table.c.parliament,
                table.c.session,
            ]
        )
        .returning(table.c.id)
    )

    with engine.begin() as conn:
        return len(conn.execute(insert_stmt).scalars().all())


def seed_committee(
    engine,
    committees_table: Table,
    meetings_table: Table,
    slug: str,
    meeting_limit: int,
    jurisdiction: str,
) -> int:
    """Fetch and store committee + meeting data for a single slug."""
    try:
        committee_meta = fetch_committee_metadata(slug)
    except (HTTPError, RequestException) as exc:
        print(f"[warn] Failed to fetch committee '{slug}': {exc}")
        return 0

    committee_payload = build_committee_payload(slug, committee_meta, jurisdiction)
    committee_id = upsert_committee(engine, committees_table, committee_payload)

    try:
        summaries = fetch_meeting_summaries(slug, meeting_limit)
    except (HTTPError, RequestException) as exc:
        print(f"[warn] Failed to fetch meetings for '{slug}': {exc}")
        return 0

    meeting_payloads: List[Dict[str, Any]] = []
    for summary in summaries:
        try:
            detail = fetch_meeting_detail(summary)
        except (HTTPError, RequestException) as exc:
            print(f"  - skipped meeting {summary.get('url', 'unknown')}: {exc}")
            continue

        payload = build_meeting_payload(committee_id, summary, detail)
        if payload:
            meeting_payloads.append(payload)

    inserted = upsert_meetings(engine, meetings_table, meeting_payloads)
    print(
        f"[info] Committee '{slug}' -> attempted={len(meeting_payloads)} inserted={inserted}"
    )
    return inserted


def main() -> None:
    load_environment()
    clear_tls_env()

    database_url = resolve_database_url()

    engine = create_engine(database_url, future=True)
    metadata = MetaData()
    metadata.reflect(bind=engine, only=["committees", "committee_meetings"], views=False)

    committees_table = metadata.tables["committees"]
    meetings_table = metadata.tables["committee_meetings"]

    slug_env = os.getenv("SEED_COMMITTEE_SLUGS")
    slugs = [slug.strip().lower() for slug in slug_env.split(",")] if slug_env else ["environment"]
    slugs = [slug for slug in slugs if slug]
    if not slugs:
        slugs = ["environment"]

    meeting_limit = int(os.getenv("SEED_MEETING_COUNT", "5"))
    jurisdiction = os.getenv("SEED_COMMITTEE_JURISDICTION", "ca-federal")

    total_inserted = 0
    for slug in slugs:
        total_inserted += seed_committee(
            engine,
            committees_table,
            meetings_table,
            slug,
            meeting_limit,
            jurisdiction,
        )

    with engine.begin() as conn:
        committee_total = conn.execute(
            select(func.count()).select_from(committees_table)
        ).scalar_one()
        meeting_total = conn.execute(
            select(func.count()).select_from(meetings_table)
        ).scalar_one()

    print(
        "[done] Seed complete: "
        f"committees={committee_total} meetings={meeting_total} newly_inserted={total_inserted}"
    )


if __name__ == "__main__":
    main()
