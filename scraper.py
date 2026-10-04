import re
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
SCRAPER_PROFILE_DIR = BASE_DIR / "browser_profile_scraper"

CARS_JSON = OUTPUT_DIR / "cars.json"
INVENTORY_JSON = DATA_DIR / "inventory.json"

# All excluded models preserved
EXCLUDED_MODELS = [
   "2023 Suzuki Eeco", "2025 BMW X1", "2026 Suzuki Swift", "2015 Hyundai Grand i10", "2020 Volkswagen Caddy", "2018 Mazda CX-5", "2021 Mazda CX-3", "2025 Mahindra XUV 700", "2011 Toyota Land Cruiser 200", "2026 Suzuki S-Presso", "2015 BMW X3", "2024 Audi Q5", "2008 Volkswagen Polo", "2026 Suzuki Ignis", "2026 Chery Tiggo Cross", "2026 Suzuki Eeco", "2026 GWM Ora 5", "2020 Hyundai Venue", "2023 Haval H6 GT", "2019 Hyundai Grand i10", "2017 Mercedes-Benz GLC", "2021 Hyundai Creta", "2024 Ford Mustang", "2018 Hyundai Creta", "2025 Suzuki Swift", "2013 Toyota Land Cruiser 200", "2021 Nissan NP200", "2006 Volkswagen Pat", "2015 Toyota Fortuner", "2018 Toyota Etios", "2020 Renault Kwid", "2014 Chevrolet Utility", "2017 Mercedes-Benz C-Cl", "2022 Suzuki Jimny", "2019 Mercedes-Benz C-Cl", "2026 GAC GS3 Emzoom", "2017 Mercedes-Benz GLC", "2019 Toyota Fortuner", "2023 Renault Kwid", "2024 Chery Tiggo 4 Pro", "2023 Volkswagen T-Roc", "2023 Mercedes-Benz Vito", "2022 Haval H9","2021 BMW M4", "2025 Volkswagen Golf", "2022 Volkswagen Polo", "2026 Chery Tiggo 7 Pro", "2017 Hyundai Tucson", "2025 Mahindra XUV 3XO", "2024 Kia Sorento", "2024 Jaecoo J7", "2023 Toyota Corolla Cross","2023 Hyundai Tucson","2026 Kia Carens","2021 Toyota Fortuner", "2026 Kia Tasman", "2026 Mercedes-Benz GLE", "2023 Toyota Land Cruiser 300", "2023 Toyota Hilux", "2026 Alfa Romeo Junior", "2026 Ford Everest", "2023 Ford EcoSport", "2024 Suzuki Ertiga", "2023 Ford Ranger", "2021 Mahindra XUV 500", "2024 Toyota Hilux", "2019 Suzuki Vitara", "2015 Toyota Corolla", "2018 BMW X5", "2020 Ford Figo", "2016 Toyota Fortuner", "2021 Volkswagen T-Cross", "2011 Mercedes-Benz Vito", "2025 Ford Puma", "2026 Land Rover Defender 110", "2008 Toyota Auris", "2021 Hyundai Venue", "2019 Mitsubishi Pajero", "2021 GWM Steed 5", "2014 Ford Ranger", "2021 Land Rover Range Rover Sport", "2023 Toyota Land Cruiser 79", "2016 Hyundai i10", "2016 Toyota Hilux", "2022 Renault Kiger", "2024 Ford Everest", "2022 Nissan Magnite", "2026 Toyota Land Cruiser 76", "2026 Mitsubishi Triton", "2026 Renault Kwid", "2024 Renault Kiger", "2023 Land Rover Defender 110", "2022 Mercedes-Benz C-Cl", "2022 Volkswagen Tiguan", "2018 Volkswagen Golf", "2026 Toyota Land Cruiser 79", "2021 Datsun Go", "2024 Ford Ranger", "2024 Toyota Corolla Cross", "2026 Suzuki Fronx", "2023 Toyota Urban Cruiser", "2024 Mazda 2", "2020 Volkswagen Kombi", "2021 Citroen C3", "2011 BMW 1 Series", "2013 Toyota Land Cruiser 79", "2011 Volkswagen Pat", "2026 Suzuki Jimny", "2020 Suzuki Swift", "2022 Audi S3", "2017 Volkswagen Caravelle", "2026 Subaru WRX", "2024 Subaru Crosstrek", "2025 Toyota Vitz", "2019 Ford Ranger", "2015 Nissan NP300", "2025 Suzuki Baleno", "2025 Jaecoo J7", "2025 Chery Tiggo Cross", "2023 Audi Q3", "2019 Ford Fiesta", "2023 Mercedes-Benz A-Cl", "2025 Mitsubishi Outlander Sport", "2022 Kia Sonet", "2025 Toyota Urban Cruiser", "2018 Kia Sportage", "2022 Chery Tiggo 4 Pro", "2025 Mazda CX-5", "2020 BMW X5", "2024 Volkswagen Polo", "2024 BMW M3", "2021 Volkswagen Transporter", "2024 Suzuki Baleno", "2023 Hyundai Venue", "2014 Ford Figo", "2022 Chery Tiggo 7 Pro", "2020 Honda Jazz", "2024 Nissan NP200", "2024 Volkswagen T-Roc", "2015 Ford Focus", "2019 Ford Figo", "2018 Nissan X-Trail", "2025 Toyota Hilux", "2012 Audi A1", "2025 Toyota Rumion", "2026 Toyota Fortuner", "2022 Toyota Quantum", "2016 Ford Ranger", "2018 Volkswagen Kombi", "2014 Volkswagen Caravelle", "2026 Lexus LX", "2026 Volkswagen Polo Vivo", "2024 Haval Jolion", "2026 Haval H6", "2025 Haval H6", "2020 Audi A3", "2023 Nissan Magnite", "2026 Mercedes-Benz C-Cl", "2017 Audi Q7", "2023 Mercedes-AMG E-Cl", "2023 BMW X5", "2016 Nissan X-Trail", "2026 GWM P500", "2013 Toyota Hilux", "2023 Mazda CX-60", "2016 Mercedes-Benz GLE", "2019 Honda HR-V", "2023 BAIC X55", "2014 Lexus IS", "2014 Volkswagen Polo", "2024 Suzuki Ciaz", "2017 Volkswagen Polo", "2023 Isuzu D-Max", "2022 Suzuki Ciaz", "2019 Toyota Corolla", "2022 Nissan NP200", "2021 Volkswagen Polo Vivo", "2026 Omoda C9", "2008 Volkswagen Golf", "2019 Kia Rio", "2024 Renault Triber", "2023 Land Rover Discovery Sport", "2022 Toyota Land Cruiser 76", "2026 Chery Tiggo 8 Pro", "2026 Jetour X70", "2026 Volkswagen Amarok", "2026 Mercedes-Benz A-Cl", "2021 MINI Hatch", "2016 Audi A4", "2019 Audi TT", "2021 Suzuki Ciaz", "2020 Mitsubishi Outlander", "2012 BMW 1 Series", "2023 BMW X4", "2018 BMW 5 Series", "2026 Volkswagen Polo", "2015 Dodge Journey", "2023 Suzuki Ertiga", "2020 Kia K-Series Pick-Up", "2023 Chery Tiggo 4 Pro", "2014 BMW X4", "2013 Ford Ranger", "2014 Toyota Corolla", "2025 Mahindra Scorpio N", "2011 Toyota Quantum", "2008 Toyota Avanza", "2007 Toyota Avanza", "2018 Mazda 2", "2017 Toyota Aygo", "2026 Hyundai i20", "2021 Volkswagen Polo", "2026 Toyota Hilux", "2024 Toyota Fortuner", "2021 Haval Jolion", "2022 Toyota Hilux", "2024 Land Rover Defender 110", "2016 Renault Clio", "2026 Suzuki Ertiga", "2024 Toyota Starlet Cross", "2012 Toyota FJ Cruiser", "2026 Jetour T1", "2025 Suzuki Ertiga", "2020 Toyota Fortuner", "2023 Mercedes-Benz V-Cl", "2026 Mahindra Scorpio N", "2011 Chevrolet Lumina", "2024 Audi Q3", "2023 Renault Kiger", "2022 Kia Seltos", "2026 Kia Picanto", "2024 Volkswagen Kombi", "2018 Ford Fiesta", "2025 Lexus GX", "2021 Suzuki S-Presso", "2026 Toyota Urban Cruiser", "2023 BMW X1", "2015 Mercedes-Benz C-Cl", "2023 BMW 2 Series", "2024 Toyota Starlet", "2013 Renault Clio", "2019 Volkswagen Caddy", "2018 Hyundai i20", "2013 Volvo V40", "2026 Jetour T2", "2015 Mitsubishi Mirage", "2016 Honda CR-V", "2026 Isuzu D-Max", "2017 Mercedes-AMG SLC", "2018 Ford Ranger", "2021 Isuzu D-Max", "2013 Volkswagen Polo", "2017 Honda BR-V", "2022 Mercedes-Benz S-Cl", "2020 BMW 3 Series", "2022 GWM P-Series", "2020 Mercedes-Benz C-Cl", "2020 Mazda 2", "2022 GWM Steed 5", "2014 Volkswagen Golf", "2017 Volkswagen Touareg", "2018 Mercedes-AMG GLE", "2024 Citroen C3", "2018 Haval H1", "2020 Volkswagen T-Cross", "2015 Lexus RC", "2023 BMW 4 Series", "2018 Isuzu KB", "2016 Chevrolet Utility", "2016 Volkswagen Polo", "2022 Isuzu D-Max", "2024 Ford Puma", "2025 GWM P-Series", "2016 Ford Figo", "2026 GWM P-Series", "2025 Changan CS75", "2022 Hyundai Atos", "2026 Geely E5 EM-i", "2025 Kia Sonet", "2024 Kia Sonet", "2019 Hyundai Tucson", "2022 Haval Jolion", "2022 BMW 1 Series", "2023 Volkswagen Polo Vivo", "2023 Volkswagen T-Cross", "2018 Hyundai Tucson", "2025 Renault Kiger", "2026 Nissan Magnite", "2025 Nissan Magnite", "2023 Land Rover Range Rover Evoque", "2019 Honda Ballade", "2026 Opel Mokka", "2025 Hyundai Exter", "2016 Toyota Land Cruiser 79", "2023 Subaru Outback", "2026 GWM Tank 300", "2021 Toyota Starlet", "2025 Ford Ranger", "2017 Volkswagen Golf", "2016 Mercedes-AMG GLE", "2023 Audi A4", "2024 GWM Tank 300", "2018 Volvo XC60", "2023 Mitsubishi Outlander", "2020 Volvo XC60", "2013 Volkswagen Tiguan", "2013 Nissan Juke", "2023 Jeep Wrangler", "2023 Jeep Grand Cherokee", "2013 Toyota Etios", "2023 Toyota Corolla Quest", "2015 Ford EcoSport", "2017 Ford EcoSport", "2013 Mercedes-Benz C-Cl", "2020 Ford Kuga", "2023 BMW 3 Series", "2018 BMW 1 Series", "2026 Volkswagen T-Cross", "2025 Chery Tiggo 4 Pro", "2025 Toyota Corolla Cross", "2013 MINI Convertible", "2026 Nissan Navara", "2023 Hyundai Atos", "2024 Mahindra Scorpio N", "2020 Ford Ranger", "2021 Volvo XC40", "2018 Kia K-Series Pick-Up", "2021 BMW M5", "2018 Nissan Qashqai", "2019 BMW 2 Series", "2018 Toyota Hilux", "2019 Volkswagen Polo", "2024 Kia K-Series Pick-Up", "2017 Audi A4", "2025 Hyundai Venue", "2021 Toyota Urban Cruiser", "2025 Suzuki Fronx", "2022 BMW 3 Series", "2022 Ford Ranger", "2026 Renault Triber", "2026 Ford Ranger", "2026 Toyota Starlet", "2013 Nissan Murano", "2020 Land Rover Range Rover Evoque", "2023 Mazda CX-3", "2022 Volkswagen Amarok", "2018 MINI Hatch", "2017 Ford Fiesta", "2015 MINI Countryman", "2022 Toyota Corolla Quest", "2025 Toyota Land Cruiser 79", "2021 Kia Sportage", "2016 Renault Captur", "2025 Toyota RAV4", "2020 Land Rover Defender 110", "2026 BYD Seal", "2018 Mercedes-Benz C-Cl", "2018 Toyota Aygo", "2015 Kia Rio", "2024 Suzuki Swift", "2014 BMW 5 Series", "2026 Foton Tunland", "2023 Isuzu Mu-x", "2025 Chery Tiggo 7 Pro", "2017 Ford Ranger", "2021 Audi Q8", "2020 Haval H6", "2022 JAC T8", "2025 Jetour T1", "2024 Suzuki Jimny", "2025 Suzuki Dzire", "2019 Renault Kwid", "2025 Haval Jolion", "2020 Renault Sandero", "2020 Nissan NP200", "2024 Nissan Magnite", "2021 Ford Ranger", "2022 Hyundai Grand i10", "2026 Geely E2", "2020 Mazda CX-3", "2019 BMW 3 Series", "2021 BMW 3 Series", "2017 Datsun Go", "2023 Hyundai i20", "2026 Renault Trafic", "2022 Volkswagen T-Roc", "2026 Lepas L4", "2020 Mercedes-Benz GLA", "2020 Kia Picanto", "2024 Kia Pegas", "2025 Isuzu D-Max", "2013 Toyota 86", "2022 Toyota Urban Cruiser", "2023 GWM P-Series", "2025 Toyota Starlet Cross", "2025 Volkswagen Polo", "2025 Toyota Land Cruiser 300", "2026 Omoda C7", "2026 Mahindra Pik Up", "2025 Volkswagen Polo Vivo", "2025 Kia Pegas", "2023 Kia Pegas", "2024 Nissan Navara", "2021 Kia Rio"
]


