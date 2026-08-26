"""Browser automation using Playwright Persistent Context."""

from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page
from config import BROWSER_PROFILE_DIR, HEADLESS, PAGE_TIMEOUT


class PersistentBrowserSession:
    """Manages persistent Chromium browser contexts to preserve manual logins."""

    def __init__(self, profile_dir: Path = BROWSER_PROFILE_DIR, headless: bool = HEADLESS):
        self.profile_dir = Path(profile_dir).resolve()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.headless,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled"]
        )
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.set_default_timeout(PAGE_TIMEOUT)
        return self

    def get_page(self) -> Page:
        if not self.page or self.page.is_closed():
            self.page = self.context.new_page()
        return self.page

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()