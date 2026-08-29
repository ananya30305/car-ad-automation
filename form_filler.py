"""Positional Form Filler - Direct Index Field Assignment."""

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
        title = car_data.get("title") or "."
        variant = car_data.get("title description") or car_data.get("variant") or "."
        top_condition = "Used"
        year = str(car_data.get("year") or ".")
        km = str(car_data.get("Kilometers driven") or car_data.get("mileage") or ".")
        transmission = str(car_data.get("transmission") or ".")
        fuel = str(car_data.get("fuel") or ".")
        drive_type = str(car_data.get("4x2 / 4x4") or car_data.get("drive_type") or ".")
        colour = str(car_data.get("body colour") or car_data.get("colour") or ".")
        bottom_condition = str(car_data.get("condition") or ".")
        seats = str(car_data.get("seats") or ".")
        pricing_summary = str(car_data.get("price summary") or car_data.get("pricing_summary") or ".")
        dealer_name = str(car_data.get("dealer_name") or ".")
        dealer_address = str(car_data.get("dealer_address") or car_data.get("address") or ".")
        dealer_rating = str(car_data.get("Dealer average rating") or car_data.get("dealer_rating") or ".")
        features_txt = str(car_data.get("features") or ".")
        contact_number = str(car_data.get("contact_number") or car_data.get("contact_phone") or ".")
        source_link = str(car_data.get("Source Link") or car_data.get("source_url") or ".")
        highlights_txt = str(car_data.get("vehicle highlights") or ".")
        price_val = str(car_data.get("price", "0")).replace("R", "").replace(" ", "").strip()

        # 3. Direct Index-Based Input Fill
        text_inputs = [inp for inp in self.page.query_selector_all("input[type='text']") if inp.is_visible()]

        # Field mapping ordered strictly top-to-bottom as shown in the portal form UI
        ordered_values = [
            title,            # Field 0: Title*
            variant,          # Field 1: Title Description*
            top_condition,    # Field 2: Condition* (Top - Always "Used")
            year,             # Field 3: Year*
            km,               # Field 4: Kilometers driven*
            transmission,     # Field 5: Transmission*
            fuel,             # Field 6: Fuel*
            drive_type,       # Field 7: 4x2 / 4x4*
            colour,           # Field 8: Body colour*
            bottom_condition, # Field 9: Condition* (Bottom - Extracted condition badge or '.')
            seats,            # Field 10: Seats*
            pricing_summary,  # Field 11: pricing Summary*
            dealer_name,      # Field 12: Dealer Name*
            dealer_address,   # Field 13: Dealer Address*
            dealer_rating,    # Field 14: Dealer average rating*
        ]

        for i, val in enumerate(ordered_values):
            if i < len(text_inputs):
                try:
                    text_inputs[i].click()
                    text_inputs[i].fill("")
                    text_inputs[i].fill(val)
                except Exception as err:
                    logger.warning(f"Error filling index {i} ({val}): {err}")

        # 4. Fill Textarea Fields
        textareas = [ta for ta in self.page.query_selector_all("textarea") if ta.is_visible()]
        textarea_mapping = [
            (features_txt),     # Textarea 0: Features*
            (contact_number),   # Textarea 1: Contact Number*
            (source_link),      # Textarea 2: Source Link*
            (highlights_txt),   # Textarea 3: Vehicle Highlights*
        ]

        for i, val in enumerate(textarea_mapping):
            if i < len(textareas):
                try:
                    textareas[i].click()
                    textareas[i].fill("")
                    textareas[i].fill(val)
                except Exception as err:
                    logger.warning(f"Error filling textarea index {i}: {err}")

        # 5. Price & Contact Address
        price_input = self.page.query_selector("input[name*='price'], input[id*='price']")
        if price_input and price_input.is_visible():
            price_input.click()
            price_input.fill("")
            price_input.fill(price_val)

        # Fill lower contact details address field
        bottom_address_input = self.page.query_selector("input[name*='address']:not([name*='dealer']), textarea[name*='address']")
        if bottom_address_input and bottom_address_input.is_visible():
            bottom_address_input.click()
            bottom_address_input.fill("")
            bottom_address_input.fill(dealer_address)

        # 6. Fill Dropdowns
        self._force_dropdown_selection("currency", "R (Rand)")
        self._force_dropdown_selection("tagid", "Sale")
        self._force_dropdown_selection("location", "South Africa")

        # 7. Fill TinyMCE Description Frame
        desc_content = car_data.get("description") or title
        self._fill_tinymce_description(desc_content)

        return True

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