def is_excluded_url(url: str) -> bool:
    """Check if a URL slug contains any of the excluded car titles."""
    clean_url = url.lower().replace('-', ' ')
    for model in EXCLUDED_MODELS:
        normalized_model = " ".join(model.strip().lower().split())
        if normalized_model in clean_url:
            return True
    return False


def is_excluded_title(title: str) -> bool:
    """Check if extracted title matches any excluded car."""
    normalized_title = " ".join(title.strip().lower().split())
    for model in EXCLUDED_MODELS:
        normalized_model = " ".join(model.strip().lower().split())
        if normalized_model in normalized_title or normalized_title in normalized_model:
            return True
    return False


def load_existing_scraped_urls() -> set:
    """Load previously scraped URLs/IDs to avoid duplicating records across runs."""
    seen = set()
    for file_path in [CARS_JSON, INVENTORY_JSON]:
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                for item in data:
                    if isinstance(item, dict):
                        if "Source Link" in item:
                            seen.add(item["Source Link"])
                        if "source_url" in item:
                            seen.add(item["source_url"])
            except Exception:
                pass
    return seen


def save_progress(cars: List[Dict[str, Any]]):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    json_data = json.dumps(cars, indent=4, ensure_ascii=False)
    CARS_JSON.write_text(json_data, encoding="utf-8")
    INVENTORY_JSON.write_text(json_data, encoding="utf-8")


