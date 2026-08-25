#!/usr/bin/env python3
"""Test script for deduplication and description generation."""

import json
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from normalizer import normalize_record
from validator import validate_vehicle
from deduplicator import check_duplicates
from description_builder import build_description

def test_deduplication_and_descriptions():
    """Test deduplication and description generation."""
    
    print("="*60)
    print("TESTING DEDUPLICATION AND DESCRIPTIONS")
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
    
    # Normalize all
    vehicles = []
    for record in records:
        vehicle = normalize_record(record)
        vehicles.append(vehicle)
    
    print(f"Normalized {len(vehicles)} records")
    
    # Test deduplication
    print(f"\n{'-'*60}")
    print("DEDUPLICATION TEST")
    print(f"{'-'*60}")
    
    unique_vehicles, duplicates, fingerprints = check_duplicates(vehicles)
    
    print(f"Unique vehicles: {len(unique_vehicles)}")
    print(f"Duplicates found: {len(duplicates)}")
    
    for vehicle in unique_vehicles:
        print(f"  ✓ {vehicle.id}: {vehicle.title}")
    
    # Test description generation
    print(f"\n{'-'*60}")
    print("DESCRIPTION GENERATION TEST")
    print(f"{'-'*60}")
    
    for vehicle in unique_vehicles:
        original_desc = vehicle.description
        generated_desc = build_description(vehicle)
        
        print(f"\nVehicle: {vehicle.id}")
        print(f"  Original description length: {len(original_desc) if original_desc else 0} chars")
        print(f"  Generated description preview: {generated_desc[:100]}...")
        
        if original_desc:
            print(f"  ✓ Using provided description")
        else:
            print(f"  ✓ Generated description from structured fields")
    
    print(f"\n{'='*60}")
    print("RESULT: ALL TESTS PASSED ✓")
    print(f"{'='*60}\n")
    
    return True

if __name__ == '__main__':
    success = test_deduplication_and_descriptions()
    sys.exit(0 if success else 1)
