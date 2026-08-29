"""Form detection and analysis.

Detects the main advertisement form and builds a detailed map
of all usable form fields so FormFiller can locate fields reliably.
"""

from typing import Optional, Any

from playwright.async_api import Page, Locator

from car_ad_automation.core.logger import StructuredLogger


class FormDetector:
    """Detects form structure and available fields."""

    def __init__(
        self,
        page: Page,
        logger: Optional[StructuredLogger] = None,
    ):
        """
        Initialize form detector.

        Args:
            page: Playwright page object.
            logger: Logger instance.
        """

        self.page = page
        self.logger = logger

        self.form: Optional[Locator] = None

        # Dictionary of detected fields.
        self.fields: dict[str, dict] = {}

        # Complete list of detected fields.
        self.field_list: list[dict] = []

    # ============================================================
    # LOGGING HELPERS
    # ============================================================

    def _log_info(self, message: str) -> None:
        """Safely write an info log."""
        if self.logger:
            self.logger.info(message)

    def _log_warning(self, message: str) -> None:
        """Safely write a warning log."""
        if self.logger:
            self.logger.warning(message)

    def _log_debug(self, message: str) -> None:
        """Safely write a debug log."""
        if self.logger:
            self.logger.debug(message)

    def _log_error(
        self,
        message: str,
        error: Optional[str] = None,
    ) -> None:
        """Safely write an error log."""
        if self.logger:
            if error:
                self.logger.error(message, error=error)
            else:
                self.logger.error(message)

    # ============================================================
    # FORM DETECTION
    # ============================================================

    async def find_form(
        self,
        selector: Optional[str] = None,
    ) -> bool:
        """
        Find the main advertisement form.

        The detector tries:
        1. User supplied selector.
        2. Advertisement-related form selectors.
        3. All visible forms.
        4. The visible form containing the most fields.

        Args:
            selector:
                Optional CSS selector for the form.

        Returns:
            True if a usable form was found.
        """

        try:
            selectors: list[str] = []

            if selector:
                selectors.append(selector)

            selectors.extend(
                [
                    'form[id*="post"]',
                    'form[id*="ad"]',
                    'form[id*="listing"]',
                    'form[id*="vehicle"]',
                    'form[class*="post"]',
                    'form[class*="ad"]',
                    'form[class*="listing"]',
                    'form[class*="vehicle"]',
                    "form",
                ]
            )

            # Remove duplicate selectors.
            selectors = list(dict.fromkeys(selectors))

            # ----------------------------------------------------
            # Try known selectors first
            # ----------------------------------------------------

            for sel in selectors:
                try:
                    locator = self.page.locator(sel)
                    count = await locator.count()

                    if count == 0:
                        continue

                    for index in range(count):
                        form = locator.nth(index)

                        try:
                            if not await form.is_visible():
                                continue
                        except Exception:
                            continue

                        try:
                            field_count = await form.locator(
                                "input, select, textarea"
                            ).count()
                        except Exception:
                            field_count = 0

                        if field_count > 0:
                            self.form = form

                            self._log_info(
                                f"Form detected with selector: "
                                f"{sel} "
                                f"(fields: {field_count})"
                            )

                            return True

                except Exception as e:
                    self._log_debug(
                        f"Selector failed '{sel}': {e}"
                    )

            # ----------------------------------------------------
            # Fallback: choose visible form with most fields
            # ----------------------------------------------------

            try:
                all_forms = self.page.locator("form")

                form_count = await all_forms.count()

                best_form: Optional[Locator] = None
                best_field_count = 0

                for index in range(form_count):
                    form = all_forms.nth(index)

                    try:
                        if not await form.is_visible():
                            continue
                    except Exception:
                        continue

                    try:
                        field_count = await form.locator(
                            "input, select, textarea"
                        ).count()
                    except Exception:
                        field_count = 0

                    if field_count > best_field_count:
                        best_field_count = field_count
                        best_form = form

                if best_form is not None:
                    self.form = best_form

                    self._log_info(
                        "Form detected using fallback selection "
                        f"(fields: {best_field_count})"
                    )

                    return True

            except Exception as e:
                self._log_debug(
                    f"Fallback form detection failed: {e}"
                )

            self._log_warning(
                "Could not detect a usable form on the page"
            )

            return False

        except Exception as e:
            self._log_error(
                "Error detecting form",
                str(e),
            )

            return False

    # ============================================================
    # ATTRIBUTE HELPERS
    # ============================================================

    async def _get_attribute(
        self,
        locator: Locator,
        attribute: str,
    ) -> str:
        """Safely get an HTML attribute."""

        try:
            value = await locator.get_attribute(attribute)
            return (value or "").strip()
        except Exception:
            return ""

    async def _get_text_content(
        self,
        locator: Locator,
    ) -> str:
        """Safely get text content."""

        try:
            value = await locator.text_content()
            return (value or "").strip()
        except Exception:
            return ""

    async def _get_inner_text(
        self,
        locator: Locator,
    ) -> str:
        """Safely get inner text."""

        try:
            value = await locator.inner_text()
            return (value or "").strip()
        except Exception:
            return ""

    # ============================================================
    # LABEL DETECTION
    # ============================================================

    async def _find_label(
        self,
        field: Locator,
        field_id: str,
    ) -> str:
        """
        Find the most likely label for a field.

        Checks:
        - label[for="id"]
        - wrapping label
        - parent label
        - previous label
        """

        labels: list[str] = []

        # --------------------------------------------------------
        # 1. label[for="field-id"]
        # --------------------------------------------------------

        if field_id:
            try:
                label = self.page.locator(
                    f'label[for="{field_id}"]'
                ).first

                if await label.count() > 0:
                    text = await self._get_text_content(label)

                    if text:
                        labels.append(text)

            except Exception:
                pass

        # --------------------------------------------------------
        # 2. Field inside label
        # --------------------------------------------------------

        try:
            parent_label = field.locator(
                "xpath=ancestor::label[1]"
            )

            if await parent_label.count() > 0:
                text = await self._get_text_content(
                    parent_label
                )

                if text:
                    labels.append(text)

        except Exception:
            pass

        # --------------------------------------------------------
        # 3. Parent container label
        # --------------------------------------------------------

        try:
            parent = field.locator("xpath=..")

            if await parent.count() > 0:
                label = parent.locator("label").first

                if await label.count() > 0:
                    text = await self._get_text_content(
                        label
                    )

                    if text:
                        labels.append(text)

        except Exception:
            pass

        # --------------------------------------------------------
        # 4. Previous label
        # --------------------------------------------------------

        try:
            previous_label = field.locator(
                "xpath=preceding::label[1]"
            )

            if await previous_label.count() > 0:
                text = await self._get_text_content(
                    previous_label
                )

                if text:
                    labels.append(text)

        except Exception:
            pass

        # --------------------------------------------------------
        # Return first useful label
        # --------------------------------------------------------

        for label in labels:
            cleaned = " ".join(label.split()).strip()

            if cleaned:
                return cleaned

        return ""

    # ============================================================
    # NEARBY TEXT
    # ============================================================

    async def _find_nearby_text(
        self,
        field: Locator,
    ) -> str:
        """
        Find text near a form field.

        Useful for websites where proper labels are missing.
        """

        candidates: list[str] = []

        try:
            parent = field.locator("xpath=..")

            if await parent.count() > 0:
                text = await self._get_inner_text(parent)

                if text:
                    candidates.append(text)

        except Exception:
            pass

        try:
            grandparent = field.locator("xpath=../..")

            if await grandparent.count() > 0:
                text = await self._get_inner_text(
                    grandparent
                )

                if text:
                    candidates.append(text)

        except Exception:
            pass

        for text in candidates:
            cleaned = " ".join(text.split()).strip()

            if cleaned:
                if len(cleaned) > 300:
                    cleaned = cleaned[:300]

                return cleaned

        return ""

    # ============================================================
    # FIELD ANALYSIS
    # ============================================================

    async def analyze_fields(self) -> dict[str, dict]:
        """
        Analyze all form controls.

        Detects:
        - type
        - name
        - id
        - class
        - placeholder
        - aria-label
        - aria-labelledby
        - autocomplete
        - role
        - title
        - label
        - nearby text
        - required
        - disabled
        - readonly
        - value
        - locator

        Returns:
            Dictionary of detected fields.
        """

        if not self.form:
            self._log_warning(
                "Cannot analyze fields because no form is selected"
            )
            return {}

        self.fields = {}
        self.field_list = []

        try:
            controls = self.form.locator(
                "input, select, textarea"
            )

            count = await controls.count()

            self._log_info(
                f"Analyzing {count} form controls..."
            )

            for index in range(count):

                field = controls.nth(index)

                try:
                    # ------------------------------------------------
                    # Basic attributes
                    # ------------------------------------------------

                    field_type = (
                        await self._get_attribute(
                            field,
                            "type",
                        )
                        or "text"
                    )

                    # SELECT elements don't have type="select".
                    # Normalize them here so FormFiller can detect them.
                    tag_name = ""

                    try:
                        tag_name = await field.evaluate(
                            "(element) => element.tagName.toLowerCase()"
                        )
                    except Exception:
                        pass

                    if tag_name == "select":
                        field_type = "select"

                    field_name = await self._get_attribute(
                        field,
                        "name",
                    )

                    field_id = await self._get_attribute(
                        field,
                        "id",
                    )

                    field_class = await self._get_attribute(
                        field,
                        "class",
                    )

                    placeholder = await self._get_attribute(
                        field,
                        "placeholder",
                    )

                    aria_label = await self._get_attribute(
                        field,
                        "aria-label",
                    )

                    aria_labelledby = await self._get_attribute(
                        field,
                        "aria-labelledby",
                    )

                    autocomplete = await self._get_attribute(
                        field,
                        "autocomplete",
                    )

                    role = await self._get_attribute(
                        field,
                        "role",
                    )

                    title = await self._get_attribute(
                        field,
                        "title",
                    )

                    # ------------------------------------------------
                    # State
                    # ------------------------------------------------

                    required = False
                    disabled = False
                    readonly = False

                    try:
                        required = await field.is_required()
                    except Exception:
                        pass

                    try:
                        disabled = await field.is_disabled()
                    except Exception:
                        pass

                    try:
                        readonly = (
                            await field.get_attribute(
                                "readonly"
                            )
                            is not None
                        )
                    except Exception:
                        pass

                    # ------------------------------------------------
                    # Label
                    # ------------------------------------------------

                    label_text = await self._find_label(
                        field,
                        field_id,
                    )

                    # ------------------------------------------------
                    # aria-labelledby
                    # ------------------------------------------------

                    if not label_text and aria_labelledby:
                        try:
                            label_parts = []

                            for label_id in aria_labelledby.split():

                                element = self.page.locator(
                                    f"#{label_id}"
                                )

                                if await element.count() > 0:
                                    text = await self._get_text_content(
                                        element
                                    )

                                    if text:
                                        label_parts.append(text)

                            label_text = " ".join(
                                label_parts
                            ).strip()

                        except Exception:
                            pass

                    # ------------------------------------------------
                    # aria-label fallback
                    # ------------------------------------------------

                    if not label_text:
                        label_text = aria_label

                    # ------------------------------------------------
                    # Placeholder fallback
                    # ------------------------------------------------

                    if not label_text:
                        label_text = placeholder

                    # ------------------------------------------------
                    # Nearby text
                    # ------------------------------------------------

                    nearby_text = await self._find_nearby_text(
                        field
                    )

                    # ------------------------------------------------
                    # Current value
                    # ------------------------------------------------

                    current_value = ""

                    try:
                        if field_type in {
                            "checkbox",
                            "radio",
                            "file",
                            "button",
                            "submit",
                        }:
                            current_value = (
                                await self._get_attribute(
                                    field,
                                    "value",
                                )
                            )
                        else:
                            current_value = (
                                await field.input_value()
                            )

                    except Exception:
                        current_value = ""

                    # ------------------------------------------------
                    # Field key
                    # ------------------------------------------------

                    field_key = (
                        field_name
                        or field_id
                        or label_text
                        or placeholder
                        or f"field_{index}"
                    )

                    field_key = " ".join(
                        str(field_key).split()
                    ).strip()

                    if not field_key:
                        field_key = f"field_{index}"

                    # ------------------------------------------------
                    # Prevent duplicate keys
                    # ------------------------------------------------

                    original_key = field_key
                    duplicate_number = 2

                    while field_key in self.fields:
                        field_key = (
                            f"{original_key}_"
                            f"{duplicate_number}"
                        )

                        duplicate_number += 1

                    # ------------------------------------------------
                    # Field information
                    # ------------------------------------------------

                    field_info = {
                        "index": index,
                        "tag": tag_name,
                        "type": field_type,
                        "name": field_name,
                        "id": field_id,
                        "class": field_class,
                        "label": label_text,
                        "placeholder": placeholder,
                        "aria_label": aria_label,
                        "aria_labelledby": aria_labelledby,
                        "autocomplete": autocomplete,
                        "role": role,
                        "title": title,
                        "nearby_text": nearby_text,
                        "required": required,
                        "disabled": disabled,
                        "readonly": readonly,
                        "value": current_value,
                        "locator": field,
                    }

                    self.fields[field_key] = field_info
                    self.field_list.append(field_info)

                    self._log_debug(
                        "Field detected: "
                        f"key='{field_key}', "
                        f"type='{field_type}', "
                        f"name='{field_name}', "
                        f"id='{field_id}', "
                        f"label='{label_text}', "
                        f"placeholder='{placeholder}'"
                    )

                except Exception as e:
                    self._log_debug(
                        f"Error analyzing field {index}: {e}"
                    )

            self._log_info(
                f"Found {len(self.fields)} usable form fields"
            )

            self._log_field_summary()

            return self.fields

        except Exception as e:
            self._log_error(
                "Error analyzing form fields",
                str(e),
            )

            return {}

    # ============================================================
    # FIELD SUMMARY
    # ============================================================

    def _log_field_summary(self) -> None:
        """Log all detected fields."""

        if not self.field_list:
            return

        self._log_info(
            "========== DETECTED FORM FIELDS =========="
        )

        for field in self.field_list:

            field_key = (
                field.get("name")
                or field.get("id")
                or field.get("label")
                or f"field_{field.get('index', '?')}"
            )

            self._log_info(
                f"[{field.get('index')}] "
                f"{field_key} | "
                f"type={field.get('type', '')} | "
                f"label={field.get('label', '')!r} | "
                f"placeholder={field.get('placeholder', '')!r}"
            )

        self._log_info(
            "=========================================="
        )

    # ============================================================
    # GET FIELD
    # ============================================================

    def get_field(
        self,
        field_name: str,
    ) -> Optional[dict]:
        """
        Find a field by name, id, label, placeholder,
        aria-label, autocomplete, title, or nearby text.
        """

        if not field_name:
            return None

        search = str(
            field_name
        ).strip().lower()

        # --------------------------------------------------------
        # Exact dictionary key
        # --------------------------------------------------------

        if field_name in self.fields:
            return self.fields[field_name]

        # --------------------------------------------------------
        # Exact matching
        # --------------------------------------------------------

        for key, value in self.fields.items():

            candidates = [
                key,
                value.get("name", ""),
                value.get("id", ""),
                value.get("label", ""),
                value.get("placeholder", ""),
                value.get("aria_label", ""),
                value.get("autocomplete", ""),
                value.get("title", ""),
            ]

            for candidate in candidates:

                candidate = str(
                    candidate or ""
                ).strip().lower()

                if candidate == search:
                    return value

        # --------------------------------------------------------
        # Partial matching
        # --------------------------------------------------------

        for key, value in self.fields.items():

            candidates = [
                key,
                value.get("name", ""),
                value.get("id", ""),
                value.get("label", ""),
                value.get("placeholder", ""),
                value.get("aria_label", ""),
                value.get("autocomplete", ""),
                value.get("title", ""),
                value.get("nearby_text", ""),
            ]

            for candidate in candidates:

                candidate = str(
                    candidate or ""
                ).strip().lower()

                if not candidate:
                    continue

                if search in candidate:
                    return value

        return None

    # ============================================================
    # FIND MULTIPLE FIELDS
    # ============================================================

    def find_fields(
        self,
        field_name: str,
    ) -> list[dict]:
        """
        Find all fields matching a search term.
        """

        if not field_name:
            return []

        search = str(
            field_name
        ).strip().lower()

        matches = []

        for value in self.field_list:

            candidates = [
                value.get("name", ""),
                value.get("id", ""),
                value.get("label", ""),
                value.get("placeholder", ""),
                value.get("aria_label", ""),
                value.get("autocomplete", ""),
                value.get("title", ""),
                value.get("nearby_text", ""),
            ]

            for candidate in candidates:

                candidate = str(
                    candidate or ""
                ).strip().lower()

                if search in candidate:

                    if value not in matches:
                        matches.append(value)

                    break

        return matches

    # ============================================================
    # HAS FIELD
    # ============================================================

    async def has_field(
        self,
        field_name: str,
    ) -> bool:
        """Check whether a field exists."""

        return self.get_field(
            field_name
        ) is not None

    # ============================================================
    # GET FIELD VALUE
    # ============================================================

    async def get_field_value(
        self,
        field_name: str,
    ) -> Optional[str]:
        """
        Get current value of a field.
        """

        field = self.get_field(
            field_name
        )

        if not field:
            return None

        try:
            locator = field.get("locator")

            if not locator:
                return None

            field_type = str(
                field.get("type", "text")
            ).lower()

            # ----------------------------------------------------
            # Checkbox / radio
            # ----------------------------------------------------

            if field_type in {
                "checkbox",
                "radio",
            }:

                try:
                    checked = await locator.is_checked()

                    return (
                        "true"
                        if checked
                        else "false"
                    )

                except Exception:
                    return None

            # ----------------------------------------------------
            # Normal input / select / textarea
            # ----------------------------------------------------

            try:
                return await locator.input_value()

            except Exception:

                value = await locator.get_attribute(
                    "value"
                )

                return value

        except Exception as e:

            self._log_debug(
                f"Could not get value for "
                f"'{field_name}': {e}"
            )

        return None

    # ============================================================
    # GET FIELD LOCATOR
    # ============================================================

    def get_field_locator(
        self,
        field_name: str,
    ) -> Optional[Locator]:
        """
        Return Playwright locator for a field.
        """

        field = self.get_field(
            field_name
        )

        if not field:
            return None

        return field.get("locator")

    # ============================================================
    # TINYMCE DETECTION
    # ============================================================

    async def detect_tinymce(self) -> bool:
        """
        Detect whether TinyMCE or similar rich-text editor exists.
        """

        selectors = [
            "#tinymce",
            ".mce-container",
            ".tox-tinymce",
            ".tox-editor-container",
            "[class*='tinymce']",
            "iframe.tox-edit-area__iframe",
        ]

        try:

            for selector in selectors:

                locator = self.page.locator(
                    selector
                ).first

                try:

                    if await locator.count() == 0:
                        continue

                    if await locator.is_visible():

                        self._log_info(
                            f"TinyMCE editor detected: "
                            f"{selector}"
                        )

                        return True

                except Exception:
                    continue

        except Exception as e:

            self._log_debug(
                f"TinyMCE detection failed: {e}"
            )

        return False

    # ============================================================
    # RECAPTCHA DETECTION
    # ============================================================

    async def detect_recaptcha(self) -> bool:
        """
        Detect whether reCAPTCHA is present.
        """

        selectors = [
            "[data-sitekey]",
            ".g-recaptcha",
            "iframe[src*='recaptcha']",
            "iframe[title*='reCAPTCHA']",
            "[class*='recaptcha']",
        ]

        try:

            for selector in selectors:

                locator = self.page.locator(
                    selector
                ).first

                try:

                    if await locator.count() == 0:
                        continue

                    if await locator.is_visible():

                        self._log_warning(
                            "reCAPTCHA detected on page"
                        )

                        return True

                except Exception:
                    continue

        except Exception as e:

            self._log_debug(
                f"reCAPTCHA detection failed: {e}"
            )

        return False

    # ============================================================
    # FILE INPUT DETECTION
    # ============================================================

    async def find_file_inputs(self) -> list[Locator]:
        """
        Find usable file upload inputs.
        """

        file_inputs: list[Locator] = []

        if not self.form:
            return file_inputs

        try:

            inputs = self.form.locator(
                'input[type="file"]'
            )

            count = await inputs.count()

            for index in range(count):

                locator = inputs.nth(index)

                try:

                    if await locator.is_disabled():
                        continue

                    file_inputs.append(locator)

                except Exception:
                    continue

            self._log_info(
                f"Found {len(file_inputs)} usable "
                f"file input(s)"
            )

        except Exception as e:

            self._log_debug(
                f"File input detection failed: {e}"
            )

        return file_inputs

    # ============================================================
    # FORM SUMMARY
    # ============================================================

    async def get_form_summary(self) -> dict[str, Any]:
        """
        Return summary information about the detected form.
        """

        summary = {
            "form_found": self.form is not None,
            "field_count": len(self.fields),
            "file_input_count": 0,
            "tinymce": False,
            "recaptcha": False,
        }

        if not self.form:
            return summary

        try:
            file_inputs = await self.find_file_inputs()

            summary["file_input_count"] = len(
                file_inputs
            )

        except Exception:
            pass

        try:
            summary["tinymce"] = (
                await self.detect_tinymce()
            )
        except Exception:
            pass

        try:
            summary["recaptcha"] = (
                await self.detect_recaptcha()
            )
        except Exception:
            pass

        return summary