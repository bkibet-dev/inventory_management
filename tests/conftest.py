import pytest

from app import create_app, data


@pytest.fixture
def client():
    """Flask test client with a fresh copy of the seed data for every test."""
    data.reset_inventory()
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client
