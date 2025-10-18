"""
Bill data pipeline orchestration.

Coordinates fetching bills from OpenParliament and enriching them with LEGISinfo data.
Handles the full flow: fetch → enrich → validate → return.

Responsibility: Orchestrate multi-source data fetching and merging for bills
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from ..adapters.openparliament_bills import OpenParliamentBillsAdapter
from ..adapters.legisinfo_adapter import LEGISinfoAdapter
from ..models.bill import Bill
from ..models.adapter_models import AdapterResponse, AdapterStatus, AdapterError, AdapterMetrics
from ..utils.retry import retry_async

logger = logging.getLogger(__name__)


class BillPipeline:
    """
    Orchestrates the complete bill data pipeline.
    
    Pipeline stages:
    1. Fetch bills from OpenParliament (latest first)
    2. For each bill with legisinfo_id, fetch enrichment data
    3. Merge enrichment data into bill model
    4. Validate and return enriched bills
    
    Example:
        pipeline = BillPipeline()
        response = await pipeline.fetch_and_enrich(
            parliament=44,
            session=1,
            limit=100,
            enrich=True
        )
        bills = response.data
    """
    
    def __init__(
        self,
        enrich_by_default: bool = True,
        max_enrichment_errors: int = 10
    ):
        """
        Initialize bill pipeline.
        
        Args:
            enrich_by_default: Whether to enrich bills by default
            max_enrichment_errors: Max enrichment failures before stopping
        """
        self.enrich_by_default = enrich_by_default
        self.max_enrichment_errors = max_enrichment_errors
        
        # Initialize adapters
        self.openparliament_adapter = OpenParliamentBillsAdapter()
        self.legisinfo_adapter = LEGISinfoAdapter()
        
        logger.info("BillPipeline initialized")
    
    async def fetch_and_enrich(
        self,
        parliament: Optional[int] = None,
        session: Optional[int] = None,
        limit: int = 100,
        enrich: Optional[bool] = None,
        introduced_after: Optional[datetime] = None,
        introduced_before: Optional[datetime] = None,
        **kwargs: Any
    ) -> AdapterResponse[Bill]:
        """
        Fetch bills and optionally enrich with LEGISinfo data.
        
        This is the main entry point for the pipeline.
        
        Args:
            parliament: Filter by parliament number (e.g., 44)
            session: Filter by session number (e.g., 1)
            limit: Maximum bills to fetch
            enrich: Whether to enrich with LEGISinfo (defaults to pipeline setting)
            **kwargs: Additional parameters passed to adapters
        
        Returns:
            AdapterResponse containing enriched Bill objects
        """
        start_time = datetime.utcnow()
        
        # Determine if we should enrich
        should_enrich = enrich if enrich is not None else self.enrich_by_default
        
        logger.info(
            f"Starting bill pipeline: parliament={parliament}, "
            f"session={session}, limit={limit}, enrich={should_enrich}, "
            f"introduced_after={introduced_after}, introduced_before={introduced_before}"
        )
        
        # Stage 1: Fetch bills from OpenParliament
        logger.info("Stage 1: Fetching bills from OpenParliament")
        
        openparliament_response = await self._fetch_with_retry(
            parliament=parliament,
            session=session,
            limit=limit,
            introduced_after=introduced_after,
            introduced_before=introduced_before
        )
        
        # Check if fetch succeeded
        if openparliament_response.status == AdapterStatus.FAILURE:
            logger.error("OpenParliament fetch failed, aborting pipeline")
            return openparliament_response
        
        bills = openparliament_response.data or []
        logger.info(f"Fetched {len(bills)} bills from OpenParliament")
        
        # Stage 2: Enrich bills with LEGISinfo (if requested)
        all_errors = list(openparliament_response.errors)
        
        if should_enrich and bills:
            logger.info("Stage 2: Enriching bills with LEGISinfo data")
            
            enriched_bills, enrichment_errors = await self._enrich_bills(bills)
            bills = enriched_bills
            all_errors.extend(enrichment_errors)
            
            logger.info(
                f"Enrichment complete: {len(enrichment_errors)} errors encountered"
            )
        else:
            logger.info("Stage 2: Skipping enrichment (not requested)")
        
        # Calculate total duration
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Build final response
        final_status = self._determine_final_status(
            openparliament_response.status,
            all_errors,
            len(bills)
        )
        
        # Aggregate metrics
        final_metrics = AdapterMetrics(
            records_attempted=openparliament_response.metrics.records_attempted,
            records_succeeded=len(bills),
            records_failed=len(all_errors),
            duration_seconds=duration,
            rate_limit_hits=openparliament_response.metrics.rate_limit_hits,
            retry_count=openparliament_response.metrics.retry_count
        )
        
        logger.info(
            f"Pipeline complete: status={final_status}, "
            f"bills={len(bills)}, errors={len(all_errors)}"
        )
        
        return AdapterResponse(
            status=final_status,
            data=bills,
            errors=all_errors,
            metrics=final_metrics,
            source="bill_pipeline",
            fetch_timestamp=datetime.utcnow(),
            cache_until=openparliament_response.cache_until
        )
    
    async def _fetch_with_retry(
        self,
        parliament: Optional[int],
        session: Optional[int],
        limit: int,
        introduced_after: Optional[datetime] = None,
        introduced_before: Optional[datetime] = None
    ) -> AdapterResponse[Bill]:
        """
        Fetch bills from OpenParliament with retry logic.
        
        Wraps the adapter call with exponential backoff retry.
        """
        async def fetch():
            return await self.openparliament_adapter.fetch(
                parliament=parliament,
                session=session,
                limit=limit,
                introduced_after=introduced_after,
                introduced_before=introduced_before
            )
        
        try:
            return await retry_async(
                fetch,
                max_attempts=3,
                base_delay=1.0,
                max_delay=30.0,
                logger_instance=logger
            )
        except Exception as e:
            # If retry fails completely, return failure response
            logger.error(f"All retry attempts failed: {e}")
            return self.openparliament_adapter._build_failure_response(
                error=e,
                start_time=datetime.utcnow(),
                retryable=False
            )
    
    async def _enrich_bills(
        self,
        bills: List[Bill]
    ) -> tuple[List[Bill], List[AdapterError]]:
        """
        Enrich bills with LEGISinfo data.
        
        For each bill with a legisinfo_id:
        1. Fetch enrichment data from LEGISinfo
        2. Merge enrichment fields into bill
        3. Track errors but continue processing
        
        Args:
            bills: List of bills to enrich
        
        Returns:
            Tuple of (enriched_bills, errors)
        """
        enriched_bills: List[Bill] = []
        errors: List[AdapterError] = []
        
        enrichment_error_count = 0
        
        for bill in bills:
            # Check if bill has legisinfo_id
            if not bill.legisinfo_id:
                logger.debug(
                    f"Bill {bill.natural_key()} has no legisinfo_id, "
                    f"skipping enrichment"
                )
                enriched_bills.append(bill)
                continue
            
            # Check if we've hit max enrichment errors
            if enrichment_error_count >= self.max_enrichment_errors:
                logger.warning(
                    f"Hit max enrichment errors ({self.max_enrichment_errors}), "
                    f"skipping remaining bills"
                )
                enriched_bills.append(bill)
                continue
            
            try:
                # Fetch enrichment data with retry
                async def fetch_enrichment():
                    return await self.legisinfo_adapter.fetch(
                        legisinfo_id=bill.legisinfo_id
                    )
                
                enrichment_response = await retry_async(
                    fetch_enrichment,
                    max_attempts=2,  # Fewer retries for enrichment
                    base_delay=2.0,  # Longer delay for scraping
                    max_delay=10.0,
                    logger_instance=logger
                )
                
                # Check if enrichment succeeded
                if enrichment_response.status == AdapterStatus.SUCCESS:
                    if enrichment_response.data:
                        # Merge enrichment data into bill
                        enrichment_data = enrichment_response.data[0]
                        enriched_bill = self._merge_enrichment(bill, enrichment_data)
                        enriched_bills.append(enriched_bill)
                        
                        logger.debug(
                            f"Successfully enriched bill {bill.natural_key()}"
                        )
                    else:
                        # No data returned, use original bill
                        enriched_bills.append(bill)
                else:
                    # Enrichment failed, use original bill and track error
                    enriched_bills.append(bill)
                    errors.extend(enrichment_response.errors)
                    enrichment_error_count += 1
                    
                    logger.warning(
                        f"Enrichment failed for bill {bill.natural_key()}, "
                        f"using original data"
                    )
            
            except Exception as e:
                # Unexpected error during enrichment
                enriched_bills.append(bill)
                errors.append(AdapterError(
                    timestamp=datetime.utcnow(),
                    error_type=type(e).__name__,
                    message=f"Enrichment error for bill {bill.natural_key()}: {e}",
                    context={"bill_key": bill.natural_key()},
                    retryable=False
                ))
                enrichment_error_count += 1
                
                logger.warning(
                    f"Exception during enrichment of {bill.natural_key()}: {e}",
                    exc_info=True
                )
        
        return enriched_bills, errors
    
    def _merge_enrichment(
        self,
        bill: Bill,
        enrichment_data: Dict[str, Any]
    ) -> Bill:
        """
        Merge LEGISinfo enrichment data into bill.
        
        Creates a new Bill instance with enrichment fields populated.
        
        Args:
            bill: Original bill from OpenParliament
            enrichment_data: Enrichment dict from LEGISinfo
        
        Returns:
            New Bill instance with enrichment data
        """
        # Create updated bill with enrichment fields
        return Bill(
            # Natural key fields (unchanged)
            jurisdiction=bill.jurisdiction,
            parliament=bill.parliament,
            session=bill.session,
            number=bill.number,
            
            # Core fields (unchanged)
            title_en=bill.title_en,
            title_fr=bill.title_fr,
            short_title_en=bill.short_title_en,
            short_title_fr=bill.short_title_fr,
            sponsor_politician_id=bill.sponsor_politician_id,
            introduced_date=bill.introduced_date,
            law_status=bill.law_status,
            
            # Enrichment fields (NEW)
            legisinfo_id=bill.legisinfo_id,
            subject_tags=enrichment_data.get("subject_tags"),
            committee_studies=enrichment_data.get("committee_studies"),
            royal_assent_date=enrichment_data.get("royal_assent_date"),
            royal_assent_chapter=enrichment_data.get("royal_assent_chapter"),
            related_bill_numbers=enrichment_data.get("related_bill_numbers"),
            
            # Source tracking
            source_openparliament=bill.source_openparliament,
            source_legisinfo=True,  # Mark as enriched
            last_fetched_at=bill.last_fetched_at,
            last_enriched_at=datetime.utcnow()  # Track enrichment time
        )
    
    def _determine_final_status(
        self,
        openparliament_status: AdapterStatus,
        all_errors: List[AdapterError],
        successful_records: int
    ) -> AdapterStatus:
        """
        Determine final pipeline status based on stage results.
        
        Logic:
        - If OpenParliament failed → FAILURE
        - If no records succeeded → FAILURE
        - If some errors but some success → PARTIAL_SUCCESS
        - If no errors → SUCCESS
        """
        if openparliament_status == AdapterStatus.FAILURE:
            return AdapterStatus.FAILURE
        
        if successful_records == 0:
            return AdapterStatus.FAILURE
        
        if all_errors:
            return AdapterStatus.PARTIAL_SUCCESS
        
        return AdapterStatus.SUCCESS
    
    async def close(self):
        """Close all adapter connections"""
        await self.openparliament_adapter.close()
        await self.legisinfo_adapter.close()
        logger.info("BillPipeline closed")
