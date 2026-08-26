"""Robust Form Filler - Handles Joomla AJAX cascading categories and fills all dynamic spec fields."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class RobustFormFiller:
    def __init__(self, page: Page):
        self.page = page

    def fill_all_car_fields(self, car_data: Dict[str, Any]) -> bool:
        # 1. Fully expand the dynamic AJAX category chain
        self._select_cascading_categories()

        # 2. Extract values with fallbacks
        title = car_data.get("title") or "Used Car Listing"
        variant = car_data.get("variant") or car_data.get("title_description") or title
        km = str(car_data.get("mileage") or car_data.get("kilometer") or car_data.get("kilometers_driven") or ".").replace("km", "").strip()
        fuel = str(car_data.get("fuel") or car_data.get("engine") or "Petrol")
        colour = str(car_data.get("colour") or car_data.get("color") or ".")
        price_val = str(car_data.get("price", "0")).replace("R", "").replace(" ", "").strip()
        
        dealer_name = car_data.get("dealer_name") or "."
        dealer_addr = car_data.get("dealer_address") or car_data.get("address") or "."
        dealer_rating = str(car_data.get("dealer_rating") or car_data.get("rating") or "4.5")
        phone = str(car_data.get("contact_number") or car_data.get("contact_phone") or car_data.get("phone") or ".")
        source_url = car_data.get("source_url") or car_data.get("source_link") or "."
        
        features = car_data.get("features") or "."
        highlights = car_data.get("highlights") or "."
        pricing_summary = car_data.get("pricing_summary") or f"Pricing Summary R {price_val}"

        # 3. Direct field mapping rules
        field_assignments = [
            (["title"], title),
            (["title description", "description title", "variant"], variant),
            (["condition"], "Used"),
            (["year"], str(car_data.get("year") or ".")),
            (["kilometer", "km", "mileage", "kilometers driven"], km),
            (["engine", "fuel"], fuel),
            (["vehicle"], variant),
            (["colour", "color"], colour),
            (["interior colour"], "."),
            (["comfort", "features"], features),
            (["lights"], "."),
            (["interior"], "."),
            (["seating", "seats"], str(car_data.get("seats") or ".")),
            (["instruments"], "."),
            (["exterior", "highlights", "vehicle highlights"], highlights),
            (["pricing summary"], pricing_summary),
            (["dealer name"], dealer_name),
            (["dealer address"], dealer_addr),
            (["dealer average rating", "rating"], dealer_rating),
            (["contact number", "phone"], phone),
            (["source link", "source url"], source_url),
            (["price"], price_val),
            (["address"], dealer_addr),
        ]

        # 4. Fill text inputs and textareas
        for keywords, val in field_assignments:
            if val and str(val).strip() != "":
                self._fill_field_by_keywords(keywords, str(val).strip())

        # 5. Fill main dropdowns
        self._force_dropdown_selection("currency", "R (Rand)")
        self._force_dropdown_selection("tagid", "Sale")
        self._force_dropdown_selection("location", "South Africa")

        # 6. Fill description iframe
        desc_content = car_data.get("description") or title
        self._fill_tinymce_description(desc_content)

        return True

    def _select_cascading_categories(self):
        """Hardcodes exact option values and forces the website to expand the full AJAX form."""
        try:
            # 1. Main Category: Select 'Vehicles' (Value = 6)
            selects = self.page.query_selector_all("select")
            if len(selects) >= 1:
                selects[0].select_option(value="6")
                selects[0].evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                self.page.wait_for_timeout(1500)

            # 2. Subcategory: Select EXACT 'Cars' (Skip 'Cars - Parts')
            selects = self.page.query_selector_all("select")
            if len(selects) >= 2:
                sub_select = selects[1]
                opts = sub_select.query_selector_all("option")
                target_value = None
                
                # Iterate through options to match EXACT 'Cars' or 'Used Cars' (explicitly ignoring 'Parts')
                for opt in opts:
                    txt = opt.inner_text().strip()
                    val = opt.get_attribute("value")
                    if txt.lower() == "cars" or txt.lower() == "used cars":
                        target_value = val
                        break
                    elif "cars" in txt.lower() and "parts" not in txt.lower() and val != "-1":
                        target_value = val

                if target_value:
                    sub_select.select_option(value=target_value)
                    sub_select.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                    self.page.wait_for_timeout(2000)

            # 3. Third Level: Select 'Used cars in South Africa'
            selects = self.page.query_selector_all("select")
            if len(selects) >= 3:
                third_select = selects[2]
                opts = third_select.query_selector_all("option")
                for opt in opts:
                    txt = opt.inner_text().strip().lower()
                    if "south africa" in txt or "used cars in south africa" in txt:
                        third_select.select_option(value=opt.get_attribute("value"))
                        third_select.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                        self.page.wait_for_timeout(2000)
                        break
        except Exception as e:
            logger.warning(f"Category selection error: {e}")
    def _fill_field_by_keywords(self, keywords: List[str], value: str):
        val_str = str(value).strip()
        elements = self.page.query_selector_all("input[type='text'], input[type='number'], textarea")
        
        for elem in elements:
            try:
                if not elem.is_visible():
                    continue
                name_attr = (elem.get_attribute("name") or "").lower()
                id_attr = (elem.get_attribute("id") or "").lower()
                placeholder = (elem.get_attribute("placeholder") or "").lower()
                parent_txt = elem.evaluate("el => el.parentElement?.parentElement?.innerText || el.parentElement?.innerText || ''").lower()

                if any(kw in name_attr or kw in id_attr or kw in placeholder or kw in parent_txt for kw in keywords):
                    elem.click()
                    elem.fill("")
                    elem.fill(val_str)
                    return
            except Exception:
                continue

    def _force_dropdown_selection(self, field_keyword: str, target_text: str):
        try:
            selects = self.page.query_selector_all("select")
            for sel in selects:
                if not sel.is_visible():
                    continue
                name_attr = (sel.get_attribute("name") or "").lower()
                id_attr = (sel.get_attribute("id") or "").lower()
                parent_txt = sel.evaluate("el => el.parentElement?.innerText || ''").lower()

                if field_keyword.lower() in name_attr or field_keyword.lower() in id_attr or field_keyword.lower() in parent_txt:
                    options = sel.query_selector_all("option")
                    for opt in options:
                        if target_text.lower() in opt.inner_text().strip().lower():
                            val = opt.get_attribute("value")
                            sel.select_option(value=val)
                            sel.evaluate("el => el.dispatchEvent(new Event('change', { bubbles: true }))")
                            return
        except Exception as e:
            logger.warning(f"Dropdown selection failed for {field_keyword}: {e}")

    def _fill_tinymce_description(self, content: str):
        try:
            iframe = self.page.query_selector("iframe[id*='description']") or self.page.query_selector("iframe[id*='tinymce']")
            if iframe:
                frame = iframe.content_frame()
                if frame:
                    frame.evaluate(f"document.body.innerHTML = {json.dumps(content)};")
        except Exception:
            pass

    def upload_images(self, image_paths: Optional[List[str]] = None, source_id: Optional[str] = None, car_data: Optional[Dict[str, Any]] = None) -> bool:
        paths = []
        if car_data and car_data.get("images"):
            paths = car_data["images"]
        elif image_paths:
            paths = image_paths

        if not paths and (source_id or (car_data and car_data.get("source_id"))):
            sid = source_id or car_data.get("source_id")
            local_dir = Path("data") / "images" / str(sid)
            if local_dir.exists():
                paths = [str(f.resolve()) for f in sorted(local_dir.glob("*.jpg"))]

        valid_paths = [str(Path(p).resolve()) for p in paths if Path(p).exists()]
        if not valid_paths:
            logger.warning("No isolated images found on disk for upload.")
            return False

        try:
            file_input = self.page.query_selector("input[type='file'][name*='images']") or self.page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(valid_paths[:5])
                self.page.wait_for_timeout(2000)
                logger.info(f"Uploaded {len(valid_paths[:5])} isolated images.")
                return True
        except Exception as e:
            logger.warning(f"Failed image upload: {e}")
        return False