"""Command-line interface for the inventory API.

The Flask server must be running (python run.py). Examples:
    python cli.py list
    python cli.py add --name "Oat Milk" --brand Oatly --price 3.5 --qty 12
    python cli.py import --barcode 3017620422003 --qty 10 --price 4.49
"""
import argparse
import os
import sys

import requests

BASE_URL = os.environ.get("INVENTORY_API_URL", "http://127.0.0.1:5000")


def call_api(method, path, **kwargs):
    """Send a request to the API. Returns parsed JSON ({} for 204) or None on error."""
    try:
        resp = requests.request(method, BASE_URL + path, timeout=15, **kwargs)
    except requests.exceptions.RequestException:
        print(f"Error: could not reach the API at {BASE_URL}. Is the server running?")
        return None
    if resp.status_code == 204:
        return {}
    try:
        payload = resp.json()
    except ValueError:
        payload = {}
    if not resp.ok:
        print(f"Error {resp.status_code}: {payload.get('error', resp.reason)}")
        return None
    return payload


def print_item(item, detailed=False):
    product = item["product"]
    print(f"[{item['id']}] {product['product_name']} ({product['brands'] or 'no brand'})")
    print(f"     barcode: {item['barcode'] or '-'} | "
          f"price: ${float(item['price']):.2f} | qty: {item['quantity']}")
    if detailed:
        print(f"     categories: {product['categories'] or '-'}")
        print(f"     ingredients: {product['ingredients_text'] or '-'}")


# ---------- commands ----------

def cmd_list(args):
    params = {"search": args.search} if args.search else None
    items = call_api("GET", "/inventory", params=params)
    if items is None:
        return 1
    if not items:
        print("No items found.")
    for item in items:
        print_item(item)
    return 0


def cmd_view(args):
    item = call_api("GET", f"/inventory/{args.id}")
    if item is None:
        return 1
    print_item(item, detailed=True)
    return 0


def _payload(args):
    """Map CLI flags to API field names, skipping unset ones."""
    mapping = {
        "product_name": args.name, "brands": args.brand, "barcode": args.barcode,
        "ingredients_text": getattr(args, "ingredients", None),
        "categories": getattr(args, "categories", None),
        "price": args.price, "quantity": args.qty,
    }
    return {k: v for k, v in mapping.items() if v is not None}


def cmd_add(args):
    item = call_api("POST", "/inventory", json=_payload(args))
    if item is None:
        return 1
    print("Item added:")
    print_item(item, detailed=True)
    return 0


def cmd_update(args):
    payload = _payload(args)
    if not payload:
        print("Error: provide at least one field to update.")
        return 1
    item = call_api("PATCH", f"/inventory/{args.id}", json=payload)
    if item is None:
        return 1
    print("Item updated:")
    print_item(item, detailed=True)
    return 0


def cmd_delete(args):
    if not args.yes and input(f"Delete item {args.id}? [y/N] ").strip().lower() != "y":
        print("Cancelled.")
        return 0
    if call_api("DELETE", f"/inventory/{args.id}") is None:
        return 1
    print(f"Item {args.id} deleted.")
    return 0


def cmd_lookup(args):
    params = {"barcode": args.barcode} if args.barcode else {"name": args.name}
    result = call_api("GET", "/lookup", params=params)
    if result is None:
        return 1
    product = result["product"]
    print(f"{product['product_name']} ({product['brands'] or 'no brand'})")
    print(f"  barcode: {product['barcode'] or '-'}")
    print(f"  categories: {product['categories'] or '-'}")
    print(f"  ingredients: {product['ingredients_text'] or '-'}")
    return 0


def cmd_import(args):
    payload = {}
    if args.barcode:
        payload["barcode"] = args.barcode
    if args.name:
        payload["name"] = args.name
    if args.price is not None:
        payload["price"] = args.price
    if args.qty is not None:
        payload["quantity"] = args.qty
    item = call_api("POST", "/inventory/from-api", json=payload)
    if item is None:
        return 1
    print("Imported from OpenFoodFacts:")
    print_item(item, detailed=True)
    return 0


def cmd_enrich(args):
    result = call_api("POST", f"/inventory/{args.id}/enrich")
    if result is None:
        return 1
    fields = result["enriched_fields"]
    print(f"Enriched fields: {', '.join(fields) if fields else 'none (already complete)'}")
    print_item(result["item"], detailed=True)
    return 0


# ---------- parser ----------

def build_parser():
    parser = argparse.ArgumentParser(description="Inventory management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="List all items")
    p.add_argument("--search", help="Filter by name or brand")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("view", help="View one item")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_view)

    def item_flags(p):
        p.add_argument("--name")
        p.add_argument("--brand")
        p.add_argument("--barcode")
        p.add_argument("--ingredients")
        p.add_argument("--categories")
        p.add_argument("--price", type=float)
        p.add_argument("--qty", type=int)

    p = sub.add_parser("add", help="Add a new item (barcode alone auto-fills details)")
    item_flags(p)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("update", help="Update fields of an item")
    p.add_argument("id", type=int)
    item_flags(p)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete an item")
    p.add_argument("id", type=int)
    p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("lookup", help="Preview OpenFoodFacts data (not saved)")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--barcode")
    group.add_argument("--name")
    p.set_defaults(func=cmd_lookup)

    p = sub.add_parser("import", help="Fetch from OpenFoodFacts and add to inventory")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--barcode")
    group.add_argument("--name")
    p.add_argument("--price", type=float)
    p.add_argument("--qty", type=int)
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("enrich", help="Fill an item's blank details from OpenFoodFacts")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_enrich)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
