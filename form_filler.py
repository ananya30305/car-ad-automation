"""Robust Form Filler - Separate Dual-Condition Field Handlers."""

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
        # 1. Expand Category Cascade: Vehicles -> Cars - Parts -> Used cars in South Africa
        self._select_exact_category_hierarchy()

        # 2. Extract Values
        title = car_data.get("title") or "Used Car"
        variant = car_data.get("title description") or car_data.get("variant") or title
        km = str(car_data.get("Kilometers driven") or car_data.get("mileage") or ".")
        fuel = str(car_data.get("fuel") or "Petrol")
        colour = str(car_data.get("body colour") or car_data.get("colour") or ".")
        price_val = str(car_data.get("price", "0")).replace("R", "").replace(" ", "").strip()
        
        dealer_name = car_data.get("dealer_name") or "."
        dealer_addr = car_data.get("dealer_address") or car_data.get("address") or "."
        dealer_rating = str(car_data.get("Dealer average rating") or car_data.get("dealer_rating") or "4.0 (322 reviews)")
        phone = str(car_data.get("contact_number") or car_data.get("phone") or ".")
        source_url = car_data.get("Source Link") or car_data.get("source_url") or "."
        
        # Specific extracted vehicle status for bottom field
        vehicle_specific_condition = car_data.get("condition") or "."
        if vehicle_specific_condition.lower() == "used":
            vehicle_specific_condition = "."  # Default to dot if no specific detail string like 'Excellent condition' exists
        
        features_txt = car_data.get("features", "")
        highlights_txt = car_data.get("vehicle highlights", "")
        pricing_summary = car_data.get("price summary") or f"Pricing Summary R {price_val}"

        # 3. Handle Dual Condition Fields Separately
        self._fill_dual_condition_fields(top_condition="Used", bottom_condition=vehicle_specific_condition)

        # 4. Standard Field Mappings
        field_assignments = [
            (["title description", "description title", "variant"], variant),
            (["title"], title),
            (["year"], str(car_data.get("year") or ".")),
            (["kilometer", "km", "mileage", "kilometers driven"], km),
            (["transmission"], str(car_data.get("transmission") or "Automatic")),
            (["engine", "fuel"], fuel),
            (["4x2 / 4x4", "drive"], str(car_data.get("4x2 / 4x4") or "4x2")),
            (["colour", "color", "body colour"], colour),
            (["seating", "seats"], str(car_data.get("seats") or ".")),
            (["pricing summary", "price summary"], pricing_summary),
            (["dealer name"], dealer_name),
            (["dealer address"], dealer_addr),
            (["dealer average rating", "dealer rating", "rating"], dealer_rating),
            (["features"], features_txt),
            (["contact number", "phone"], phone),
            (["source link", "source url"], source_url),
            (["highlights", "vehicle highlights"], highlights_txt),
            (["price"], price_val),
            (["address"], dealer_addr),  # Fill contact details address field
        ]

        # Fill text inputs
        for keywords, val in field_assignments:
            if val and str(val).strip() != "":
                self._fill_field_by_keywords(keywords, str(val).strip())

        # 5. Fill Dropdowns
        self._force_dropdown_selection("currency", "R (Rand)")
        self._force_dropdown_selection("tagid", "Sale")
        self._force_dropdown_selection("location", "South Africa")

        # 6. Fill Description iFrame
        desc_content = car_data.get("description") or title
        self._fill_tinymce_description(desc_content)

        return True

    def _fill_dual_condition_fields(self, top_condition: str, bottom_condition: str):
        """Finds both fields labeled 'Condition' and fills top with 'Used' and bottom with extracted status/dot."""
        try:
            inputs = self.page.query_selector_all("input[type='text']")
            condition_inputs = []

            for inp in inputs:
                if not inp.is_visible():
                    continue
                parent_txt = inp.evaluate("el => el.parentElement?.parentElement?.innerText || el.parentElement?.innerText || ''").lower()
                if "condition" in parent_txt:
                    condition_inputs.append(inp)

            # Order: 1st condition input is under Title Description, 2nd condition input is under Body Colour
            if len(condition_inputs) >= 1:
                condition_inputs[0].click()
                condition_inputs[0].fill(top_condition)  # Always "Used"

            if len(condition_inputs) >= 2:
                condition_inputs[1].click()
                condition_inputs[1].fill(bottom_condition)  # Exact status (e.g., "Excellent condition") or "."
        except Exception as e:
            logger.warning(f"Error handling dual condition fields: {e}")

    def _select_exact_category_hierarchy(self):
        try:
            selects = self.page.query_selector_all("select")
            if len(selects) >= 1:
                selects[0].select_option(label="Vehicles")
                selects[0].dispatch_event("change")
                self.page.wait_for_timeout(3000)

            selects = self.page.query_selector_all("select")
            if len(selects) >= 2:
                selects[1].select_option(label="Cars - Parts")
                selects[1].dispatch_event("change")
                self.page.wait_for_timeout(3500)

            selects = self.page.query_selector_all("select")
            if len(selects) >= 3:
                selects[2].select_option(label="Used cars in South Africa")
                selects[2].dispatch_event("change")
                self.page.wait_for_timeout(2500)
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

                # Avoid re-overwriting condition fields here
                if "condition" in parent_txt:
                    continue

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
                paths = [str(f.resolve()) for f in sorted(local_dir.glob("*.jpg")) + sorted(local_dir.glob("*.png"))]

        valid_paths = [str(Path(p).resolve()) for p in paths if Path(p).exists()]
        if not valid_paths:
            logger.warning("No images found on disk for upload.")
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