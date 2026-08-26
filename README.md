# Vehicle Advertisement Automation System

A streamlined Python and Playwright automation tool designed to normalize car inventory data and automatically fill dynamic multi-step advertisement forms on target classifieds portals.

---

## Key Features

- **Sequential Pipeline**: Modular execution flow (`Extract` → `Build` → `Automate`).
- **Strict Category Automation**: Automatically selects **Vehicles → Cars → Used cars in South Africa** while explicitly filtering out *Parts* or *RVs*.
- **AJAX Handling**: Waits dynamically for server-side Joomla/Select2 DOM mutations before populating extended fields.
- **Deep Field Mapping**: Maps up to 25 specifications including Title Description, Kilometers, Dealer Rating, Features, Highlights, and Source Links.
- **Rich Text Description Ingestion**: Injects vehicle descriptions directly into TinyMCE iFrame HTML editors.
- **Multi-Image Upload**: Validates and attaches up to 5 local vehicle photos automatically per listing.
- **Interactive Approval**: Pauses browser automation prior to submission to allow manual review per listing.

---

## Project Architecture

```text
car-ad-automation/
├── batch_processor.py   # Entry point & Playwright browser session orchestrator
├── form_filler.py        # Core automation engine (handles AJAX categories & DOM filling)
├── extract_cars.py      # Normalizes raw inventory files into structured schema
├── ad_builder.py        # Compiles normalized records into output payloads
├── config.py            # Global paths, URLs, and browser context constants
│
├── data/
│   ├── inventory.json   # Primary source dataset (formatted JSON array)
│   └── images/          # Local photo directories structured by listing ID
│
├── output/
│   └── ads_ready_for_form.json  # Final processed JSON payload read by batch processor
│
└── browser_profile/     # Persistent Chromium browser context (remembers logins & cookies)
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
Execution WorkflowExecute these commands sequentially in PowerShell:Step 1: Normalize & Extract Car DataPowerShellpython extract_cars.py
Step 2: Build Form-Ready PayloadsPowerShellpython ad_builder.py
Step 3: Run Automation EnginePowerShellpython batch_processor.py
Automated Form Mapping MatrixJSON KeyAutomated Portal FieldDescriptiontitleTitleFull listing header stringtitle descriptionTitle DescriptionSub-variant or engine trim detailsKilometers drivenKilometer / MileageNumeric value (auto-strips "km")conditionConditionDefaults to UsedpricePriceStandardized currency formatfeaturesComfort / FeaturesBulleted list of installed optionsvehicle highlightsVehicle HighlightsKey selling points text blockDealer average ratingDealer RatingStar score and review breakdowncontact_numberContact NumberSeller phone contact detailsimagesUpload File WidgetAttaches up to 5 validated JPG/PNG filesGit WorkflowTo commit updates to GitHub:PowerShellgit add .
git commit -m "Update form automation and README documentation"
git push origin main
License & SupportInternal private use automation project. Managed by Ananya P.