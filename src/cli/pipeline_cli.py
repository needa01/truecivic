"""
Command-line interface for testing Parliament Explorer pipeline.

Provides commands to test bill fetching and enrichment.

Usage:
    python -m src.cli.pipeline_cli --parliament 44 --session 1 --limit 10
    python -m src.cli.pipeline_cli --parliament 44 --no-enrich
    python -m src.cli.pipeline_cli --help
"""

import asyncio
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..orchestration.bill_pipeline import BillPipeline
from ..models.adapter_models import AdapterStatus


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_pipeline(
    parliament: Optional[int],
    session: Optional[int],
    limit: int,
    enrich: bool,
    output_file: Optional[str]
):
    """
    Test the bill pipeline with given parameters.
    
    Args:
        parliament: Parliament number to filter (e.g., 44)
        session: Session number to filter (e.g., 1)
        limit: Maximum bills to fetch
        enrich: Whether to enrich with LEGISinfo
        output_file: Optional JSON output file path
    """
    print("\n" + "="*60)
    print("Parliament Explorer - Pipeline Test")
    print("="*60)
    print(f"Parliament: {parliament or 'ALL'}")
    print(f"Session: {session or 'ALL'}")
    print(f"Limit: {limit}")
    print(f"Enrichment: {'ENABLED' if enrich else 'DISABLED'}")
    print("="*60 + "\n")
    
    # Initialize pipeline
    pipeline = BillPipeline(
        enrich_by_default=enrich,
        max_enrichment_errors=10
    )
    
    try:
        # Run pipeline
        print("🚀 Starting pipeline...\n")
        start_time = datetime.utcnow()
        
        response = await pipeline.fetch_and_enrich(
            parliament=parliament,
            session=session,
            limit=limit,
            enrich=enrich
        )
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Display results
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print(f"Status: {response.status.value}")
        print(f"Duration: {duration:.2f}s")
        print(f"Bills Fetched: {len(response.data or [])}")
        print(f"Errors: {len(response.errors)}")
        print(f"Source: {response.source}")
        
        # Display metrics
        if response.metrics:
            print("\nMetrics:")
            print(f"  Records Attempted: {response.metrics.records_attempted}")
            print(f"  Records Succeeded: {response.metrics.records_succeeded}")
            print(f"  Records Failed: {response.metrics.records_failed}")
            print(f"  Duration: {response.metrics.duration_seconds:.2f}s")
            print(f"  Rate Limit Hits: {response.metrics.rate_limit_hits}")
            print(f"  Retry Count: {response.metrics.retry_count}")
        
        # Display errors if any
        if response.errors:
            print("\n⚠️  Errors:")
            for i, error in enumerate(response.errors[:5], 1):  # Show first 5
                print(f"  {i}. [{error.error_type}] {error.message}")
            if len(response.errors) > 5:
                print(f"  ... and {len(response.errors) - 5} more errors")
        
        # Display sample bills
        if response.data:
            print("\n📋 Sample Bills (first 3):")
            for i, bill in enumerate(response.data[:3], 1):
                print(f"\n  {i}. {bill.number} - {bill.title_en[:80]}...")
                print(f"     Parliament: {bill.parliament}, Session: {bill.session}")
                print(f"     Introduced: {bill.introduced_date}")
                print(f"     Sponsor ID: {bill.sponsor_politician_id}")
                
                if enrich and bill.source_legisinfo:
                    print(f"     ✅ ENRICHED from LEGISinfo")
                    if bill.subject_tags:
                        print(f"     Tags: {', '.join(bill.subject_tags[:3])}")
                    if bill.committee_studies:
                        print(f"     Committees: {', '.join(bill.committee_studies[:2])}")
                    if bill.royal_assent_date:
                        print(f"     Royal Assent: {bill.royal_assent_date}")
                else:
                    print(f"     ⭕ OpenParliament only")
        
        # Save to file if requested
        if output_file:
            output_data = {
                "status": response.status.value,
                "timestamp": response.fetch_timestamp.isoformat(),
                "duration_seconds": duration,
                "metrics": {
                    "records_attempted": response.metrics.records_attempted,
                    "records_succeeded": response.metrics.records_succeeded,
                    "records_failed": response.metrics.records_failed,
                    "rate_limit_hits": response.metrics.rate_limit_hits,
                    "retry_count": response.metrics.retry_count,
                } if response.metrics else None,
                "bills": [
                    {
                        "natural_key": bill.natural_key(),
                        "number": bill.number,
                        "title_en": bill.title_en,
                        "title_fr": bill.title_fr,
                        "parliament": bill.parliament,
                        "session": bill.session,
                        "introduced_date": bill.introduced_date.isoformat() if bill.introduced_date else None,
                        "sponsor_politician_id": bill.sponsor_politician_id,
                        "law_status": bill.law_status,
                        "legisinfo_id": bill.legisinfo_id,
                        "subject_tags": bill.subject_tags,
                        "committee_studies": bill.committee_studies,
                        "royal_assent_date": bill.royal_assent_date.isoformat() if bill.royal_assent_date else None,
                        "royal_assent_chapter": bill.royal_assent_chapter,
                        "related_bill_numbers": bill.related_bill_numbers,
                        "source_openparliament": bill.source_openparliament,
                        "source_legisinfo": bill.source_legisinfo,
                        "is_government_bill": bill.is_government_bill(),
                        "is_senate_bill": bill.is_senate_bill(),
                    }
                    for bill in (response.data or [])
                ],
                "errors": [
                    {
                        "timestamp": error.timestamp.isoformat(),
                        "error_type": error.error_type,
                        "message": error.message,
                        "context": error.context,
                        "retryable": error.retryable,
                    }
                    for error in response.errors
                ]
            }
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {output_path.absolute()}")
        
        print("\n" + "="*60)
        
        # Return status code
        if response.status == AdapterStatus.SUCCESS:
            print("✅ Pipeline test SUCCESSFUL\n")
            return 0
        elif response.status == AdapterStatus.PARTIAL_SUCCESS:
            print("⚠️  Pipeline test PARTIAL SUCCESS (some errors)\n")
            return 0
        else:
            print("❌ Pipeline test FAILED\n")
            return 1
    
    except Exception as e:
        print(f"\n❌ Pipeline test FAILED with exception: {e}\n")
        logger.error("Pipeline test failed", exc_info=True)
        return 1
    
    finally:
        # Clean up
        await pipeline.close()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Test Parliament Explorer bill pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch latest 10 bills from Parliament 44, Session 1 (with enrichment)
  python -m src.cli.pipeline_cli --parliament 44 --session 1 --limit 10

  # Fetch latest 20 bills from Parliament 44 (all sessions, no enrichment)
  python -m src.cli.pipeline_cli --parliament 44 --limit 20 --no-enrich

  # Fetch latest 5 bills from all parliaments and save to JSON
  python -m src.cli.pipeline_cli --limit 5 --output results.json

  # Verbose logging
  python -m src.cli.pipeline_cli --parliament 44 --limit 5 --verbose
        """
    )
    
    parser.add_argument(
        "--parliament",
        type=int,
        help="Parliament number to filter (e.g., 44)"
    )
    
    parser.add_argument(
        "--session",
        type=int,
        help="Session number to filter (e.g., 1)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of bills to fetch (default: 10)"
    )
    
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Disable LEGISinfo enrichment"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
    )
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Run pipeline test
    enrich = not args.no_enrich
    
    exit_code = asyncio.run(
        test_pipeline(
            parliament=args.parliament,
            session=args.session,
            limit=args.limit,
            enrich=enrich,
            output_file=args.output
        )
    )
    
    exit(exit_code)


if __name__ == "__main__":
    main()
