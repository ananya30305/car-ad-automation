"""Batch processing orchestration."""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional

from models import (
    Vehicle,
    ValidationResult,
    SubmissionResult,
    BatchProcessingReport,
    Advertisement,
)
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
        logger: Optional[StructuredLogger] = None,
    ):
        """
        Initialize batch processor.

        Args:
            config: Configuration dictionary.
            logger: Logger instance.
        """
        self.config = config
        self.logger = logger or create_logger()

        self.checkpoint = Checkpoint(
            config.get(
                "CHECKPOINT_FILE",
                Path("checkpoints/checkpoint.json"),
            )
        )

        self.report = BatchProcessingReport()
        self.processed_fingerprints = set()
        self.submission_results = []

    async def load_source_data(self) -> list[dict]:
        """
        Load source inventory data.

        JSON is attempted first, followed by CSV.

        Returns:
            List of raw records.
        """
        source_json = self.config.get("SOURCE_JSON")
        source_csv = self.config.get("SOURCE_CSV")

        # ---------------------------------------------------------
        # JSON
        # ---------------------------------------------------------
        if source_json and Path(source_json).exists():
            try:
                json_path = Path(source_json)

                data = json.loads(
                    json_path.read_text(encoding="utf-8")
                )

                records = data if isinstance(data, list) else [data]

                self.logger.info(
                    f"Loaded {len(records)} records from JSON"
                )

                return records

            except Exception as e:
                self.logger.warning(
                    f"Failed to load JSON: {e}"
                )

        # ---------------------------------------------------------
        # CSV
        # ---------------------------------------------------------
        if source_csv and Path(source_csv).exists():
            try:
                csv_path = Path(source_csv)

                with open(
                    csv_path,
                    "r",
                    encoding="utf-8-sig",
                    newline="",
                ) as f:
                    reader = csv.DictReader(f)
                    records = list(reader)

                self.logger.info(
                    f"Loaded {len(records)} records from CSV"
                )

                return records

            except Exception as e:
                self.logger.warning(
                    f"Failed to load CSV: {e}"
                )

        self.logger.error(
            "No source data file found"
        )

        return []

    async def process_batch(
        self,
        records: list[dict],
        dry_run: bool = True,
        validate_only: bool = False,
        skip_browser: bool = False,
    ) -> BatchProcessingReport:
        """
        Process a batch of vehicle records.

        Args:
            records:
                List of raw vehicle records.

            dry_run:
                If True, forms are filled and verified,
                but never submitted.

            validate_only:
                Validate records without browser automation.

            skip_browser:
                Prepare records without browser automation.

        Returns:
            BatchProcessingReport
        """

        start_time = datetime.now()

        self.report.started_at = start_time.isoformat()
        self.report.total_records = len(records)

        self.logger.info(
            f"Starting batch processing: {len(records)} records"
        )

        # ---------------------------------------------------------
        # CHECKPOINT
        # ---------------------------------------------------------
        self.checkpoint.initialize(len(records))

        # ---------------------------------------------------------
        # NORMALIZATION
        # ---------------------------------------------------------
        normalized_vehicles = []

        for idx, record in enumerate(records):
            try:
                vehicle = normalize_record(record)

                normalized_vehicles.append(vehicle)

            except Exception as e:
                self.logger.error(
                    f"Normalization failed for record {idx}",
                    error=str(e),
                )

                self.report.invalid_records += 1

        self.logger.info(
            f"Normalized {len(normalized_vehicles)} records"
        )

        # ---------------------------------------------------------
        # VALIDATION
        # ---------------------------------------------------------
        valid_vehicles = []

        for vehicle in normalized_vehicles:

            try:
                result = validate_vehicle(vehicle)

            except Exception as e:
                self.logger.error(
                    f"Validation crashed for {vehicle.id}",
                    error=str(e),
                )

                self.report.invalid_records += 1
                continue

            if result.valid:
                valid_vehicles.append(vehicle)

            else:
                self.logger.error(
                    f"Validation failed for {vehicle.id}",
                    errors=", ".join(result.errors[:3]),
                )

        self.report.valid_records = len(valid_vehicles)

        self.report.invalid_records = (
            self.report.total_records
            - self.report.valid_records
        )

        self.logger.info(
            f"Validated {len(valid_vehicles)} records, "
            f"{self.report.invalid_records} rejected"
        )

        # ---------------------------------------------------------
        # DEDUPLICATION
        # ---------------------------------------------------------
        try:
            (
                unique_vehicles,
                duplicate_results,
                fingerprints,
            ) = check_duplicates(
                valid_vehicles,
                self.processed_fingerprints,
            )

            self.processed_fingerprints = fingerprints

        except Exception as e:
            self.logger.error(
                "Deduplication failed",
                error=str(e),
            )

            unique_vehicles = valid_vehicles
            duplicate_results = []

        self.report.duplicates = len(
            duplicate_results
        )

        if duplicate_results:
            self.logger.info(
                f"Found {len(duplicate_results)} duplicates"
            )

        self.logger.info(
            f"Processing {len(unique_vehicles)} unique vehicles"
        )

        # ---------------------------------------------------------
        # PROCESS EACH VEHICLE
        # ---------------------------------------------------------
        for idx, vehicle in enumerate(unique_vehicles):

            try:

                self.logger.info(
                    f"Processing vehicle {idx + 1}/"
                    f"{len(unique_vehicles)}: {vehicle.id}"
                )

                # -------------------------------------------------
                # DESCRIPTION
                # -------------------------------------------------
                vehicle = ensure_description(vehicle)

                # -------------------------------------------------
                # IMAGES
                # -------------------------------------------------
                valid_images, image_errors = (
                    validate_vehicle_images(vehicle)
                )

                vehicle.images = valid_images

                if image_errors:
                    self.logger.warning(
                        f"{vehicle.id}: "
                        f"{', '.join(image_errors[:3])}"
                    )

                # -------------------------------------------------
                # ADVERTISEMENT OBJECT
                # -------------------------------------------------
                ad = Advertisement(
                    id=vehicle.id,
                    vehicle=vehicle,
                    validation=ValidationResult(
                        id=vehicle.id,
                        valid=True,
                    ),
                    description_generated=True,
                    images_validated=True,
                    ready_to_post=True,
                )

                # -------------------------------------------------
                # VALIDATE ONLY
                # -------------------------------------------------
                if validate_only:

                    self.submission_results.append(
                        SubmissionResult(
                            id=vehicle.id,
                            submitted=False,
                            status="VALIDATED",
                        )
                    )

                    self.report.successful += 1
                    self.report.processed += 1

                    self.checkpoint.mark_processed(
                        vehicle.id,
                        idx,
                        success=True,
                    )

                    continue

                # -------------------------------------------------
                # PREPARE ONLY
                # -------------------------------------------------
                if skip_browser:

                    self.submission_results.append(
                        SubmissionResult(
                            id=vehicle.id,
                            submitted=False,
                            status="PREPARED",
                        )
                    )

                    self.report.successful += 1
                    self.report.processed += 1

                    self.checkpoint.mark_processed(
                        vehicle.id,
                        idx,
                        success=True,
                    )

                    continue

                # -------------------------------------------------
                # BROWSER AUTOMATION
                # -------------------------------------------------
                should_submit = (
                    not dry_run
                    and bool(self.config.get("SUBMIT_AD"))
                )

                if should_submit:

                    success, status = (
                        await self._post_advertisement(
                            ad,
                            dry_run=False,
                        )
                    )

                    self.submission_results.append(
                        SubmissionResult(
                            id=vehicle.id,
                            submitted=success,
                            status=status,
                        )
                    )

                else:

                    success, status = (
                        await self._post_advertisement(
                            ad,
                            dry_run=True,
                        )
                    )

                    self.submission_results.append(
                        SubmissionResult(
                            id=vehicle.id,
                            submitted=False,
                            status=status,
                        )
                    )

                # -------------------------------------------------
                # REPORT COUNTERS
                # -------------------------------------------------
                if success:
                    self.report.successful += 1
                else:
                    self.report.failed += 1

                self.report.processed += 1

                self.checkpoint.mark_processed(
                    vehicle.id,
                    idx,
                    success=success,
                )

            except Exception as e:

                self.logger.error(
                    f"Processing failed for {vehicle.id}",
                    error=str(e),
                )

                self.report.failed += 1

                self.checkpoint.mark_processed(
                    vehicle.id,
                    idx,
                    success=False,
                )

        # ---------------------------------------------------------
        # FINALIZE REPORT
        # ---------------------------------------------------------
        end_time = datetime.now()

        self.report.finished_at = end_time.isoformat()

        self.report.runtime_seconds = (
            end_time - start_time
        ).total_seconds()

        self.logger.info(
            "Batch processing completed"
        )

        return self.report

    async def _post_advertisement(
        self,
        ad: Advertisement,
        dry_run: bool = False,
    ) -> tuple[bool, str]:
        """
        Open destination website, detect the form,
        fill vehicle information, upload images,
        verify the form and optionally submit.

        Returns:
            Tuple of (success, status).
        """

        browser_auto = None

        destination_url = self.config.get(
            "DESTINATION_POST_URL"
        )

        # ---------------------------------------------------------
        # DESTINATION URL VALIDATION
        # ---------------------------------------------------------
        if (
            not destination_url
            or not isinstance(destination_url, str)
            or not destination_url.startswith(
                ("http://", "https://")
            )
        ):
            raise ValueError(
                "DESTINATION_POST_URL is missing or invalid. "
                "Set it in config.py or the environment "
                "to the authorized destination form URL "
                "before running browser automation."
            )

        try:

            # -----------------------------------------------------
            # LAUNCH BROWSER
            # -----------------------------------------------------
            browser_auto = BrowserAutomation(
                profile_dir=self.config.get(
                    "BROWSER_PROFILE_DIR",
                    Path("browser_profile"),
                ),
                headless=self.config.get(
                    "HEADLESS",
                    False,
                ),
                logger=self.logger,
            )

            page = await browser_auto.launch(
                timeout=self.config.get(
                    "PAGE_TIMEOUT",
                    30_000,
                )
            )

            # -----------------------------------------------------
            # OPEN DESTINATION
            # -----------------------------------------------------
            self.logger.info(
                f"{ad.id}: Opening destination URL"
            )

            await browser_auto.goto(
                destination_url
            )

            # -----------------------------------------------------
            # SAVE NAVIGATION DEBUG FILES
            # -----------------------------------------------------
            screenshots_dir = Path("screenshots")
            debug_dir = Path("debug")

            screenshots_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            debug_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            await browser_auto.take_screenshot(
                screenshots_dir
                / f"{ad.id}_navigation.png"
            )

            await browser_auto.save_html(
                debug_dir
                / f"{ad.id}_navigation.html"
            )

            # -----------------------------------------------------
            # FORM DETECTION
            # -----------------------------------------------------
            self.logger.info(
                f"{ad.id}: Detecting advertisement form"
            )

            detector = FormDetector(
                page,
                self.logger,
            )

            form_found = await detector.find_form()

            if not form_found:

                self.logger.error(
                    f"{ad.id}: Form detection failed"
                )

                return False, "BLOCKED"

            # -----------------------------------------------------
            # ANALYZE FORM FIELDS
            # -----------------------------------------------------
            await detector.analyze_fields()

            # -----------------------------------------------------
            # FORM FILLING
            # -----------------------------------------------------
            self.logger.info(
                f"{ad.id}: Filling vehicle information"
            )

            filler = FormFiller(
                page,
                detector,
                self.logger,
            )

            filled = await filler.fill_vehicle_data(
                ad.vehicle
            )

            if not filled:

                self.logger.warning(
                    f"{ad.id}: No fields were filled"
                )

                return False, "BLOCKED"

            # -----------------------------------------------------
            # IMAGE UPLOAD
            # -----------------------------------------------------
            if ad.vehicle.images:

                self.logger.info(
                    f"{ad.id}: Uploading "
                    f"{len(ad.vehicle.images)} images"
                )

                uploaded = await filler.upload_images(
                    ad.vehicle.images
                )

                if not uploaded:
                    self.logger.warning(
                        f"{ad.id}: Image upload failed "
                        f"or no file input was found"
                    )

            # -----------------------------------------------------
            # FORM VERIFICATION
            # -----------------------------------------------------
            self.logger.info(
                f"{ad.id}: Verifying filled form"
            )

            verification = await filler.verify_form(
                ad.vehicle
            )

            mismatches = verification.get(
                "mismatches",
                [],
            )

            if mismatches:

                self.logger.warning(
                    f"{ad.id}: Form verification failed",
                    mismatches=len(mismatches),
                )

                return False, "BLOCKED"

            # -----------------------------------------------------
            # SAVE VERIFIED STATE
            # -----------------------------------------------------
            await browser_auto.take_screenshot(
                screenshots_dir
                / f"{ad.id}_dry_run_verified.png"
            )

            await browser_auto.save_html(
                debug_dir
                / f"{ad.id}_dry_run_verified.html"
            )

            # -----------------------------------------------------
            # DRY RUN
            # -----------------------------------------------------
            if dry_run:

                self.logger.info(
                    f"{ad.id}: Form filled and verified. "
                    f"Submission skipped because dry-run is enabled."
                )

                return True, "VERIFIED"

            # -----------------------------------------------------
            # SUBMISSION
            # -----------------------------------------------------
            if self.config.get("SUBMIT_AD"):

                confirm = bool(
                    self.config.get(
                        "CONFIRM_SUBMISSION",
                        False,
                    )
                )

                self.logger.info(
                    f"{ad.id}: Submitting advertisement"
                )

                submit_ok = (
                    await filler.submit_form(
                        confirm=confirm
                    )
                )

                if submit_ok:

                    self.logger.info(
                        f"{ad.id}: Advertisement submitted successfully"
                    )

                    return True, "SUBMITTED"

                self.logger.error(
                    f"{ad.id}: Advertisement submission failed"
                )

                return False, "FAILED"

            # -----------------------------------------------------
            # FORM FILLED BUT NOT SUBMITTED
            # -----------------------------------------------------
            self.logger.info(
                f"{ad.id}: Form filled successfully "
                f"but submission is disabled"
            )

            return True, "FORM_FILLED"

        except Exception as e:

            self.logger.error(
                f"{ad.id}: Exception during browser automation",
                error=str(e),
            )

            return False, "FAILED"

        finally:

            # -----------------------------------------------------
            # CLOSE BROWSER
            # -----------------------------------------------------
            if browser_auto:

                try:
                    await browser_auto.close()

                except Exception as e:

                    self.logger.warning(
                        f"{ad.id}: Browser close failed: {e}"
                    )

    def save_report(self, output_dir: Path) -> None:
        """
        Save final processing reports.

        Creates:
            final_report.json
            final_report.csv
            submission_results.json
        """

        output_dir = Path(output_dir)

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # ---------------------------------------------------------
        # REPORT DATA
        # ---------------------------------------------------------
        report_data = self.report.to_dict()

        # ---------------------------------------------------------
        # STATUS SUMMARY
        # ---------------------------------------------------------
        status_counts = {}

        for result in self.submission_results:

            status = result.status

            status_counts[status] = (
                status_counts.get(status, 0) + 1
            )

        report_data["status_summary"] = status_counts

        # ---------------------------------------------------------
        # JSON REPORT
        # ---------------------------------------------------------
        report_file = (
            output_dir / "final_report.json"
        )

        report_file.write_text(
            json.dumps(
                report_data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # ---------------------------------------------------------
        # CSV REPORT
        # ---------------------------------------------------------
        csv_file = (
            output_dir / "final_report.csv"
        )

        with open(
            csv_file,
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.writer(f)

            writer.writerow(
                ["Metric", "Count"]
            )

            for key, value in report_data.items():

                if key in {
                    "started_at",
                    "finished_at",
                }:
                    continue

                # Dictionaries/lists are converted to JSON
                # so the CSV remains readable.
                if isinstance(
                    value,
                    (dict, list),
                ):
                    value = json.dumps(
                        value,
                        ensure_ascii=False,
                    )

                writer.writerow(
                    [key, value]
                )

        # ---------------------------------------------------------
        # SUBMISSION RESULTS
        # ---------------------------------------------------------
        if self.submission_results:

            results_file = (
                output_dir
                / "submission_results.json"
            )

            results_file.write_text(
                json.dumps(
                    [
                        result.to_dict()
                        for result in self.submission_results
                    ],
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        self.logger.info(
            f"Reports saved to {output_dir}"
        )