# Vehicle Advertisement Automation System

A Python-based automation system for processing authorized vehicle inventory data and automatically posting advertisements to a destination classifieds website.

## Features

- **Data Normalization**: Intelligent field mapping with support for alternative column names
- **Validation**: Comprehensive record validation with detailed error reporting
- **Duplicate Detection**: Fingerprint-based deduplication using title, year, price, and condition
- **Image Management**: Local image validation and organization (supports JPG, PNG, JPEG, WEBP)
- **Description Generation**: Automatic description building from structured vehicle data
- **Browser Automation**: Playwright-based form filling and submission
- **Form Detection**: Smart form field detection and mapping
- **Checkpoint System**: Resumable processing with atomic checkpoint saves
- **Batch Processing**: Sequential processing with configurable batch sizes
- **Comprehensive Logging**: Structured logging with file and console output
- **Dry-Run Mode**: Test complete workflow without submission
- **Submission Controls**: Manual confirmation requirements for posting

## Project Structure

```
car-ad-automation/
├── models.py                 # Data models and classes
├── normalizer.py             # Data normalization and field mapping
├── validator.py              # Record validation
├── deduplicator.py           # Duplicate detection
├── image_manager.py          # Image handling and validation
├── description_builder.py    # Description generation
├── checkpoint.py             # Checkpoint system
├── logger.py                 # Structured logging
├── browser.py                # Playwright browser automation
├── form_detector.py          # Form structure detection
├── form_filler.py            # Form field filling
├── batch_processor.py        # Main batch processing orchestration
├── main.py                   # CLI interface
├── config.py                 # Configuration settings
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── data/
│   ├── inventory.json        # Source inventory (JSON format)
│   ├── inventory.csv         # Source inventory (CSV format)
│   └── images/               # Optional authorized images
│
├── browser_profile/          # Persistent browser profile/cookies
├── checkpoints/              # Processing checkpoints
├── logs/                     # Log files
├── reports/                  # Generated reports
└── debug/                    # Debug HTML/screenshots
```

## Installation

### Prerequisites
- Python 3.9+
- pip (Python package manager)
- Playwright browsers

### Setup

1. **Clone/navigate to project directory**:
   ```bash
   cd d:\car-ad-automation
   ```

