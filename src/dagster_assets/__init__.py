"""
Dagster assets package for Parliament Explorer.

Exports all asset definitions and schedules.
"""

from src.dagster_assets.definitions import defs

__all__ = ["defs"]
