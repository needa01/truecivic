"""
Repository package for data access operations.

Implements repository pattern for abstracting database operations.
"""

from .bill_repository import BillRepository
from .politician_repository import PoliticianRepository
from .debate_repository import DebateRepository
from .document_repository import DocumentRepository
from .embedding_repository import EmbeddingRepository

__all__ = [
    "BillRepository",
    "PoliticianRepository",
    "DebateRepository",
    "DocumentRepository",
    "EmbeddingRepository",
]
