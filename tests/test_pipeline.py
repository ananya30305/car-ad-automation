import unittest

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


if __name__ == "__main__":
    unittest.main()