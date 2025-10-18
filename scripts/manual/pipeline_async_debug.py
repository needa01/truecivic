"""Async pipeline debug runner.

Usage:
    python scripts/manual/pipeline_async_debug.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.bill_pipeline import BillPipeline


async def main() -> None:
    """Run the pipeline debug helper."""
    print("\n" + "=" * 60)
    print("Parliament Explorer - Quick Pipeline Test")
    print("=" * 60)
    print("Fetching latest 5 bills from Parliament 44, Session 1")
    print("Enrichment: ENABLED")
    print("=" * 60 + "\n")

    pipeline = BillPipeline(enrich_by_default=True)

    try:
        print("🚀 Starting pipeline...\n")

        response = await pipeline.fetch_and_enrich(
            parliament=44,
            session=1,
            limit=5,
            enrich=True,
        )

        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Status: {response.status.value}")
        print(f"Bills Fetched: {len(response.data or [])}")
        print(f"Errors: {len(response.errors)}")

        if response.data:
            print("\n📋 Bills Retrieved:")
            for index, bill in enumerate(response.data, 1):
                print(f"\n  {index}. {bill.number} - {bill.title_en[:60]}...")
                print(f"     Parliament {bill.parliament}, Session {bill.session}")
                print(f"     Introduced: {bill.introduced_date}")

                if bill.source_legisinfo:
                    print("     ✅ ENRICHED")
                    if bill.subject_tags:
                        print(f"        Tags: {', '.join(bill.subject_tags[:2])}")
                else:
                    print("     ⭕ OpenParliament only")

        if response.errors:
            print(f"\n⚠️  {len(response.errors)} errors encountered")
            for error in response.errors[:3]:
                print(f"  - [{error.error_type}] {error.message[:80]}")

        print("\n" + "=" * 60)
        print("✅ Test complete!\n")

    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"\n❌ Test failed: {exc}\n")
        import traceback

        traceback.print_exc()

    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
