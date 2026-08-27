Markdown# Vehicle Advertisement Automation System

A streamlined Python and Playwright automation tool designed to extract car inventory data directly and automatically populate dynamic multi-step advertisement forms on target classifieds portals.

---

## Key Features

- **Direct 2-Step Pipeline**: Streamlined execution flow (`extract_cars.py` → `batch_processor.py`).
- **Strict Category Automation**: Automatically expands **Vehicles → Cars → Used cars in South Africa** while explicitly filtering out *Parts* or *RVs*.
- **AJAX DOM Mutation Handling**: Polls the DOM dynamically for server-side Joomla dropdown responses before attempting to populate extended fields.
- **Deep Specification Mapping**: Maps up to 25 specs including Title Description, Kilometers, Seats, Dealer Rating, Features, Highlights, and Source Links.
- **Rich Text Editor Ingestion**: Directly injects vehicle descriptions into TinyMCE iFrame HTML editors.
- **Local Photo Upload**: Validates and attaches up to 5 local vehicle photos per listing (`.jpg`, `.png`).
- **Interactive Approval**: Pauses browser automation prior to posting to allow visual verification.

---

## Project Architecture

```text
car-ad-automation/
├── batch_processor.py   # Entry point & Playwright persistent browser context orchestrator
├── form_filler.py       # Core automation engine (handles AJAX category selection & field population)
├── extract_cars.py     # Parses data/inventory.json and builds payload output
├── config.py           # Global file paths, portal URLs, and browser settings
├── scraper.py          # Standalone inventory scraper utility
│
├── data/
│   ├── inventory.json  # Source inventory data
│   └── images/         # Local vehicle photos organized by source ID
│
├── output/
│   └── ads_ready_for_form.json  # Final output payload consumed by batch processor
│
└── browser_profile/    # Persistent Chromium profile keeping login sessions active
Quick SetupPrerequisitesPython 3.9+pip package managerInstallationPowerShell# Navigate to project root directory
cd D:\car-ad-automation

# Install Python dependencies
pip install playwright requests beautifulsoup4 pillow python-dotenv pandas

# Install Playwright browser binaries
playwright install chromium
Source Data Schema (data/inventory.json)Place your vehicle inventory in data/inventory.json:JSON[
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
    "Source Link": "[https://www.cars.co.za/for-sale/used/2022-Volkswagen-Amarok-3.0-TDI-Highline-EX-190kW-4Motion-Auto-Double-Ca-Mpumalanga-Nelspruit/11198989/](https://www.cars.co.za/for-sale/used/2022-Volkswagen-Amarok-3.0-TDI-Highline-EX-190kW-4Motion-Auto-Double-Ca-Mpumalanga-Nelspruit/11198989/)",
    "vehicle highlights": [
      "Exceptional Torque Output 580 Nm Exceptional pulling power for strong in-gear acceleration.Excellent Towing Capacity 3300 Kg Can haul heavy trailers and caravans with ease.High Ground Clearance 239 mm Improved approach, break-over and departure off-road."
    ],
    "description": "This 2022 Volkswagen Amarok 3.0TDi H-LINE EX is a remarkable pickup that combines rugged capability with luxurious comfort...",
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
Execution WorkflowRun these two commands sequentially in PowerShell:Step 1: Extract & Format Inventory PayloadReads data/inventory.json and generates output/ads_ready_for_form.json.PowerShellpython extract_cars.py
Step 2: Run Browser Automation EngineLaunches persistent Chromium context, handles dynamic category selection, populates specifications, and attaches images.PowerShellpython batch_processor.py
Automated Field Mapping MatrixSource Key (inventory.json)Portal Form ElementDescriptiontitleTitleFull vehicle listing titletitle descriptionTitle DescriptionEngine trim and vehicle variantKilometers drivenKilometer / MileageNumeric value (strips "km")conditionConditionForm standard (used)pricePriceNormalized numeric stringfeaturesComfort / FeaturesFormatted feature blockvehicle highlightsVehicle HighlightsHighlight points text blockDealer average ratingDealer RatingScore and review stringcontact_numberContact PhonePhone number fieldimagesFile Upload WidgetAttaches up to 5 validated local imagesPush Updates to GitHubRun these commands in PowerShell to push your clean workspace and updated README:PowerShellgit add .
git commit -m "Update core engine, clean repository workspace, and update README"
git push origin main
License & SupportInternal private use automation project. Managed by Ananya P.