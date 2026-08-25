"""Extract and enrich vehicle fields from HTML / free text. Never invent values."""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.canonical.models import CanonicalVehicle

BAD_VALUES = {".", "n/a", "na", "unknown", "null", "none", "test"}

KNOWN_MAKES = [
    "Mercedes-Benz",
    "Mercedes",
    "Volkswagen",
    "Land Rover",
    "Range Rover",
    "Alfa Romeo",
    "Aston Martin",
    "BMW",
    "Audi",
    "Toyota",
    "Ford",
    "Nissan",
    "Honda",
    "Hyundai",
    "Kia",
    "Mazda",
    "Suzuki",
    "Isuzu",
    "Haval",
    "GWM",
    "Volvo",
    "Porsche",
    "Jaguar",
    "Mini",
    "Jeep",
    "Lexus",
    "Renault",
    "Peugeot",
    "Chevrolet",
    "Opel",
    "Fiat",
    "Subaru",
    "Mitsubishi",
    "Mahindra",
    "Datsun",
    "Chery",
]


def clean_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = " ".join(str(item) for item in value)
    text = re.sub(r"\s+", " ", unescape(str(value))).strip()
    if not text or text.casefold() in BAD_VALUES:
        return None
    return text


def unique_values(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            result.append(text)
    return result


def parse_title_parts(title: Optional[str]) -> dict[str, Any]:
    """Decompose titles like '2020 Toyota Corolla 1.8 XS' when possible."""
    result: dict[str, Any] = {"year": None, "make": None, "model": None, "variant": None}
    text = clean_text(title)
    if not text:
        return result
    year_match = re.match(r"^((?:19|20)\d{2})\s+(.+)$", text)
    remainder = text
    if year_match:
        result["year"] = int(year_match.group(1))
        remainder = year_match.group(2).strip()
    make = None
    for candidate in sorted(KNOWN_MAKES, key=len, reverse=True):
        if remainder.casefold().startswith(candidate.casefold() + " ") or remainder.casefold() == candidate.casefold():
            make = candidate if candidate != "Mercedes" else "Mercedes-Benz"
            remainder = remainder[len(candidate) :].strip()
            break
    result["make"] = make
    if not remainder:
        return result
    parts = remainder.split()
    if not parts:
        return result
    result["model"] = parts[0]
    if len(parts) > 1:
        result["variant"] = " ".join(parts[1:])
    return result


def _json_ld_objects(soup: BeautifulSoup) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            value = json.loads(script.get_text(strip=True))
        except (TypeError, json.JSONDecodeError):
            continue
        values = value if isinstance(value, list) else [value]
        objects.extend(item for item in values if isinstance(item, dict))
    return objects


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _vehicle_object(objects: list[dict[str, Any]]) -> dict[str, Any]:
    wanted = {"vehicle", "car", "product"}
    for root in objects:
        for item in _walk(root):
            types = item.get("@type", [])
            types = types if isinstance(types, list) else [types]
            if wanted.intersection(str(kind).casefold() for kind in types):
                return item
    return {}


def _labeled_value(soup: BeautifulSoup, labels: list[str]) -> Optional[str]:
    pattern = re.compile(r"^(?:" + "|".join(map(re.escape, labels)) + r")\s*:?$", re.I)
    for node in soup.find_all(string=pattern):
        parent = node.parent
        if not parent:
            continue
        sibling = parent.find_next_sibling()
        value = clean_text(sibling.get_text(" ", strip=True)) if sibling else None
        if value and value.casefold() not in {label.casefold() for label in labels}:
            return value
    return None


def _nested(value: Any, *keys: str) -> Any:
    for key in keys:
        if isinstance(value, dict) and value.get(key) not in (None, ""):
            return value[key]
    return None


def image_urls_from_html(html: str, source_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    listing_match = re.search(r"/(\d+)/?$", source_url)
    listing_id = listing_match.group(1) if listing_match else None
    for node in soup.select("main img, [class*=gallery] img, [class*=Gallery] img"):
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            if node.get(attr):
                urls.append(node[attr])
        if node.get("srcset"):
            urls.append(node["srcset"].split(",")[-1].strip().split(" ")[0])
    for node in soup.select('meta[property="og:image"], meta[name="twitter:image"]'):
        if node.get("content"):
            urls.append(node["content"])
    result: list[str] = []
    for value in urls:
        url = urljoin(source_url, value).split("?")[0]
        lower = url.casefold()
        if not url.startswith("http"):
            continue
        if listing_id and f"/{listing_id}/" not in url and f"/{listing_id}." not in url:
            continue
        if any(word in lower for word in ("logo", "placeholder", "sprite", "icon", "avatar")):
            continue
        if url not in result:
            result.append(url)
    return result


def parse_listing_html(html: str, source_url: str) -> dict[str, Any]:
    """Priority: JSON-LD → labeled specs → metadata → empty (caller may use description)."""
    soup = BeautifulSoup(html, "html.parser")
    vehicle = _vehicle_object(_json_ld_objects(soup))
    offers = vehicle.get("offers") if isinstance(vehicle.get("offers"), dict) else {}
    seller = vehicle.get("seller") if isinstance(vehicle.get("seller"), dict) else {}
    address = _nested(seller, "address") or vehicle.get("address")
    address_text = None
    if isinstance(address, dict):
        address_text = ", ".join(
            str(address[key])
            for key in ("streetAddress", "addressLocality", "addressRegion", "postalCode")
            if address.get(key)
        )
    else:
        address_text = clean_text(address)

    title = clean_text(vehicle.get("name")) or clean_text(
        soup.find("meta", property="og:title")["content"]
        if soup.find("meta", property="og:title")
        else None
    )
    parts = parse_title_parts(title)
    mileage = (
        _nested(vehicle.get("mileageFromOdometer"), "value")
        or vehicle.get("mileageFromOdometer")
        or vehicle.get("mileage")
    )
    price_value = offers.get("price") or vehicle.get("price") or _labeled_value(soup, ["Price", "Selling Price"])
    year = _nested(vehicle, "productionDate", "modelDate") or _labeled_value(soup, ["Year", "Model Year"])
    meta_description = soup.find("meta", attrs={"name": "description"})
    description = clean_text(vehicle.get("description")) or clean_text(
        meta_description.get("content") if meta_description else None
    )
    condition = clean_text(vehicle.get("itemCondition")) or _labeled_value(soup, ["Condition"])
    transmission = clean_text(vehicle.get("vehicleTransmission")) or _labeled_value(
        soup, ["Transmission", "Gearbox"]
    )
    fuel = clean_text(vehicle.get("fuelType")) or _labeled_value(soup, ["Fuel", "Fuel Type"])
    colour = clean_text(vehicle.get("color")) or _labeled_value(soup, ["Colour", "Color"])
    drive = clean_text(vehicle.get("driveWheelConfiguration")) or _labeled_value(
        soup, ["Drive Type", "Drivetrain", "4x2 / 4x4"]
    )
    seats = clean_text(vehicle.get("seatingCapacity")) or _labeled_value(soup, ["Seats"])
    features = unique_values(
        [item.get_text(" ", strip=True) for item in soup.select("[class*=feature] li, [class*=specification] li")]
    )
    contact = clean_text(next((a.get("href", "")[4:] for a in soup.select('a[href^="tel:"]')), None))
    brand = clean_text(_nested(vehicle, "brand", "name") if isinstance(vehicle.get("brand"), dict) else vehicle.get("brand"))
    model = clean_text(vehicle.get("model"))
    country = None
    if isinstance(address, dict):
        country = clean_text(address.get("addressCountry"))
    location = None
    if isinstance(address, dict):
        location = clean_text(address.get("addressLocality") or address.get("addressRegion"))

    listing_id = (re.search(r"/(\d+)/?$", source_url) or [None, None])[1]
    price_digits = re.sub(r"[^\d]", "", str(price_value)) if price_value is not None else ""

    return {
        "listing_id": listing_id,
        "source_url": source_url,
        "title": title,
        "title_description": parts.get("variant"),
        "year": year or parts.get("year"),
        "make": brand or parts.get("make"),
        "model": model or parts.get("model"),
        "variant": parts.get("variant"),
        "condition": condition,
        "mileage": mileage,
        "transmission": transmission,
        "fuel": fuel,
        "drive_type": drive,
        "colour": colour,
        "seats": seats,
        "price": int(price_digits) if price_digits else None,
        "pricing_summary": clean_text(price_value),
        "dealer_name": clean_text(seller.get("name")),
        "dealer_address": address_text,
        "contact_number": contact,
        "features": features,
        "highlights": [],
        "description": description,
        "images": image_urls_from_html(html, source_url),
        "location": location,
        "country": country,
    }


def _extract_bullet_features(description: str) -> list[str]:
    features: list[str] = []
    # Prefer explicit "Key Features: • a • b" blocks only — avoid narrative fragments
    key_match = re.search(r"Key Features:\s*(.+)$", description, re.I | re.S)
    if key_match:
        chunk = key_match.group(1)
        for part in re.split(r"[•●▪]|\n+", chunk):
            text = clean_text(part)
            if not text:
                continue
            if len(text) > 100:
                continue
            if text.casefold().startswith("key features"):
                continue
            # Drop sentence fragments that are not feature labels
            if text.casefold().startswith(("that ", "which ", "with ", "and ")):
                continue
            features.append(text)
        return unique_values(features)

    # Controlled fallback: "features such as a, b and c"
    std = re.search(
        r"(?:standard features such as|features such as)\s+([^.]+)",
        description,
        re.I,
    )
    if std:
        blob = std.group(1)
        for part in re.split(r",| and ", blob):
            text = clean_text(part)
            if text and 2 < len(text) < 60:
                features.append(text)
    return unique_values(features)


def enrich_from_text(vehicle: CanonicalVehicle) -> None:
    """Fill missing structured fields from title/description. Never overwrite existing values."""
    text = " ".join(filter(None, [vehicle.title, vehicle.title_description, vehicle.description]))
    if not text:
        return

    if vehicle.year is None:
        match = re.search(r"\b((?:19|20)\d{2})\b", text)
        if match:
            vehicle.year = int(match.group(1))

    if vehicle.mileage is None:
        match = re.search(r"\b([\d][\d\s,]{2,})\s*km\b", text, re.I)
        if match:
            digits = re.sub(r"[^\d]", "", match.group(1))
            if digits:
                vehicle.mileage = int(digits)

    if vehicle.transmission is None:
        if re.search(r"\b(automatic|steptronic|s tronic|dct)\b", text, re.I):
            vehicle.transmission = "Automatic"
        elif re.search(r"\bmanual\b", text, re.I):
            vehicle.transmission = "Manual"
        elif re.search(r"\bcvt\b", text, re.I):
            vehicle.transmission = "CVT"

    if vehicle.fuel is None:
        for token, mapped in (
            ("diesel", "Diesel"),
            ("petrol", "Petrol"),
            ("hybrid", "Hybrid"),
            ("electric", "Electric"),
        ):
            if re.search(rf"\b{token}\b", text, re.I):
                vehicle.fuel = mapped
                break

    if vehicle.drive_type is None:
        for pattern, mapped in (
            (r"\brear[-\s]?wheel\b|\bRWD\b", "RWD"),
            (r"\bfront[-\s]?wheel\b|\bfront wheels\b|\bFWD\b", "FWD"),
            (r"\b4x4\b|\bfour[-\s]?wheel\b", "4x4"),
            (r"\b4x2\b", "4x2"),
            (r"\bAWD\b|\ball[-\s]?wheel\b", "AWD"),
        ):
            if re.search(pattern, text, re.I):
                vehicle.drive_type = mapped
                break

    if vehicle.colour is None:
        # Prefer explicit colour phrases
        colour_match = re.search(
            r"\bin\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3})\b",
            text,
        )
        basic = re.search(
            r"\b(White|Black|Silver|Blue|Red|Grey|Gray|Green|Orange|Brown|Beige|Gold)\b",
            text,
            re.I,
        )
        if colour_match and any(
            c in colour_match.group(1).casefold()
            for c in ("white", "black", "silver", "blue", "red", "grey", "gray", "green", "metal", "pearl", "sapphire", "daytona")
        ):
            vehicle.colour = colour_match.group(1)
        elif basic:
            vehicle.colour = basic.group(1).title()

    if vehicle.seats is None:
        match = re.search(
            r"\b(?:seating for|seats(?:\s+for)?|cabin for|seats)\s+(\d+|five|four|two|seven|eight)\b",
            text,
            re.I,
        )
        if not match:
            match = re.search(r"\b(?:for)\s+(five|four|two|seven|eight)\b", text, re.I)
        if match:
            word = match.group(1).casefold()
            words = {"five": 5, "four": 4, "two": 2, "seven": 7, "eight": 8}
            vehicle.seats = words.get(word, int(word) if word.isdigit() else None)

    if vehicle.make is None or vehicle.model is None:
        parts = parse_title_parts(vehicle.title)
        vehicle.make = vehicle.make or parts.get("make")
        vehicle.model = vehicle.model or parts.get("model")
        vehicle.variant = vehicle.variant or parts.get("variant")
        vehicle.year = vehicle.year or parts.get("year")

    if not vehicle.features and vehicle.description:
        vehicle.features = _extract_bullet_features(vehicle.description)[:20]

    if not vehicle.highlights:
        # Controlled highlight selection from features / key phrases — not invented marketing
        candidates = list(vehicle.features)
        if vehicle.transmission:
            candidates.append(f"{vehicle.transmission} transmission")
        if vehicle.fuel:
            candidates.append(f"{vehicle.fuel} engine")
        if vehicle.mileage is not None and vehicle.mileage < 30000:
            candidates.append(f"Low mileage ({vehicle.mileage} km)")
        vehicle.highlights = unique_values(candidates)[:5]

    if vehicle.dealer_name is None and vehicle.description:
        match = re.search(
            r"(?:Brought to you by|Contact|Visit)\s+([A-Z][\w&'. -]{2,40}?)(?:,|\s+to\s+|\s+in\s+|\.|$)",
            vehicle.description,
        )
        if match:
            vehicle.dealer_name = clean_text(match.group(1))
