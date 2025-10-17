"""
Models package for Parliament Explorer.

This package contains all Pydantic models for:
- Adapter responses and metadata
- Domain entities (bills, MPs, votes, etc.)
- API request/response schemas
"""

from .adapter_models import (
    AdapterStatus,
    AdapterError,
    AdapterMetrics,
    AdapterResponse,
)

__all__ = [
    "AdapterStatus",
    "AdapterError",
    "AdapterMetrics",
    "AdapterResponse",
]
