"""
Orchestration package for Parliament Explorer.

This package contains pipeline orchestrators that coordinate
multiple adapters and data sources.
"""

from .bill_pipeline import BillPipeline

__all__ = [
    "BillPipeline",
]
