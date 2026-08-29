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
    print(f"11. Price Summary          : {car_data['price summary']}")
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
    
    desc_snippet = (car_data['description'][:80] + '...') if len(car_data['description']) > 80 else car_data['description']
    print(f"20. Description (Snippet)  : {desc_snippet}")
    
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
    
    title_el = page.query_selector("h1, .mantine-Title-root")
    if title_el:
        full_h1 = title_el.inner_text().strip()
        lines = [l.strip() for l in full_h1.split("\n") if l.strip()]
        if lines:
            title = lines[0]
            if len(lines) > 1:
                variant = lines[1]

    if variant == "." or not variant:
        sub_heading = page.query_selector("p[class*='mantine-Text-root']:has-text('TSI'), h1 + div, div[class*='variant']")
        if sub_heading:
            variant = sub_heading.inner_text().strip()

    # 2. Extract Price & Price Summary Block
    price_val = "0"
    pricing_summary = "."

    pricing_summary_el = page.query_selector("div[class*='pricing-summary'], div[class*='price-container']")
    if pricing_summary_el:
        summary_text = pricing_summary_el.inner_text().strip()
        pricing_summary = " ".join([line.strip() for line in summary_text.split("\n") if line.strip()])

    price_el = page.query_selector("p[class*='price'], span[class*='price'], div[class*='price-main']")
    if price_el:
        raw_p_text = price_el.inner_text().strip()
        digits = re.sub(r'[^\d]', '', raw_p_text)
        if digits and len(digits) >= 4:
            price_val = digits

    if price_val == "0":
        p_match = re.search(r'-R(\d+)-', url)
        if p_match:
            price_val = p_match.group(1)
            
    if pricing_summary == "." and price_val != "0":
        pricing_summary = f"Pricing Summary R {int(price_val):,}".replace(",", " ")

    # 3. Spec Row Parsing (Year, Mileage, Transmission, Fuel, Drive, Colour, Condition, Seats)
    year = "."
    mileage = "."
    transmission = "."
    fuel = "."
    drive_type = "."
    colour = "."
    condition_val = "."
    seats_val = "."

    # Check Schema structured JSON-LD first
    try:
        scripts = page.query_selector_all("script[type='application/ld+json']")
        for script in scripts:
            try:
                data = json.loads(script.inner_text().strip())
                if isinstance(data, dict) and data.get("@type") in ["Car", "Vehicle", "Product"]:
                    if "modelDate" in data or "productionDate" in data:
                        year = str(data.get("modelDate") or data.get("productionDate"))[:4]
                    if "mileageFromOdometer" in data:
                        m_val = data["mileageFromOdometer"]
                        mileage = f"{m_val.get('value', m_val)} km" if isinstance(m_val, dict) else f"{m_val} km"
                    if "vehicleTransmission" in data:
                        transmission = str(data["vehicleTransmission"]).capitalize()
                    if "fuelType" in data:
                        fuel = str(data["fuelType"]).capitalize()
                    if "color" in data:
                        colour = str(data["color"]).capitalize()
                    if "seatingCapacity" in data:
                        seats_val = str(data["seatingCapacity"])
            except Exception:
                continue
    except Exception:
        pass

    # DOM Spec Icon Bar Scanning
    spec_items = page.query_selector_all("p[class*='mantine-Text-root'], div[class*='spec-icon-text'], td, li")
    for sp in spec_items:
        txt = sp.inner_text().strip()
        if not txt or len(txt) > 40:
            continue
        
        if seats_val == ".":
            seat_m = re.search(r'\b([2-9]|10|12)\s*(?:seats|seater|seat)\b', txt, re.I)
            if seat_m:
                seats_val = seat_m.group(1)

        if "\n" in txt:
            continue

        if year == "." and re.match(r'^(19|20)\d{2}$', txt):
            year = txt
        elif mileage == "." and re.search(r'\b\d+[\d\s,]*\s*km\b', txt, re.I):
            mileage = txt
        elif transmission == "." and txt.lower() in ["manual", "automatic", "auto"]:
            transmission = txt.capitalize()
        elif fuel == "." and txt.lower() in ["petrol", "diesel", "hybrid", "electric"]:
            fuel = txt.capitalize()
        elif drive_type == "." and txt.lower() in ["4x2", "4x4", "awd", "fwd", "rwd"]:
            drive_type = txt.upper() if "4x" in txt.lower() else txt.capitalize()
        elif colour == "." and txt.lower() in ["white", "black", "silver", "grey", "gray", "red", "blue", "brown", "gold", "orange", "beige", "green"]:
            colour = txt.capitalize()
        elif condition_val == "." and txt.lower() in ["used", "demo", "new", "excellent condition"]:
            condition_val = txt.capitalize()

    # Dynamic Fallback: Check Technical Spec Tab for Seats
    if seats_val == ".":
        try:
            seats_row = page.query_selector("xpath=//*[contains(text(), 'Seats quantity') or contains(text(), 'Seats')]")
            if seats_row:
                parent_text = seats_row.evaluate("el => el.parentElement.innerText")
                digits = re.sub(r'[^\d]', '', parent_text)
                if digits:
                    seats_val = digits
        except Exception:
            pass

    # URL / Context Fallbacks
    if year == ".":
        y_match = re.search(r'/(19|20\d{2})-', url)
        if y_match:
            year = y_match.group(1)

    if drive_type == ".":
        if "4x4" in url.lower() or "4x4" in title.lower():
            drive_type = "4X4"
        elif "4x2" in url.lower() or "4x2" in title.lower():
            drive_type = "4X2"

    if transmission == ".":
        transmission = "Automatic" if "auto" in url.lower() else ("Manual" if "manual" in url.lower() else ".")

    if fuel == ".":
        if any(k in url.lower() for k in ["gd-6", "tdci", "d-4d", "cdi", "did"]):
            fuel = "Diesel"
        elif any(k in url.lower() for k in ["v6", "tsi", "tfsi", "ecoboost"]):
            fuel = "Petrol"

    if condition_val == ".":
        condition_val = "Used"

    # 4. Dealer Details & Location Extraction
    dealer_name = "."
    dealer_address = "."
    dealer_rating = "."

    d_name_el = page.query_selector("a[href*='/dealer/'], h3[class*='seller'], div[class*='dealer-name']")
    if d_name_el:
        dealer_name = d_name_el.inner_text().strip()

    d_addr_el = page.query_selector("div[class*='dealer-address'], p[class*='mantine-Text-root']:has-text('Gauteng'), span[class*='location-text']")
    if d_addr_el:
        dealer_address = d_addr_el.inner_text().replace("Distance From You", "").replace("Location", "").strip()

    if dealer_address == "." or not dealer_address:
        loc_match = re.search(r'-([A-Z][a-zA-Z\-]+-[A-Z][a-zA-Z\-]+)/\d+/?$', url)
        if loc_match:
            dealer_address = loc_match.group(1).replace("-", ", ")

    # Click Rating Popup Trigger
    try:
        rating_btn = page.query_selector("xpath=//*[contains(text(), 'reviews') or contains(text(), 'rating')]")
        if rating_btn:
            rating_btn.click()
            page.wait_for_timeout(1200)
            modal = page.query_selector("div[class*='mantine-Modal-content'], div[class*='modal']")
            if modal:
                r_match = re.search(r'\d\.\d\s*\(\d+[\d,]*\s*reviews\)', modal.inner_text(), re.I)
                if r_match:
                    dealer_rating = r_match.group(0)
            page.keyboard.press("Escape")
    except Exception:
        pass

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

    # 6. Description & Show More Expansion
    try:
        show_more = page.query_selector("xpath=//*[contains(text(), 'Show More') or contains(text(), 'show more')]")
        if show_more and show_more.is_visible():
            show_more.click()
            page.wait_for_timeout(600)
    except Exception:
        pass

    desc_block = page.query_selector("div[class*='description'], section[class*='description'], #description-content")
    description_text = desc_block.inner_text().strip() if desc_block else f"{title} {variant}"

    # 7. Features & Vehicle Highlights
    features_list = []
    feat_elements = page.query_selector_all("p[class*='mantine-Text-root'], div[class*='Vehicle_item'], div[class*='feature-item']")
    for fe in feat_elements:
        txt = fe.inner_text().strip()
        if txt and txt not in features_list and len(txt) > 2 and "\n" not in txt:
            features_list.append(txt)

    highlights_list = []
    hl_elements = page.query_selector_all("div[class*='highlight'], div[class*='key-fact']")
    for hl in hl_elements:
        txt = hl.inner_text().strip()
        if txt and txt not in highlights_list:
            highlights_list.append(txt)

    # 8. Download 5 Isolated Images
    img_urls = []
    imgs = page.query_selector_all("div[class*='gallery'] img, div[class*='carousel'] img, img[class*='image']")
    for img in imgs:
        src = img.get_attribute("src") or img.get_attribute("data-src")
        if src and "http" in src and src not in img_urls and not src.endswith(".svg"):
            img_urls.append(src)
            if len(img_urls) == 5:
                break

    listing_img_dir = IMAGES_DIR / source_id
    listing_img_dir.mkdir(parents=True, exist_ok=True)
    downloaded_paths = []

    for idx, img_url in enumerate(img_urls, start=1):
        try:
            res = requests.get(img_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if res.status_code == 200:
                img_file = listing_img_dir / f"img_{idx}.jpg"
                img_file.write_bytes(res.content)
                downloaded_paths.append(str(img_file.resolve()))
        except Exception:
            continue

    # Validation
    mandatory_specs_map = {
        "Year": year,
        "Kilometers driven": mileage,
        "Transmission": transmission,
        "Fuel": fuel,
        "4x2 / 4x4": drive_type,
        "Body colour": colour
    }
    
    missing_fields = [name for name, val in mandatory_specs_map.items() if val == "."]
    missing_count = len(missing_fields)
    
    if missing_count > 3:
        fields_str = ", ".join(missing_fields)
        raise ValueError(f"Listing skipped due to {missing_count} missing mandatory specs -> Missing Fields: [{fields_str}]")

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
    seen_urls = set()
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

                    # Exclude sponsored cards directly
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
                                seen_urls.add(full_url)
                                page_urls.append(full_url)

                    if not page_urls:
                        anchors = page.query_selector_all("a[href*='/for-sale/used/']")
                        for a in anchors:
                            href = a.get_attribute("href")
                            if href:
                                full_url = href if href.startswith("http") else f"https://www.cars.co.za{href}"
                                if re.search(r'/\d+/?$', full_url) and full_url not in seen_urls:
                                    seen_urls.add(full_url)
                                    page_urls.append(full_url)

                    for car_url in page_urls:
                        if len(collected_cars) >= target_count:
                            break
                        try:
                            car_data = scrape_single_car_detail(page, car_url)
                            if len(car_data.get("images", [])) == 5:
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