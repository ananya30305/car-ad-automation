"""Batch processing orchestration."""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
import csv

from models import Vehicle, ValidationResult, SubmissionResult, BatchProcessingReport, Advertisement
from normalizer import normalize_record
from validator import validate_vehicle
from deduplicator import check_duplicates
from description_builder import ensure_description
from image_manager import validate_vehicle_images
from browser import BrowserAutomation
from form_detector import FormDetector
from form_filler import FormFiller
from checkpoint import Checkpoint
from logger import create_logger, StructuredLogger


class BatchProcessor:
    """Main processor for batch advertisement automation."""
    
    def __init__(
        self,
        config: dict,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize batch processor.
        
        Args:
            config: Configuration dictionary (from config.py)
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or create_logger()
        
        self.checkpoint = Checkpoint(
            config.get('CHECKPOINT_FILE', Path('checkpoints/checkpoint.json'))
        )
        
        self.report = BatchProcessingReport()
        self.processed_fingerprints = set()
        self.submission_results = []
    
    async def load_source_data(self) -> list[dict]:
        """
        Load source inventory data.
        
        Returns:
            List of raw records
        """
        source_csv = self.config.get('SOURCE_CSV')
        source_json = self.config.get('SOURCE_JSON')
        
        records = []
        
        # Try JSON first
        if source_json and Path(source_json).exists():
            try:
                data = json.loads(Path(source_json).read_text(encoding='utf-8'))
                records = data if isinstance(data, list) else [data]
                self.logger.info(f"Loaded {len(records)} records from JSON")
                return records
            except Exception as e:
                self.logger.warning(f"Failed to load JSON: {e}")
        
        # Try CSV
        if source_csv and Path(source_csv).exists():
            try:
                rows = []
                with open(source_csv, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                records = rows
                self.logger.info(f"Loaded {len(records)} records from CSV")
                return records
            except Exception as e:
                self.logger.warning(f"Failed to load CSV: {e}")
        
        self.logger.error("No source data file found")
        return []
    
    async def process_batch(self, records: list[dict], dry_run: bool = True) -> BatchProcessingReport:
        """
        Process batch of records.
        
        Args:
            records: List of raw records
            dry_run: If True, don't submit
            
        Returns:
            BatchProcessingReport
        """
        start_time = datetime.now()
        self.report.started_at = start_time.isoformat()
        self.report.total_records = len(records)
        
        self.logger.info(f"Starting batch processing: {len(records)} records")
        
        # Initialize checkpoint
        self.checkpoint.initialize(len(records))
        
        # Normalize all records
        normalized_vehicles = []
        for idx, record in enumerate(records):
            try:
                vehicle = normalize_record(record)
                normalized_vehicles.append(vehicle)
            except Exception as e:
                self.logger.error(f"Normalization failed for record {idx}", error=str(e))
                self.report.invalid_records += 1
                continue
        
        self.logger.info(f"Normalized {len(normalized_vehicles)} records")
        
        # Validate records
        valid_vehicles = []
        validation_results = []
        
        for vehicle in normalized_vehicles:
            result = validate_vehicle(vehicle)
            validation_results.append(result)
            
            if result.valid:
                valid_vehicles.append(vehicle)
            else:
                self.logger.error(
                    f"Validation failed for {vehicle.id}",
                    errors=", ".join(result.errors[:2])
                )
        
        self.report.valid_records = len(valid_vehicles)
        self.report.invalid_records = len(normalized_vehicles) - len(valid_vehicles)
        
        self.logger.info(f"Validated {len(valid_vehicles)} records, {self.report.invalid_records} rejected")
        
        # Deduplication
        unique_vehicles, duplicate_results, fingerprints = check_duplicates(
            valid_vehicles,
            self.processed_fingerprints
        )
        self.processed_fingerprints = fingerprints
        self.report.duplicates = len(duplicate_results)
        
        if duplicate_results:
            self.logger.info(f"Found {len(duplicate_results)} duplicates")
        
        # Process each unique vehicle
        self.logger.info(f"Processing {len(unique_vehicles)} unique vehicles")
        
        for idx, vehicle in enumerate(unique_vehicles):
            try:
                # Ensure description
                vehicle = ensure_description(vehicle)
                
                # Validate images
                valid_images, image_errors = validate_vehicle_images(vehicle)
                vehicle.images = valid_images
                
                if image_errors:
                    self.logger.warning(f"{vehicle.id}: {', '.join(image_errors[:2])}")
                
                # Create advertisement
                ad = Advertisement(
                    id=vehicle.id,
                    vehicle=vehicle,
                    validation=ValidationResult(id=vehicle.id, valid=True),
                    description_generated=True,
                    images_validated=True,
                    ready_to_post=True
                )
                
                # Browser automation (if not dry-run)
                if not dry_run and self.config.get('SUBMIT_AD'):
                    success = await self._post_advertisement(ad)
                    result = SubmissionResult(
                        id=vehicle.id,
                        submitted=success,
                        status="submitted" if success else "failed"
                    )
                    self.submission_results.append(result)
                    
                    if success:
                        self.report.successful += 1
                    else:
                        self.report.failed += 1
                else:
                    # Dry run
                    self.report.successful += 1
                
                self.report.processed += 1
                self.checkpoint.mark_processed(vehicle.id, idx, success=True)
                
            except Exception as e:
                self.logger.error(f"Processing failed for {vehicle.id}", error=str(e))
                self.report.failed += 1
                self.checkpoint.mark_processed(vehicle.id, idx, success=False)
        
        # Finalize report
        end_time = datetime.now()
        self.report.finished_at = end_time.isoformat()
        self.report.runtime_seconds = (end_time - start_time).total_seconds()
        
        return self.report
    
    async def _post_advertisement(self, ad: Advertisement) -> bool:
        """
        Post single advertisement to destination.
        
        Args:
            ad: Advertisement to post
            
        Returns:
            True if posted successfully
        """
        browser_auto = None
        
        try:
            # Launch browser
            browser_auto = BrowserAutomation(
                profile_dir=self.config.get('BROWSER_PROFILE_DIR', Path('browser_profile')),
                headless=self.config.get('HEADLESS', False),
                logger=self.logger
            )
            
            page = await browser_auto.launch(timeout=self.config.get('PAGE_TIMEOUT', 30_000))
            
            # Navigate to destination
            destination_url = self.config.get('DESTINATION_POST_URL')
            await browser_auto.goto(destination_url)
            
            # Detect form
            detector = FormDetector(page, self.logger)
            if not await detector.find_form():
                self.logger.error(f"{ad.id}: Form detection failed")
                return False
            
            # Analyze fields
            await detector.analyze_fields()
            
            # Fill form
            filler = FormFiller(page, detector, self.logger)
            await filler.fill_vehicle_data(ad.vehicle)
            
            # Upload images
            if ad.vehicle.images:
                await filler.upload_images(ad.vehicle.images)
            
            # Verify form
            verification = await filler.verify_form(ad.vehicle)
            
            if verification['mismatches']:
                self.logger.warning(f"{ad.id}: Form verification failed", mismatches=len(verification['mismatches']))
                return False
            
            # Submit (if enabled and not dry-run)
            if self.config.get('SUBMIT_AD') and not self.config.get('DRY_RUN'):
                confirm = self.config.get('CONFIRM_SUBMISSION', False)
                success = await filler.submit_form(confirm=confirm)
                return success
            
            return True
        
        except Exception as e:
            self.logger.error(f"{ad.id}: Exception during posting", error=str(e))
            return False
        
        finally:
            if browser_auto:
                await browser_auto.close()
    
    def save_report(self, output_dir: Path) -> None:
        """
        Save final report.
        
        Args:
            output_dir: Directory for report files
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # JSON report
        report_file = output_dir / "final_report.json"
        report_file.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        # CSV report
        csv_file = output_dir / "final_report.csv"
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'Count'])
            for key, value in self.report.to_dict().items():
                if key != 'started_at' and key != 'finished_at':
                    writer.writerow([key, value])
        
        # Submission results
        if self.submission_results:
            results_file = output_dir / "submission_results.json"
            results_file.write_text(
                json.dumps([r.to_dict() for r in self.submission_results], indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        
        self.logger.info(f"Reports saved to {output_dir}")
