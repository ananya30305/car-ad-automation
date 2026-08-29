import json
from pathlib import Path

from car_ad_automation.core.config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "cars.json"
OUTPUT_FILE = OUTPUT_DIR / "sample_car.html"


def main():

    if not Path(INPUT_FILE).exists():
        print(f"ERROR: {INPUT_FILE} does not exist.")
        return

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        cars = json.load(file)

    if not isinstance(cars, list) or not cars:
        print("ERROR: cars.json contains no cars.")
        return

    car = cars[0]

    html = car.get("html", "")

    if not html:
        print("ERROR: First car does not contain HTML.")
        print("Available keys:")
        print(car.keys())
        return

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(html)

    print("=" * 70)
    print("HTML SAMPLE EXTRACTED")
    print("=" * 70)
    print(f"Saved to: {OUTPUT_FILE}")
    print(f"HTML length: {len(html)} characters")
    print()
    print("First 1000 characters:")
    print("-" * 70)
    print(html[:1000])
    print("-" * 70)


if __name__ == "__main__":
    main()