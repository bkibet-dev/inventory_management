"""REST routes for the inventory API (CRUD + OpenFoodFacts helper routes)."""
from flask import Blueprint, jsonify, request

from . import data
from . import openfoodfacts as off

bp = Blueprint("inventory", __name__)

PRODUCT_FIELDS = ("product_name", "brands", "ingredients_text", "categories")


# ---------- helpers ----------

def error(message, status):
    return jsonify({"error": message}), status


@bp.errorhandler(off.ExternalAPIError)
def handle_external_error(exc):
    """Any OpenFoodFacts failure becomes a 502 Bad Gateway."""
    return error(str(exc), 502)


def validate(body):
    """Validate a flat JSON body. Returns (clean_dict, error_message)."""
    clean = {}
    for field in PRODUCT_FIELDS + ("barcode",):
        if field in body:
            if not isinstance(body[field], str):
                return None, f"'{field}' must be a string"
            clean[field] = body[field].strip()
    if "product_name" in clean and not clean["product_name"]:
        return None, "'product_name' cannot be empty"

    if "price" in body:
        price = body["price"]
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0:
            return None, "'price' must be a non-negative number"
        clean["price"] = round(float(price), 2)

    if "quantity" in body:
        qty = body["quantity"]
        if isinstance(qty, bool) or not isinstance(qty, int) or qty < 0:
            return None, "'quantity' must be a non-negative integer"
        clean["quantity"] = qty
    return clean, None


def build_item(clean):
    """Turn validated fields into a full inventory item with a new ID."""
    return {
        "id": data.next_id(),
        "barcode": clean.get("barcode", ""),
        "price": clean.get("price", 0.0),
        "quantity": clean.get("quantity", 0),
        "status": 1,
        "product": {f: clean.get(f, "") for f in PRODUCT_FIELDS},
    }


def fill_from_external(clean, external):
    """Fill any blank product fields in `clean` using OpenFoodFacts data."""
    for field in PRODUCT_FIELDS + ("barcode",):
        if not clean.get(field) and external.get(field):
            clean[field] = external[field]


def lookup_product(barcode, name):
    """Try barcode first, then fall back to a name search."""
    if barcode:
        found = off.fetch_by_barcode(barcode)
        if found:
            return found
    if name:
        return off.search_by_name(name)
    return None


def json_body():
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else None


# ---------- CRUD routes ----------

@bp.route("/inventory", methods=["GET"])
def list_items():
    """Fetch all items. Optional ?search=<text> and ?limit=<n>."""
    items = data.inventory
    search = request.args.get("search")
    if search:
        term = search.lower()
        items = [i for i in items if term in i["product"]["product_name"].lower()
                 or term in i["product"]["brands"].lower()]
    limit = request.args.get("limit")
    if limit is not None:
        if not limit.isdigit():
            return error("'limit' must be a non-negative integer", 400)
        items = items[: int(limit)]
    return jsonify(items), 200


@bp.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = data.find_item(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    return jsonify(item), 200


@bp.route("/inventory", methods=["POST"])
def create_item():
    """Add an item. If only a barcode is given, details come from OpenFoodFacts."""
    body = json_body()
    if body is None:
        return error("Request body must be a JSON object", 400)
    clean, problem = validate(body)
    if problem:
        return error(problem, 400)

    if clean.get("barcode") and not clean.get("product_name"):
        external = off.fetch_by_barcode(clean["barcode"])
        if external is None:
            return error("Barcode not found on OpenFoodFacts; provide product_name", 404)
        fill_from_external(clean, external)

    if not clean.get("product_name"):
        return error("'product_name' (or a valid barcode) is required", 400)

    item = build_item(clean)
    data.inventory.append(item)
    return jsonify(item), 201


@bp.route("/inventory/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    """Partially update an item; omitted fields stay unchanged."""
    item = data.find_item(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    body = json_body()
    if body is None:
        return error("Request body must be a JSON object", 400)
    clean, problem = validate(body)
    if problem:
        return error(problem, 400)
    if not clean:
        return error("No valid fields to update", 400)

    for key, value in clean.items():
        if key in PRODUCT_FIELDS:
            item["product"][key] = value
        else:
            item[key] = value
    return jsonify(item), 200


@bp.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = data.find_item(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    data.inventory.remove(item)
    return "", 204


# ---------- OpenFoodFacts helper routes ----------

@bp.route("/lookup", methods=["GET"])
def lookup():
    """Preview OpenFoodFacts data without saving: /lookup?barcode=... or ?name=..."""
    barcode = request.args.get("barcode")
    name = request.args.get("name")
    if not barcode and not name:
        return error("Provide a 'barcode' or 'name' query parameter", 400)
    product = lookup_product(barcode, name)
    if product is None:
        return jsonify({"status": 0, "error": "Product not found"}), 404
    return jsonify({"status": 1, "product": product}), 200


@bp.route("/inventory/from-api", methods=["POST"])
def create_from_api():
    """Fetch a product by barcode/name and add it to inventory in one step."""
    body = json_body()
    if body is None:
        return error("Request body must be a JSON object", 400)
    clean, problem = validate(body)
    if problem:
        return error(problem, 400)
    name = body.get("name") if isinstance(body.get("name"), str) else None
    if not clean.get("barcode") and not name:
        return error("Provide a 'barcode' or 'name' to look up", 400)

    external = lookup_product(clean.get("barcode"), name)
    if external is None:
        return error("Product not found on OpenFoodFacts", 404)
    fill_from_external(clean, external)
    if not clean.get("product_name"):
        return error("OpenFoodFacts returned no product name for this item", 404)

    item = build_item(clean)
    data.inventory.append(item)
    return jsonify(item), 201


@bp.route("/inventory/<int:item_id>/enrich", methods=["POST"])
def enrich_item(item_id):
    """Fill this item's blank details using OpenFoodFacts (never overwrites)."""
    item = data.find_item(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)

    external = lookup_product(item["barcode"], item["product"]["product_name"])
    if external is None:
        return error("No matching product found on OpenFoodFacts", 404)

    enriched = []
    for field in PRODUCT_FIELDS:
        if not item["product"][field] and external.get(field):
            item["product"][field] = external[field]
            enriched.append(field)
    if not item["barcode"] and external.get("barcode"):
        item["barcode"] = external["barcode"]
        enriched.append("barcode")
    return jsonify({"item": item, "enriched_fields": enriched}), 200
