# Auto Listing Sync: Cars.co.za to Web Portal

An end-to-end Python & Playwright automation pipeline designed to scrape used vehicle listings from `cars.co.za` and automatically populate dynamic multi-step advertisement forms on target web portals.

---

## 💡 Key Highlights

* **Automated Web Scraping**: Extracts comprehensive vehicle metadata including title, trim variant, dynamic Google dealer rating, specs, vehicle highlights, features, and local image downloads.
* **Interactive Batch Processing**: Human-in-the-loop queue management. Displays vehicle source links, auto-fills ad forms, allows visual inspection before submission, and logs confirmed listings.
* **Smart Data Normalization**: Automatically strips unit strings (`km`), standardizes drive types (`4x2`/`4x4`), unmasks hidden phone numbers, and injects descriptions into TinyMCE iFrame editors.
* **Customizable Exclusion Filtering**: Built-in support to skip specific models, sponsored cars, or duplicate listings across batch runs.
* **Queue Recovery & Logging**: Automatically removes posted listings from the active JSON queue, cleans up local media, and logs completed titles directly to `output/carlist.txt`.

---

## ⚙️ Architecture & Pipeline Flow

The system operates in two independent stages:
              ┌──────────────────────────────┐
              │   1. Inventory Scraping      │
              │        (scraper.py)          │
              └──────────────┬───────────────┘
                             │
                             ▼
                 data/ & output/*.json
                (inventory.json / images)
                             │
                             ▼
              ┌──────────────────────────────┐
              │  2. Batch Auto-Form Filler   │
              │    (batch_processor.py)      │
              └──────────────┬───────────────┘
                             │
                             ▼
               Target Web Portal / Post Ad

### 1. Data Collection (`scraper.py`)
* Navigates `cars.co.za` search results page by page.
* Filters out sponsored listings and checks URL slugs against an exclusion list.
* Scrolls to the dealer section to trigger lazy-loaded Google Reviews and unmask dealer contact numbers.
* Saves normalized metadata into `data/inventory.json` and downloads the first 5 images per car to `data/images/<source_id>/`.

### 2. Form Auto-Filler (`batch_processor.py` & `form_filler.py`)
* Loads queued ads from `output/ads_ready_for_form.json` (or `data/inventory.json`).
* Uses a persistent Chromium session to maintain portal authentication.
* Handles AJAX DOM mutations for hierarchical categories (*Vehicles → Cars → Used cars*).
* Fills all technical specs, uploads local images, and waits for user confirmation (`y/n`).
* Appends posted titles to `output/carlist.txt` and removes completed records from the queue.

---

## 🗺️ Field Mapping Matrix

| Source Key (`inventory.json`) | Portal Form Element | Processing & Normalization Rules |
| :--- | :--- | :--- |
| `title` | Ad Title | Primary vehicle title string |
| `title description` / `variant` | Variant / Subtitle | Submodel trim (e.g., *2.0D XLT Auto*) |
| `year` | Registration Year | 4-digit year format |
| `Kilometers driven` | Mileage | Strips `"km"`, extracts pure digits |
| `transmission` | Transmission | Standardized (`Automatic` / `Manual`) |
| `fuel` | Fuel Type | Standardized (`Petrol` / `Diesel` / `Hybrid` / `Electric`) |
| `4x2 / 4x4` | Drive Type | Preserved as lowercase (`4x2` / `4x4`) |
| `price` | Price (ZAR) | Extracted numeric string |
| `dealer_name` | Dealer Name | Extracted seller name |
| `dealer_address` | Location | Formatted seller town & province |
| `Dealer average rating` | Rating & Reviews | Triggers dynamic widget/modal to parse score & count (e.g., `4.8 (630 reviews)`) |
| `description` | Full Description | Injected into TinyMCE rich text editor iFrame |
| `features` | Features / Accessories | Array converted to itemized spec tags |
| `vehicle highlights` | Vehicle Highlights | Highlight summary block |
| `images` | Image Uploader | Uploads up to 5 local `.jpg` files from `data/images/<source_id>/` |

---

## 🛠️ Exclusion Filtering

To prevent scraping unwanted, rare, or non-target vehicles, `scraper.py` includes a model exclusion list (`EXCLUDED_MODELS`).

> **Note**: The default exclusion array contains preset target models. Users can customize `EXCLUDED_MODELS` inside `scraper.py` by adding or removing exact model name strings to fit their own inventory requirements:

```python
# Custom model exclusions (Matches against URL slugs and extracted titles)
EXCLUDED_MODELS = [
    "2021 Toyota Fortuner",
    "2023 Ford Ranger",
    # Add your own custom titles here...
]
🚀 Quick Start
1. Installation
PowerShell
# Clone the repository
git clone [https://github.com/YOUR_USERNAME/car-ad-automation.git](https://github.com/YOUR_USERNAME/car-ad-automation.git)
cd car-ad-automation

# Install Python dependencies
pip install playwright requests beautifulsoup4 pillow python-dotenv pandas

# Install Playwright Chromium browser
playwright install chromium
2. Run Scraper
Scrape inventory directly from cars.co.za:

PowerShell
python scraper.py
3. Run Batch Form Processor
Launch the interactive batch auto-filler:

PowerShell
python batch_processor.py
Navigate to the blank Post Ad page on the portal in the opened browser window.

Press ENTER in the terminal to auto-fill all fields and upload images.

Review the form, click Post Ad, and enter y in the terminal to log the car to output/carlist.txt and advance to the next listing.

📁 Repository Structure
Plaintext
car-ad-automation/
├── scraper.py           # Inventory collection & image downloader script
├── batch_processor.py   # Queue manager & CLI interface
├── form_filler.py       # Core Playwright DOM automation engine
├── config.py            # System configuration & file paths
│
├── data/
│   ├── inventory.json   # Active inventory data store
│   └── images/          # Local downloaded vehicle images (by source_id)
│
├── output/
│   ├── cars.json        # Output inventory JSON
│   └── carlist.txt      # Text log of successfully posted car titles
│
└── browser_profile/     # Persistent browser session state
📄 License
This repository is maintained for custom automation workflows. Distributed under the MIT License.


---

### Commands to Push to GitHub

Run these commands in your PowerShell terminal to initialize Git (if not already initialized), add your updated files, and push to GitHub:

```powershell
# 1. Initialize git (if new repository)
git init

# 2. Add remote origin (replace with your actual GitHub repo URL)
git remote add origin https://github.com/YOUR_USERNAME/car-ad-automation.git

# 3. Stage all files
git add .

# 4. Commit changes
git commit -m "Add complete scraper, batch processor, and documentation"

# 5. Push to main branch
git branch -M main
git push -u origin main