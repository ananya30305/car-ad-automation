"""Form detection and analysis."""

from typing import Optional
from playwright.async_api import Page, Locator
from logger import StructuredLogger


class FormDetector:
    """Detects form structure and available fields."""
    
    def __init__(self, page: Page, logger: Optional[StructuredLogger] = None):
        """
        Initialize form detector.
        
        Args:
            page: Playwright page object
            logger: Logger instance
        """
        self.page = page
        self.logger = logger
        self.form = None
        self.fields = {}
    
    async def find_form(self, selector: Optional[str] = None) -> bool:
        """
        Find the main form on the page.
        
        Args:
            selector: Optional CSS selector for form
            
        Returns:
            True if form found
        """
        try:
            # Try common selectors
            selectors = [
                selector,  # User-provided
                'form[id*="post"]',
                'form[id*="ad"]',
                'form[id*="listing"]',
                'form',
            ]
            
            for sel in selectors:
                if not sel:
                    continue
                
                try:
                    form = self.page.locator(sel).first
                    if await form.is_visible():
                        self.form = form
                        if self.logger:
                            self.logger.info(f"Form detected with selector: {sel}")
                        return True
                except Exception:
                    continue
            
            if self.logger:
                self.logger.warning("Could not detect form on page")
            return False
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error detecting form: {e}")
            return False
    
    async def analyze_fields(self) -> dict[str, dict]:
        """
        Analyze available form fields.
        
        Returns:
            Dictionary mapping field names to field info
        """
        if not self.form:
            return {}
        
        self.fields = {}
        
        try:
            # Find all inputs
            inputs = await self.form.locator('input, select, textarea').all()
            
            for field in inputs:
                try:
                    # Get field attributes
                    field_type = await field.get_attribute('type') or 'text'
                    field_name = await field.get_attribute('name') or ''
                    field_id = await field.get_attribute('id') or ''
                    field_class = await field.get_attribute('class') or ''
                    
                    # Try to get label
                    label_text = ''
                    try:
                        if field_id:
                            label = self.page.locator(f'label[for="{field_id}"]')
                            label_text = await label.text_content() or ''
                        
                        if not label_text:
                            # Try parent label
                            parent_label = await field.locator('..').locator('label').first.text_content()
                            label_text = parent_label or ''
                    except:
                        pass
                    
                    field_key = field_name or field_id or label_text.lower()
                    
                    self.fields[field_key] = {
                        'type': field_type,
                        'name': field_name,
                        'id': field_id,
                        'label': label_text.strip(),
                        'class': field_class,
                        'locator': field
                    }
                except Exception as e:
                    if self.logger:
                        self.logger.debug(f"Error analyzing field: {e}")
                    continue
            
            if self.logger:
                self.logger.info(f"Found {len(self.fields)} form fields")
            
            return self.fields
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error analyzing form fields: {e}")
            return {}
    
    def get_field(self, field_name: str) -> Optional[dict]:
        """
        Get field information.
        
        Args:
            field_name: Field name or partial match
            
        Returns:
            Field info dict or None
        """
        # Exact match
        if field_name in self.fields:
            return self.fields[field_name]
        
        # Case-insensitive match
        field_lower = field_name.lower()
        for key, value in self.fields.items():
            if key.lower() == field_lower:
                return value
            if value.get('label', '').lower() == field_lower:
                return value
        
        # Partial match
        for key, value in self.fields.items():
            if field_lower in key.lower():
                return value
            if field_lower in value.get('label', '').lower():
                return value
        
        return None
    
    async def has_field(self, field_name: str) -> bool:
        """Check if field exists."""
        return self.get_field(field_name) is not None
    
    async def get_field_value(self, field_name: str) -> Optional[str]:
        """
        Get current value of a field.
        
        Args:
            field_name: Field name
            
        Returns:
            Field value or None
        """
        field = self.get_field(field_name)
        if not field:
            return None
        
        try:
            locator = field.get('locator')
            if locator:
                return await locator.input_value()
        except:
            pass
        
        return None
    
    async def detect_tinymce(self) -> bool:
        """
        Detect if TinyMCE editor is present.
        
        Returns:
            True if TinyMCE detected
        """
        try:
            tinymce = self.page.locator('#tinymce, .mce-container, [class*="tinymce"]').first
            return await tinymce.is_visible()
        except:
            return False
    
    async def detect_recaptcha(self) -> bool:
        """
        Detect if reCAPTCHA is present.
        
        Returns:
            True if reCAPTCHA detected
        """
        try:
            recaptcha = self.page.locator('[data-sitekey], .g-recaptcha, iframe[src*="recaptcha"]').first
            return await recaptcha.is_visible()
        except:
            return False
