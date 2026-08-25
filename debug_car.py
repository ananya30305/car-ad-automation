import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from config import OUTPUT_DIR


INPUT_FILE = OUTPUT_DIR / "cars.json"


def clean(text):
    if text is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text).replace("\xa0", " ")
    ).strip()


def main():

    if not Path(INPUT_FILE).exists():
        print(f"ERROR: {INPUT_FILE} not found.")
        return

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        cars = json.load(file)

    if not cars:
        print("ERROR: cars.json is empty.")
        return

    car = cars[0]

    html = car.get("html", "")

    if not html:
        print("ERROR: First record has no HTML.")
        print("Keys:", list(car.keys()))
        return

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    print()
    print("=" * 80)
    print("CAR DEBUG INFORMATION")
    print("=" * 80)

    # --------------------------------------------------------
    # URLs
    # --------------------------------------------------------

    print("\nSOURCE URL")
    print("-" * 80)
    print(car.get("url", ""))
    print(car.get("source_url", ""))

    # --------------------------------------------------------
    # H1/H2/H3
    # --------------------------------------------------------

    print("\nHEADINGS")
    print("-" * 80)

    for tag in soup.find_all(
        ["h1", "h2", "h3", "h4", "h5"]
    ):

        text = clean(
            tag.get_text(
                " ",
                strip=True
            )
        )

        if text:
            print(
                f"{tag.name.upper():4} | {text}"
            )

    # --------------------------------------------------------
    # Strong / bold text
    # --------------------------------------------------------

    print("\nSTRONG / BOLD TEXT")
    print("-" * 80)

    count = 0

    for tag in soup.find_all(
        ["strong", "b"]
    ):

        text = clean(
            tag.get_text(
                " ",
                strip=True
            )
        )

        if text:

            print(text)

            count += 1

            if count >= 100:
                break

    # --------------------------------------------------------
    # Links containing vehicle information
    # --------------------------------------------------------

    print("\nVEHICLE-RELATED LINKS")
    print("-" * 80)

    count = 0

    for link in soup.find_all("a"):

        text = clean(
            link.get_text(
                " ",
                strip=True
            )
        )

        href = link.get(
            "href",
            ""
        )

        combined = f"{text} {href}"

        if re.search(
            r"\b(19|20)\d{2}\b",
            combined
        ):

            print(
                f"TEXT: {text}"
            )

            print(
                f"HREF: {href}"
            )

            print()

            count += 1

            if count >= 30:
                break

    # --------------------------------------------------------
    # Text around important words
    # --------------------------------------------------------

    page_text = clean(
        soup.get_text(
            " ",
            strip=True
        )
    )

    keywords = [
        "Mileage",
        "Automatic",
        "Manual",
        "Diesel",
        "Petrol",
        "4x2",
        "4x4",
        "Vehicle Highlights",
        "Pricing Summary",
        "Description",
    ]

    print("\nIMPORTANT TEXT OCCURRENCES")
    print("-" * 80)

    for keyword in keywords:

        position = page_text.lower().find(
            keyword.lower()
        )

        if position == -1:
            continue

        start = max(
            0,
            position - 150
        )

        end = min(
            len(page_text),
            position + 400
        )

        print(
            f"\n[{keyword}]"
        )

        print(
            page_text[start:end]
        )

    print()
    print("=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()