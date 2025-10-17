"""
Repository package for data access operations.

Implements repository pattern for abstracting database operations.
"""

from .bill_repository import BillRepository

__all__ = [
    "BillRepository",
]
