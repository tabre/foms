"""CSRF double-submit cookie: token exposure and validation."""
from flask import g

from src import csrf
from src.server import app

TOKEN = "a" * 32
COOKIE = f"{csrf.COOKIE}={csrf.signed(TOKEN)}"


def test_existing_cookie_is_reused_and_exposed():
    with app.test_request_context("/", headers={"Cookie": COOKIE}):
        assert csrf.get_or_new() == TOKEN
        assert g.csrf_token == TOKEN


def test_form_field_is_accepted():
    with app.test_request_context("/orders", method="POST", headers={"Cookie": COOKIE},
                                 data={"csrf_token": TOKEN}):
        assert csrf.valid()


def test_header_token_is_accepted():
    with app.test_request_context("/orders/1/complete", method="POST",
                                 headers={"Cookie": COOKIE, "X-CSRF-Token": TOKEN}):
        assert csrf.valid()


def test_missing_token_is_refused():
    with app.test_request_context("/orders/1/complete", method="POST", headers={"Cookie": COOKIE}):
        assert not csrf.valid()


def test_rendered_page_exposes_the_token_for_htmx():
    client = app.test_client()
    html = client.get("/login").get_data(as_text=True)
    token = html.split('name="csrf-token" content="')[1].split('"')[0]
    assert token
    cookie = client.get_cookie("foms_csrf")
    assert cookie and csrf._serializer.loads(cookie.value) == token
