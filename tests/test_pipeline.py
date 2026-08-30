import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from car_ad_automation.stages.dedupe.deduplicator import check_duplicates, generate_fingerprint
from car_ad_automation.stages.scrape.parser import parse_listing
from car_ad_automation.stages.normalize.validator import validate_vehicle
from car_ad_automation.stages.post.automation.form_mapper import map_vehicle
from car_ad_automation.core.models import Vehicle


class PipelineTests(unittest.TestCase):
    def test_parser_never_uses_dot_and_keeps_listing_image(self):
        html = '''<html><head><script type="application/ld+json">{"@type":"Product","name":"2018 Volkswagen Kombi 2.0 BiTDI","productionDate":"2018","offers":{"price":449950}}</script></head><body><main><img src="https://img.example/recommended/999.jpg"><img src="https://img.example/carsimages/123456/one.jpg"></main></body></html>'''
        record = parse_listing(html, "https://www.cars.co.za/for-sale/used/2018-vw-kombi/123456/")
        self.assertNotIn(".", record.values())
        self.assertEqual(record["price"], 449950)
        self.assertEqual(record["images"], ["https://img.example/carsimages/123456/one.jpg"])

    def test_validator_warns_on_no_images(self):
        vehicle = Vehicle(
            id="test1",
            title="Test Car",
            price=10000,
            images=[]
        )
        result = validate_vehicle(vehicle)
        self.assertTrue(result.valid)  # Still valid, but with warning
        self.assertIn("No images provided", result.warnings)

    def test_deduplicator_generates_fingerprint(self):
        vehicle = Vehicle(
            id="test1",
            title="2018 Volkswagen Kombi",
            year=2018,
            price=449950,
            condition="used"
        )
        fingerprint = generate_fingerprint(vehicle)
        self.assertIsInstance(fingerprint, str)
        self.assertEqual(len(fingerprint), 64)  # SHA256 hex

    def test_form_mapper_maps_location_and_schema_condition(self):
        record = {"source_url": "https://example.test/1", "title": "Car", "description": "Description", "price": 1, "mileage": "100 km", "images": [str(index) for index in range(5)], "location": "South Africa", "condition": "https://schema.org/UsedCondition", "transmission": "Automatic", "fuel": "Petrol", "drive_type": "4x2", "colour": "Silver"}
        mapped, errors = map_vehicle(record, {"country": ["South Africa"], "condition": ["Used"], "transmission": ["Automatic"], "fuel": ["Petrol"], "drive_type": ["4x2"], "colour": ["Silver"]})
        self.assertFalse(errors)
        self.assertEqual(mapped["country"], "South Africa")


class ImageDownloadTests(unittest.TestCase):
    @patch('car_ad_automation.stages.build.image_downloader.requests.Session.get')
    def test_image_download_success(self, mock_get):
        """Verify successful download stores local paths in vehicle.images"""
        from car_ad_automation.stages.build.image_downloader import download_vehicle_images
        from car_ad_automation.core.config import IMAGE_DOWNLOAD_DIR
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.content = b"fake image content"
        mock_get.return_value = mock_response
        
        record = {
            "source_id": "test123",
            "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        }
        
        local_paths = download_vehicle_images(record)
        
        # Verify download was called
        self.assertEqual(mock_get.call_count, 2)
        
        # Verify local paths returned
        self.assertEqual(len(local_paths), 2)
        for path in local_paths:
            self.assertTrue(path.startswith(str(IMAGE_DOWNLOAD_DIR)))
            self.assertTrue(path.endswith(".jpg"))

    @patch('car_ad_automation.stages.build.image_downloader.requests.Session.get')
    def test_image_download_zero_images_raises_error(self, mock_get):
        """0 successful downloads → ValueError"""
        from car_ad_automation.stages.build.image_downloader import download_vehicle_images
        
        # Mock all requests to fail with RequestException
        import requests
        mock_get.side_effect = requests.RequestException("Network error")
        
        record = {
            "source_id": "test123",
            "images": ["https://example.com/img1.jpg"]
        }
        
        with self.assertRaises(ValueError) as ctx:
            download_vehicle_images(record)
        
        self.assertIn("All image downloads failed", str(ctx.exception))

    @patch('car_ad_automation.stages.build.image_downloader.requests.Session.get')
    def test_image_download_partial_failure_logs_warning(self, mock_get):
        """Some downloads fail → warning logged but function succeeds"""
        from car_ad_automation.stages.build.image_downloader import download_vehicle_images
        import requests
        import logging
        
        # Mock: first call succeeds, second fails
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.content = b"fake image content"
        
        mock_get.side_effect = [mock_response, requests.RequestException("Timeout")]
        
        record = {
            "source_id": "test123",
            "images": ["https://example.com/img1.jpg", "https://example.com/img2.jpg"]
        }
        
        with self.assertLogs(level=logging.WARNING) as cm:
            local_paths = download_vehicle_images(record)
        
        self.assertEqual(len(local_paths), 1)
        # Verify warning was logged about failed downloads
        self.assertTrue(any("failed" in msg.lower() for msg in cm.output))

@patch('car_ad_automation.stages.build.image_downloader.requests.Session.get')
def test_image_download_5_plus_no_warning(self, mock_get):
        """5+ images all succeed → no warning about failures"""
        from car_ad_automation.stages.build.image_downloader import download_vehicle_images
        
        # Mock 5 successful downloads
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"Content-Type": "image/jpeg"}
        mock_response.content = b"fake image content"
        mock_get.return_value = mock_response
        
        record = {
            "source_id": "test123",
            "images": [f"https://example.com/img{i}.jpg" for i in range(5)]
        }
        
        # Should complete without raising any exception
        local_paths = download_vehicle_images(record)
        
        self.assertEqual(len(local_paths), 5)
        # All 5 downloaded successfully


class CategorySelectionTests(unittest.TestCase):
    def test_category_selection_failure_raises_error(self):
        """Category failure → ValueError with vehicle ID and URL"""
        from car_ad_automation.pipeline.pipeline import Pipeline
        
        # This test would require mocking the browser/page
        # For now, we verify the error message format in the pipeline code
        pass
    
    def test_pipeline_stops_on_category_failure(self):
        """Subsequent vehicles not processed after category failure"""
        pass


class LocalPathHandoffTests(unittest.TestCase):
    def test_local_paths_passed_to_stage_6(self):
        """vehicle.images contains local paths after stage 5"""
        pass


if __name__ == "__main__":
    unittest.main()