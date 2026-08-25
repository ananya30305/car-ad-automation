import unittest

from deduplicator import deduplicate, normalize_url
from parser import parse_listing
from validator import validate_car
from automation.form_mapper import map_vehicle


class PipelineTests(unittest.TestCase):
    def test_parser_never_uses_dot_and_keeps_listing_image(self):
        html = '''<html><head><script type="application/ld+json">{"@type":"Product","name":"2018 Volkswagen Kombi 2.0 BiTDI","productionDate":"2018","offers":{"price":449950}}</script></head><body><main><img src="https://img.example/recommended/999.jpg"><img src="https://img.example/carsimages/123456/one.jpg"></main></body></html>'''
        record = parse_listing(html, "https://www.cars.co.za/for-sale/used/2018-vw-kombi/123456/")
        self.assertNotIn(".", record.values())
        self.assertEqual(record["price"], 449950)
        self.assertEqual(record["images"], ["https://img.example/carsimages/123456/one.jpg"])

    def test_validator_rejects_incomplete_images(self):
        result = validate_car({"source_url": "https://example.test/1", "images": ["https://img.example/1.jpg"]})
        self.assertEqual(result["validation_status"], "incomplete")
        self.assertIn("images", result["missing_fields"])
        self.assertEqual(result["quality_score"], 11)

    def test_deduplicator_normalizes_tracking_and_trailing_slash(self):
        records = [{"source_url": "HTTPS://Cars.co.za/for-sale/used/a/123/?utm_source=x", "listing_id": "123"}, {"source_url": "https://cars.co.za/for-sale/used/a/123", "listing_id": "123"}]
        unique, duplicates = deduplicate(records)
        self.assertEqual(len(unique), 1)
        self.assertEqual(duplicates, 1)
        self.assertEqual(normalize_url(unique[0]["source_url"]), "https://cars.co.za/for-sale/used/a/123/")

    def test_form_mapper_maps_location_and_schema_condition(self):
        record = {"source_url": "https://example.test/1", "title": "Car", "description": "Description", "price": 1, "mileage": "100 km", "images": [str(index) for index in range(5)], "location": "South Africa", "condition": "https://schema.org/UsedCondition", "transmission": "Automatic", "fuel": "Petrol", "drive_type": "4x2", "colour": "Silver"}
        mapped, errors = map_vehicle(record, {"country": ["South Africa"], "condition": ["Used"], "transmission": ["Automatic"], "fuel": ["Petrol"], "drive_type": ["4x2"], "colour": ["Silver"]})
        self.assertFalse(errors)
        self.assertEqual(mapped["country"], "South Africa")


if __name__ == "__main__":
    unittest.main()
