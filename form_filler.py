"""Robust Form Filler - Label & Targeted Attribute Matching."""

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
        # 1. Select Categories
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
        contact_number = str(car_data.get("contact_number") or car_data.get("contact_phone") or ".")
        source_link = str(car_data.get("Source Link") or car_data.get("source_url") or ".")
        
        features_txt = str(car_data.get("features") or ".")
        highlights_txt = str(car_data.get("vehicle highlights") or ".")
        price_val = str(car_data.get("price", "0")).replace("R", "").replace(" ", "").strip()

        # 3. Fill ALL Text Inputs in exact portal visual order (0 to 16)
        inputs = [i for i in self.page.query_selector_all("input[type='text']") if i.is_visible()]
        ordered_values = [
            title,            # Field 0: Title
            variant,          # Field 1: Title Description
            top_condition,    # Field 2: Condition
            year,             # Field 3: Year
            km,               # Field 4: Kilometers driven
            transmission,     # Field 5: Transmission
            fuel,             # Field 6: Fuel
            drive_type,       # Field 7: 4x2 / 4x4
            colour,           # Field 8: Body colour
            bottom_condition, # Field 9: Condition (Bottom)
            seats,            # Field 10: Seats
            pricing_summary,  # Field 11: Pricing Summary
            dealer_name,      # Field 12: Dealer Name
            dealer_address,   # Field 13: Dealer Address
            dealer_rating,    # Field 14: Dealer average rating
            contact_number,   # Field 15: Contact Number (INPUT)
            source_link       # Field 16: Source Link (INPUT)
        ]

        for i, val in enumerate(ordered_values):
            if i < len(inputs):
                try:
                    inputs[i].click()
                    inputs[i].fill("")
                    inputs[i].fill(val)
                except Exception as err:
                    logger.warning(f"Error filling input index {i}: {err}")

        # 4. Fill Textareas (Features & Highlights)
        textareas = [ta for ta in self.page.query_selector_all("textarea") if ta.is_visible()]
        if len(textareas) >= 2:
            textareas[0].fill(features_txt)     # Textarea 0: Features
            textareas[1].fill(highlights_txt)   # Textarea 1: Vehicle Highlights
        elif len(textareas) == 1:
            textareas[0].fill(features_txt)

        # 5. Price Field
        price_inp = self.page.query_selector("input[name*='price'], input[id*='price']")
        if price_inp and price_inp.is_visible():
            price_inp.click()
            price_inp.fill("")
            price_inp.fill(price_val)

        # 6. Bottom Address Field
        bottom_addr = self.page.query_selector("div[class*='contact'] input[name*='address'], textarea[name*='address']")
        if bottom_addr and bottom_addr.is_visible():
            bottom_addr.click()
            bottom_addr.fill("")
            bottom_addr.fill(dealer_address)

        # 7. Force Dropdown Options (Direct Currency Dropdown Selector for Rand)
        self._select_rand_currency()
        self._force_dropdown_by_value_or_text("tag", ["Sale", "For Sale"])
        self._force_dropdown_by_value_or_text("location", ["South Africa"])

        # 8. Description Editor
        desc_content = car_data.get("description") or title
        self._fill_tinymce_description(desc_content)

        # 9. Upload Images
        images = car_data.get("images", [])
        sid = car_data.get("source_id") or car_data.get("id")
        self.upload_images(image_paths=images, source_id=sid, car_data=car_data)

        # 10. Auto-check privacy checkbox via comprehensive Playwright click handlers
        self._check_privacy_policy_checkbox()

        return True

    def _check_privacy_policy_checkbox(self):
        """Scans for and forces checking on any Privacy Policy or Terms checkboxes/labels."""
        try:
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            self.page.wait_for_timeout(800)

            # Check 1: Playwright native check on input[type='checkbox']
            checkboxes = self.page.query_selector_all("input[type='checkbox']")
            checked_any = False
            for cb in checkboxes:
                try:
                    if cb.is_visible() and not cb.is_checked():
                        cb.scroll_into_view_if_needed()
                        cb.check(force=True)
                        checked_any = True
                except Exception:
                    pass

            # Check 2: Direct click on clickable elements containing policy text (for custom-styled toggles/labels)
            if not checked_any:
                clickables = self.page.query_selector_all("label, span, div, a, p")
                for el in clickables:
                    try:
                        txt = (el.inner_text() or "").lower()
                        if el.is_visible() and ("privacy" in txt or "policy" in txt or "terms" in txt or "agree" in txt):
                            el.scroll_into_view_if_needed()
                            el.click(force=True)
                            self.page.wait_for_timeout(300)
                            break
                    except Exception:
                        pass

            # Focus submit button visually at the bottom
            submit_btn = self.page.query_selector("button:has-text('Post Ad'), input[value*='Post Ad']")
            if submit_btn and submit_btn.is_visible():
                submit_btn.scroll_into_view_if_needed()

        except Exception as err:
            logger.warning(f"Privacy policy auto-check failed: {err}")

    def _select_exact_category_hierarchy(self):
        try:
            selects = self.page.query_selector_all("select")
            if len(selects) >= 1:
                selects[0].select_option(label="Vehicles")
                selects[0].dispatch_event("change")
                self.page.wait_for_timeout(2000)

            selects = self.page.query_selector_all("select")
            if len(selects) >= 2:
                selects[1].select_option(label="Cars - Parts")
                selects[1].dispatch_event("change")
                self.page.wait_for_timeout(2000)

            selects = self.page.query_selector_all("select")
            if len(selects) >= 3:
                selects[2].select_option(label="Used cars in South Africa")
                selects[2].dispatch_event("change")
                self.page.wait_for_timeout(1500)
        except Exception as e:
            logger.warning(f"Category selection error: {e}")

    def _select_rand_currency(self):
        """Specifically selects Rand (R) from the currency dropdown next to the Price input."""
        try:
            currency_select = self.page.query_selector("input[name*='price'] + select, select[name*='currency'], select[id*='currency']")
            
            if not currency_select:
                selects = self.page.query_selector_all("select")
                for sel in selects:
                    if sel.is_visible():
                        opts_text = sel.inner_text()
                        if "Rs" in opts_text or "Rand" in opts_text or "ZAR" in opts_text:
                            currency_select = sel
                            break

            if currency_select:
                opts = currency_select.query_selector_all("option")
                target_val = None
                for opt in opts:
                    txt = opt.inner_text().strip().lower()
                    val = (opt.get_attribute("value") or "").lower()
                    if "rand" in txt or "zar" in txt or txt == "r" or "r (" in txt or "rand" in val or "zar" in val:
                        target_val = opt.get_attribute("value")
                        break

                if target_val is not None:
                    currency_select.select_option(value=target_val)
                    currency_select.evaluate("el => { el.dispatchEvent(new Event('change', { bubbles: true })); el.dispatchEvent(new Event('input', { bubbles: true })); }")
        except Exception as e:
            logger.warning(f"Failed setting currency dropdown to Rand: {e}")

    def _force_dropdown_by_value_or_text(self, field_keyword: str, target_options: List[str]):
        try:
            selects = self.page.query_selector_all("select")
            for sel in selects:
                if not sel.is_visible():
                    continue
                name_attr = (sel.get_attribute("name") or "").lower()
                id_attr = (sel.get_attribute("id") or "").lower()
                parent_text = sel.evaluate("el => el.parentElement ? el.parentElement.innerText : ''").lower()

                if field_keyword.lower() in name_attr or field_keyword.lower() in id_attr or field_keyword.lower() in parent_text:
                    opts = sel.query_selector_all("option")
                    for opt in opts:
                        opt_text = opt.inner_text().strip()
                        opt_val = opt.get_attribute("value") or ""

                        if any(t.lower() in opt_text.lower() or t.lower() == opt_val.lower() for t in target_options):
                            sel.select_option(value=opt_val)
                            sel.evaluate("el => { el.dispatchEvent(new Event('change', { bubbles: true })); el.dispatchEvent(new Event('input', { bubbles: true })); }")
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
        sid = source_id or (car_data.get("source_id") if car_data else None) or (car_data.get("id") if car_data else None)
        valid_paths = []

        if sid:
            img_dir = Path("data") / "images" / str(sid)
            if img_dir.exists():
                valid_paths = [str(p.resolve()) for p in sorted(img_dir.glob("*.jpg")) + sorted(img_dir.glob("*.png"))]

        if not valid_paths and car_data and car_data.get("images"):
            valid_paths = [str(Path(p).resolve()) for p in car_data["images"] if Path(p).exists()]

        if not valid_paths and image_paths:
            valid_paths = [str(Path(p).resolve()) for p in image_paths if Path(p).exists()]

        if not valid_paths:
            return False

        try:
            file_input = self.page.query_selector("input[type='file']")
            if file_input:
                file_input.set_input_files(valid_paths[:5])
                self.page.wait_for_timeout(1500)
                return True
        except Exception as e:
            logger.warning(f"Image upload failed: {e}")
        return False