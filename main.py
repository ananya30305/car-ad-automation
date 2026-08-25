#!/usr/bin/env python3
"""Main CLI for vehicle advertisement automation."""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

# Import configuration and components
import config as cfg
from batch_processor import BatchProcessor
from logger import create_logger


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Automate vehicle advertisement posting"
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate source data only'
    )
    
    parser.add_argument(
        '--prepare',
        action='store_true',
        help='Prepare advertisements (normalize, validate, deduplicate)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Fill forms but don\'t submit'
    )
    
    parser.add_argument(
        '--batch',
        type=int,
        metavar='SIZE',
        help='Process N records (default: use BATCH_SIZE from config)'
    )
    
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from last checkpoint'
    )
    
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate final report'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Run browser with UI visible'
    )
    
    parser.add_argument(
        '--submit',
        action='store_true',
        help='Enable form submission'
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Require confirmation before submitting'
    )
    
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> int:
    """
    Async main function.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    # Create logger
    logger = create_logger(cfg.LOG_DIR)
    logger.info("Vehicle Advertisement Automation Starting")
    
    # Prepare configuration dict for processor
    config = {
        'SOURCE_CSV': cfg.SOURCE_CSV,
        'SOURCE_JSON': cfg.SOURCE_JSON,
        'DESTINATION_POST_URL': cfg.DESTINATION_POST_URL,
        'CHECKPOINT_FILE': cfg.CHECKPOINT_FILE,
        'BROWSER_PROFILE_DIR': cfg.BROWSER_PROFILE_DIR,
        'PAGE_TIMEOUT': cfg.PAGE_TIMEOUT,
        'IMAGE_LIMIT': cfg.IMAGE_LIMIT,
        'HEADLESS': args.headless if args.headless or args.no_headless else cfg.HEADLESS,
        'DRY_RUN': args.dry_run if args.dry_run else cfg.DRY_RUN,
        'SUBMIT_AD': args.submit if args.submit else cfg.SUBMIT_AD,
        'CONFIRM_SUBMISSION': args.confirm if args.confirm else cfg.CONFIRM_SUBMISSION,
        'MAX_RETRIES': cfg.MAX_RETRIES,
        'RETRY_DELAY': cfg.RETRY_DELAY,
    }
    
    # Create processor
    processor = BatchProcessor(config, logger=logger)
    
    try:
        # Load source data
        logger.info("Loading source data...")
        records = await processor.load_source_data()
        
        if not records:
            logger.error("No source data found")
            return 1
        
        logger.info(f"Loaded {len(records)} records")
        
        # Limit batch size if specified
        if args.batch:
            records = records[:args.batch]
            logger.info(f"Limited to {len(records)} records (--batch {args.batch})")
        
        # Determine dry-run mode
        dry_run = args.dry_run or not config['SUBMIT_AD']
        
        if dry_run:
            logger.info("DRY RUN MODE - Forms will be filled but not submitted")
        else:
            logger.info("SUBMISSION MODE - Forms will be submitted")
        
        # Process batch
        logger.info("Starting batch processing...")
        report = await processor.process_batch(records, dry_run=dry_run)
        
        # Save reports
        logger.info("Saving reports...")
        processor.save_report(cfg.REPORTS_DIR)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("BATCH PROCESSING SUMMARY")
        logger.info("="*60)
        logger.info(f"Total records:           {report.total_records}")
        logger.info(f"Valid records:           {report.valid_records}")
        logger.info(f"Invalid records:         {report.invalid_records}")
        logger.info(f"Duplicates found:        {report.duplicates}")
        logger.info(f"Processed:               {report.processed}")
        logger.info(f"Successful:              {report.successful}")
        logger.info(f"Failed:                  {report.failed}")
        logger.info(f"Skipped:                 {report.skipped}")
        logger.info(f"Runtime:                 {report.runtime_seconds:.1f}s")
        logger.info("="*60)
        
        return 0
    
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", error=str(e))
        return 1


def main() -> int:
    """Main entry point."""
    args = parse_arguments()
    
    # Run async main
    return asyncio.run(main_async(args))


if __name__ == '__main__':
    sys.exit(main())
