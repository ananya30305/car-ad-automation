"""Form Filler - Direct Selector Mapping, Exact Category Hierarchy, and Isolated Images."""

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
        # 1. Automate Category Selection (Vehicles -> Cars -> Used cars in South Africa)
        self._select_category_hierarchy()

        # 2. Map payload keys directly to input fields
        field_assignments = [
            (["title"], car_data.get("title")),
            (["title description", "description title"], car_data.get("title_description")),
            (["kilometer", "km", "mileage"], car_data.get("mileage")),
            (["engine"], car_data.get("fuel")),
            (["vehicle"], car_data.get("variant")),
            (["colour", "color"], car_data.get("colour")),
            (["interior colour"], car_data.get("interior_colour")),
            (["comfort", "features"], car_data.get("features")),
            (["lights"], "."),
            (["interior"], "."),
            (["seating", "seats"], car_data.get("seats")),
            (["instruments"], "."),
            (["exterior", "highlights"], car_data.get("highlights")),
            (["pricing summary"], car_data.get("pricing_summary")),
            (["dealer name"], car_data.get("dealer_name")),
            (["dealer address"], car_data.get("dealer_address")),
            (["dealer average rating", "rating"], car_data.get("dealer_rating")),
            (["contact number", "phone"], car_data.get("contact_number")),
            (["source link", "source url"], car_data.get("source_url")),
            (["price"], car_data.get("price")),
        ]

        for keywords, val in field_assignments:
            if val and str(val).strip() != ".":
                self._fill_field_by_keywords(keywords, str(val).strip())

        # 3. Handle Address, Location, Currency, and Tag
        addr_val = car_data.get("dealer_address")
        if addr_val and str(addr_val).strip() != ".":
            self._fill_field_by_keywords(["address"], str(addr_val).strip())

        self._force_dropdown_selection("currency", "R (Rand)")
        self._force_dropdown_selection("tag", "Sale")
        self._force_dropdown_selection("location", "South Africa")

        # 4. Fill Rich Text Description
        desc_content = car_data.get("description") or car_data.get("title") or "."
        self._fill_tinymce_description(desc_content)

        return True

    def _select_category_hierarchy(self):
        try:
            selects = self.page.query_selector_all("select")
            if len(selects) >= 1:
                self._select_option_by_exact_keywords(selects[0], ["Vehicles"])
                self.page.wait_for_timeout(600)
            
            selects = self.page.query_selector_all("select")
            if len(selects) >= 2:
                self._select_option_by_exact_keywords(selects[1], ["Cars", "Used Cars", "Passenger Vehicles"], exclude=["parts"])
                self.page.wait_for_timeout(600)

            selects = self.page.query_selector_all("select")
            if len(selects) >= 3:
                target_sel = selects[3] if len(selects) > 3 else selects[2]
                self._select_option_by_exact_keywords(target_sel, ["Used cars in South Africa", "South Africa", "Used cars"])
        except Exception as e:
            logger.warning(f"Category navigation warning: {e}")

    def _select_option_by_exact_keywords(self, select_elem, keywords: List[str], exclude: Optional[List[str]] = None) -> bool:
        try:
            options = select_elem.query_selector_all("option")
            for opt in options:
                opt_txt = opt.inner_text().strip()
                if exclude and any(ex.lower() in opt_txt.lower() for ex in exclude):
                    continue
                if any(kw.lower() in opt_txt.lower() for kw in keywords):
                    val = opt.get_attribute("value")
                    select_elem.select_option(value=val)
                    return True
        except Exception:
            pass
        return False

    def _fill_field_by_keywords(self, keywords: List[str], value: str):
        val_str = str(value).strip()
        elements = self.page.query_selector_all("input[type='text'], input[type='number'], textarea")
        
        for elem in elements:
            try:
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
                name_attr = (sel.get_attribute("name") or "").lower()
                id_attr = (sel.get_attribute("id") or "").lower()
                parent_txt = sel.evaluate("el => el.parentElement?.innerText || ''").lower()

                if field_keyword.lower() in name_attr or field_keyword.lower() in id_attr or field_keyword.lower() in parent_txt:
                    options = sel.query_selector_all("option")
                    for opt in options:
                        if target_text.lower() in opt.inner_text().strip().lower():
                            val = opt.get_attribute("value")
                            sel.select_option(value=val)
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
        # 1. Clear any existing UI thumbnails on the form
        try:
            delete_btns = self.page.query_selector_all("a[class*='delete'], button[class*='delete'], span[class*='delete'], .qq-upload-delete, div[class*='remove']")
            for btn in delete_btns:
                if btn.is_visible():
                    btn.click()
                    self.page.wait_for_timeout(300)
        except Exception:
            pass

        # 2. Get isolated images for current listing
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
                file_input.set_input_files([])
                self.page.wait_for_timeout(500)
                file_input.set_input_files(valid_paths[:5])
                self.page.wait_for_timeout(2500)
                logger.info(f"Uploaded {len(valid_paths[:5])} isolated images.")
                return True
        except Exception as e:
            logger.warning(f"Failed image upload: {e}")
        return False