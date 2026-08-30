"""Main pipeline orchestrating all stages with checkpoint/resume support."""

import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from car_ad_automation.core.checkpoint import Checkpoint
from car_ad_automation.core.models import (
    Vehicle,
    ValidationResult,
    BatchProcessingReport,
    Advertisement,
)
from car_ad_automation.stages.normalize.normalizer import normalize_record
from car_ad_automation.stages.normalize.validator import validate_vehicle
from car_ad_automation.stages.dedupe.deduplicator import check_duplicates
from car_ad_automation.stages.build.description_builder import ensure_description
from car_ad_automation.stages.build.image_manager import validate_vehicle_images
from car_ad_automation.stages.build.image_downloader import download_vehicle_images
from car_ad_automation.stages.post.form_filler import RobustFormFiller
from car_ad_automation.stages.build.category_handler import DynamicCategoryCascader
from car_ad_automation.stages.post.browser import PersistentBrowserSession
from car_ad_automation.core.config import MIN_IMAGES, RECOMMENDED_IMAGES


class Pipeline:
    """End-to-end pipeline for vehicle advertisement automation."""

    STAGES = [
        "normalize",
        "validate",
        "deduplicate",
        "descriptions",
        "images",
        "post_ads",
    ]

    def __init__(self, config: dict, logger):
        self.config = config
        self.logger = logger
        self.checkpoint = Checkpoint(config["CHECKPOINT_FILE"])
        self.report = BatchProcessingReport()
        self.fingerprints = set()
        self.processed_vehicle_ids = set()

    def load_source_data(self, source_mode: str, source_arg: str = None) -> list[dict]:
        """Load source data from website, file, or default location."""
        if source_mode == "website":
            return self._run_scraper(source_arg)
        elif source_mode == "file":
            return self._load_file(source_arg)
        else:
            return self._load_default()

    def _run_scraper(self, url: str) -> list[dict]:
        """Run scraper and return normalized records."""
        from car_ad_automation.stages.scrape.scraper import scrape_website

        if not url:
            raise ValueError("Website URL required for scraping mode")

        self.logger.info(f"Starting scraper for: {url}")
        records = scrape_website(url)
        self.logger.info(f"Scraper returned {len(records)} records")
        return records

    def _load_file(self, file_path: str) -> list[dict]:
        """Load records from CSV or JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Source file not found: {file_path}")

        self.logger.info(f"Loading source data from: {file_path}")

        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON file must contain a list of records")
            return data

        elif path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)

        else:
            raise ValueError(f"Unsupported file format: {path.suffix}. Use .csv or .json")

    def _load_default(self) -> list[dict]:
        """Load from default data/inventory.csv or data/inventory.json."""
        from car_ad_automation.core.config import DATA_DIR

        csv_path = DATA_DIR / "inventory.csv"
        json_path = DATA_DIR / "inventory.json"

        if json_path.exists():
            self.logger.info(f"Loading default JSON: {json_path}")
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON file must contain a list of records")
            return data

        if csv_path.exists():
            self.logger.info(f"Loading default CSV: {csv_path}")
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                return list(reader)

        raise FileNotFoundError(
            f"No source data found. Create {csv_path} or {json_path}, "
            "or use --source file --file <path> or --source website --url <url>"
        )

    def run(
        self,
        records: list[dict],
        dry_run: bool = True,
        resume: bool = False,
        max_stage: Optional[str] = None,
    ) -> BatchProcessingReport:
        """Execute pipeline stages sequentially, stopping on first error.
        
        Args:
            records: List of raw records
            dry_run: If True, don't submit ads
            resume: If True, resume from checkpoint
            max_stage: Optional stage name to stop after (e.g., 'images' to stop before post_ads)
        """
        start_time = datetime.now()
        self.report.started_at = start_time.isoformat()
        self.report.total_records = len(records)

        # Define stage order for max_stage support
        stage_order = ["normalize", "validate", "deduplicate", "descriptions", "images", "post_ads"]
        max_stage_idx = stage_order.index(max_stage) if max_stage and max_stage in stage_order else len(stage_order)

        self.logger.info(f"Starting pipeline with {len(records)} records (dry_run={dry_run}, resume={resume}, max_stage={max_stage})")

        if resume:
            records = self._resume_from_checkpoint(records)
            self.logger.info(f"Resumed: {len(records)} records remaining")

        try:
            # Stage 1: Normalize
            if max_stage_idx >= 0:
                vehicles = self._stage_normalize(records)
            else:
                return self.report

            # Stage 2: Validate
            if max_stage_idx >= 1:
                vehicles = self._stage_validate(vehicles)

            # Stage 3: Deduplicate
            if max_stage_idx >= 2:
                vehicles = self._stage_deduplicate(vehicles)

            # Stage 4: Build descriptions
            if max_stage_idx >= 3:
                self._stage_descriptions(vehicles)

            # Stage 5: Validate images
            if max_stage_idx >= 4:
                self._stage_images(vehicles)

            # Stage 6: Post ads (only if not dry_run and SUBMIT_AD enabled)
            if max_stage_idx >= 5:
                if not dry_run and self.config.get("SUBMIT_AD"):
                    self._stage_post_ads(vehicles, dry_run=False)
                else:
                    self._stage_post_ads(vehicles, dry_run=True)

        except Exception as e:
            self.logger.exception(f"Pipeline failed at stage '{self.current_stage}': {e}")
            # Don't clear checkpoint on error - preserve for resume
            end_time = datetime.now()
            self.report.finished_at = end_time.isoformat()
            self.report.runtime_seconds = (end_time - start_time).total_seconds()
            raise

        # Only clear checkpoint if all stages completed successfully (no max_stage limit)
        if max_stage is None:
            self.checkpoint.clear()
        else:
            # For partial runs, keep checkpoint for potential resume
            pass

        end_time = datetime.now()
        self.report.finished_at = end_time.isoformat()
        self.report.runtime_seconds = (end_time - start_time).total_seconds()

        return self.report

    def _resume_from_checkpoint(self, records: list[dict]) -> list[dict]:
        """Filter out already-processed records based on checkpoint."""
        processed_ids = self.checkpoint.get_processed_ids()
        if not processed_ids:
            return records

        self.logger.info(f"Checkpoint found: {len(processed_ids)} records already processed")
        remaining = [r for r in records if self._get_record_id(r) not in processed_ids]
        self.logger.info(f"Resuming with {len(remaining)} remaining records")
        return remaining

    def _get_record_id(self, record: dict) -> str:
        """Extract unique ID from record for checkpoint tracking.
        
        Matches the ID generation logic in normalize_record to ensure
        resume can match checkpoint IDs with raw records.
        """
        import re
        
        source_id = record.get("source_id")
        if source_id:
            return str(source_id).strip()
        
        # Fallback: same logic as normalize_record
        title = record.get("title", "vehicle")
        price = record.get("price", "0")
        
        # Clean title
        title_clean = re.sub(r"[^a-zA-Z0-9]+", "_", str(title)).strip("_")
        price_clean = re.sub(r"[^0-9]", "", str(price))
        
        fallback_base = f"{title_clean}_{price_clean}"
        return f"auto_{fallback_base}"

    # ============================================================
    # STAGE 1: NORMALIZE
    # ============================================================
    def _stage_normalize(self, records: list[dict]) -> list[Vehicle]:
        self.current_stage = "normalize"
        self.logger.info("=" * 60)
        self.logger.info("STAGE 1: NORMALIZE")
        self.logger.info("=" * 60)

        self.checkpoint.mark_stage_start("normalize")

        vehicles = []
        for idx, record in enumerate(records):
            try:
                vehicle = normalize_record(record)
                vehicles.append(vehicle)
            except Exception as e:
                self.logger.error(f"Normalization failed for record {idx}: {e}")
                self.report.invalid_records += 1
                raise

        self.logger.info(f"Normalized {len(vehicles)} records")
        self.report.valid_records = len(vehicles)
        self.checkpoint.mark_stage_complete("normalize", [v.id for v in vehicles])
        return vehicles

    # ============================================================
    # STAGE 2: VALIDATE
    # ============================================================
    def _stage_validate(self, vehicles: list[Vehicle]) -> list[Vehicle]:
        self.current_stage = "validate"
        self.logger.info("=" * 60)
        self.logger.info("STAGE 2: VALIDATE")
        self.logger.info("=" * 60)

        self.checkpoint.mark_stage_start("validate")

        valid_vehicles = []
        for vehicle in vehicles:
            result = validate_vehicle(vehicle)

            if result.valid:
                valid_vehicles.append(vehicle)
                self.processed_vehicle_ids.add(vehicle.id)
            else:
                self.logger.error(f"Validation failed for {vehicle.id}: {result.errors}")
                self.report.invalid_records += 1
                raise ValueError(f"Validation failed for {vehicle.id}: {result.errors}")

        self.logger.info(f"Validated {len(valid_vehicles)} records, {self.report.invalid_records} rejected")
        self.checkpoint.mark_stage_complete("validate", [v.id for v in valid_vehicles])
        return valid_vehicles

    # ============================================================
    # STAGE 3: DEDUPLICATE
    # ============================================================
    def _stage_deduplicate(self, vehicles: list[Vehicle]) -> list[Vehicle]:
        self.current_stage = "deduplicate"
        self.logger.info("=" * 60)
        self.logger.info("STAGE 3: DEDUPLICATE")
        self.logger.info("=" * 60)

        self.checkpoint.mark_stage_start("deduplicate")

        unique_vehicles, duplicate_results, fingerprints = check_duplicates(
            vehicles, self.fingerprints
        )
        self.fingerprints = fingerprints
        self.report.duplicates = len(duplicate_results)

        if duplicate_results:
            self.logger.info(f"Found {len(duplicate_results)} duplicates")

        self.logger.info(f"Unique vehicles after dedupe: {len(unique_vehicles)}")
        self.checkpoint.mark_stage_complete("deduplicate", [v.id for v in unique_vehicles])
        return unique_vehicles

    # ============================================================
    # STAGE 4: BUILD DESCRIPTIONS
    # ============================================================
    def _stage_descriptions(self, vehicles: list[Vehicle]) -> None:
        self.current_stage = "descriptions"
        self.logger.info("=" * 60)
        self.logger.info("STAGE 4: BUILD DESCRIPTIONS")
        self.logger.info("=" * 60)

        self.checkpoint.mark_stage_start("descriptions")

        for vehicle in vehicles:
            try:
                ensure_description(vehicle)
            except Exception as e:
                self.logger.error(f"Description generation failed for {vehicle.id}: {e}")
                raise

        self.logger.info(f"Descriptions built for {len(vehicles)} vehicles")
        self.checkpoint.mark_stage_complete("descriptions", [v.id for v in vehicles])

    # ============================================================
    # STAGE 5: VALIDATE AND DOWNLOAD IMAGES
    # ============================================================
    def _stage_images(self, vehicles: list[Vehicle]) -> None:
        self.current_stage = "images"
        self.logger.info("=" * 60)
        self.logger.info("STAGE 5: VALIDATE AND DOWNLOAD IMAGES")
        self.logger.info("=" * 60)

        self.checkpoint.mark_stage_start("images")

        for vehicle in vehicles:
            try:
                # 1. Validate URLs first
                valid_images, errors = validate_vehicle_images(vehicle)

                if errors:
                    self.logger.warning(f"{vehicle.id}: {', '.join(errors)}")
                    raise ValueError(f"Image validation failed for {vehicle.id}: {errors}")

                # 2. Download validated images
                if valid_images:
                    # Prepare record for downloader
                    record = vehicle.to_dict()
                    local_paths = download_vehicle_images(record)

                    # Replace URLs with local paths
                    vehicle.images = local_paths
                    downloaded_count = len(local_paths)

                    # Apply image requirement rules
                    if downloaded_count < MIN_IMAGES:
                        raise ValueError(f"Vehicle {vehicle.id}: 0 images downloaded (minimum {MIN_IMAGES} required)")
                    elif downloaded_count < RECOMMENDED_IMAGES:
                        self.logger.warning(f"{vehicle.id}: Only {downloaded_count} images downloaded (recommended: {RECOMMENDED_IMAGES})")
                        self.report.missing_images += (RECOMMENDED_IMAGES - downloaded_count)
                    else:
                        self.logger.info(f"{vehicle.id}: Downloaded {downloaded_count} images")

                    # Store count for checkpoint/report
                    vehicle.downloaded_image_count = downloaded_count
                    self.report.downloaded_images_total += downloaded_count
                else:
                    vehicle.images = []
                    vehicle.downloaded_image_count = 0
                    raise ValueError(f"Vehicle {vehicle.id}: No valid image URLs provided (minimum {MIN_IMAGES} required)")

            except Exception as e:
                self.logger.error(f"Image processing failed for {vehicle.id}: {e}")
                raise

        self.logger.info(f"Images validated and downloaded for {len(vehicles)} vehicles")
        # Store downloaded counts in checkpoint
        completed_data = [{"id": v.id, "downloaded_images": getattr(v, 'downloaded_image_count', 0)} for v in vehicles]
        self.checkpoint.mark_stage_complete("images", [v.id for v in vehicles])

    # ============================================================
    # STAGE 6: POST ADS
    # ============================================================
    def _stage_post_ads(self, vehicles: list[Vehicle], dry_run: bool) -> None:
        self.current_stage = "post_ads"
        self.logger.info("=" * 60)
        self.logger.info(f"STAGE 6: POST ADS (dry_run={dry_run})")
        self.logger.info("=" * 60)

        self.checkpoint.mark_stage_start("post_ads")

        if dry_run:
            self.logger.info("DRY RUN MODE - Forms will be filled but not submitted")
        else:
            self.logger.info("SUBMISSION MODE - Forms will be submitted")

        for idx, vehicle in enumerate(vehicles, 1):
            self.logger.info(f"Processing vehicle {idx}/{len(vehicles)}: {vehicle.id}")

            try:
                with PersistentBrowserSession(
                    profile_dir=self.config["BROWSER_PROFILE_DIR"],
                    headless=self.config.get("HEADLESS", False),
                ) as session:
                    page = session.get_page()

                    # Navigate to destination
                    destination_url = self.config["DESTINATION_POST_URL"]
                    page.goto(destination_url, wait_until="domcontentloaded")

                    # Select category
                    cascader = DynamicCategoryCascader(page)
                    if not cascader.select_categories():
                        current_url = page.url
                        raise ValueError(
                            f"Category selection failed for vehicle {vehicle.id} at URL {current_url}. "
                            f"Expected selectors: Vehicles (value=6), Cars (exact match), Used cars in South Africa (exact match)"
                        )

                    # Fill form
                    filler = RobustFormFiller(page)
                    car_data = vehicle.to_dict()
                    filler.fill_all_car_fields(car_data)

                    # Upload images
                    if vehicle.images:
                        filler.upload_images(vehicle.images)

                    if not dry_run:
                        # Wait for user confirmation if required
                        if self.config.get("CONFIRM_SUBMISSION"):
                            input(f"Press ENTER to submit ad for {vehicle.id}...")

                        # Find and click submit button
                        submit_btn = page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Post"), button:has-text("Submit")')
                        if submit_btn:
                            submit_btn.click()
                            page.wait_for_timeout(3000)
                            self.logger.info(f"Submitted: {vehicle.id}")
                            self.report.successful += 1
                        else:
                            raise ValueError("Submit button not found")
                    else:
                        self.logger.info(f"Dry run complete for {vehicle.id} (form filled, not submitted)")
                        self.report.successful += 1

                    self.report.processed += 1
                    self.checkpoint.mark_processed(vehicle.id, idx)

            except Exception as e:
                self.logger.error(f"Posting failed for {vehicle.id}: {e}")
                self.report.failed += 1
                self.report.processed += 1
                raise

        self.checkpoint.mark_stage_complete("post_ads", [v.id for v in vehicles])

    # ============================================================
    # REPORT
    # ============================================================
    def save_report(self, output_dir: Path) -> None:
        """Save final report to output directory."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # JSON report
        report_file = output_dir / "final_report.json"
        report_file.write_text(
            json.dumps(self.report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # CSV report
        csv_file = output_dir / "final_report.csv"
        with csv_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Count"])
            for key, value in self.report.to_dict().items():
                if key not in ("started_at", "finished_at"):
                    writer.writerow([key, value])

        self.logger.info(f"Reports saved to {output_dir}")