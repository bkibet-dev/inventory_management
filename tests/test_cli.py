"""Tests for CLI commands. The HTTP layer (requests.request) is mocked."""
from unittest.mock import MagicMock, patch

import requests

import cli

ITEM = {
    "id": 1, "barcode": "123", "price": 3.99, "quantity": 24, "status": 1,
    "product": {"product_name": "Organic Almond Milk", "brands": "Silk",
                "ingredients_text": "Water, almonds", "categories": "Beverages"},
}


def fake_response(status=200, payload=None):
    resp = MagicMock()
    resp.status_code = status
    resp.ok = status < 400
    resp.reason = "Reason"
    resp.json.return_value = payload if payload is not None else {}
    return resp


def run(argv, response):
    """Run the CLI with a mocked HTTP response; return (exit_code, mock)."""
    with patch("cli.requests.request", return_value=response) as mock:
        code = cli.main(argv)
    return code, mock


def test_list(capsys):
    code, mock = run(["list"], fake_response(200, [ITEM]))
    assert code == 0
    assert mock.call_args.args[:2] == ("GET", f"{cli.BASE_URL}/inventory")
    assert "Organic Almond Milk" in capsys.readouterr().out


def test_list_empty(capsys):
    code, _ = run(["list", "--search", "zzz"], fake_response(200, []))
    assert code == 0 and "No items found" in capsys.readouterr().out


def test_view_detailed(capsys):
    code, _ = run(["view", "1"], fake_response(200, ITEM))
    out = capsys.readouterr().out
    assert code == 0 and "ingredients" in out and "Water, almonds" in out


def test_view_not_found(capsys):
    code, _ = run(["view", "99"], fake_response(404, {"error": "Item 99 not found"}))
    assert code == 1 and "Item 99 not found" in capsys.readouterr().out


def test_add_sends_correct_payload():
    code, mock = run(["add", "--name", "Oat Milk", "--brand", "Oatly", "--price", "3.5", "--qty", "12"],
                     fake_response(201, ITEM))
    assert code == 0
    assert mock.call_args.args[0] == "POST"
    assert mock.call_args.kwargs["json"] == {
        "product_name": "Oat Milk", "brands": "Oatly", "price": 3.5, "quantity": 12}


def test_update_sends_only_given_fields():
    code, mock = run(["update", "1", "--price", "9.99"], fake_response(200, ITEM))
    assert code == 0
    assert mock.call_args.args[0] == "PATCH"
    assert mock.call_args.kwargs["json"] == {"price": 9.99}


def test_update_without_fields_makes_no_request(capsys):
    with patch("cli.requests.request") as mock:
        code = cli.main(["update", "1"])
    assert code == 1
    mock.assert_not_called()
    assert "at least one field" in capsys.readouterr().out


def test_delete_with_yes(capsys):
    code, mock = run(["delete", "1", "--yes"], fake_response(204))
    assert code == 0
    assert mock.call_args.args[0] == "DELETE"
    assert "deleted" in capsys.readouterr().out


def test_delete_cancelled_by_user(capsys):
    with patch("builtins.input", return_value="n"), patch("cli.requests.request") as mock:
        code = cli.main(["delete", "1"])
    assert code == 0
    mock.assert_not_called()
    assert "Cancelled" in capsys.readouterr().out


def test_lookup_by_barcode(capsys):
    payload = {"status": 1, "product": {"barcode": "123", "product_name": "Nutella", "brands": "Ferrero",
                                        "categories": "Spreads", "ingredients_text": "Sugar"}}
    code, mock = run(["lookup", "--barcode", "123"], fake_response(200, payload))
    assert code == 0
    assert mock.call_args.kwargs["params"] == {"barcode": "123"}
    assert "Nutella" in capsys.readouterr().out


def test_import_and_enrich(capsys):
    code, mock = run(["import", "--barcode", "123", "--qty", "5"], fake_response(201, ITEM))
    assert code == 0
    assert mock.call_args.args[1].endswith("/inventory/from-api")
    assert mock.call_args.kwargs["json"] == {"barcode": "123", "quantity": 5}

    code, _ = run(["enrich", "1"], fake_response(200, {"item": ITEM, "enriched_fields": ["brands"]}))
    assert code == 0 and "brands" in capsys.readouterr().out


def test_server_down_message(capsys):
    with patch("cli.requests.request", side_effect=requests.exceptions.ConnectionError()):
        code = cli.main(["list"])
    assert code == 1
    assert "Is the server running" in capsys.readouterr().out
