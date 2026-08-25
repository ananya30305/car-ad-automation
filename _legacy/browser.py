"""Browser automation using Playwright."""

import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from logger import StructuredLogger


class BrowserAutomation:
    """Manages browser automation with Playwright."""
    
    def __init__(
        self,
        profile_dir: Path,
        headless: bool = False,
        browser_type: str = "chromium",
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize browser automation.
        
        Args:
            profile_dir: Directory for persistent browser profile
            headless: Run in headless mode
            browser_type: Type of browser (chromium, firefox, webkit)
            logger: Logger instance
        """
        self.profile_dir = Path(profile_dir)
        self.headless = headless
        self.browser_type = browser_type
        self.logger = logger
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
    
    async def launch(self, timeout: int = 30_000) -> Page:
        """
        Launch browser and create page.
        
        Args:
            timeout: Navigation timeout in ms
            
        Returns:
            Page object
        """
        self.playwright = await async_playwright().start()
        
        # Select browser type
        if self.browser_type == "firefox":
            launcher = self.playwright.firefox
        elif self.browser_type == "webkit":
            launcher = self.playwright.webkit
        else:
            launcher = self.playwright.chromium
        
        # Launch browser
        self.browser = await launcher.launch(headless=self.headless)
        
        # Create persistent context
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
        self.context = await self.browser.new_context(
            storage_state=str(self.profile_dir / "state.json") if (self.profile_dir / "state.json").exists() else None
        )
        
        # Create page
        self.page = await self.context.new_page()
        self.page.set_default_timeout(timeout)
        
        if self.logger:
            self.logger.info("Browser launched successfully")
        
        return self.page
    
    async def goto(self, url: str) -> None:
        """
        Navigate to URL.
        
        Args:
            url: Target URL
        """
        if not self.page:
            raise RuntimeError("Browser not launched")
        
        await self.page.goto(url, wait_until='domcontentloaded')
        
        if self.logger:
            self.logger.info(f"Navigated to {url}")
    
    async def save_session(self) -> None:
        """Save browser session state."""
        if not self.context:
            return
        
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Save cookies and local storage
        state = await self.context.storage_state()
        
        import json
        state_file = self.profile_dir / "state.json"
        state_file.write_text(json.dumps(state, indent=2), encoding='utf-8')
        
        if self.logger:
            self.logger.info(f"Session saved to {state_file}")
    
    async def close(self) -> None:
        """Close browser and cleanup."""
        if self.context:
            await self.save_session()
            await self.context.close()
        
        if self.browser:
            await self.browser.close()
        
        if self.playwright:
            await self.playwright.stop()
        
        if self.logger:
            self.logger.info("Browser closed")
    
    async def take_screenshot(self, filename: Path) -> None:
        """
        Take screenshot.
        
        Args:
            filename: Output file path
        """
        if not self.page:
            raise RuntimeError("Browser not launched")
        
        filename.parent.mkdir(parents=True, exist_ok=True)
        await self.page.screenshot(path=str(filename))
    
    async def save_html(self, filename: Path) -> None:
        """
        Save page HTML.
        
        Args:
            filename: Output file path
        """
        if not self.page:
            raise RuntimeError("Browser not launched")
        
        content = await self.page.content()
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_text(content, encoding='utf-8')


async def run_browser_automation(
    destination_url: str,
    profile_dir: Path,
    headless: bool = False,
    logger: Optional[StructuredLogger] = None
) -> Page:
    """
    Helper to launch browser and navigate to destination.
    
    Args:
        destination_url: URL to navigate to
        profile_dir: Browser profile directory
        headless: Run headless
        logger: Logger instance
        
    Returns:
        Page object
    """
    browser_auto = BrowserAutomation(
        profile_dir=profile_dir,
        headless=headless,
        logger=logger
    )
    
    page = await browser_auto.launch()
    await browser_auto.goto(destination_url)
    
    return page