2. **Create virtual environment** (recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install chromium
   ```

## Configuration

Edit `config.py` to adjust settings:

- `DESTINATION_POST_URL`: URL of destination classifieds website
- `DRY_RUN`: Set to `False` to enable form submission
- `SUBMIT_AD`: Enable/disable form submission
- `CONFIRM_SUBMISSION`: Require manual confirmation before posting
- `HEADLESS`: Run browser in headless mode
- `BATCH_SIZE`: Number of records to process per run
- `IMAGE_LIMIT`: Maximum images per advertisement

Or use environment variables:
```bash
set DESTINATION_POST_URL=https://...
set DRY_RUN=False
set SUBMIT_AD=True
```

## Usage

### 1. Validate Source Data

```bash
python main.py --validate
```

Tests normalization, validation, and deduplication without browser automation.

### 2. Dry-Run (Recommended First)

```bash
python main.py --dry-run --batch 3
```

- Loads 3 records
- Normalizes and validates
- Fills forms
- Generates verification reports
- **Does NOT submit** (safe for testing)

### 3. Process and Submit

```bash
python main.py --batch 1 --submit
```

- Processes 1 record at a time
- Performs dry-run first
- Requires manual site login (browser will stay open)
- Submits forms after verification

### 4. With Confirmation

```bash
python main.py --batch 10 --submit --confirm
```

- Prompts "Type YES" before each submission
- Safer for production runs

### 5. Resume from Checkpoint

```bash
python main.py --resume
```

- Continues from last checkpoint
- Skips already-processed records
- Useful for resuming interrupted runs

## Source Data Format

### JSON Format (data/inventory.json)

[
  {
    "id": "STOCK001",
    "title": "2022 Volkswagen Amarok",
    "title description": "3.0 TDI Highline EX (190kW) 4Motion Auto Double-Ca",
    "condition": "used",
    "year": "2022",
    "Kilometers driven": "77 000 km",
    "transmission": "automatic",
    "fuel": "petrol",
    "4x2 / 4x4": "4x4",
    " body colour": "White",
    "seats": ".",
    "price summary": "Pricing Summary R 729 900 Est. R 13 014 p/m",
    "dealer_name": "ABC Motors",
    "dealer_address": "Nelspruit, Mpumalanga",
    "Dealer average rating": "4.0 (322 reviews)",
    "features": [
      "ABS Air Conditioner Airbag - DriverPass & Sides Airbag - On/Off Switch Alloy Wheels Audio Control on Steering Wheel Auxilary Input Bluetooth Central Locking Remote Cruise Control Electric Windows - Front & Back Fog Lamps - Front Leather Seats Leather Trim Mags Mud Flaps Park Distance Control (PDC) - Front Reverse Camera Smash and Grab Steering Wheel control Tow Bar Traction Control"
    ],
    "contact_number": "0600431011",
    "Source Link": "https://www.cars.co.za/for-sale/used/2022-Volkswagen-Amarok-3.0-TDI-Highline-EX-190kW-4Motion-Auto-Double-Ca-Mpumalanga-Nelspruit/11198989/",
    "vehicle highlights": [
      "Exceptional Torque Output 580 Nm Exceptional pulling power for strong in-gear acceleration.Excellent Towing Capacity 3300 Kg Can haul heavy trailers and caravans with ease.High Ground Clearance 239 mm Improved approach, break-over and departure off-road."
    ],
    "description": "This 2022 Volkswagen Amarok 3.0TDi H-LINE EX is a remarkable pickup that combines rugged capability with luxurious comfort, making it a perfect companion for both work and leisure. With only 77,000 kilometres on the clock and supported by a full service history, this used vehicle promises reliability and performance.Finished in a pristine white, this Amarok boasts an array of impressive features designed for those who demand both utility and style. Its robust diesel engine, paired with an automatic transmission, ensures a smooth, commanding drive. Enjoy the convenience of modern amenities including Bluetooth connectivity, a reverse camera, leather seats, and park distance control, enhancing your journeys. Ideal for adventures or everyday use, this vehicle is ready to tackle any terrain with confidence. Don't miss out on this exceptional opportunity.Reference: WV001|USED|509534",
    "price": "729 900",
    "Select a tag ": "Sale",
    "images": [
      "D:\\car-ad-automation\\data\\images\\0001\\Screenshot 2026-08-26 195720.png",
      "D:\\car-ad-automation\\data\\images\\0001\\Screenshot 2026-08-26 195716.png",
      "D:\\car-ad-automation\\data\\images\\0001\\Screenshot 2026-08-26 195701.png",
      "D:\\car-ad-automation\\data\\images\\0001\\Screenshot 2026-08-26 195711.png",
      "D:\\car-ad-automation\\data\\images\\0001\\Screenshot 2026-08-26 195706.png"
    ],
    "address": "Nelspruit, Mpumalanga",
    "location": "South Africa"
  }
]

### CSV Format (data/inventory.csv)

Same fields as column headers with data in rows.

### Field Normalization

The system automatically maps alternative field names:

| Source Name | Canonical Name |
|---|---|
| vehicle_year | year |
| manufacture_year | year |
| selling_price | price |
| asking_price | price |
| kms, kilometers | mileage |
| phone, mobile | contact_number |
| seller_name, dealer | dealer_name |
| image_urls, photos | images |

## Validation Rules

### Required Fields
- `title` (3-200 characters)
- `price` (positive number)

### Recommended Fields
- year (plausible 1900-2050)
- mileage (0-10,000,000)
- fuel type
- transmission
- contact number
- description (50+ characters)
- images (at least 1)

### Quality Score
Calculated as percentage of available fields. Higher is better.

## Processing Workflow

1. **Load** source inventory (JSON/CSV)
2. **Normalize** records using field mapping
3. **Validate** against rules (required fields, format)
4. **Deduplicate** using fingerprints
5. **Generate** descriptions if missing
6. **Validate** images
7. **Launch** browser and navigate to destination
8. **Detect** form structure automatically
9. **Fill** form fields with vehicle data
10. **Upload** images
11. **Verify** form contents match input
12. **Submit** (if enabled and verified)
13. **Save** checkpoint for resumability
14. **Log** results

## Reports

Generated in `reports/` directory:

### final_report.json
Complete metrics in JSON format:
```json
{
  "total_records": 100,
  "valid_records": 98,
  "invalid_records": 2,
  "duplicates": 5,
  "processed": 93,
  "successful": 85,
  "failed": 8,
  "runtime_seconds": 245.3,
  "started_at": "2026-08-25T16:27:40...",
  "finished_at": "2026-08-25T16:31:45..."
}
```

### final_report.csv
Same data in CSV format for spreadsheet import.

## Logging

Log files in `logs/` directory:

- `ad_automation.log`: Main application log with structured entries
- `scraper.log`: Legacy scraper log (if used)

Log format:
```
2026-08-25 16:27:34 | INFO     | message
2026-08-25 16:27:35 | WARNING  | warning message
2026-08-25 16:27:36 | ERROR    | error message | field=value | extra=data
```

## Checkpoint System

Processing is resumable via `checkpoints/checkpoint.json`:

```json
{
  "last_processed_index": 42,
  "processed_ids": ["ID001", "ID002", ...],
  "successful_ids": ["ID001", "ID002", ...],
  "failed_ids": [],
  "started_at": "...",
  "last_updated": "...",
  "total_records": 100
}
```

Crashes or interruptions don't cause reprocessing of completed records.

## Browser Profile

Persistent profile stored in `browser_profile/`:

- Keeps login session and cookies
- Survives between runs
- Supports manual login if required

## Image Handling

- Supported formats: JPG, JPEG, PNG, WEBP
- Max file size: 50 MB
- Max images per ad: 10
- Local files only (no scraping from third-party sites)

## Duplicate Detection

Records are marked as duplicates if they have matching:
- Vehicle ID
- Normalized title
- Year
- Price
- Condition

## Troubleshooting

### No source data found
- Check `data/inventory.json` or `data/inventory.csv` exists
- Verify JSON is valid

### Form not detected
- Check form structure on destination website
- May need custom selectors (see form_detector.py)
- Save debug HTML: check `debug/` directory

### Images not uploading
- Verify image paths are absolute or relative to project
- Check file formats are supported
- Ensure files are readable

### Login required
- Browser will wait for manual login
- Check browser window for login page
- Session is saved for next run

### Records reprocessing
- Check `checkpoints/checkpoint.json` for corrupted data
- Delete checkpoint to restart from beginning
- Use `--resume` to continue from last point

## Performance Tips

1. Start with `--batch 1` for testing
2. Increase batch size gradually (5, 10, 25, 50)
3. Use `--dry-run` before actual submission
4. Run during off-peak hours for destination site
5. Enable `HEADLESS = True` in config for faster processing

## Error Handling

The system is designed to be resilient:

- **Transient errors** (network timeouts, DOM loading): Retried up to MAX_RETRIES times
- **Invalid data**: Recorded in logs and skipped
- **Form errors**: Saved as debug HTML for inspection
- **Global errors**: Processing pauses, user intervention needed

Failed records are saved but don't stop the batch.

## Safety Features

- ✅ Dry-run mode prevents accidental submission
- ✅ Checkpoint system prevents duplicate posting
- ✅ Form verification ensures correct data
- ✅ Manual confirmation option
- ✅ No hardcoded credentials
- ✅ Local image validation only
- ✅ Debug HTML capture for troubleshooting

## Testing

Run included tests:

```bash
# Test normalization and validation
python test_validation.py

# Test deduplication and descriptions
python test_dedup_desc.py

# Compile all Python files
python -m py_compile *.py
```

## Dependencies

- **playwright** (1.40.0+): Browser automation
- **requests** (2.31.0+): HTTP requests
- **beautifulsoup4** (4.12.0+): HTML parsing
- **Pillow** (10.0.0+): Image handling
- **python-dotenv** (1.0.0+): Environment variables
- **pandas** (2.0.0+): Data processing

## Limitations

- Only supports authorized inventory data
- Cannot bypass CAPTCHA (requires manual interaction)
- Cannot bypass MFA or 2FA (requires manual interaction)
- Browser automation depends on form structure stability
- Does not scrape third-party marketplace data

## Architecture

### Core Components

1. **Models** (`models.py`): Typed data classes for type safety
2. **Normalizer** (`normalizer.py`): Flexible field mapping
3. **Validator** (`validator.py`): Configurable validation rules
4. **Deduplicator** (`deduplicator.py`): Fingerprint-based duplicate detection
5. **Batch Processor** (`batch_processor.py`): Main orchestration engine
6. **Browser Automation** (`browser.py`, `form_detector.py`, `form_filler.py`): Playwright wrapper
7. **Checkpoint** (`checkpoint.py`): Resumable state management
8. **Logger** (`logger.py`): Structured logging with file output

### Data Flow

```
Source Data → Load → Normalize → Validate → Deduplicate 
→ Enrich (Description, Images) → Batch Process
→ Browser Automation → Form Fill & Verify → Submit (optional)
→ Checkpoint → Report
```

## Support

For issues or questions:

1. Check logs in `logs/ad_automation.log`
2. Review debug HTML in `debug/` directory
3. Check checkpoint status in `checkpoints/checkpoint.json`
4. Review final report in `reports/final_report.json`

## License

This software is provided as-is for private use only.

## Disclaimer

This software is designed to work with authorized inventory data only. Users are responsible for ensuring:

- Data used is authorized
- Terms of service of destination website are not violated
- No unauthorized scraping or data misuse occurs
- All applicable laws and regulations are followed

---

**Last Updated**: 2026-08-25
**Version**: 1.0
**Python**: 3.9+
