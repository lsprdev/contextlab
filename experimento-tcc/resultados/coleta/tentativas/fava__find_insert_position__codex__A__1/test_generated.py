import re
from datetime import date, timedelta
from decimal import Decimal
from typing import NamedTuple

import pytest
from beancount.core import data
from beancount.core.account import TYPE as ACCOUNT_TYPE
from beancount.core.amount import Amount

from fava.core.fava_options import InsertEntryOption
from fava.core.file import find_insert_position


ENTRY_DATE = date(2025, 1, 15)
DEFAULT_FILE = "main.beancount"


def insert_option(days_from_entry, pattern, filename, lineno):
    return InsertEntryOption(
        date=ENTRY_DATE + timedelta(days=days_from_entry),
        re=re.compile(pattern),
        filename=filename,
        lineno=lineno,
    )


@pytest.fixture
def account_entry():
    return data.Open({}, ENTRY_DATE, "Assets:Bank:Checking", None, None)


@pytest.fixture
def transaction():
    postings = [
        data.Posting(account, Amount(Decimal(units), "USD"), None, None, None, None)
        for account, units in (
            ("Assets:Bank", "-30"),
            ("Expenses:Food", "20"),
            ("Expenses:Travel", "10"),
        )
    ]
    return data.Transaction(
        {}, ENTRY_DATE, "*", None, "Purchase", frozenset(), frozenset(), postings
    )


def test_selects_latest_eligible_matching_option_from_unsorted_list(account_entry):
    options = [
        insert_option(-20, r"Assets:", "december.beancount", 90),
        insert_option(2, r"Assets:", "future.beancount", 9),
        insert_option(-2, r"Assets:(Bank|Cash):", "january.beancount", 18),
        insert_option(-1, r"Liabilities:", "liabilities.beancount", 7),
        insert_option(0, r"Assets:", "same-day.beancount", 4),
        insert_option(-5, r"Assets:", "older-january.beancount", 100),
    ]
    original_order = options.copy()

    assert find_insert_position(account_entry, options, DEFAULT_FILE) == (
        "january.beancount",
        17,
    )
    assert options == original_order


@pytest.mark.parametrize("offset", [0, 1], ids=["same-day", "future"])
def test_ineligible_date_has_no_insert_position(account_entry, offset):
    options = (insert_option(offset, r"Assets:", "bank.beancount", 20),)

    assert find_insert_position(account_entry, options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )


@pytest.mark.parametrize(
    "pattern",
    [r"Bank:Checking", r"Assets:Bank$", r"assets:", r"Expenses:.*"],
    ids=["middle-of-account", "end-anchor", "wrong-case", "different-account"],
)
def test_regex_must_match_from_the_start_of_the_account(account_entry, pattern):
    options = (insert_option(-1, pattern, "other.beancount", 20),)

    assert find_insert_position(account_entry, options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )


def test_first_line_and_compiled_regex_flags(account_entry):
    options = (
        InsertEntryOption(
            date=ENTRY_DATE - timedelta(days=1),
            re=re.compile(r"assets:bank:", re.IGNORECASE),
            filename="bank.beancount",
            lineno=1,
        ),
    )

    assert find_insert_position(account_entry, options, DEFAULT_FILE) == (
        "bank.beancount",
        0,
    )


@pytest.mark.parametrize("reverse_order", [False, True])
def test_matching_options_with_equal_dates_follow_input_order(account_entry, reverse_order):
    broad = insert_option(-1, r"Assets:", "z-assets.beancount", 40)
    exact = insert_option(-1, r"Assets:Bank:Checking$", "a-checking.beancount", 10)
    if reverse_order:
        options = (exact, broad)
        expected = ("a-checking.beancount", 9)
    else:
        options = (broad, exact)
        expected = ("z-assets.beancount", 39)

    assert find_insert_position(account_entry, options, DEFAULT_FILE) == expected


def test_empty_options_fall_back_to_default_file(account_entry):
    assert find_insert_position(account_entry, (), DEFAULT_FILE) == (DEFAULT_FILE, None)


def test_directive_without_accounts_falls_back_even_with_a_wildcard():
    entry = data.Event({}, ENTRY_DATE, "location", "Home")
    options = (insert_option(-1, r".*", "catchall.beancount", 7),)

    assert find_insert_position(entry, options, DEFAULT_FILE) == (DEFAULT_FILE, None)


def test_transaction_prioritizes_last_posting_over_newer_rules(transaction):
    options = (
        insert_option(-1, r"Assets:Bank$", "bank.beancount", 6),
        insert_option(-12, r"Expenses:Travel$", "old-travel.beancount", 30),
        insert_option(-2, r"Expenses:Food$", "food.beancount", 15),
        insert_option(-8, r"Expenses:Travel$", "travel.beancount", 21),
    )

    assert find_insert_position(transaction, options, DEFAULT_FILE) == (
        "travel.beancount",
        20,
    )


def test_transaction_tries_earlier_postings_when_last_has_no_eligible_match(transaction):
    options = (
        insert_option(-1, r"Assets:Bank$", "bank.beancount", 6),
        insert_option(0, r"Expenses:Travel$", "same-day-travel.beancount", 21),
        insert_option(-3, r"Expenses:Food$", "food.beancount", 15),
    )

    assert find_insert_position(transaction, options, DEFAULT_FILE) == (
        "food.beancount",
        14,
    )


@pytest.mark.parametrize("include_target", [True, False], ids=["target", "source"])
def test_pad_tries_target_account_before_source(include_target):
    entry = data.Pad({}, ENTRY_DATE, "Assets:Bank", "Equity:Opening-Balances")
    source = insert_option(-1, r"Equity:", "equity.beancount", 13)
    target = insert_option(-4, r"Assets:", "assets.beancount", 24)
    options = (source, target) if include_target else (source,)
    expected = ("assets.beancount", 23) if include_target else ("equity.beancount", 12)

    assert find_insert_position(entry, options, DEFAULT_FILE) == expected


class CustomValue(NamedTuple):
    value: str
    dtype: object


def test_custom_uses_account_values_in_directive_order():
    entry = data.Custom(
        {},
        ENTRY_DATE,
        "example",
        [
            CustomValue("Assets:Text", str),
            CustomValue("Expenses:Food", ACCOUNT_TYPE),
            CustomValue("Assets:Bank", ACCOUNT_TYPE),
        ],
    )
    options = (
        insert_option(-1, r"Assets:Text$", "text.beancount", 5),
        insert_option(-2, r"Assets:Bank$", "bank.beancount", 14),
        insert_option(-3, r"Expenses:Food$", "food.beancount", 23),
    )

    assert find_insert_position(entry, options, DEFAULT_FILE) == ("food.beancount", 22)
