"""Tests for the Flask endpoints. OpenFoodFacts calls are mocked."""
from unittest.mock import patch

from app import openfoodfacts as off

FAKE_PRODUCT = {
    "barcode": "1234567890123", "product_name": "Test Cereal", "brands": "Acme",
    "ingredients_text": "Oats, honey", "categories": "Cereals",
}


# ----- GET -----
def test_get_all(client):
    resp = client.get("/inventory")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 5


def test_get_search_and_limit(client):
    assert len(client.get("/inventory?search=nutella").get_json()) == 1
    assert len(client.get("/inventory?limit=2").get_json()) == 2
    assert client.get("/inventory?limit=abc").status_code == 400


def test_get_one(client):
    resp = client.get("/inventory/1")
    assert resp.status_code == 200
    assert resp.get_json()["product"]["product_name"] == "Organic Almond Milk"


def test_get_one_not_found(client):
    resp = client.get("/inventory/999")
    assert resp.status_code == 404
    assert "not found" in resp.get_json()["error"]


# ----- POST -----
def test_post_creates_item(client):
    body = {"product_name": "Oat Milk", "brands": "Oatly", "price": 3.5, "quantity": 12}
    resp = client.post("/inventory", json=body)
    assert resp.status_code == 201
    assert resp.get_json()["id"] == 6
    assert len(client.get("/inventory").get_json()) == 6


def test_post_missing_name(client):
    assert client.post("/inventory", json={"price": 2}).status_code == 400


def test_post_invalid_price_and_quantity(client):
    assert client.post("/inventory", json={"product_name": "X", "price": -1}).status_code == 400
    assert client.post("/inventory", json={"product_name": "X", "quantity": 1.5}).status_code == 400


def test_post_non_json(client):
    resp = client.post("/inventory", data="nope", content_type="text/plain")
    assert resp.status_code == 400


def test_post_barcode_only_autofills(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=FAKE_PRODUCT):
        resp = client.post("/inventory", json={"barcode": "1234567890123", "quantity": 5})
    assert resp.status_code == 201
    assert resp.get_json()["product"]["product_name"] == "Test Cereal"


def test_post_unknown_barcode(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=None):
        resp = client.post("/inventory", json={"barcode": "999"})
    assert resp.status_code == 404


# ----- PATCH -----
def test_patch_updates_only_given_fields(client):
    resp = client.patch("/inventory/1", json={"price": 9.99, "brands": "NewBrand"})
    item = resp.get_json()
    assert resp.status_code == 200
    assert item["price"] == 9.99
    assert item["product"]["brands"] == "NewBrand"
    assert item["product"]["product_name"] == "Organic Almond Milk"  # unchanged


def test_patch_errors(client):
    assert client.patch("/inventory/1", json={}).status_code == 400
    assert client.patch("/inventory/1", json={"price": "free"}).status_code == 400
    assert client.patch("/inventory/999", json={"price": 1}).status_code == 404


# ----- DELETE -----
def test_delete(client):
    resp = client.delete("/inventory/2")
    assert resp.status_code == 204
    assert client.get("/inventory/2").status_code == 404
    assert len(client.get("/inventory").get_json()) == 4


def test_delete_not_found(client):
    assert client.delete("/inventory/999").status_code == 404


# ----- helper routes (OpenFoodFacts) -----
def test_lookup_by_barcode(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=FAKE_PRODUCT):
        resp = client.get("/lookup?barcode=1234567890123")
    assert resp.status_code == 200
    assert resp.get_json()["product"]["brands"] == "Acme"


def test_lookup_by_name_falls_back_to_search(client):
    with patch("app.openfoodfacts.search_by_name", return_value=FAKE_PRODUCT):
        resp = client.get("/lookup?name=cereal")
    assert resp.status_code == 200


def test_lookup_requires_param_and_handles_miss(client):
    assert client.get("/lookup").status_code == 400
    with patch("app.openfoodfacts.search_by_name", return_value=None):
        assert client.get("/lookup?name=zzz").status_code == 404


def test_from_api_adds_item(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=FAKE_PRODUCT):
        resp = client.post("/inventory/from-api",
                           json={"barcode": "1234567890123", "quantity": 7, "price": 4.2})
    item = resp.get_json()
    assert resp.status_code == 201
    assert item["quantity"] == 7 and item["product"]["product_name"] == "Test Cereal"


def test_from_api_requires_barcode_or_name(client):
    assert client.post("/inventory/from-api", json={"quantity": 1}).status_code == 400


def test_enrich_fills_blanks_without_overwriting(client):
    created = client.post("/inventory", json={"product_name": "Cereal"}).get_json()
    with patch("app.openfoodfacts.search_by_name", return_value=FAKE_PRODUCT):
        resp = client.post(f"/inventory/{created['id']}/enrich")
    body = resp.get_json()
    assert resp.status_code == 200
    assert body["item"]["product"]["product_name"] == "Cereal"  # kept
    assert body["item"]["product"]["brands"] == "Acme"          # filled
    assert "brands" in body["enriched_fields"]


def test_enrich_not_found(client):
    assert client.post("/inventory/999/enrich").status_code == 404


def test_external_failure_returns_502(client):
    with patch("app.openfoodfacts.fetch_by_barcode", side_effect=off.ExternalAPIError("down")):
        resp = client.get("/lookup?barcode=123")
    assert resp.status_code == 502
