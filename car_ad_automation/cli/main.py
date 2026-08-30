#!/usr/bin/env python3
"""
Main CLI for vehicle advertisement automation.
"""

import argparse
import sys

from car_ad_automation.core import config as cfg
from car_ad_automation.pipeline.pipeline import Pipeline
from car_ad_automation.core.logger import create_logger


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(
        description="Automate vehicle advertisement posting"
    )

    # Input source selection
    parser.add_argument(
        "--source",
        choices=["website", "file", "auto"],
        default="auto",
        help="Input source mode: 'website' to scrape, 'file' to load CSV/JSON, 'auto' to use default data/inventory.csv|.json (default: auto)"
    )
    parser.add_argument(
        "--url",
        metavar="URL",
        help="Website URL to scrape (overrides --source)"
    )
    parser.add_argument(
        "--file",
        metavar="PATH",
        help="Path to CSV/JSON file (overrides --source)"
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate source data only (run through validation stage)"
    )

    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Prepare advertisements without browser automation (run through images stage)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Open browser, fill forms and verify, but do not submit"
    )

    parser.add_argument(
        "--batch",
        type=int,
        metavar="SIZE",
        help="Process N records"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint"
    )

    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate final report"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser with UI visible"
    )

    parser.add_argument(
        "--submit",
        action="store_true",
        help="Enable form submission"
    )

    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Require confirmation before submitting"
    )

    return parser.parse_args()