def print_realtime_log(car_data: Dict[str, Any], current_count: int, target_count: int):
    print("\n" + "=" * 80)
    print(f" [EXTRACTED RECORD {current_count}/{target_count}] -> ID: {car_data['source_id']}")
    print("=" * 80)
    print(f" 1. Title                  : {car_data['title']}")
    print(f" 2. Title Description      : {car_data['title description']}")
    print(f" 3. Year                   : {car_data['year']}")
    print(f" 4. Kilometers Driven      : {car_data['Kilometers driven']}")
    print(f" 5. Transmission           : {car_data['transmission']}")
    print(f" 6. Fuel                   : {car_data['fuel']}")
    print(f" 7. 4x2 / 4x4              : {car_data['4x2 / 4x4']}")
    print(f" 8. Body Colour            : {car_data['body colour']}")
    print(f" 9. Bottom Condition       : {car_data['condition']}")
    print(f"10. Seats                  : {car_data['seats']}")
    print(f"11. Price Summary          : \n{car_data['price summary']}")
    print(f"12. Dealer Name            : {car_data['dealer_name']}")
    print(f"13. Dealer Address         : {car_data['dealer_address']}")
    print(f"14. Dealer Average Rating  : {car_data['Dealer average rating']}")
    
    feats = car_data['features'] if isinstance(car_data['features'], list) else []
    feats_preview = feats[:3] if feats else ["."]
    print(f"15. Features (Sample)      : {feats_preview} ... (Total: {len(feats)})")
    
    print(f"16. Contact Number         : {car_data['contact_number']}")
    print(f"17. Source Link            : {car_data['Source Link']}")
    
    hl = car_data['vehicle highlights'] if isinstance(car_data['vehicle highlights'], list) else []
    hl_preview = hl[:2] if hl else ["."]
    print(f"18. Vehicle Highlights     : {hl_preview}")
    
    print(f"19. Price (Rand)           : R {car_data['price']}")
    
    print(f"20. Full Description       : \n{car_data['description']}")
    
    print(f"21. Downloaded Images      : {len(car_data['images'])} Files Saved")
    print(f"22. Bottom Contact Address : {car_data['dealer_address']}")
    print("-" * 80 + "\n")


