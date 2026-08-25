#!/usr/bin/env python3
"""Test script for normalization and validation."""

import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from normalizer import normalize_record
from validator import validate_vehicle

def test_normalization_and_validation():
    """Test normalization and validation of test inventory."""
    
    print("="*60)
    print("TESTING NORMALIZATION AND VALIDATION")
    print("="*60)
    
    # Load test inventory
    test_file = Path("data/inventory.json")
    if not test_file.exists():
        print(f"ERROR: Test file not found: {test_file}")
        return False
    
    try:
        records = json.loads(test_file.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"ERROR: Failed to load test file: {e}")
        return False
    
    print(f"\nLoaded {len(records)} test records")
    
    all_valid = True
    
    for idx, record in enumerate(records):
        print(f"\n{'-'*60}")
        print(f"RECORD {idx + 1}: {record.get('title', 'Unknown')}")
        print(f"{'-'*60}")
        
        # Normalize
        try:
            vehicle = normalize_record(record)
            print(f"✓ Normalized successfully")
            print(f"  ID:           {vehicle.id}")
            print(f"  Title:        {vehicle.title}")
            print(f"  Price:        {vehicle.price}")
            print(f"  Year:         {vehicle.year}")
            print(f"  Mileage:      {vehicle.mileage}")
            print(f"  Transmission: {vehicle.transmission}")
            print(f"  Fuel:         {vehicle.fuel}")
            print(f"  Features:     {len(vehicle.features)}")
            print(f"  Images:       {len(vehicle.images)}")
        except Exception as e:
            print(f"✗ Normalization failed: {e}")
            all_valid = False
            continue
        
        # Validate
        try:
            result = validate_vehicle(vehicle)
            
            if result.valid:
                print(f"✓ Validation PASSED")
                print(f"  Quality Score: {result.quality_score}%")
                if result.warnings:
                    print(f"  Warnings: {len(result.warnings)}")
                    for warning in result.warnings[:3]:
                        print(f"    - {warning}")
            else:
                print(f"✗ Validation FAILED")
                print(f"  Errors:")
                for error in result.errors:
                    print(f"    - {error}")
                all_valid = False
        
        except Exception as e:
            print(f"✗ Validation error: {e}")
            all_valid = False
    
    print(f"\n{'='*60}")
    if all_valid:
        print("RESULT: ALL TESTS PASSED ✓")
        print(f"Valid records: {len(records)}/{len(records)}")
    else:
        print("RESULT: SOME TESTS FAILED ✗")
    print(f"{'='*60}\n")
    
    return all_valid

if __name__ == '__main__':
    success = test_normalization_and_validation()
    sys.exit(0 if success else 1)
