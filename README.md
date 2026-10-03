# Inventory Management System

A small admin portal for a retail company: a **Flask REST API** for inventory CRUD, **OpenFoodFacts** integration to fill in product details, a **CLI** to drive the API, and a **pytest** suite.

Data is stored in an in-memory Python list (`app/data.py`), seeded with five products shaped like OpenFoodFacts responses. It resets whenever the server restarts.

## Project structure

```
app/
  __init__.py        # create_app() factory + JSON error handlers
  routes.py          # all Flask endpoints
  openfoodfacts.py   # OpenFoodFacts client (barcode + name search)
  data.py            # mock database array + helpers
cli.py               # command-line interface
run.py               # starts the dev server (debug mode)
tests/               # test_api.py, test_cli.py, test_external.py
```

## Installation

```bash
git clone https://github.com/bkibet-dev/inventory_management && cd inventory-management
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
python run.py                   # API at http://127.0.0.1:5000 (debug mode on)
python cli.py list              # in a second terminal
```

To point the CLI at another address: `export INVENTORY_API_URL=http://host:port`.

## Item shape

```json
{
  "id": 1,
  "barcode": "3017620422003",
  "price": 4.49,
  "quantity": 40,
  "status": 1,
  "product": {
    "product_name": "Nutella",
    "brands": "Ferrero",
    "ingredients_text": "Sugar, palm oil, hazelnuts, ...",
    "categories": "Spreads, Sweet spreads"
  }
}
```

Request bodies are **flat** JSON: `product_name`, `brands`, `ingredients_text`, `categories`, `barcode`, `price`, `quantity`.

## API endpoints

| Method | Route | Purpose | Success | Errors |
|---|---|---|---|---|
| GET | `/inventory` | List all items. Optional `?search=` (name/brand) and `?limit=` | 200 | 400 bad limit |
| GET | `/inventory/<id>` | Fetch one item | 200 | 404 |
| POST | `/inventory` | Add an item. `product_name` required, unless a `barcode` is given, in which case details are fetched from OpenFoodFacts | 201 | 400 invalid input, 404 unknown barcode, 502 API down |
| PATCH | `/inventory/<id>` | Partial update (omitted fields unchanged) | 200 | 400, 404 |
| DELETE | `/inventory/<id>` | Remove an item | 204 | 404 |
| GET | `/lookup?barcode=...` or `?name=...` | Preview OpenFoodFacts data (nothing saved) | 200 | 400, 404, 502 |
| POST | `/inventory/from-api` | Fetch by `barcode` or `name` and add to inventory (optional `price`, `quantity`) | 201 | 400, 404, 502 |
| POST | `/inventory/<id>/enrich` | Fill an item's *blank* fields from OpenFoodFacts (never overwrites) | 200 | 404, 502 |

All errors return JSON: `{"error": "message"}`.

### curl examples

```bash
curl http://127.0.0.1:5000/inventory
curl -X POST http://127.0.0.1:5000/inventory -H "Content-Type: application/json" \
     -d '{"product_name": "Oat Milk", "brands": "Oatly", "price": 3.5, "quantity": 12}'
curl -X PATCH http://127.0.0.1:5000/inventory/1 -H "Content-Type: application/json" -d '{"price": 4.25}'
curl -X DELETE http://127.0.0.1:5000/inventory/1
curl "http://127.0.0.1:5000/lookup?barcode=3017620422003"
```

## CLI usage

| Command | What it does |
|---|---|
| `python cli.py list [--search TEXT]` | Show all items |
| `python cli.py view 1` | Show one item with ingredients and categories |
| `python cli.py add --name "Oat Milk" --brand Oatly --price 3.5 --qty 12` | Add an item |
| `python cli.py add --barcode 3017620422003 --qty 10` | Add by barcode (details auto-filled) |
| `python cli.py update 1 --price 4.25 --qty 30` | Update fields |
| `python cli.py delete 1` (`-y` skips the prompt) | Delete an item |
| `python cli.py lookup --barcode 3017620422003` | Preview OpenFoodFacts data |
| `python cli.py lookup --name "almond milk"` | Preview by name |
| `python cli.py import --barcode 3017620422003 --qty 10 --price 4.49` | Fetch from OpenFoodFacts and add |
| `python cli.py enrich 1` | Fill blank details of item 1 |

`python cli.py --help` and `python cli.py <command> --help` list every flag.

## Testing

```bash
pytest -v
```

External API calls are mocked with `unittest.mock`, so tests run offline. The suite covers all CRUD endpoints, validation errors, the OpenFoodFacts client (success, not found, timeouts, bad JSON), and every CLI command.

For manual checks, run `python run.py` (Flask debug mode) and import the endpoints above into Postman.

## Notes

- OpenFoodFacts asks clients to send a `User-Agent`; this is set in `app/openfoodfacts.py`.
- On macOS, port 5000 can be taken by AirPlay Receiver. If so, change the port in `run.py` and set `INVENTORY_API_URL`.