def scrape_single_car_detail(page, url: str) -> Dict[str, Any]:
    id_match = re.search(r'/(\d+)/?$', url)
    source_id = id_match.group(1) if id_match else f"car_{int(time.time()*1000)}"

    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(3500)

    # 1. Title & Variant Extraction
    title = "."
    variant = "."
    
    title_el = page.query_selector("h1")
    if title_el:
        full_h1 = title_el.inner_text().strip()
        lines = [l.strip() for l in full_h1.split("\n") if l.strip()]
        if lines:
            title = lines[0]
            if len(lines) > 1:
                variant = lines[1]

    # Check extracted title against exclusion list
    if is_excluded_title(title):
        print(f"[SKIP] Excluded model title detected: '{title}'")
        return None

    # Target variant/subtitle element placed directly under title element
    if variant == "." or not variant:
        subtitle_el = page.query_selector("h1 + p, h1 + div, div[class*='title'] + p, div[class*='heading'] + p, p[class*='mantine-Text-root']")
        if subtitle_el:
            sub_txt = subtitle_el.inner_text().strip()
            if sub_txt and len(sub_txt) < 80 and not re.match(r'^(19|20)\d{2}$', sub_txt) and "km" not in sub_txt.lower():
                variant = sub_txt

    # 2. Extract Price & Price Summary Block
    price_val = "0"
    pricing_summary = "."

    # Wait for the exact Pricing Summary box to render completely
    try:
        page.wait_for_selector("xpath=//*[contains(text(), 'Pricing Summary')]", timeout=5000)
    except Exception:
        pass

    # Target the container box holding Pricing Summary, Main Price, and Monthly Estimate
    p_box = page.query_selector("xpath=//*[text()='Pricing Summary']/ancestor::div[2]")
    if not p_box:
        p_box = page.query_selector("div[class*='PriceSummary_container']")

    if p_box:
        raw_lines = [line.strip() for line in p_box.inner_text().split("\n") if line.strip()]
        clean_lines = []
        for line in raw_lines:
            # Filter out UI action buttons like Track Price, Recalculate, or Badges
            if any(bad in line.lower() for bad in ["track price", "recalculate", "fair deal", "good deal", "great deal"]):
                continue
            clean_lines.append(line)

        if clean_lines:
            pricing_summary = "\n".join(clean_lines)

            # Extract price value from line 2 of the summary if present
            for line in clean_lines:
                if re.search(r'R\s*[\d\s]+', line) and "Est." not in line and "Summary" not in line:
                    digits = re.sub(r'[^\d]', '', line)
                    if digits and len(digits) >= 4:
                        price_val = digits
                        break

    # Fallback to direct price selector if container line parsing missed price_val
    if price_val == "0":
        price_el = page.query_selector("h2[class*='price'], p[class*='price'], span[class*='price'], div[class*='Price_price']")
        if price_el:
            digits = re.sub(r'[^\d]', '', price_el.inner_text().strip())
            if digits and len(digits) >= 4:
                price_val = digits

    if price_val == "0":
        p_match = re.search(r'-R(\d+)-', url)
        if p_match:
            price_val = p_match.group(1)

   # 3. Specs, Condition, Seats & Body Colour
    year = "."
    mileage = "."
    transmission = "."
    fuel = "."
    drive_type = "."
    colour = "."
    condition_val = "."
    seats_val = "."

    cond_el = page.query_selector("xpath=//*[contains(text(), 'condition') or contains(text(), 'Condition')]")
    if cond_el:
        cond_text = cond_el.inner_text().strip()
        if len(cond_text) < 35 and "\n" not in cond_text:
            condition_val = cond_text

    spec_items = page.query_selector_all("div[class*='spec-icon-text'], p[class*='mantine-Text-root']")
    for sp in spec_items:
        txt = sp.inner_text().strip()
        if not txt or len(txt) > 40 or "\n" in txt:
            continue
        
        if any(bad in txt.lower() for bad in ["bluetooth", "aircon", "airbag", "steering", "abs"]):
            continue

        if seats_val == "." and re.search(r'\b([1-9]|10|12)\s*(?:seats|seater|seat)\b', txt, re.I):
            seats_val = txt
        elif year == "." and re.match(r'^(19|20)\d{2}$', txt):
            year = txt
        elif mileage == "." and re.search(r'\b\d+[\d\s,]*\s*km\b', txt, re.I):
            mileage = txt
        elif transmission == "." and txt.lower() in ["manual", "automatic", "auto"]:
            transmission = txt.capitalize()
        elif fuel == "." and txt.lower() in ["petrol", "diesel", "hybrid", "electric"]:
            fuel = txt.capitalize()
        elif drive_type == "." and txt.lower() in ["4x2", "4x4", "awd", "fwd", "rwd"]:
            drive_type = txt.lower() if "4x" in txt.lower() else txt.capitalize()
        elif colour == "." and txt.lower() in ["white", "black", "silver", "grey", "gray", "red", "blue", "brown", "gold", "orange", "beige", "green", "yellow", "frozen white"]:
            colour = txt.capitalize()

    if year == ".":
        y_match = re.search(r'/(19|20\d{2})-', url)
        if y_match: year = y_match.group(1)

    if drive_type == ".":
        drive_type = "4x4" if "4x4" in url.lower() or "4x4" in title.lower() else ("4x2" if "4x2" in url.lower() or "4x2" in title.lower() else ".")

    # Force drive_type lowercase check
    drive_type = str(drive_type).lower() if "4x" in str(drive_type).lower() else drive_type
    # 4. Dealer Details & Location
    dealer_name = "."
    dealer_address = "."
    dealer_rating = "."

    d_name_el = page.query_selector("xpath=//*[contains(text(), 'View Map') or contains(text(), 'Distance From You')]/ancestor::div[contains(@class, 'Seller') or contains(@class, 'seller') or contains(@class, 'mantine')][1]//descendant::*[self::h2 or self::h3 or self::h4 or contains(@class, 'name') or contains(@class, 'title') or contains(@class, 'Text')][1]")
    if not d_name_el:
        d_name_el = page.query_selector("div[class*='Seller_name'], div[class*='seller_name'], a[href*='/dealer/'], div[class*='SellerCard'] h3, div[class*='SellerCard'] h2")

    if d_name_el:
        raw_d_name = d_name_el.inner_text().strip()
        if raw_d_name and len(raw_d_name) < 100:
            dealer_name = raw_d_name.split("\n")[0].strip()

    if dealer_name == "." or not dealer_name:
        side_dealer_el = page.query_selector("xpath=//*[contains(@class, 'WhatsApp') or contains(text(), 'WhatsApp')]/ancestor::div[1]/preceding-sibling::*[1]")
        if side_dealer_el:
            dealer_name = side_dealer_el.inner_text().strip().split("\n")[0]

    d_addr_el = page.query_selector("div[class*='Seller_address'], span[class*='location-text'], p[class*='mantine-Text-root']:has-text('Gauteng'), p[class*='mantine-Text-root']:has-text('Western Cape')")
    if d_addr_el:
        dealer_address = d_addr_el.inner_text().replace("Distance From You", "").replace("Location", "").strip()

    if dealer_address == "." or not dealer_address:
        loc_match = re.search(r'-(Western-Cape|Gauteng|KwaZulu-Natal|Eastern-Cape|Free-State|Limpopo|Mpumalanga|North-West|Northern-Cape)-([A-Za-z]+)/\d+/?$', url)
        if loc_match:
            dealer_address = f"{loc_match.group(2)}, {loc_match.group(1).replace('-', ' ')}"

