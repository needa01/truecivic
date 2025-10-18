"""Manual smoke test for the database layer.

Usage:
    python scripts/manual/database_layer_smoke_test.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import BillModel, db
from src.db.repositories import BillRepository
from src.models.bill import Bill


async def main() -> None:
    """Run the manual smoke test."""
    print("\n" + "=" * 60)
    print("Parliament Explorer - Database Layer Test")
    print("=" * 60)
    print("Environment: LOCAL (PostgreSQL + pgvector)")
    print("=" * 60 + "\n")

    try:
        # Initialize database
        print("1. Initializing database...")
        await db.initialize()
        print("   ✅ Database initialized\n")

        # Create tables
        print("2. Creating tables...")
        await db.create_tables()
        print("   ✅ Tables created\n")

        # Create test bill
        print("3. Creating test bill...")
        test_bill = Bill(
            jurisdiction="ca-federal",
            parliament=44,
            session=1,
            number="C-TEST-1",
            title_en="Test Bill for Database Layer",
            title_fr="Projet de loi test pour la couche base de données",
            sponsor_politician_id=12345,
            introduced_date=datetime.utcnow(),
            law_status=None,
            legisinfo_id=99999,
            subject_tags=["testing", "database", "parliament"],
            source_openparliament=True,
            source_legisinfo=False,
            last_fetched_at=datetime.utcnow(),
        )
        print(f"   Created: {test_bill.natural_key()}\n")

        # Test upsert (insert)
        print("4. Testing repository upsert (INSERT)...")
        async with db.session() as session:
            repo = BillRepository(session)
            bill_model, created = await repo.upsert(test_bill)
            print(f"   ✅ Upserted bill (created={created})")
            print(f"   ID: {bill_model.id}")
            print(
                "   Natural Key: "
                f"{bill_model.jurisdiction}/{bill_model.parliament}-"
                f"{bill_model.session}/{bill_model.number}\n"
            )

        # Test fetch by natural key
        print("5. Testing fetch by natural key...")
        async with db.session() as session:
            repo = BillRepository(session)
            fetched = await repo.get_by_natural_key("ca-federal", 44, 1, "C-TEST-1")
            if fetched:
                print(f"   ✅ Found bill: {fetched.title_en}")
                print(f"   Tags: {fetched.subject_tags}\n")
            else:
                print("   ❌ Bill not found\n")

        # Test upsert (update)
        print("6. Testing repository upsert (UPDATE)...")
        test_bill.title_en = "Updated Test Bill Title"
        test_bill.source_legisinfo = True
        test_bill.committee_studies = ["Standing Committee on Test"]

        async with db.session() as session:
            repo = BillRepository(session)
            bill_model, created = await repo.upsert(test_bill)
            print(f"   ✅ Upserted bill (created={created})")
            print(f"   Updated title: {bill_model.title_en}")
            print(f"   Committees: {bill_model.committee_studies}\n")

        # Test fetch by parliament/session
        print("7. Testing fetch by parliament/session...")
        async with db.session() as session:
            repo = BillRepository(session)
            bills = await repo.get_by_parliament_session(44, 1, limit=10)
            print(f"   ✅ Found {len(bills)} bills in Parliament 44, Session 1\n")

        # Test bulk upsert
        print("8. Testing bulk upsert...")
        bulk_bills = [
            Bill(
                jurisdiction="ca-federal",
                parliament=44,
                session=1,
                number=f"C-TEST-{i}",
                title_en=f"Bulk Test Bill {i}",
                introduced_date=datetime.utcnow(),
                source_openparliament=True,
                last_fetched_at=datetime.utcnow(),
            )
            for i in range(2, 6)
        ]

        async with db.session() as session:
            repo = BillRepository(session)
            models = await repo.upsert_many(bulk_bills)
            print(f"   ✅ Bulk upserted {len(models)} bills\n")

        # Final count
        print("9. Final database state...")
        async with db.session() as session:
            repo = BillRepository(session)
            all_bills = await repo.get_by_parliament_session(44, 1, limit=100)
            print(f"   📊 Total bills in database: {len(all_bills)}")
            for bill in all_bills[:3]:
                print(f"      - {bill.number}: {bill.title_en[:50]}")

        print("\n" + "=" * 60)
        print("✅ Database layer test SUCCESSFUL!")
        print("=" * 60 + "\n")

    except Exception as exc:  # pragma: no cover - diagnostic script
        print(f"\n❌ Database test FAILED: {exc}\n")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        print("\n10. Cleaning up...")
        await db.close()
        print("    ✅ Database connections closed\n")


if __name__ == "__main__":
    asyncio.run(main())
