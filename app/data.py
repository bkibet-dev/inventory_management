"""Simulated data storage: a plain list of dicts held in memory.

Each item mirrors the shape of an OpenFoodFacts response
({"status": 1, "product": {...}}) plus our own inventory fields
(id, barcode, price, quantity).
"""
import copy

SEED_ITEMS = [
    {
        "id": 1, "barcode": "0000000000011", "price": 3.99, "quantity": 24, "status": 1,
        "product": {
            "product_name": "Organic Almond Milk", "brands": "Silk",
            "ingredients_text": "Filtered water, almonds, cane sugar, sea salt",
            "categories": "Beverages, Plant-based milks",
        },
    },
    {
        "id": 2, "barcode": "3017620422003", "price": 4.49, "quantity": 40, "status": 1,
        "product": {
            "product_name": "Nutella", "brands": "Ferrero",
            "ingredients_text": "Sugar, palm oil, hazelnuts, skimmed milk powder, cocoa",
            "categories": "Spreads, Sweet spreads",
        },
    },
    {
        "id": 3, "barcode": "5449000000996", "price": 1.79, "quantity": 120, "status": 1,
        "product": {
            "product_name": "Coca-Cola", "brands": "Coca-Cola",
            "ingredients_text": "Carbonated water, sugar, colour (caramel E150d), acid (phosphoric acid)",
            "categories": "Beverages, Carbonated drinks",
        },
    },
    {
        "id": 4, "barcode": "0000000000042", "price": 5.25, "quantity": 18, "status": 1,
        "product": {
            "product_name": "Whole Grain Oats", "brands": "Quaker",
            "ingredients_text": "Whole grain rolled oats",
            "categories": "Breakfast cereals, Oat flakes",
        },
    },
    {
        "id": 5, "barcode": "0000000000059", "price": 2.99, "quantity": 0, "status": 1,
        "product": {
            "product_name": "Dark Chocolate 70%", "brands": "Lindt",
            "ingredients_text": "Cocoa mass, sugar, cocoa butter, vanilla",
            "categories": "Snacks, Chocolates",
        },
    },
]

# The "database". Always mutate in place (append/remove/clear) so imports stay valid.
inventory = []


def reset_inventory():
    """Restore the seed data (used at startup and by tests)."""
    inventory.clear()
    inventory.extend(copy.deepcopy(SEED_ITEMS))


def next_id():
    return max((item["id"] for item in inventory), default=0) + 1


def find_item(item_id):
    return next((item for item in inventory if item["id"] == item_id), None)


reset_inventory()
