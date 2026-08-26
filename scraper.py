"""Cars.co.za Scraper - Strict Isolated Gallery Download (5 Images Minimum Target)."""

import re
import json
import time
import random
import requests
from pathlib import Path
from typing import Dict, Any, List
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
IMAGES_DIR = BASE_DIR / "data" / "images"
SCRAPER_PROFILE_DIR = BASE_DIR / "browser_profile_scraper"
CARS_JSON = OUTPUT_DIR / "cars.json"


def save_progress(cars: List[Dict[str, Any]]):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CARS_JSON.write_text(json.dumps(cars, indent=4, ensure_ascii=False), encoding="utf-8")


def scrape_single_car_detail(page, url: str) -> Dict[str, Any]:
    id_match = re.search(r'/(\d+)/?$', url)
    source_id = id_match.group(1) if id_match else f"car_{int(time.time()*1000)}"

    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1500)

    # 1. Unmask Contact Phone Number
    contact_phone = "."
    try:
        show_btn = page.query_selector("xpath=//*[contains(translate(text(), 'SHOW NUMBER', 'show number'), 'show number')]") or page.query_selector("[class*='show-number']")
        if show_btn and show_btn.is_visible():
            show_btn.click()
            page.wait_for_timeout(1000)

        phone_elem = page.query_selector("a[href^='tel:']") or page.query_selector("xpath=//*[contains(text(), '060') or contains(text(), '07') or contains(text(), '08')]")
        if phone_elem:
            raw_digits = re.sub(r'[^\d]', '', phone_elem.inner_text().strip())
            if len(raw_digits) >= 10:
                contact_phone = raw_digits[:10]
    except Exception:
        pass

    # 2. Extract Basic Spec Data
    title = "."
    variant = "."
    h1 = page.query_selector("h1")
    if h1:
        full_h1 = h1.inner_text().strip()
        parts = [p.strip() for p in full_h1.split("\n") if p.strip()]
        title = parts[0] if parts else "."
        if len(parts) > 1:
            variant = parts[1]

    year = "."
    mileage = "."
    transmission = "Automatic"
    fuel = "Petrol"
    drive_type = "4x2"
    colour = "."

    specs_box = page.query_selector_all("div[class*='spec'], div[class*='overview'], span[class*='badge'], div[class*='key-specs']")
    for sb in specs_box:
        t = sb.inner_text().strip()
        if re.match(r'^(19|20)\d{2}$', t):
            year = t
        elif "km" in t.lower():
            mileage = re.sub(r'[^\d]', '', t)
        elif t.lower() in ["automatic", "manual"]:
            transmission = t
        elif t.lower() in ["petrol", "diesel", "hybrid", "electric"]:
            fuel = t
        elif t.lower() in ["4x2", "4x4", "awd", "fwd", "rwd"]:
            drive_type = t
        elif t.lower() in ["grey", "white", "black", "silver", "blue", "red", "brown", "gold"]:
            colour = t.capitalize()

    price_text = "."
    price_elem = page.query_selector("span[class*='price'], div[class*='price']")
    if price_elem:
        digits = re.sub(r'[^\d]', '', price_elem.inner_text().strip())
        if digits:
            price_text = digits

    dealer_name = "."
    dealer_address = "."
    dealer_rating = "4.5"

    d_elem = page.query_selector("h2[class*='dealer'], div[class*='dealer-name'], a[href*='dealer']")
    if d_elem:
        dealer_name = d_elem.inner_text().strip()

    addr_elem = page.query_selector("span[class*='address'], div[class*='location']")
    if addr_elem:
        dealer_address = addr_elem.inner_text().strip()

    # 3. Strictly Scrape Main Hero Photo Gallery (Targeting Minimum 5 Images)
    img_urls = []
    gallery_container = page.query_selector("div[class*='gallery'], div[class*='carousel'], div[class*='slider'], div[class*='hero']")
    
    if gallery_container:
        imgs = gallery_container.query_selector_all("img")
    else:
        imgs = page.query_selector_all("div[class*='image'] img")

    for img in imgs:
        src = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("srcset")
        if src:
            src = src.split(" ")[0]
        if src and "http" in src and src not in img_urls and not src.endswith(".svg") and "logo" not in src.lower() and "dealer" not in src.lower():
            img_urls.append(src)
            if len(img_urls) == 5:
                break

    # Strictly Save Images in Isolated Folder Named by source_id
    listing_img_dir = IMAGES_DIR / source_id
    if listing_img_dir.exists():
        for old_f in listing_img_dir.glob("*"):
            try:
                old_f.unlink()
            except Exception:
                pass
    listing_img_dir.mkdir(parents=True, exist_ok=True)
    downloaded_paths = []

    for idx, img_url in enumerate(img_urls, start=1):
        try:
            res = requests.get(img_url, timeout=10)
            if res.status_code == 200:
                img_file = listing_img_dir / f"img_{idx}.jpg"
                img_file.write_bytes(res.content)
                downloaded_paths.append(str(img_file.resolve()))
        except Exception:
            continue

    return {
        "source_id": source_id,
        "source_url": url,
        "title": title,
        "variant": variant,
        "condition": "Used",
        "year": year,
        "mileage": mileage,
        "transmission": transmission,
        "fuel": fuel,
        "drive_type": drive_type,
        "colour": colour,
        "seats": ".",
        "price": price_text,
        "dealer_name": dealer_name,
        "dealer_address": dealer_address,
        "dealer_rating": dealer_rating,
        "contact_phone": contact_phone,
        "description": title,
        "features": [],
        "highlights": [],
        "images": downloaded_paths
    }


def scrape_cars_co_za(target_count: int = 1000, start_page: int = 2):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.pages[0] if context.pages else context.new_page()

        try:
            while len(collected_cars) < target_count:
                page_url = f"https://www.cars.co.za/usedcars/?sort=sort_rank&price_type=listing_price&P={current_page}"
                print(f"[SCRAPE] Page {current_page} | Progress: {len(collected_cars)}/{target_count}")

                try:
                    page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(random.randint(1500, 2500))

                    anchors = page.query_selector_all("a[href*='/for-sale/used/']")
                    page_urls = []

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
                            # Strictly verify minimum 5 images are downloaded before saving
                            if len(car_data.get("images", [])) == 5:
                                collected_cars.append(car_data)
                                save_progress(collected_cars)
                                print(f" -> [{len(collected_cars)}/{target_count}] Successfully Scraped: {car_data.get('title')} (5 Images Downloaded)")
                            else:
                                print(f" -> [SKIP] {car_url} (Found only {len(car_data.get('images', []))}/5 images)")
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