"""
Utilities for normalizing committee identifiers and resolving slug mappings.

The OpenParliament APIs mix committee acronyms (e.g., ``HUMA``) with slugified
identifiers (e.g., ``human-resources``). Internally we prefer to expose an
explicit jurisdiction-prefixed slug (``ca-HUMA``) so downstream systems can
quickly distinguish sources. This module centralizes the mapping helpers so
adapters, flows, and repositories share a consistent view.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

# We currently only ingest data from the Canadian federal parliament.
DEFAULT_JURISDICTION_PREFIX = "ca"


# Mapping of committee acronyms to their OpenParliament slug values.
# NOTE: Keep entries lowercase and limited to canonical committee acronyms.
COMMITTEE_CODE_TO_SOURCE_SLUG: Dict[str, str] = {
    "ETHI": "ethics",
    "AGRI": "agriculture",
    "CHPC": "canadian-heritage",
    "CIMM": "immigration",
    "ENVI": "environment",
    "FINA": "finance",
    "FOPO": "fisheries",
    "FAAE": "foreign-affairs",
    "OGGO": "government-operations",
    "HESA": "health",
    "HUMA": "human-resources",
    "INAN": "indigenous-affairs",
    "INDU": "industry-and-technology",
    "CIIT": "international-trade",
    "JUST": "justice",
    "LIAI": "liaison",
    "BILI": "library-of-parliament",
    "NDDN": "national-defence",
    "RNNR": "natural-resources",
    "LANG": "official-languages",
    "PROC": "house-affairs",
    "PACF": "public-accounts",
    "SECU": "public-safety",
    "SRSR": "science-and-research",
    "REGS": "scrutiny-of-regulations",
    "FEWO": "status-of-women",
    "TRAN": "transport",
    "ACVA": "veterans-affairs",
}

# Reverse lookup for slug -> code.
SOURCE_SLUG_TO_CODE: Dict[str, str] = {
    slug: code for code, slug in COMMITTEE_CODE_TO_SOURCE_SLUG.items()
}


@dataclass(frozen=True)
class CommitteeIdentifier:
    """Normalized committee identifiers."""

    code: str
    internal_slug: str
    source_slug: Optional[str]


def normalize_committee_code(value: Optional[str]) -> Optional[str]:
    """
    Normalize any representation of a committee identifier to its acronym.

    Accepts acronyms (``HUMA``), jurisdiction-prefixed slugs (``ca-HUMA``),
    and OpenParliament slugs (``human-resources``). Returns the uppercase
    committee acronym when a match is found, otherwise ``None``.
    """
    if not value:
        return None

    trimmed = value.strip()
    if not trimmed:
        return None

    lower_value = trimmed.lower()
    # Already an OpenParliament slug
    if lower_value in SOURCE_SLUG_TO_CODE:
        return SOURCE_SLUG_TO_CODE[lower_value]

    # Jurisdiction-prefixed slug (e.g., ca-HUMA)
    if "-" in trimmed:
        prefix, remainder = trimmed.split("-", 1)
        if prefix.lower() == DEFAULT_JURISDICTION_PREFIX:
            return remainder.strip().upper()

    # Fallback: treat the value as an acronym
    return trimmed.upper()


def ensure_internal_slug(value: str, jurisdiction_prefix: str = DEFAULT_JURISDICTION_PREFIX) -> str:
    """
    Ensure an identifier is expressed as our internal jurisdiction-prefixed slug.

    Example: ``HUMA`` -> ``ca-HUMA``.
    """
    if not value:
        raise ValueError("Committee identifier cannot be empty")

    trimmed = value.strip()
    if not trimmed:
        raise ValueError("Committee identifier cannot be blank")

    lower_value = trimmed.lower()
    prefix = jurisdiction_prefix.lower()

    if lower_value.startswith(f"{prefix}-"):
        _, remainder = trimmed.split("-", 1)
        return f"{prefix}-{remainder.strip().upper()}"

    code = normalize_committee_code(trimmed)
    if not code:
        raise ValueError(f"Unable to derive committee code from '{value}'")

    return f"{prefix}-{code}"


def resolve_source_slug(value: Optional[str]) -> Optional[str]:
    """
    Resolve any identifier to an OpenParliament slug suitable for API calls.

    Returns ``None`` when a slug cannot be determined.
    """
    if not value:
        return None

    trimmed = value.strip()
    if not trimmed:
        return None

    lower_value = trimmed.lower()

    if lower_value in SOURCE_SLUG_TO_CODE:
        return lower_value

    code = normalize_committee_code(trimmed)
    if not code:
        return None

    slug = COMMITTEE_CODE_TO_SOURCE_SLUG.get(code)
    if slug:
        return slug

    # Fallback: treat the provided value as an already normalized slug
    return lower_value


def build_committee_identifier(value: str) -> CommitteeIdentifier:
    """Construct the trio of identifiers for downstream use."""
    code = normalize_committee_code(value)
    if not code:
        raise ValueError(f"Unable to derive committee code from '{value}'")

    internal_slug = ensure_internal_slug(code)
    source_slug = resolve_source_slug(value)

    return CommitteeIdentifier(code=code, internal_slug=internal_slug, source_slug=source_slug)
