"""
Adapters package for Parliament Explorer.

This package contains all data source adapters that implement
the BaseAdapter interface.
"""

from .base_adapter import BaseAdapter
from .openparliament_bills import OpenParliamentBillsAdapter
from .legisinfo_adapter import LEGISinfoAdapter

__all__ = [
    "BaseAdapter",
    "OpenParliamentBillsAdapter",
    "LEGISinfoAdapter",
]
