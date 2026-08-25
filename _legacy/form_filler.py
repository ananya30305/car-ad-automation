"""Form filling and submission."""

from typing import Optional, Any
from playwright.async_api import Page
from models import Vehicle
from form_detector import FormDetector
from logger import StructuredLogger


class FormFiller:
    """Fills form fields with vehicle data."""
    
    def __init__(self, page: Page, detector: FormDetector, logger: Optional[StructuredLogger] = None):
        """
        Initialize form filler.
        
        Args:
            page: Playwright page
            detector: FormDetector instance
            logger: Logger instance
        """
        self.page = page
        self.detector = detector
        self.logger = logger
    
    async def fill_field(self, field_name: str, value: Any) -> bool:
        """
        Fill a single form field.
        
        Args:
            field_name: Field name
            value: Value to fill
            
        Returns:
            True if successful
        """
        if not value:
            return True  # Skip empty values
        
        field = self.detector.get_field(field_name)
        if not field:
            if self.logger:
                self.logger.warning(f"Field not found: {field_name}")
            return False
        
        try:
            locator = field.get('locator')
            field_type = field.get('type', 'text')
            
            if not locator:
                return False
            
            # Wait for field to be visible
            await locator.wait_for(state='visible', timeout=5000)
            
            if field_type == 'select':
                # Handle select elements
                await locator.select_option(str(value))
            elif field_type in ('checkbox', 'radio'):
                # Handle checkboxes/radio buttons
                if value:
                    await locator.check()
                else:
                    await locator.uncheck()
            else:
                # Handle text inputs
                await locator.fill(str(value))
            
            if self.logger:
                self.logger.debug(f"Filled field {field_name} with {value}")
            
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error filling field {field_name}: {e}", field=field_name, error=str(e))
            return False
    
    async def fill_vehicle_data(self, vehicle: Vehicle) -> dict[str, bool]:
        """
        Fill form with vehicle data.
        
        Args:
            vehicle: Vehicle object with data
            
        Returns:
            Dictionary mapping field names to success status
        """
        results = {}
        
        # Mapping of vehicle attributes to form field names
        field_mapping = {
            'title': ['title', 'vehicle_title', 'listing_title'],
            'price': ['price', 'asking_price', 'selling_price'],
            'year': ['year', 'vehicle_year', 'model_year'],
            'mileage': ['mileage', 'kilometers', 'odometer'],
            'transmission': ['transmission', 'gearbox'],
            'fuel': ['fuel', 'fuel_type', 'engine_type'],
            'drive_type': ['drive_type', 'drivetrain'],
            'colour': ['colour', 'color', 'paint_color'],
            'seats': ['seats', 'seat_count'],
            'condition': ['condition'],
            'description': ['description', 'notes', 'details'],
            'contact_number': ['contact_number', 'phone', 'mobile'],
            'dealer_name': ['dealer_name', 'dealer', 'seller_name'],
            'dealer_address': ['dealer_address', 'seller_address', 'location'],
        }
        
        # Try to fill each field
        for attr, possible_names in field_mapping.items():
            value = getattr(vehicle, attr, None)
            
            if not value:
                continue
            
            success = False
            for field_name in possible_names:
                if await self.detector.has_field(field_name):
                    success = await self.fill_field(field_name, value)
                    results[field_name] = success
                    if success:
                        break
            
            if not success and value:
                if self.logger:
                    self.logger.warning(f"Could not fill attribute {attr}")
        
        return results
    
    async def upload_images(self, image_paths: list[str]) -> bool:
        """
        Upload images to form.
        
        Args:
            image_paths: List of image file paths
            
        Returns:
            True if all images uploaded
        """
        if not image_paths:
            return True
        
        try:
            # Find file input
            file_input = self.page.locator('input[type="file"]').first
            
            if not await file_input.is_visible():
                if self.logger:
                    self.logger.warning("No file input found for images")
                return False
            
            # Upload files (single or multiple)
            for image_path in image_paths[:10]:  # Limit to 10
                try:
                    await file_input.set_input_files(image_path)
                    if self.logger:
                        self.logger.info(f"Uploaded image: {image_path}")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Failed to upload image {image_path}: {e}")
            
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error uploading images: {e}")
            return False
    
    async def fill_tinymce(self, content: str) -> bool:
        """
        Fill TinyMCE editor.
        
        Args:
            content: HTML content to insert
            
        Returns:
            True if successful
        """
        try:
            # Try direct content insertion
            await self.page.evaluate(f"""
                if (window.tinymce && window.tinymce.activeEditor) {{
                    window.tinymce.activeEditor.setContent('{content}');
                }}
            """)
            
            return True
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to fill TinyMCE: {e}")
            return False
    
    async def verify_form(self, vehicle: Vehicle) -> dict[str, Any]:
        """
        Verify that form was filled correctly.
        
        Args:
            vehicle: Original vehicle data
            
        Returns:
            Verification report
        """
        report = {
            'verified_fields': [],
            'unverified_fields': [],
            'mismatches': []
        }
        
        # Check key fields
        fields_to_verify = {
            'title': vehicle.title,
            'price': str(vehicle.price) if vehicle.price else None,
            'year': str(vehicle.year) if vehicle.year else None,
        }
        
        for field_name, expected_value in fields_to_verify.items():
            if not expected_value:
                continue
            
            actual_value = await self.detector.get_field_value(field_name)
            
            if actual_value and str(expected_value).lower() in actual_value.lower():
                report['verified_fields'].append(field_name)
            else:
                report['unverified_fields'].append(field_name)
                report['mismatches'].append({
                    'field': field_name,
                    'expected': expected_value,
                    'actual': actual_value
                })
        
        return report
    
    async def submit_form(self, confirm: bool = False) -> bool:
        """
        Submit the form.
        
        Args:
            confirm: If True, require explicit confirmation
            
        Returns:
            True if submitted
        """
        if confirm:
            # Require user confirmation
            confirmation = input("\nSUBMIT AD?\nType YES to continue: ")
            if confirmation.strip().upper() != "YES":
                if self.logger:
                    self.logger.info("Submission cancelled by user")
                return False
        
        try:
            # Find and click submit button
            submit_button = self.page.locator('button[type="submit"], input[type="submit"]').first
            
            if not await submit_button.is_visible():
                if self.logger:
                    self.logger.warning("Submit button not found")
                return False
            
            await submit_button.click()
            
            # Wait for navigation/success
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            if self.logger:
                self.logger.info("Form submitted successfully")
            
            return True
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error submitting form: {e}")
            return False
