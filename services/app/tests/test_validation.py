"""Validation rules."""
from datetime import date, timedelta

from src import errors as E
from src import validation as V


def test_required_field():
    _, errs = V.clean_text("", "Color", True, 40)
    assert errs[0]["message"] == E.field_required("Color")


def test_max_length():
    _, errs = V.clean_text("x" * 41, "Color", True, 40)
    assert errs[0]["message"] == "Color must be at most 40 characters."


def test_number_negative_rejected():
    _, errs = V.parse_number("-1", "Starting weight (g)", True)
    assert errs[0]["message"] == "Starting weight (g) cannot be negative."


def test_number_more_than_one_decimal_rejected():
    _, errs = V.parse_number("1.23", "Starting weight (g)", True)
    assert errs[0]["message"] == "Starting weight (g) must be a number of 0 or more."


def test_whole_number_required_for_units():
    _, errs = V.parse_number("1.5", "Starting stock (units)", True, whole=True)
    assert errs[0]["message"] == "Starting stock (units) must be a whole number of 0 or more."


def test_quantity_range():
    _, errs = V.parse_quantity("0", "Quantity")
    assert errs[0]["message"] == "Quantity must be a whole number from 1 to 9999."
    _, errs = V.parse_quantity("10000", "Quantity")
    assert errs[0]["message"] == "Quantity must be a whole number from 1 to 9999."
    value, errs = V.parse_quantity("5", "Quantity")
    assert value == 5 and not errs


def test_adjust_amount_must_be_positive():
    _, errs = V.parse_adjust_amount("0", "Amount", grams=True)
    assert errs[0]["message"] == "Amount must be greater than 0."
    _, errs = V.parse_adjust_amount("0", "Amount", grams=False)
    assert errs[0]["message"] == "Amount must be greater than 0."


def test_due_date_in_past_rejected():
    past = (date.today() - timedelta(days=1)).isoformat()
    _, errs = V.validate_due_date(past, "Due date")
    assert errs[0]["message"] == E.due_date_in_past()


def test_username_and_password_rules():
    assert V.validate_username("ab")
    assert not V.validate_username("good_user-1")
    assert V.validate_password("short") == [{"field": "Password", "message": E.password_length_invalid()}]
    assert not V.validate_password("a" * 12)
