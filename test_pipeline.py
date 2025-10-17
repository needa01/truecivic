"""
Quick test runner for Parliament Explorer pipeline.

Simple wrapper to test the bill pipeline without module imports.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path FIRST
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Now import from the modules
from orchestration.bill_pipeline import BillPipeline


async def main():
    """Run a simple pipeline test"""
    print("\n" + "="*60)
    print("Parliament Explorer - Quick Pipeline Test")
    print("="*60)
    print("Fetching latest 5 bills from Parliament 44, Session 1")
    print("Enrichment: ENABLED")
    print("="*60 + "\n")
    
    # Initialize pipeline
    pipeline = BillPipeline(enrich_by_default=True)
    
    try:
        # Fetch bills
        print("🚀 Starting pipeline...\n")
        
        response = await pipeline.fetch_and_enrich(
            parliament=44,
            session=1,
            limit=5,
            enrich=True
        )
        
        # Display results
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print(f"Status: {response.status.value}")
        print(f"Bills Fetched: {len(response.data or [])}")
        print(f"Errors: {len(response.errors)}")
        
        # Display sample bills
        if response.data:
            print("\n📋 Bills Retrieved:")
            for i, bill in enumerate(response.data, 1):
                print(f"\n  {i}. {bill.number} - {bill.title_en[:60]}...")
                print(f"     Parliament {bill.parliament}, Session {bill.session}")
                print(f"     Introduced: {bill.introduced_date}")
                
                if bill.source_legisinfo:
                    print(f"     ✅ ENRICHED")
                    if bill.subject_tags:
                        print(f"        Tags: {', '.join(bill.subject_tags[:2])}")
                else:
                    print(f"     ⭕ OpenParliament only")
        
        # Display errors if any
        if response.errors:
            print(f"\n⚠️  {len(response.errors)} errors encountered")
            for error in response.errors[:3]:
                print(f"  - [{error.error_type}] {error.message[:80]}")
        
        print("\n" + "="*60)
        print("✅ Test complete!\n")
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
    
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
