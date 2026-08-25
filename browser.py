"""Browser automation using Playwright.

Handles:
- Browser startup
- Persistent login/session storage
- Page navigation
- Waiting for pages to become usable
- Screenshots
- HTML debugging files
- Session saving
- Browser cleanup
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Page,
    Browser,
    BrowserContext,
)

from logger import StructuredLogger


class BrowserAutomation:
    """Manages browser automation with Playwright."""

    def __init__(
        self,
        profile_dir: Path,
        headless: bool = False,
        browser_type: str = "chromium",
        logger: Optional[StructuredLogger] = None,
    ):
        """
        Initialize browser automation.

        Args:
            profile_dir:
                Directory where browser session information is stored.

            headless:
                If False, browser UI is visible.

            browser_type:
                chromium, firefox, or webkit.

            logger:
                Logger instance.
        """

        self.profile_dir = Path(profile_dir)
        self.headless = headless
        self.browser_type = browser_type.lower().strip()
        self.logger = logger

        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

        # Session storage file.
        self.state_file = self.profile_dir / "state.json"

        # Prevent multiple close operations.
        self._closed = False

    # ============================================================
    # LOGGING HELPERS
    # ============================================================

    def _log_info(self, message: str) -> None:
        """Safely write info log."""
        if self.logger:
            self.logger.info(message)

    def _log_warning(self, message: str) -> None:
        """Safely write warning log."""
        if self.logger:
            self.logger.warning(message)

    def _log_debug(self, message: str) -> None:
        """Safely write debug log."""
        if self.logger:
            self.logger.debug(message)

    def _log_error(
        self,
        message: str,
        error: Optional[str] = None,
    ) -> None:
        """Safely write error log."""

        if not self.logger:
            return

        if error:
            self.logger.error(
                message,
                error=error,
            )
        else:
            self.logger.error(message)

    # ============================================================
    # BROWSER LAUNCH
    # ============================================================

    async def launch(
        self,
        timeout: int = 30_000,
    ) -> Page:
        """
        Launch browser and create a page.

        Important:
        The browser is launched with a saved storage state when
        state.json exists.

        This allows cookies/local-storage based login sessions
        to survive between runs.

        Args:
            timeout:
                Default Playwright timeout in milliseconds.

        Returns:
            Playwright Page object.
        """

        # Prevent accidentally launching twice.
        if self.page:
            self._log_warning(
                "Browser is already launched"
            )
            return self.page

        try:
            # ----------------------------------------------------
            # Create profile directory
            # ----------------------------------------------------

            self.profile_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            # ----------------------------------------------------
            # Start Playwright
            # ----------------------------------------------------

            self.playwright = await async_playwright().start()

            # ----------------------------------------------------
            # Select browser engine
            # ----------------------------------------------------

            if self.browser_type == "firefox":

                launcher = self.playwright.firefox

            elif self.browser_type == "webkit":

                launcher = self.playwright.webkit

            else:

                launcher = self.playwright.chromium

            # ----------------------------------------------------
            # Launch browser
            # ----------------------------------------------------

            self.browser = await launcher.launch(
                headless=self.headless,
            )

            # ----------------------------------------------------
            # Load saved session if available
            # ----------------------------------------------------

            storage_state = None

            if self.state_file.exists():

                try:

                    # Validate JSON before passing it to Playwright.
                    json.loads(
                        self.state_file.read_text(
                            encoding="utf-8"
                        )
                    )

                    storage_state = str(
                        self.state_file
                    )

                    self._log_info(
                        f"Loading saved browser session: "
                        f"{self.state_file}"
                    )

                except Exception as e:

                    self._log_warning(
                        "Saved browser session is invalid. "
                        "Starting with a fresh session."
                    )

                    self._log_debug(
                        f"Invalid session error: {e}"
                    )

                    storage_state = None

            else:

                self._log_info(
                    "No saved browser session found. "
                    "Starting a new session."
                )

            # ----------------------------------------------------
            # Create browser context
            # ----------------------------------------------------

            self.context = await self.browser.new_context(
                storage_state=storage_state,

                # Keep normal desktop-like viewport.
                viewport={
                    "width": 1440,
                    "height": 900,
                },

                # Normal browser locale.
                locale="en-US",

                # Keep timezone automatic.
                timezone_id=None,
            )

            # ----------------------------------------------------
            # Set default timeout
            # ----------------------------------------------------

            self.context.set_default_timeout(
                timeout
            )

            # Navigation timeout.
            self.context.set_default_navigation_timeout(
                timeout
            )

            # ----------------------------------------------------
            # Create page
            # ----------------------------------------------------

            self.page = await self.context.new_page()

            self.page.set_default_timeout(
                timeout
            )

            self.page.set_default_navigation_timeout(
                timeout
            )

            # ----------------------------------------------------
            # Browser event logging
            # ----------------------------------------------------

            self.page.on(
                "console",
                lambda message: self._log_debug(
                    f"Browser console [{message.type}]: "
                    f"{message.text}"
                ),
            )

            self.page.on(
                "pageerror",
                lambda error: self._log_warning(
                    f"Browser page error: {error}"
                ),
            )

            self._closed = False

            self._log_info(
                "Browser launched successfully"
            )

            self._log_info(
                f"Headless mode: {self.headless}"
            )

            self._log_info(
                f"Browser type: {self.browser_type}"
            )

            return self.page

        except Exception as e:

            self._log_error(
                "Failed to launch browser",
                str(e),
            )

            # Clean up partially created resources.
            await self._cleanup_resources()

            raise

    # ============================================================
    # NAVIGATION
    # ============================================================

    async def goto(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
    ) -> None:
        """
        Navigate to a URL.

        Args:
            url:
                Destination URL.

            wait_until:
                Playwright load state.

        Raises:
            RuntimeError:
                If browser has not been launched.

            ValueError:
                If URL is invalid.
        """

        if not self.page:
            raise RuntimeError(
                "Browser not launched. "
                "Call launch() before goto()."
            )

        if not url:
            raise ValueError(
                "URL cannot be empty."
            )

        if not url.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                f"Invalid URL: {url}"
            )

        try:

            self._log_info(
                f"Navigating to: {url}"
            )

            response = await self.page.goto(
                url,
                wait_until=wait_until,
            )

            # ------------------------------------------------
            # Give dynamically loaded pages a small opportunity
            # to finish rendering.
            # ------------------------------------------------

            try:

                await self.page.wait_for_load_state(
                    "domcontentloaded",
                    timeout=10_000,
                )

            except Exception:
                pass

            # ------------------------------------------------
            # Log HTTP response information.
            # ------------------------------------------------

            if response:

                self._log_info(
                    f"Navigation completed: "
                    f"{response.status} "
                    f"{response.url}"
                )

            else:

                self._log_info(
                    "Navigation completed without "
                    "an HTTP response object."
                )

        except Exception as e:

            self._log_error(
                f"Navigation failed: {url}",
                str(e),
            )

            raise

    # ============================================================
    # WAIT FOR PAGE
    # ============================================================

    async def wait_for_page_ready(
        self,
        timeout: int = 15_000,
    ) -> bool:
        """
        Wait for the page DOM to become usable.

        Returns:
            True if page is ready.
        """

        if not self.page:
            return False

        try:

            await self.page.wait_for_load_state(
                "domcontentloaded",
                timeout=timeout,
            )

        except Exception:
            pass

        try:

            await self.page.wait_for_function(
                """
                () => document.readyState === 'interactive'
                    || document.readyState === 'complete'
                """,
                timeout=timeout,
            )

        except Exception:
            pass

        return True

    # ============================================================
    # CURRENT URL
    # ============================================================

    def current_url(self) -> str:
        """
        Return current page URL.
        """

        if not self.page:
            return ""

        try:
            return self.page.url
        except Exception:
            return ""

    # ============================================================
    # PAGE TITLE
    # ============================================================

    async def page_title(self) -> str:
        """
        Return current page title.
        """

        if not self.page:
            return ""

        try:
            return await self.page.title()
        except Exception:
            return ""

    # ============================================================
    # SESSION SAVE
    # ============================================================

    async def save_session(self) -> None:
        """
        Save browser cookies and local-storage state.

        The resulting state.json is loaded during the next run.
        """

        if not self.context:
            self._log_warning(
                "Cannot save session: browser context does not exist."
            )
            return

        try:

            self.profile_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            state = await self.context.storage_state()

            self.state_file.write_text(
                json.dumps(
                    state,
                    indent=2,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            self._log_info(
                f"Browser session saved to: "
                f"{self.state_file}"
            )

        except Exception as e:

            self._log_error(
                "Failed to save browser session",
                str(e),
            )

    # ============================================================
    # CLEAR SESSION
    # ============================================================

    async def clear_session(self) -> None:
        """
        Delete saved session state.

        Use this when the saved login session becomes invalid
        and a fresh login is required.
        """

        try:

            if self.state_file.exists():

                self.state_file.unlink()

                self._log_info(
                    "Saved browser session deleted."
                )

            else:

                self._log_info(
                    "No saved browser session to delete."
                )

        except Exception as e:

            self._log_error(
                "Failed to clear browser session",
                str(e),
            )

    # ============================================================
    # CHECK SESSION
    # ============================================================

    def has_saved_session(self) -> bool:
        """
        Check whether a saved browser session exists.
        """

        return (
            self.state_file.exists()
            and self.state_file.is_file()
        )

    # ============================================================
    # SCREENSHOT
    # ============================================================

    async def take_screenshot(
        self,
        filename: Path,
        full_page: bool = True,
    ) -> None:
        """
        Take screenshot of current page.

        Args:
            filename:
                Screenshot output path.

            full_page:
                Capture complete page when True.
        """

        if not self.page:
            raise RuntimeError(
                "Browser not launched"
            )

        try:

            filename = Path(filename)

            filename.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            await self.page.screenshot(
                path=str(filename),
                full_page=full_page,
            )

            self._log_info(
                f"Screenshot saved: {filename}"
            )

        except Exception as e:

            self._log_error(
                f"Failed to save screenshot: {filename}",
                str(e),
            )

            raise

    # ============================================================
    # SAVE HTML
    # ============================================================

    async def save_html(
        self,
        filename: Path,
    ) -> None:
        """
        Save current page HTML.

        Useful for debugging form detection.
        """

        if not self.page:
            raise RuntimeError(
                "Browser not launched"
            )

        try:

            filename = Path(filename)

            filename.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            content = await self.page.content()

            filename.write_text(
                content,
                encoding="utf-8",
            )

            self._log_info(
                f"HTML saved: {filename}"
            )

        except Exception as e:

            self._log_error(
                f"Failed to save HTML: {filename}",
                str(e),
            )

            raise

    # ============================================================
    # DEBUG PAGE INFORMATION
    # ============================================================

    async def log_page_information(self) -> None:
        """
        Log useful information about the current page.
        """

        if not self.page:
            return

        try:

            url = self.page.url

            title = await self.page.title()

            self._log_info(
                "========== PAGE INFORMATION =========="
            )

            self._log_info(
                f"URL: {url}"
            )

            self._log_info(
                f"Title: {title}"
            )

            self._log_info(
                "======================================="
            )

        except Exception as e:

            self._log_debug(
                f"Could not read page information: {e}"
            )

    # ============================================================
    # WAIT FOR USER LOGIN
    # ============================================================

    async def wait_for_manual_login(
        self,
        timeout_seconds: int = 300,
    ) -> bool:
        """
        Give the user time to manually log in.

        This is useful when the destination website requires
        interactive login.

        The function does NOT attempt to bypass authentication,
        CAPTCHA, or security checks.

        It simply keeps the visible browser open while the user
        completes the normal login process.

        Args:
            timeout_seconds:
                Maximum time to wait.

        Returns:
            True when the page remains available.
        """

        if not self.page:
            raise RuntimeError(
                "Browser not launched"
            )

        if self.headless:

            self._log_warning(
                "Manual login requested while browser "
                "is running headless."
            )

            return False

        self._log_info(
            "Waiting for manual login..."
        )

        self._log_info(
            f"You have up to {timeout_seconds} seconds "
            "to complete the normal login."
        )

        try:

            await asyncio.sleep(
                timeout_seconds
            )

            # Save whatever session state was established.
            await self.save_session()

            self._log_info(
                "Manual login wait finished."
            )

            return True

        except asyncio.CancelledError:

            self._log_warning(
                "Manual login wait cancelled."
            )

            return False

        except Exception as e:

            self._log_error(
                "Error while waiting for manual login",
                str(e),
            )

            return False

    # ============================================================
    # CLEANUP INTERNAL RESOURCES
    # ============================================================

    async def _cleanup_resources(self) -> None:
        """
        Clean up browser resources after a failed launch.
        """

        try:

            if self.context:

                try:
                    await self.context.close()
                except Exception:
                    pass

                self.context = None

            if self.browser:

                try:
                    await self.browser.close()
                except Exception:
                    pass

                self.browser = None

            if self.playwright:

                try:
                    await self.playwright.stop()
                except Exception:
                    pass

                self.playwright = None

            self.page = None

        except Exception:
            pass

    # ============================================================
    # CLOSE
    # ============================================================

    async def close(self) -> None:
        """
        Save session and close browser cleanly.
        """

        if self._closed:
            return

        self._closed = True

        # --------------------------------------------------------
        # Save session before closing context.
        # --------------------------------------------------------

        if self.context:

            try:

                await self.save_session()

            except Exception as e:

                self._log_warning(
                    f"Could not save session before closing: {e}"
                )

        # --------------------------------------------------------
        # Close context.
        # --------------------------------------------------------

        if self.context:

            try:

                await self.context.close()

                self._log_info(
                    "Browser context closed."
                )

            except Exception as e:

                self._log_warning(
                    f"Error closing browser context: {e}"
                )

            finally:

                self.context = None

        # --------------------------------------------------------
        # Close browser.
        # --------------------------------------------------------

        if self.browser:

            try:

                await self.browser.close()

                self._log_info(
                    "Browser closed."
                )

            except Exception as e:

                self._log_warning(
                    f"Error closing browser: {e}"
                )

            finally:

                self.browser = None

        # --------------------------------------------------------
        # Stop Playwright.
        # --------------------------------------------------------

        if self.playwright:

            try:

                await self.playwright.stop()

                self._log_info(
                    "Playwright stopped."
                )

            except Exception as e:

                self._log_warning(
                    f"Error stopping Playwright: {e}"
                )

            finally:

                self.playwright = None

        self.page = None

    # ============================================================
    # ASYNC CONTEXT MANAGER
    # ============================================================

    async def __aenter__(self):
        """
        Allow:

            async with BrowserAutomation(...) as browser:
                ...
        """

        await self.launch()

        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        """Close browser automatically."""

        await self.close()


# ================================================================
# HELPER FUNCTION
# ================================================================

async def run_browser_automation(
    destination_url: str,
    profile_dir: Path,
    headless: bool = False,
    logger: Optional[StructuredLogger] = None,
) -> Page:
    """
    Launch browser and navigate to destination.

    Note:
        The returned Page remains associated with the
        BrowserAutomation instance created inside this function.
        For larger workflows, prefer creating BrowserAutomation
        directly so you can explicitly close it.

    Args:
        destination_url:
            Destination URL.

        profile_dir:
            Browser session directory.

        headless:
            Run browser headlessly.

        logger:
            Logger instance.

    Returns:
        Playwright Page object.
    """

    browser_auto = BrowserAutomation(
        profile_dir=profile_dir,
        headless=headless,
        logger=logger,
    )

    await browser_auto.launch()

    await browser_auto.goto(
        destination_url
    )

    return browser_auto.page