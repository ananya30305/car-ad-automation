"""Extract listing-owned vehicle data from a Cars.co.za detail page."""

import json
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup


FIELDS = (
    "source_url", "title", "title_description", "condition", "year",
    "mileage", "transmission", "fuel", "drive_type", "colour", "seats",
    "pricing_summary", "dealer_name", "dealer_address", "dealer_rating",
    "features", "contact_number", "images", "highlights", "description",
    "price", "currency", "address", "location", "listing_id",
)
BAD_VALUES = {".", "n/a", "na", "unknown", "null", "test"}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        value = " ".join(str(item) for item in value)
    value = re.sub(r"\s+", " ", unescape(str(value))).strip()
    return None if not value or value.lower() in BAD_VALUES else value


def unique_values(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean_text(value)
        if text and text.casefold() not in seen:
            seen.add(text.casefold())
            result.append(text)
    return result


def json_ld_objects(soup: BeautifulSoup) -> list[dict[str, Any]]:
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


def vehicle_object(objects: list[dict[str, Any]]) -> dict[str, Any]:
    wanted = {"vehicle", "car", "product"}
    for root in objects:
        for item in _walk(root):
            types = item.get("@type", [])
            types = types if isinstance(types, list) else [types]
            if wanted.intersection(str(kind).casefold() for kind in types):
                return item
    return {}


def labeled_value(soup: BeautifulSoup, labels: list[str]) -> str | None:
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


def nested(value: Any, *keys: str) -> Any:
    for key in keys:
        if isinstance(value, dict) and value.get(key) not in (None, ""):
            return value[key]
    return None


def image_urls(soup: BeautifulSoup, source_url: str) -> list[str]:
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
    result = []
    for value in urls:
        url = urljoin(source_url, value).split("?")[0]
        lower = url.casefold()
        if (url.startswith("http") and (not listing_id or f"/{listing_id}/" in url or f"/{listing_id}." in url) and not any(word in lower for word in ("logo", "placeholder", "sprite", "icon", "avatar"))):
            if url not in result:
                result.append(url)
    return result


def _title_parts(title: str | None) -> tuple[str | None, str | None]:
    if not title:
        return None, None
    match = re.match(r"^((?:19|20)\d{2}\s+\S+\s+\S+)(?:\s+(.+))?$", title)
    return (match.group(1), match.group(2)) if match else (title, None)


def parse_listing(html: str, source_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    vehicle = vehicle_object(json_ld_objects(soup))
    offers = vehicle.get("offers") if isinstance(vehicle.get("offers"), dict) else {}
    seller = vehicle.get("seller") if isinstance(vehicle.get("seller"), dict) else {}
    address = nested(seller, "address") or vehicle.get("address")
    address_text = ", ".join(str(address[key]) for key in ("streetAddress", "addressLocality", "addressRegion", "postalCode") if isinstance(address, dict) and address.get(key)) if isinstance(address, dict) else clean_text(address)
    title = clean_text(vehicle.get("name")) or clean_text(soup.find("meta", property="og:title").get("content") if soup.find("meta", property="og:title") else None)
    title, title_description = _title_parts(title)
    mileage = nested(vehicle.get("mileageFromOdometer"), "value") or vehicle.get("mileageFromOdometer") or vehicle.get("mileage")
    price_value = offers.get("price") or vehicle.get("price") or labeled_value(soup, ["Price", "Selling Price"])
    price_digits = re.sub(r"[^0-9]", "", str(price_value)) if price_value is not None else ""
    year = nested(vehicle, "productionDate", "modelDate") or labeled_value(soup, ["Year", "Model Year"])
    year_match = re.search(r"(?:19|20)\d{2}", str(year)) if year else None
    meta_description = soup.find("meta", attrs={"name": "description"})
    description = clean_text(vehicle.get("description")) or clean_text(meta_description.get("content") if meta_description else None)
    description_text = description or ""
    condition = clean_text(vehicle.get("itemCondition")) or labeled_value(soup, ["Condition"])
    if condition and condition.startswith("https://schema.org/"):
        condition = condition.rsplit("/", 1)[-1].replace("Condition", "")
    mileage_value = clean_text(mileage)
    if not mileage_value:
        match = re.search(r"\b([\d, ]{3,})\s*km\b", description_text, re.I)
        mileage_value = f"{match.group(1).replace(',', '').strip()} km" if match else None
    transmission = clean_text(vehicle.get("vehicleTransmission")) or labeled_value(soup, ["Transmission", "Gearbox"])
    if not transmission:
        transmission = next((word.title() for word in ("automatic", "manual") if re.search(rf"\b{word}\b", description_text, re.I)), None)
    fuel = clean_text(vehicle.get("fuelType")) or labeled_value(soup, ["Fuel", "Fuel Type"])
    if not fuel:
        fuel = next((word.title() for word in ("diesel", "petrol", "hybrid", "electric") if re.search(rf"\b{word}\b", description_text, re.I)), None)
    colour = clean_text(vehicle.get("color")) or labeled_value(soup, ["Colour", "Color"])
    if not colour:
        colour = next((word.title() for word in ("white", "silver", "black", "blue", "red", "grey", "gray") if re.search(rf"\b{word}\b", description_text, re.I)), None)
    dealer_name = clean_text(seller.get("name")) or labeled_value(soup, ["Dealer", "Dealer Name"])
    if not dealer_name:
        match = re.search(r"(?:Contact|Visit)\s+([A-Z][\w& -]+?)(?:,|\s+to\s+|\s+in\s+the\s+|\.|$)", description_text)
        dealer_name = clean_text(match.group(1)) if match else None
    result: dict[str, Any] = {field: None for field in FIELDS}
    result.update({
        "source_url": source_url, "title": title, "title_description": title_description,
        "condition": condition,
        "year": int(year_match.group()) if year_match else None,
        "mileage": f"{mileage} km" if mileage and str(mileage).replace(" ", "").isdigit() else mileage_value,
        "transmission": transmission,
        "fuel": fuel,
        "drive_type": clean_text(vehicle.get("driveWheelConfiguration")) or labeled_value(soup, ["Drive Type", "Drivetrain"]),
        "colour": colour,
        "seats": clean_text(vehicle.get("seatingCapacity")) or labeled_value(soup, ["Seats"]),
        "pricing_summary": clean_text(price_value), "dealer_name": dealer_name,
        "dealer_address": address_text or labeled_value(soup, ["Dealer Address", "Address"]),
        "dealer_rating": clean_text((seller.get("aggregateRating") or {}).get("ratingValue")) if isinstance(seller.get("aggregateRating"), dict) else labeled_value(soup, ["Dealer Rating"]),
        "features": unique_values([item.get_text(" ", strip=True) for item in soup.select('[class*=feature] li, [class*=specification] li')]),
        "contact_number": clean_text(next((a.get("href", "")[4:] for a in soup.select('a[href^="tel:"]')), None)),
        "images": image_urls(soup, source_url), "highlights": [], "description": description,
        "price": int(price_digits) if price_digits else None, "currency": "R (Rand)", "address": address_text,
        "location": "South Africa", "listing_id": (re.search(r"/(\d+)/?$", source_url) or [None, None])[1],
    })
    return result
