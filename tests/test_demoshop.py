"""Unit tests for demoshop/app.py in vulnerable and secure modes."""
import json
import pytest
from demoshop.app import Handler, ORDERS, TEST_USERS


class MockWFile:
    def __init__(self):
        self.data = bytearray()

    def write(self, b):
        self.data.extend(b)


class DummyHandler(Handler):
    """Subclass of Handler to test payload and route responses in memory."""
    def __init__(self):
        self.wfile = MockWFile()
        self.headers = {}
        self.response_status = None
        self.response_headers = {}

    def send_response(self, code, message=None):
        self.response_status = code

    def send_header(self, keyword, value):
        self.response_headers[keyword.lower()] = value

    def end_headers(self):
        pass


def test_demoshop_root_returns_html():
    handler = DummyHandler()
    handler.path = "/"
    handler.do_GET()
    assert handler.response_status == 200
    assert "text/html" in handler.response_headers.get("content-type", "")
    assert b"DemoShop" in handler.wfile.data


def test_demoshop_root_with_csp_enabled():
    DummyHandler.secure_mode = True
    handler = DummyHandler()
    handler.path = "/"
    handler.do_GET()
    assert handler.response_status == 200
    assert "content-security-policy" in handler.response_headers
    assert handler.response_headers["content-security-policy"] == "default-src 'self'"


def test_demoshop_orders_unauthorized():
    DummyHandler.secure_mode = False
    handler = DummyHandler()
    handler.path = "/api/orders/101"
    handler.headers = {}  # No authorization header
    handler.do_GET()
    assert handler.response_status == 401


def test_demoshop_orders_owner_access():
    DummyHandler.secure_mode = False
    handler = DummyHandler()
    handler.path = "/api/orders/101"
    handler.headers = {"Authorization": "Bearer demo-alice"}
    handler.do_GET()
    assert handler.response_status == 200
    payload = json.loads(handler.wfile.data.decode())
    assert payload["id"] == "101"
    assert payload["owner"] == "alice"


def test_demoshop_bola_vulnerable_mode():
    """In vulnerable mode, non-owner Bob can access Alice's order (BOLA vulnerability)."""
    DummyHandler.secure_mode = False
    handler = DummyHandler()
    handler.path = "/api/orders/101"
    handler.headers = {"Authorization": "Bearer demo-bob"}
    handler.do_GET()
    assert handler.response_status == 200
    payload = json.loads(handler.wfile.data.decode())
    assert payload["owner"] == "alice"  # Bob read Alice's order!


def test_demoshop_bola_secure_mode():
    """In secure mode, non-owner Bob is blocked with HTTP 403 Forbidden."""
    DummyHandler.secure_mode = True
    handler = DummyHandler()
    handler.path = "/api/orders/101"
    handler.headers = {"Authorization": "Bearer demo-bob"}
    handler.do_GET()
    assert handler.response_status == 403
    payload = json.loads(handler.wfile.data.decode())
    assert payload.get("error") == "forbidden"