def main_async(args: argparse.Namespace) -> int:
    """
    Main function.

    Args:
        args: Command line arguments.

    Returns:
        Exit code.
    """

    # ---------------------------------------------------------
    # LOGGER
    # ---------------------------------------------------------

    logger = create_logger(cfg.LOG_DIR)

    logger.info("=" * 60)
    logger.info("VEHICLE ADVERTISEMENT AUTOMATION STARTING")
    logger.info("=" * 60)

    # ---------------------------------------------------------
    # DETERMINE INPUT SOURCE
    # ---------------------------------------------------------

    if args.url:
        source_mode = "website"
        source_arg = args.url
    elif args.file:
        source_mode = "file"
        source_arg = args.file
    else:
        source_mode = args.source
        source_arg = None

    # ---------------------------------------------------------
    # BROWSER MODE
    # ---------------------------------------------------------

    headless_mode = cfg.HEADLESS

    if args.headless:
        headless_mode = True

    if args.no_headless:
        headless_mode = False

    # ---------------------------------------------------------
    # DRY RUN / SUBMISSION MODE
    # ---------------------------------------------------------

    # By default, automation does NOT submit advertisements.
    #
    # Submission requires:
    #
    #     --submit
    #
    # and dry-run must NOT be enabled.

    dry_run = bool(
        args.dry_run
        or not (args.submit or cfg.SUBMIT_AD)
    )

    submit_ad = bool(
        args.submit
        if args.submit
        else cfg.SUBMIT_AD
    )

    # Dry run always overrides submission.
    if dry_run:
        submit_ad = False

    # ---------------------------------------------------------
    # CONFIGURATION FOR PIPELINE
    # ---------------------------------------------------------

    processor_config = {
        "SOURCE_CSV": cfg.SOURCE_CSV,
        "SOURCE_JSON": cfg.SOURCE_JSON,

        "DESTINATION_POST_URL": cfg.DESTINATION_POST_URL,

        "CHECKPOINT_FILE": cfg.CHECKPOINT_FILE,

        "BROWSER_PROFILE_DIR": cfg.BROWSER_PROFILE_DIR,

        "PAGE_TIMEOUT": cfg.PAGE_TIMEOUT,

        "IMAGE_LIMIT": cfg.IMAGE_LIMIT,

        "HEADLESS": headless_mode,

        "DRY_RUN": dry_run,

        "SUBMIT_AD": submit_ad,

        "CONFIRM_SUBMISSION": bool(
            args.confirm
            if args.confirm
            else cfg.CONFIRM_SUBMISSION
        ),

        "MAX_RETRIES": cfg.MAX_RETRIES,

        "RETRY_DELAY": cfg.RETRY_DELAY,
    }

    logger.info(
        f"Browser headless mode: {headless_mode}"
    )

    logger.info(
        f"Dry run: {dry_run}"
    )

    logger.info(
        f"Submit advertisements: {submit_ad}"
    )

    logger.info(
        f"Input source: {source_mode}" + (f" ({source_arg})" if source_arg else "")
    )

    # ---------------------------------------------------------
    # CREATE PIPELINE
    # ---------------------------------------------------------

    pipeline = Pipeline(
        processor_config,
        logger=logger
    )

    try:

        # -----------------------------------------------------
        # LOAD SOURCE DATA
        # -----------------------------------------------------

        logger.info("=" * 60)
        logger.info("LOADING SOURCE DATA")
        logger.info("=" * 60)

        records = pipeline.load_source_data(source_mode, source_arg)

        if not records:
            logger.error("No source data found.")
            return 1

        logger.info(
            f"Loaded {len(records)} records."
        )

        # -----------------------------------------------------
        # BATCH LIMIT
        # -----------------------------------------------------

        if args.batch:

            if args.batch <= 0:
                logger.error(
                    "--batch must be greater than 0."
                )
                return 1

            records = records[:args.batch]

            logger.info(
                f"Processing first {len(records)} records."
            )

        # -----------------------------------------------------
        # DETERMINE DRY RUN FOR VALIDATE/PREPARE MODES
        # -----------------------------------------------------

        # --validate and --prepare imply dry_run=True (no browser submission)
        effective_dry_run = dry_run or args.validate or args.prepare

        # Determine max_stage based on flags
        if args.validate:
            max_stage = "validate"
        elif args.prepare:
            max_stage = "images"
        else:
            max_stage = None  # Run all stages

        # -----------------------------------------------------
        # RUN PIPELINE
        # -----------------------------------------------------

        if args.validate:
            logger.info("=" * 60)
            logger.info("VALIDATE-ONLY MODE")
            logger.info("=" * 60)

        elif args.prepare:
            logger.info("=" * 60)
            logger.info("PREPARE MODE")
            logger.info("=" * 60)

        else:
            if effective_dry_run:
                logger.info("=" * 60)
                logger.info("DRY RUN MODE")
                logger.info("=" * 60)
                logger.info("The browser will open and the form will be filled.")
                logger.info("The advertisement will NOT be submitted.")
            else:
                logger.info("=" * 60)
                logger.info("SUBMISSION MODE")
                logger.info("=" * 60)
                logger.info("Advertisements may be submitted.")

        logger.info("Starting pipeline processing...")

        report = pipeline.run(
            records,
            dry_run=effective_dry_run,
            resume=args.resume,
            max_stage=max_stage
        )

        # -----------------------------------------------------
        # SAVE REPORT
        # -----------------------------------------------------

        logger.info("=" * 60)
        logger.info("SAVING REPORT")
        logger.info("=" * 60)

        pipeline.save_report(cfg.REPORTS_DIR)

        # -----------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------

        logger.info("")
        logger.info("=" * 60)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("=" * 60)

        logger.info(
            f"Total records:     {report.total_records}"
        )

        logger.info(
            f"Valid records:     {report.valid_records}"
        )

        logger.info(
            f"Invalid records:   {report.invalid_records}"
        )

        logger.info(
            f"Duplicates found:  {report.duplicates}"
        )

        logger.info(
            f"Processed:         {report.processed}"
        )

        logger.info(
            f"Successful:        {report.successful}"
        )

        logger.info(
            f"Failed:            {report.failed}"
        )

        logger.info(
            f"Skipped:           {report.skipped}"
        )

        logger.info(
            f"Runtime:           {report.runtime_seconds:.1f}s"
        )

        logger.info("=" * 60)

        return 0

    # ---------------------------------------------------------
    # CTRL+C
    # ---------------------------------------------------------

    except KeyboardInterrupt:

        logger.warning(
            "Automation interrupted by user."
        )

        return 130

    # ---------------------------------------------------------
    # UNEXPECTED ERROR
    # ---------------------------------------------------------

    except Exception as e:

        logger.exception(
            f"Fatal error: {e}"
        )

        return 1


def main() -> int:
    """Main entry point."""

    args = parse_arguments()

    return main_async(args)


if __name__ == "__main__":
    sys.exit(
        main()
    )