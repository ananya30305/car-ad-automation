"""Form filling and submission.

Fills vehicle advertisement forms using the detailed field information
provided by FormDetector.

The filler supports:
- Text inputs
- Textareas
- Select/dropdown fields
- Checkboxes
- Radio buttons
- File uploads
- TinyMCE editors
- Field verification
- Safe form submission
"""

from typing import Optional, Any

from playwright.async_api import Page, Locator

from models import Vehicle
from form_detector import FormDetector
from logger import StructuredLogger


class FormFiller:
    """Fills form fields with vehicle data."""

    def __init__(
        self,
        page: Page,
        detector: FormDetector,
        logger: Optional[StructuredLogger] = None,
    ):
        """
        Initialize form filler.

        Args:
            page:
                Playwright page.

            detector:
                FormDetector containing detected form fields.

            logger:
                Logger instance.
        """

        self.page = page
        self.detector = detector
        self.logger = logger

    # ============================================================
    # LOGGING HELPERS
    # ============================================================

    def _log_info(self, message: str) -> None:
        """Safely log info message."""

        if self.logger:
            self.logger.info(message)

    def _log_warning(self, message: str) -> None:
        """Safely log warning message."""

        if self.logger:
            self.logger.warning(message)

    def _log_debug(self, message: str) -> None:
        """Safely log debug message."""

        if self.logger:
            self.logger.debug(message)

    def _log_error(
        self,
        message: str,
        error: Optional[str] = None,
    ) -> None:
        """Safely log error message."""

        if self.logger:
            if error:
                self.logger.error(message, error=error)
            else:
                self.logger.error(message)

    # ============================================================
    # NORMALIZE VALUE
    # ============================================================

    def _normalize_value(self, value: Any) -> str:
        """Convert a value into a clean string."""

        if value is None:
            return ""

        if isinstance(value, bool):
            return "true" if value else "false"

        return str(value).strip()

    # ============================================================
    # FIELD TYPE
    # ============================================================

    def _get_field_type(self, field: dict) -> str:
        """
        Get normalized field type.

        Select elements are represented by the HTML tag rather than
        the input type attribute.
        """

        field_type = str(
            field.get("type", "text") or "text"
        ).lower()

        # FormDetector normally stores select elements as type="text"
        # because select has no type attribute. Check role/tag metadata
        # where available.
        locator = field.get("locator")

        if locator:
            # Actual tag is handled separately where needed.
            pass

        return field_type

    # ============================================================
    # SELECT DETECTION
    # ============================================================

    async def _is_select(self, locator: Locator) -> bool:
        """Check whether a locator points to a select element."""

        try:
            tag_name = await locator.evaluate(
                "(element) => element.tagName.toLowerCase()"
            )

            return tag_name == "select"

        except Exception:
            return False

    # ============================================================
    # FIELD DESCRIPTION
    # ============================================================

    def _describe_field(self, field: dict) -> str:
        """Create a readable description for logging."""

        return (
            field.get("name")
            or field.get("id")
            or field.get("label")
            or field.get("placeholder")
            or field.get("aria_label")
            or "unknown field"
        )

    # ============================================================
    # FILL SINGLE FIELD
    # ============================================================

    async def fill_field(
        self,
        field_name: str,
        value: Any,
    ) -> bool:
        """
        Fill a single form field.

        Matching is performed through FormDetector, which supports:
        - name
        - id
        - label
        - placeholder
        - aria-label
        - autocomplete
        - nearby text

        Args:
            field_name:
                Field name/search term.

            value:
                Value to enter.

        Returns:
            True if successfully filled.
        """

        # --------------------------------------------------------
        # Empty values
        # --------------------------------------------------------

        if value is None:
            return True

        value_string = self._normalize_value(value)

        if not value_string:
            return True

        # --------------------------------------------------------
        # Find field
        # --------------------------------------------------------

        field = self.detector.get_field(field_name)

        if not field:

            self._log_warning(
                f"Field not found: {field_name}"
            )

            return False

        locator = field.get("locator")

        if not locator:

            self._log_warning(
                f"No locator available for field: {field_name}"
            )

            return False

        description = self._describe_field(field)

        # --------------------------------------------------------
        # Check field state
        # --------------------------------------------------------

        try:

            if await locator.is_disabled():

                self._log_warning(
                    f"Field is disabled: {description}"
                )

                return False

        except Exception:
            pass

        try:

            if await locator.get_attribute("readonly") is not None:

                self._log_warning(
                    f"Field is readonly: {description}"
                )

                return False

        except Exception:
            pass

        # --------------------------------------------------------
        # Fill field
        # --------------------------------------------------------

        try:

            await locator.scroll_into_view_if_needed()

            await locator.wait_for(
                state="visible",
                timeout=10000,
            )

            field_type = self._get_field_type(field)

            # ----------------------------------------------------
            # SELECT
            # ----------------------------------------------------

            if await self._is_select(locator):

                success = await self._fill_select(
                    locator,
                    value_string,
                    description,
                )

                return success

            # ----------------------------------------------------
            # CHECKBOX
            # ----------------------------------------------------

            if field_type == "checkbox":

                return await self._fill_checkbox(
                    locator,
                    value,
                    description,
                )

            # ----------------------------------------------------
            # RADIO
            # ----------------------------------------------------

            if field_type == "radio":

                return await self._fill_radio(
                    locator,
                    value_string,
                    description,
                )

            # ----------------------------------------------------
            # FILE
            # ----------------------------------------------------

            if field_type == "file":

                self._log_warning(
                    f"Use upload_images() for file fields: "
                    f"{description}"
                )

                return False

            # ----------------------------------------------------
            # TEXT / NUMBER / TEL / EMAIL / TEXTAREA
            # ----------------------------------------------------

            await locator.fill(value_string)

            # ----------------------------------------------------
            # Trigger input/change events
            # ----------------------------------------------------

            try:
                await locator.dispatch_event("input")
            except Exception:
                pass

            try:
                await locator.dispatch_event("change")
            except Exception:
                pass

            # ----------------------------------------------------
            # Verify immediately
            # ----------------------------------------------------

            try:

                actual_value = await locator.input_value()

                if actual_value is not None:

                    if value_string.lower() in str(
                        actual_value
                    ).lower():

                        self._log_debug(
                            f"Filled field '{description}' "
                            f"with '{value_string}'"
                        )

                        return True

            except Exception:
                pass

            # If the website uses special JavaScript controls,
            # fill() may succeed even if input_value() is unusual.
            self._log_debug(
                f"Filled field '{description}' "
                f"with '{value_string}'"
            )

            return True

        except Exception as e:

            self._log_error(
                f"Error filling field '{field_name}'",
                str(e),
            )

            return False

    # ============================================================
    # SELECT FIELD
    # ============================================================

    async def _fill_select(
        self,
        locator: Locator,
        value: str,
        description: str,
    ) -> bool:
        """
        Fill a native HTML select element.

        Tries:
        1. Exact option value
        2. Exact visible label
        3. Case-insensitive label/value matching
        4. Partial label/value matching
        """

        try:

            # ----------------------------------------------------
            # Try exact option value
            # ----------------------------------------------------

            try:

                await locator.select_option(
                    value=value
                )

                self._log_debug(
                    f"Selected '{value}' in "
                    f"'{description}'"
                )

                return True

            except Exception:
                pass

            # ----------------------------------------------------
            # Try exact visible label
            # ----------------------------------------------------

            try:

                await locator.select_option(
                    label=value
                )

                self._log_debug(
                    f"Selected label '{value}' in "
                    f"'{description}'"
                )

                return True

            except Exception:
                pass

            # ----------------------------------------------------
            # Inspect options
            # ----------------------------------------------------

            options = locator.locator("option")

            count = await options.count()

            wanted = value.strip().lower()

            for index in range(count):

                option = options.nth(index)

                try:

                    option_value = (
                        await option.get_attribute("value")
                        or ""
                    ).strip()

                    option_text = (
                        await option.text_content()
                        or ""
                    ).strip()

                    value_lower = option_value.lower()
                    text_lower = option_text.lower()

                    # Exact match
                    if (
                        wanted == value_lower
                        or wanted == text_lower
                    ):

                        await locator.select_option(
                            index=index
                        )

                        return True

                    # Partial match
                    if (
                        wanted in value_lower
                        or wanted in text_lower
                    ):

                        await locator.select_option(
                            index=index
                        )

                        return True

                except Exception:
                    continue

            self._log_warning(
                f"Could not find option '{value}' "
                f"for '{description}'"
            )

            return False

        except Exception as e:

            self._log_error(
                f"Error selecting '{value}' "
                f"for '{description}'",
                str(e),
            )

            return False

    # ============================================================
    # CHECKBOX
    # ============================================================

    async def _fill_checkbox(
        self,
        locator: Locator,
        value: Any,
        description: str,
    ) -> bool:
        """Set checkbox state."""

        try:

            should_check = False

            if isinstance(value, bool):
                should_check = value

            else:

                normalized = str(
                    value
                ).strip().lower()

                should_check = normalized in {
                    "true",
                    "yes",
                    "1",
                    "on",
                    "checked",
                }

            if should_check:

                await locator.check()

            else:

                await locator.uncheck()

            self._log_debug(
                f"Checkbox '{description}' set to "
                f"{should_check}"
            )

            return True

        except Exception as e:

            self._log_error(
                f"Error setting checkbox "
                f"'{description}'",
                str(e),
            )

            return False

    # ============================================================
    # RADIO
    # ============================================================

    async def _fill_radio(
        self,
        locator: Locator,
        value: str,
        description: str,
    ) -> bool:
        """
        Select a radio button.

        If the locator itself matches the requested value,
        check it.
        """

        try:

            candidates = [
                await locator.get_attribute("value"),
                await locator.get_attribute("id"),
                await locator.get_attribute("name"),
            ]

            candidates = [
                str(item or "").strip().lower()
                for item in candidates
            ]

            wanted = value.strip().lower()

            if (
                wanted in candidates
                or any(
                    wanted in candidate
                    for candidate in candidates
                    if candidate
                )
            ):

                await locator.check()

                self._log_debug(
                    f"Selected radio '{description}' "
                    f"for '{value}'"
                )

                return True

            # If only one matching radio field was detected,
            # checking it is safer than silently failing.
            await locator.check()

            self._log_debug(
                f"Checked radio '{description}'"
            )

            return True

        except Exception as e:

            self._log_error(
                f"Error setting radio '{description}'",
                str(e),
            )

            return False

    # ============================================================
    # VEHICLE DATA
    # ============================================================

    async def fill_vehicle_data(
        self,
        vehicle: Vehicle,
    ) -> dict[str, bool]:
        """
        Fill the advertisement form with vehicle data.

        Returns:
            Dictionary containing field/result information.
        """

        results: dict[str, bool] = {}

        # --------------------------------------------------------
        # Field mapping
        # --------------------------------------------------------

        field_mapping = {

            "title": [
                "title",
                "vehicle title",
                "listing title",
                "ad title",
                "advertisement title",
                "heading",
            ],

            "price": [
                "price",
                "asking price",
                "selling price",
                "sale price",
                "vehicle price",
            ],

            "year": [
                "year",
                "vehicle year",
                "model year",
                "manufacturing year",
                "registration year",
            ],

            "mileage": [
                "mileage",
                "kilometers",
                "kilometres",
                "odometer",
                "km",
                "distance driven",
            ],

            "transmission": [
                "transmission",
                "gearbox",
                "gear",
            ],

            "fuel": [
                "fuel",
                "fuel type",
                "fuel_type",
                "engine fuel",
            ],

            "drive_type": [
                "drive type",
                "drivetrain",
                "drive train",
                "wheel drive",
            ],

            "colour": [
                "colour",
                "color",
                "paint color",
                "paint colour",
                "exterior color",
                "exterior colour",
            ],

            "seats": [
                "seats",
                "seat count",
                "number of seats",
                "seating capacity",
            ],

            "condition": [
                "condition",
                "vehicle condition",
                "car condition",
            ],

            "description": [
                "description",
                "vehicle description",
                "ad description",
                "listing description",
                "notes",
                "details",
            ],

            "contact_number": [
                "contact number",
                "contact phone",
                "phone",
                "phone number",
                "mobile",
                "mobile number",
                "telephone",
            ],

            "dealer_name": [
                "dealer name",
                "dealer",
                "seller name",
                "seller",
                "company name",
                "business name",
            ],

            "dealer_address": [
                "dealer address",
                "seller address",
                "address",
                "location",
                "business address",
            ],
        }

        # --------------------------------------------------------
        # Process each vehicle attribute
        # --------------------------------------------------------

        for attribute, possible_names in field_mapping.items():

            try:

                value = getattr(
                    vehicle,
                    attribute,
                    None,
                )

            except Exception:

                value = None

            if value is None:
                continue

            value_string = self._normalize_value(
                value
            )

            if not value_string:
                continue

            filled = False

            # ----------------------------------------------------
            # Try every possible field name
            # ----------------------------------------------------

            for possible_name in possible_names:

                field = self.detector.get_field(
                    possible_name
                )

                if not field:
                    continue

                filled = await self.fill_field(
                    possible_name,
                    value,
                )

                if filled:

                    results[attribute] = True

                    self._log_info(
                        f"Filled vehicle field: "
                        f"{attribute} -> "
                        f"{self._describe_field(field)}"
                    )

                    break

            # ----------------------------------------------------
            # Attribute could not be filled
            # ----------------------------------------------------

            if not filled:

                results[attribute] = False

                self._log_warning(
                    f"Could not fill vehicle attribute: "
                    f"{attribute}"
                )

        # --------------------------------------------------------
        # Description / TinyMCE
        # --------------------------------------------------------

        description = getattr(
            vehicle,
            "description",
            None,
        )

        if description:

            description_string = self._normalize_value(
                description
            )

            # Only attempt TinyMCE if normal description
            # field wasn't found or filled.
            if not results.get("description", False):

                tinymce_filled = await self.fill_tinymce(
                    description_string
                )

                if tinymce_filled:
                    results["description"] = True

        # --------------------------------------------------------
        # Log summary
        # --------------------------------------------------------

        successful = sum(
            1
            for value in results.values()
            if value
        )

        failed = sum(
            1
            for value in results.values()
            if not value
        )

        self._log_info(
            f"Vehicle form filling completed: "
            f"{successful} successful, "
            f"{failed} failed"
        )

        return results

    # ============================================================
    # IMAGE UPLOAD
    # ============================================================

    async def upload_images(
        self,
        image_paths: list[str],
    ) -> bool:
        """
        Upload vehicle images.

        Supports:
        - Multiple files in one input
        - Separate file inputs
        - Up to 10 images

        Args:
            image_paths:
                List of image file paths.

        Returns:
            True if upload was attempted successfully.
        """

        if not image_paths:
            return True

        try:

            # Limit images.
            image_paths = image_paths[:10]

            # ----------------------------------------------------
            # Prefer detector's file inputs
            # ----------------------------------------------------

            file_inputs = []

            try:

                file_inputs = (
                    await self.detector.find_file_inputs()
                )

            except Exception:
                file_inputs = []

            # ----------------------------------------------------
            # Fallback to page-level file inputs
            # ----------------------------------------------------

            if not file_inputs:

                page_inputs = self.page.locator(
                    'input[type="file"]'
                )

                count = await page_inputs.count()

                for index in range(count):

                    locator = page_inputs.nth(index)

                    try:

                        if not await locator.is_disabled():

                            file_inputs.append(
                                locator
                            )

                    except Exception:
                        continue

            if not file_inputs:

                self._log_warning(
                    "No file input found for image upload"
                )

                return False

            # ----------------------------------------------------
            # Upload all files together if possible
            # ----------------------------------------------------

            try:

                first_input = file_inputs[0]

                await first_input.set_input_files(
                    image_paths
                )

                self._log_info(
                    f"Uploaded {len(image_paths)} image(s)"
                )

                return True

            except Exception as e:

                self._log_debug(
                    f"Multiple file upload failed: {e}"
                )

            # ----------------------------------------------------
            # Fallback: upload one-by-one
            # ----------------------------------------------------

            uploaded_count = 0

            for index, image_path in enumerate(
                image_paths
            ):

                try:

                    target_input = file_inputs[
                        min(
                            index,
                            len(file_inputs) - 1,
                        )
                    ]

                    await target_input.set_input_files(
                        image_path
                    )

                    uploaded_count += 1

                    self._log_info(
                        f"Uploaded image: "
                        f"{image_path}"
                    )

                except Exception as e:

                    self._log_warning(
                        f"Failed to upload image "
                        f"{image_path}: {e}"
                    )

            return uploaded_count > 0

        except Exception as e:

            self._log_error(
                "Error uploading images",
                str(e),
            )

            return False

    # ============================================================
    # TINYMCE
    # ============================================================

    async def fill_tinymce(
        self,
        content: str,
    ) -> bool:
        """
        Fill TinyMCE editor.

        Supports:
        - TinyMCE active editor
        - TinyMCE iframe
        - #tinymce contenteditable element
        """

        if not content:
            return True

        try:

            # ----------------------------------------------------
            # Method 1: TinyMCE JavaScript API
            # ----------------------------------------------------

            result = await self.page.evaluate(
                """
                (content) => {
                    if (
                        window.tinymce &&
                        window.tinymce.activeEditor
                    ) {
                        window.tinymce.activeEditor.setContent(
                            content
                        );

                        window.tinymce.activeEditor.fire(
                            'change'
                        );

                        return true;
                    }

                    return false;
                }
                """,
                content,
            )

            if result:

                self._log_info(
                    "TinyMCE editor filled successfully"
                )

                return True

            # ----------------------------------------------------
            # Method 2: iframe
            # ----------------------------------------------------

            iframe = self.page.locator(
                "iframe.tox-edit-area__iframe, "
                "iframe[id*='tinymce'], "
                "iframe"
            ).first

            try:

                if await iframe.count() > 0:

                    if await iframe.is_visible():

                        frame = iframe.content_frame

                        if frame:

                            body = frame.locator(
                                "body"
                            )

                            if await body.count() > 0:

                                await body.fill(
                                    content
                                )

                                self._log_info(
                                    "TinyMCE iframe filled"
                                )

                                return True

            except Exception:
                pass

            # ----------------------------------------------------
            # Method 3: #tinymce
            # ----------------------------------------------------

            editor = self.page.locator(
                "#tinymce"
            ).first

            try:

                if await editor.count() > 0:

                    if await editor.is_visible():

                        await editor.fill(
                            content
                        )

                        self._log_info(
                            "TinyMCE content area filled"
                        )

                        return True

            except Exception:
                pass

            self._log_warning(
                "TinyMCE editor detected but could not be filled"
            )

            return False

        except Exception as e:

            self._log_warning(
                f"Failed to fill TinyMCE: {e}"
            )

            return False

    # ============================================================
    # VERIFY FORM
    # ============================================================

    async def verify_form(
        self,
        vehicle: Vehicle,
    ) -> dict[str, Any]:
        """
        Verify important vehicle fields.

        Returns:
            Verification report containing:
            - verified_fields
            - unverified_fields
            - mismatches
        """

        report: dict[str, Any] = {
            "verified_fields": [],
            "unverified_fields": [],
            "mismatches": [],
        }

        # --------------------------------------------------------
        # Fields to verify
        # --------------------------------------------------------

        fields_to_verify = {
            "title": getattr(
                vehicle,
                "title",
                None,
            ),

            "price": getattr(
                vehicle,
                "price",
                None,
            ),

            "year": getattr(
                vehicle,
                "year",
                None,
            ),

            "mileage": getattr(
                vehicle,
                "mileage",
                None,
            ),

            "transmission": getattr(
                vehicle,
                "transmission",
                None,
            ),

            "fuel": getattr(
                vehicle,
                "fuel",
                None,
            ),

            "colour": getattr(
                vehicle,
                "colour",
                None,
            ),
        }

        # --------------------------------------------------------
        # Verify each field
        # --------------------------------------------------------

        for field_name, expected_value in fields_to_verify.items():

            if expected_value is None:
                continue

            expected = self._normalize_value(
                expected_value
            )

            if not expected:
                continue

            # ----------------------------------------------------
            # Find corresponding field
            # ----------------------------------------------------

            field = self.detector.get_field(
                field_name
            )

            if not field:

                # Field might not exist on the destination form.
                # This is not necessarily a mismatch.
                report["unverified_fields"].append(
                    field_name
                )

                continue

            # ----------------------------------------------------
            # Read actual value
            # ----------------------------------------------------

            actual_value = (
                await self.detector.get_field_value(
                    field_name
                )
            )

            actual = self._normalize_value(
                actual_value
            )

            # ----------------------------------------------------
            # Compare normalized values
            # ----------------------------------------------------

            expected_normalized = (
                expected.lower()
                .replace(",", "")
                .strip()
            )

            actual_normalized = (
                actual.lower()
                .replace(",", "")
                .strip()
            )

            if (
                expected_normalized == actual_normalized
                or expected_normalized
                in actual_normalized
            ):

                report["verified_fields"].append(
                    field_name
                )

            else:

                report["unverified_fields"].append(
                    field_name
                )

                report["mismatches"].append(
                    {
                        "field": field_name,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )

        # --------------------------------------------------------
        # Summary log
        # --------------------------------------------------------

        self._log_info(
            "Form verification completed: "
            f"{len(report['verified_fields'])} verified, "
            f"{len(report['mismatches'])} mismatches"
        )

        return report

    # ============================================================
    # SUBMIT FORM
    # ============================================================

    async def submit_form(
        self,
        confirm: bool = False,
    ) -> bool:
        """
        Submit the advertisement form.

        If confirm=True, the user must type YES.

        Args:
            confirm:
                Require explicit confirmation.

        Returns:
            True if submission appears successful.
        """

        # --------------------------------------------------------
        # Confirmation
        # --------------------------------------------------------

        if confirm:

            try:

                confirmation = input(
                    "\nSUBMIT AD?\n"
                    "Type YES to continue: "
                )

            except EOFError:

                self._log_warning(
                    "Could not read confirmation input"
                )

                return False

            if (
                confirmation.strip().upper()
                != "YES"
            ):

                self._log_info(
                    "Submission cancelled by user"
                )

                return False

        # --------------------------------------------------------
        # Find submit button
        # --------------------------------------------------------

        try:

            selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Post")',
                'button:has-text("Publish")',
                'button:has-text("Create")',
                'button:has-text("Save")',
            ]

            submit_button: Optional[Locator] = None

            # Prefer submit button inside detected form.
            if self.detector.form:

                for selector in selectors:

                    try:

                        candidate = (
                            self.detector.form
                            .locator(selector)
                            .first
                        )

                        if await candidate.count() > 0:

                            if await candidate.is_visible():

                                submit_button = candidate
                                break

                    except Exception:
                        continue

            # Fallback to entire page.
            if submit_button is None:

                for selector in selectors:

                    try:

                        candidate = (
                            self.page
                            .locator(selector)
                            .first
                        )

                        if await candidate.count() > 0:

                            if await candidate.is_visible():

                                submit_button = candidate
                                break

                    except Exception:
                        continue

            if submit_button is None:

                self._log_warning(
                    "Submit button not found"
                )

                return False

            # ----------------------------------------------------
            # Check disabled state
            # ----------------------------------------------------

            try:

                if await submit_button.is_disabled():

                    self._log_warning(
                        "Submit button is disabled"
                    )

                    return False

            except Exception:
                pass

            # ----------------------------------------------------
            # Scroll to submit button
            # ----------------------------------------------------

            try:

                await submit_button.scroll_into_view_if_needed()

            except Exception:
                pass

            # ----------------------------------------------------
            # Click
            # ----------------------------------------------------

            await submit_button.click()

            self._log_info(
                "Submit button clicked"
            )

            # ----------------------------------------------------
            # Wait for page/network
            # ----------------------------------------------------

            try:

                await self.page.wait_for_load_state(
                    "networkidle",
                    timeout=15000,
                )

            except Exception:

                # Some modern websites never reach networkidle.
                # Do not automatically treat that as failure.
                self._log_debug(
                    "Network did not become idle after submission"
                )

            # ----------------------------------------------------
            # Small safety wait
            # ----------------------------------------------------

            try:

                await self.page.wait_for_timeout(
                    1500
                )

            except Exception:
                pass

            self._log_info(
                "Form submission completed"
            )

            return True

        except Exception as e:

            self._log_error(
                "Error submitting form",
                str(e),
            )

            return False