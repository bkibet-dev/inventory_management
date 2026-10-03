"""Tests for the OpenFoodFacts client using mocked HTTP responses."""
from unittest.mock import MagicMock, patch

import pytest
import requests

from app import openfoodfacts as off


def fake_response(status=200, payload=None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    if status >= 400 and status != 404:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError("boom")
    return resp


BARCODE_PAYLOAD = {
    "status": 1,
    "product": {"code": "123", "product_name": "Organic Almond Milk", "brands": "Silk",
                "ingredients_text": "Filtered water, almonds", "categories": "Beverages"},
}


def test_fetch_by_barcode_success():
    with patch("app.openfoodfacts.requests.get", return_value=fake_response(200, BARCODE_PAYLOAD)) as get:
        result = off.fetch_by_barcode("123")
    assert result["product_name"] == "Organic Almond Milk"
    assert result["brands"] == "Silk"
    assert "/api/v2/product/123.json" in get.call_args.args[0]


def test_fetch_by_barcode_not_found():
    with patch("app.openfoodfacts.requests.get", return_value=fake_response(404, {"status": 0})):
        assert off.fetch_by_barcode("123") is None
    with patch("app.openfoodfacts.requests.get", return_value=fake_response(200, {"status": 0})):
        assert off.fetch_by_barcode("123") is None


def test_fetch_by_barcode_rejects_non_numeric_without_http_call():
    with patch("app.openfoodfacts.requests.get") as get:
        assert off.fetch_by_barcode("../etc") is None
    get.assert_not_called()


def test_missing_fields_default_to_empty_string():
    payload = {"status": 1, "product": {"code": "1", "product_name": "Plain"}}
    with patch("app.openfoodfacts.requests.get", return_value=fake_response(200, payload)):
        result = off.fetch_by_barcode("1")
    assert result["brands"] == "" and result["ingredients_text"] == ""


def test_search_by_name_returns_first_match():
    payload = {"products": [{"code": "9", "product_name": "Soy Milk", "brands": "Alpro"}]}
    with patch("app.openfoodfacts.requests.get", return_value=fake_response(200, payload)) as get:
        result = off.search_by_name("soy milk")
    assert result["product_name"] == "Soy Milk"
    assert get.call_args.kwargs["params"]["search_terms"] == "soy milk"


def test_search_by_name_no_results_or_blank():
    with patch("app.openfoodfacts.requests.get", return_value=fake_response(200, {"products": []})):
        assert off.search_by_name("zzzz") is None
    assert off.search_by_name("   ") is None


@pytest.mark.parametrize("failure", [
    {"side_effect": requests.exceptions.Timeout()},
    {"side_effect": requests.exceptions.ConnectionError()},
    {"return_value": fake_response(500, None)},
])
def test_network_problems_raise_external_error(failure):
    with patch("app.openfoodfacts.requests.get", **failure):
        with pytest.raises(off.ExternalAPIError):
            off.fetch_by_barcode("123")


def test_invalid_json_raises_external_error():
    resp = fake_response(200)
    resp.json.side_effect = ValueError("bad json")
    with patch("app.openfoodfacts.requests.get", return_value=resp):
        with pytest.raises(off.ExternalAPIError):
            off.search_by_name("milk")
