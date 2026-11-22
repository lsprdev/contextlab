import re
from dataclasses import dataclass
from datetime import date
from datetime import timedelta

import pytest
from beancount.core.data import Pad
from beancount.core.data import Posting
from fava.beans.abc import Open
from fava.beans.abc import Transaction
from fava.core.file import find_insert_position


ENTRY_DATE = date(2025, 3, 10)
DEFAULT_FILE = "main.beancount"


@dataclass(frozen=True)
class InsertOption:
    date: date
    re: re.Pattern[str]
    filename: str
    lineno: int


def option(pattern, filename, lineno, *, days_before=1):
    return InsertOption(
        ENTRY_DATE - timedelta(days=days_before),
        re.compile(pattern),
        filename,
        lineno,
    )


@pytest.fixture
def cash_entry():
    return Open({}, ENTRY_DATE, "Assets:Cash", None, None)


def transaction(*accounts):
    return Transaction(
        {}, ENTRY_DATE, "*", None, "Transfer", frozenset(), frozenset(),
        [Posting(account, None, None, None, None, None) for account in accounts],
    )


def test_chooses_latest_matching_option_strictly_before_entry(cash_entry):
    older = option(r"Assets:Cash$", "older.beancount", 9, days_before=8)
    latest_match = option(r"Assets:Cash$", "cash.beancount", 17, days_before=3)
    unrelated = option(r"Assets:Bank$", "bank.beancount", 5)
    same_day = option(r"Assets:Cash$", "today.beancount", 11, days_before=0)
    future = option(r"Assets:Cash$", "future.beancount", 21, days_before=-1)
    original_order = (older, same_day, latest_match, future, unrelated)
    options = list(original_order)

    assert find_insert_position(cash_entry, options, DEFAULT_FILE) == (
        "cash.beancount", 16,
    )
    assert tuple(options) == original_order


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        pytest.param(r"Assets:[A-Z]", ("assets.beancount", 0), id="prefix"),
        pytest.param(r"Cash$", (DEFAULT_FILE, None), id="interior-only"),
    ],
)
def test_regex_matches_from_account_start(cash_entry, pattern, expected):
    options = (option(pattern, "assets.beancount", 1),)

    assert find_insert_position(cash_entry, options, DEFAULT_FILE) == expected


@pytest.mark.parametrize("days_before", [0, -1], ids=["same-day", "future"])
def test_defaults_when_only_matching_option_is_too_recent(cash_entry, days_before):
    options = (option(r"Assets:Cash$", "cash.beancount", 4, days_before=days_before),)

    assert find_insert_position(cash_entry, options, DEFAULT_FILE) == (DEFAULT_FILE, None)


def test_defaults_with_no_options(cash_entry):
    assert find_insert_position(cash_entry, (), DEFAULT_FILE) == (DEFAULT_FILE, None)


def test_defaults_for_entry_without_accounts():
    options = [option(r".*", "any-account.beancount", 2)]

    assert find_insert_position(transaction(), options, DEFAULT_FILE) == (DEFAULT_FILE, None)


def test_equal_option_dates_preserve_input_order(cash_entry):
    first = option(r"Assets:Cash$", "z-first.beancount", 14)
    second = option(r"Assets:Cash$", "a-second.beancount", 3)

    assert find_insert_position(cash_entry, [first, second], DEFAULT_FILE) == (
        "z-first.beancount", 13,
    )
    assert find_insert_position(cash_entry, [second, first], DEFAULT_FILE) == (
        "a-second.beancount", 2,
    )


def test_last_posting_has_priority_over_newer_option_for_first_posting():
    entry = transaction("Assets:Cash", "Expenses:Food")
    options = [
        option(r"Assets:Cash$", "cash.beancount", 9),
        option(r"Expenses:Food$", "food.beancount", 20, days_before=5),
    ]

    assert find_insert_position(entry, options, DEFAULT_FILE) == ("food.beancount", 19)


def test_transaction_tries_earlier_postings_in_reverse_order():
    entry = transaction("Assets:Cash", "Expenses:Food", "Liabilities:Card")
    options = [
        option(r"Assets:Cash$", "cash.beancount", 12),
        option(r"Expenses:Food$", "food.beancount", 8, days_before=4),
        option(r"Liabilities:Card$", "card.beancount", 5, days_before=0),
    ]

    assert find_insert_position(entry, options, DEFAULT_FILE) == ("food.beancount", 7)
    assert find_insert_position(entry, options[:1], DEFAULT_FILE) == ("cash.beancount", 11)


def test_pad_prefers_target_account_and_can_fall_back_to_source():
    entry = Pad({}, ENTRY_DATE, "Assets:Cash", "Equity:Opening-Balances")
    source = option(r"Equity:Opening-Balances$", "equity.beancount", 7)
    target = option(r"Assets:Cash$", "cash.beancount", 4, days_before=3)

    assert find_insert_position(entry, [source, target], DEFAULT_FILE) == (
        "cash.beancount", 3,
    )
    assert find_insert_position(entry, [source], DEFAULT_FILE) == (
        "equity.beancount", 6,
    )
