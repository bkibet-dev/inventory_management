"""Thin client for the OpenFoodFacts API."""
import requests

BASE_URL = "https://world.openfoodfacts.org"
# OpenFoodFacts asks API users to identify their app with a User-Agent.
HEADERS = {"User-Agent": "InventoryAdminPortal/1.0 (student project)"}
FIELDS = "code,product_name,brands,ingredients_text,categories"
TIMEOUT = 10


class ExternalAPIError(Exception):
    """Raised when OpenFoodFacts can't be reached or returns bad data."""


def _get(url, params=None):
    """GET a URL and return parsed JSON, or None for a 404."""
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as exc:
        raise ExternalAPIError(f"OpenFoodFacts request failed: {exc}") from exc
    except ValueError as exc:
        raise ExternalAPIError("OpenFoodFacts returned invalid JSON") from exc


def _normalize(product):
    """Keep only the fields we store, defaulting missing ones to ''."""
    return {
        "barcode": product.get("code") or "",
        "product_name": product.get("product_name") or "",
        "brands": product.get("brands") or "",
        "ingredients_text": product.get("ingredients_text") or "",
        "categories": product.get("categories") or "",
    }


def fetch_by_barcode(barcode):
    """Return normalized product info for a barcode, or None if not found."""
    barcode = (barcode or "").strip()
    if not barcode.isdigit():
        return None
    data = _get(f"{BASE_URL}/api/v2/product/{barcode}.json", {"fields": FIELDS})
    if not data or data.get("status") != 1 or not data.get("product"):
        return None
    return _normalize(data["product"])


def search_by_name(name):
    """Return the top search match for a product name, or None."""
    name = (name or "").strip()
    if not name:
        return None
    params = {
        "search_terms": name, "search_simple": 1, "action": "process",
        "json": 1, "page_size": 1, "fields": FIELDS,
    }
    data = _get(f"{BASE_URL}/cgi/search.pl", params)
    products = (data or {}).get("products") or []
    return _normalize(products[0]) if products else None
