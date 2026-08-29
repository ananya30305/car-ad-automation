"""Resilient Category Cascader."""

import logging
from playwright.sync_api import Page

logger = logging.getLogger(__name__)


class DynamicCategoryCascader:
    def __init__(self, page: Page):
        self.page = page

    def select_categories(self) -> bool:
        try:
            selects = self.page.query_selector_all("select")
            if not selects:
                return False

            # 1. Vehicles
            selects[0].select_option(label="Vehicles")
            self.page.wait_for_timeout(1500)

            # 2. Cars / Cars - Parts (Index-based fallback)
            selects = self.page.query_selector_all("select")
            if len(selects) > 1:
                cat2 = selects[1]
                opts = cat2.evaluate("el => Array.from(el.options).map(o => o.text)")
                match = next((o for o in opts if "cars" in o.lower()), None)
                if match:
                    cat2.select_option(label=match)
                else:
                    cat2.select_option(index=1)
                self.page.wait_for_timeout(1500)

            # 3. Used cars in South Africa
            selects = self.page.query_selector_all("select")
            if len(selects) > 2:
                cat3 = selects[2]
                opts = cat3.evaluate("el => Array.from(el.options).map(o => o.text)")
                match = next((o for o in opts if "used" in o.lower() or "south africa" in o.lower()), None)
                if match:
                    cat3.select_option(label=match)
                else:
                    cat3.select_option(index=1)
                self.page.wait_for_timeout(2000)

            return True
        except Exception as e:
            logger.warning(f"Category selection warning: {e}")
            return False