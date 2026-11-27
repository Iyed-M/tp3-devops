"""Unit tests for the FastAPI application in main.py."""

import socket

import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def reset_items():
    """Restore the in-memory items after each test so tests stay independent."""
    saved = dict(main.items)
    yield
    main.items.clear()
    main.items.update(saved)


def test_root():
    """GET / confirms the app is running."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "it works !"}


def test_soustraction():
    """GET /soustraction returns a - b."""
    response = client.get("/soustraction", params={"a": 10, "b": 4})
    assert response.status_code == 200
    assert response.json() == {"result a-b=": 6, "developer": "Dev1"}


def test_soustraction_negative_result():
    """The difference can be negative."""
    response = client.get("/soustraction", params={"a": 3, "b": 8})
    assert response.status_code == 200
    assert response.json()["result a-b="] == -5


def test_soustraction_invalid_input():
    """Non-integer operands are rejected with 422."""
    response = client.get("/soustraction", params={"a": "x", "b": 1})
    assert response.status_code == 422


def test_addition():
    """GET /addition returns a + b."""
    response = client.get("/addition", params={"a": 1, "b": 2})
    assert response.status_code == 200
    assert response.json() == {"result a+b=": 3, "developer": "Dev1"}


def test_greeting():
    """GET /greeting greets by name and reports host information."""
    response = client.get("/greeting", params={"name": "Iyed"})
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Hello, Iyed"
    assert body["developer"] == "Dev2"
    assert body["hostname"] == socket.gethostname()
    assert isinstance(body["IP"], str)


def test_current_ip_without_network(monkeypatch):
    """current_ip falls back to localhost when no network is reachable."""

    class OfflineSocket:  # pylint: disable=too-few-public-methods
        """Socket stub whose connect always fails."""

        def __init__(self, *_args):
            self.closed = False

        def connect(self, _address):
            """Simulate an unreachable network."""
            raise OSError("network unreachable")

        def close(self):
            """Record that the socket was closed."""
            self.closed = True

    monkeypatch.setattr(main.socket, "socket", OfflineSocket)
    assert main.current_ip() == "127.0.0.1"


def test_multiply():
    """POST /multiply returns a * b."""
    response = client.post("/multiply", json={"a": 3, "b": 4})
    assert response.status_code == 200
    assert response.json() == {"result a*b=": 12.0, "developer": "Dev1"}


def test_divide():
    """POST /divide returns a / b."""
    response = client.post("/divide", json={"a": 10, "b": 4})
    assert response.status_code == 200
    assert response.json() == {"result a/b=": 2.5, "developer": "Dev2"}


def test_divide_by_zero():
    """POST /divide with b = 0 returns 400."""
    response = client.post("/divide", json={"a": 1, "b": 0})
    assert response.status_code == 400
    assert response.json() == {"detail": "Division by zero"}


def test_list_items():
    """GET /items lists the three default items."""
    response = client.get("/items")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "item1", "description": "first item"},
        {"id": 2, "name": "item2", "description": "second item"},
        {"id": 3, "name": "item3", "description": "third item"},
    ]


def test_remove_item():
    """DELETE /remove/{id} deletes an existing item."""
    response = client.delete("/remove/2")
    assert response.status_code == 200
    assert response.json() == {"deleted": 2, "developer": "Dev1"}
    assert [item["id"] for item in client.get("/items").json()] == [1, 3]


def test_remove_missing_item():
    """DELETE /remove/{id} on an unknown id returns 404."""
    response = client.delete("/remove/99")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}