# --- ACCURATE DEALER RATING EXTRACTION ---
    try:
        # Step A: Scroll to seller card and force wait for dynamic review element
        seller_box = page.query_selector("xpath=//*[contains(text(), 'Distance From You') or contains(text(), 'View Map')]")
        if seller_box:
            seller_box.scroll_into_view_if_needed()
            page.wait_for_timeout(1500)

        # Step B: Page-wide regex evaluation via JavaScript to extract rating + review count in sequence
        page_text = page.evaluate("() => document.body.innerText")
        
        # Regex captures patterns like "4.8 630 reviews", "4.8 (630 reviews)", or "4.8 \n 630 reviews"
        rating_match = re.search(r'\b([1-5]\.\d)[\s\n]*\(?([\d\s,]+[\s\n]*reviews?)\)?', page_text, re.IGNORECASE)
        if rating_match:
            dealer_rating = f"{rating_match.group(1)} ({rating_match.group(2).strip()})"
        else:
            # Fallback 1: Extract individual score and review count separately from page text
            score_m = re.search(r'\b([1-5]\.\d)\b', page_text)
            count_m = re.search(r'(\d+[\d\s,]*\s*reviews?)', page_text, re.IGNORECASE)
            if score_m and count_m:
                dealer_rating = f"{score_m.group(1)} ({count_m.group(1)})"

        # Step C: Fallback to clicking review trigger if inline text extraction missed
        if dealer_rating == ".":
            rev_trigger = page.query_selector("xpath=//*[contains(text(), 'reviews') or contains(text(), 'review')]")
            if rev_trigger and rev_trigger.is_visible():
                rev_trigger.click()
                page.wait_for_timeout(1500)

                modal_text = page.evaluate("() => document.body.innerText")
                m_score = re.search(r'\b([1-5]\.\d)\b', modal_text)
                m_count = re.search(r'(\d+[\d\s,]*\s*reviews?)', modal_text, re.IGNORECASE)

                if m_score and m_count:
                    dealer_rating = f"{m_score.group(1)} ({m_count.group(1)})"

                close_btn = page.query_selector("button[class*='close'], svg[class*='close']")
                if close_btn and close_btn.is_visible():
                    close_btn.click()
                    page.wait_for_timeout(500)
    except Exception as err:
        print(f"[WARN] Rating extraction bypassed: {err}")

    # 5. Phone Unmasking
    contact_phone = "."
    try:
        show_btn = page.query_selector("xpath=//*[contains(translate(text(), 'SHOW NUMBER', 'show number'), 'show number')]")
        if show_btn and show_btn.is_visible():
            show_btn.click()
            page.wait_for_timeout(1000)
        tel = page.query_selector("a[href^='tel:']")
        if tel:
            digits = re.sub(r'[^\d]', '', tel.inner_text().strip())
            if len(digits) >= 10:
                contact_phone = digits[:10]
    except Exception:
        pass

    # 6. Complete Description Scraping
    try:
        show_more_trigger = page.query_selector("xpath=//*[text()='Show More' or text()='show more' or contains(text(), 'Show More')]")
        if show_more_trigger and show_more_trigger.is_visible():
            show_more_trigger.click()
            page.wait_for_timeout(1000)
    except Exception:
        pass

    description_text = "."
    desc_section = page.query_selector("xpath=//*[self::h2 or self::h3 or self::div][text()='Description']/following-sibling::div")
    if not desc_section:
        desc_section = page.query_selector("div[class*='Description_description'], div[class*='description']")

    if desc_section:
        raw_text = desc_section.inner_text().strip()
        clean_lines = [
            line.strip() for line in raw_text.split("\n") 
            if line.strip() and not re.match(r'^(show\s*(more|less))$', line.strip(), re.I)
        ]
        if clean_lines:
            description_text = "\n".join(clean_lines)

    if not description_text or description_text == ".":
        description_text = f"{title} {variant}"

    # 7. Features & Vehicle Highlights
    highlights_list = []
    try:
        hl_header = page.query_selector("xpath=//*[text()='Vehicle Highlights' or contains(text(), 'Vehicle Highlights')]")
        if hl_header:
            hl_container = hl_header.query_selector("xpath=following::div[1]")
            if hl_container:
                raw_hl_text = hl_container.inner_text().strip()
                lines = [l.strip() for l in raw_hl_text.split("\n") if l.strip()]
                if lines:
                    formatted_highlight = " | ".join(lines)
                    highlights_list.append(formatted_highlight)
    except Exception:
        pass

    features_list = []
    try:
        # Click the "Features" tab on cars.co.za specifications table
        feat_tab = page.query_selector("xpath=//*[text()='Features' or contains(text(), 'Features')]")
        if feat_tab and feat_tab.is_visible():
            feat_tab.click()
            page.wait_for_timeout(1000)

        feat_elements = page.query_selector_all("td, div[class*='Vehicle_item'], div[class*='feature-item'], p[class*='mantine-Text-root']")
        for fe in feat_elements:
            txt = fe.inner_text().strip()
            if txt and txt not in features_list and len(txt) > 2 and "\n" not in txt:
                if txt.lower() not in ["features", "summary", "engine", "economy", "safety", "specifications"]:
                    features_list.append(txt)
    except Exception:
        pass

    # 8. Isolated Images Download per Source ID
    img_urls = []
    imgs = page.query_selector_all("div[class*='gallery'] img, div[class*='carousel'] img, img[class*='image']")
    for img in imgs:
        src = img.get_attribute("src") or img.get_attribute("data-src")
        if src and "http" in src and src not in img_urls and not src.endswith(".svg"):
            img_urls.append(src)
            if len(img_urls) == 5:
                break

    listing_img_dir = IMAGES_DIR / str(source_id)
    if listing_img_dir.exists():
        for old_f in listing_img_dir.glob("*"):
            try: old_f.unlink()
            except Exception: pass
    listing_img_dir.mkdir(parents=True, exist_ok=True)

    downloaded_paths = []
    for idx, img_url in enumerate(img_urls, start=1):
        try:
            res = requests.get(img_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                img_file = listing_img_dir / f"{source_id}_img_{idx}.jpg"
                img_file.write_bytes(res.content)
                downloaded_paths.append(str(img_file.resolve()))
        except Exception:
            continue

    return {
        "id": source_id,
        "source_id": source_id,
        "Source Link": url,
        "source_url": url,
        "title": title,
        "title description": variant,
        "variant": variant,
        "condition": condition_val,
        "year": year,
        "Kilometers driven": mileage,
        "transmission": transmission,
        "fuel": fuel,
        "4x2 / 4x4": drive_type,
        "body colour": colour,
        "seats": seats_val,
        "price": price_val,
        "price summary": pricing_summary,
        "dealer_name": dealer_name,
        "dealer_address": dealer_address,
        "Dealer average rating": dealer_rating,
        "contact_number": contact_phone,
        "description": description_text,
        "features": features_list,
        "vehicle highlights": highlights_list,
        "images": downloaded_paths
    }


def scrape_cars_co_za(target_count: int = 1000, start_page: int = 2):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    SCRAPER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    collected_cars = []
    seen_urls = load_existing_scraped_urls()
    current_page = start_page

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(SCRAPER_PROFILE_DIR),
            headless=False,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = context.pages[0] if context.pages else context.new_page()

        try:
            while len(collected_cars) < target_count:
                page_url = f"https://www.cars.co.za/usedcars/?sort=sort_rank&price_type=listing_price&P={current_page}"
                print(f"\n[SCRAPE] Fetching Page {current_page} | Progress: {len(collected_cars)}/{target_count}")

                try:
                    page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(2000)

                    cards = page.query_selector_all("div[class*='card']:not([class*='sponsored'])")
                    page_urls = []

                    for card in cards:
                        if card.query_selector("span:has-text('Sponsored')"):
                            continue

                        a = card.query_selector("a[href*='/for-sale/used/']")
                        if not a:
                            continue

                        href = a.get_attribute("href")
                        if href:
                            full_url = href if href.startswith("http") else f"https://www.cars.co.za{href}"
                            if re.search(r'/\d+/?$', full_url) and full_url not in seen_urls:
                                if is_excluded_url(full_url):
                                    print(f"[SKIP] Excluded model URL detected: {full_url}")
                                    continue

                                seen_urls.add(full_url)
                                page_urls.append(full_url)

                    if not page_urls:
                        anchors = page.query_selector_all("a[href*='/for-sale/used/']")
                        for a in anchors:
                            href = a.get_attribute("href")
                            if href:
                                full_url = href if href.startswith("http") else f"https://www.cars.co.za{href}"
                                if re.search(r'/\d+/?$', full_url) and full_url not in seen_urls:
                                    if is_excluded_url(full_url):
                                        print(f"[SKIP] Excluded model URL detected: {full_url}")
                                        continue

                                    seen_urls.add(full_url)
                                    page_urls.append(full_url)

                    for car_url in page_urls:
                        if len(collected_cars) >= target_count:
                            break
                        try:
                            car_data = scrape_single_car_detail(page, car_url)

                            if not car_data:
                                continue

                            if len(car_data.get("images", [])) != 5:
                                print(f"[SKIP] {car_url} - Missing 5 downloaded images.")
                                continue

                            feats = car_data.get("features", [])
                            if not feats or feats == ["."]:
                                print(f"[SKIP] {car_url} - Missing mandatory Features.")
                                continue

                            hls = car_data.get("vehicle highlights", [])
                            if not hls or hls == ["."]:
                                print(f"[SKIP] {car_url} - Missing mandatory Vehicle Highlights.")
                                continue

                            collected_cars.append(car_data)
                            save_progress(collected_cars)
                            print_realtime_log(car_data, len(collected_cars), target_count)

                        except Exception as err:
                            print(f"[WARN] Failed extracting {car_url}: {err}")

                except Exception as e:
                    print(f"[ERROR] Exception on Page {current_page}: {e}")

                current_page += 1

        finally:
            try:
                context.close()
            except Exception:
                pass


if __name__ == "__main__":
    scrape_cars_co_za(target_count=1000, start_page=2)