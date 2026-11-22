import re
from dataclasses import dataclass
from datetime import date

import pytest
from beancount.core.data import Posting

from fava.beans.abc import Open, Transaction
from fava.core.file import find_insert_position


ENTRY_DATE = date(2024, 5, 10)
DEFAULT_FILE = "default.beancount"


@dataclass(frozen=True)
class InsertOption:
    date: date
    re: re.Pattern[str]
    filename: str
    lineno: int


def option(day, pattern, filename="rules.beancount", lineno=12):
    return InsertOption(date(2024, 5, day), re.compile(pattern), filename, lineno)


def opening(account="Assets:Cash"):
    return Open({}, ENTRY_DATE, account, None, None)


def transaction(*accounts):
    return Transaction(
        {},
        ENTRY_DATE,
        "*",
        None,
        "Test transaction",
        frozenset(),
        frozenset(),
        [Posting(account, None, None, None, None, None) for account in accounts],
    )


@pytest.mark.parametrize(
    "options",
    [
        pytest.param((), id="no-options"),
        pytest.param((option(9, r"^Expenses:"),), id="different-account"),
        pytest.param((option(9, r"Cash"),), id="match-must-start-at-beginning"),
        pytest.param((option(10, r".*"),), id="same-day-excluded"),
        pytest.param((option(11, r".*"),), id="future-excluded"),
    ],
)
def test_defaults_when_no_option_qualifies(options):
    assert find_insert_position(opening(), options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )


def test_prefix_match_on_first_line_returns_zero():
    options = (option(9, r"Assets:", "first.beancount", 1),)

    assert find_insert_position(opening(), options, DEFAULT_FILE) == (
        "first.beancount",
        0,
    )


@pytest.mark.parametrize("order", [(0, 1, 2, 3, 4), (3, 4, 1, 0, 2), (4, 2, 3, 1, 0)])
def test_latest_eligible_matching_option_wins_in_any_input_order(order):
    rules = (
        option(2, r"Assets:", "old.beancount", 50),
        option(9, r"Expenses:", "unrelated.beancount", 40),
        option(10, r"Assets:", "same-day.beancount", 30),
        option(8, r"Assets:Cash$", "chosen.beancount", 20),
        option(11, r"Assets:", "future.beancount", 10),
    )
    options = [rules[index] for index in order]
    original_order = options.copy()

    assert find_insert_position(opening(), options, DEFAULT_FILE) == (
        "chosen.beancount",
        19,
    )
    assert options == original_order


@pytest.mark.parametrize(
    ("reverse_order", "expected"),
    [(False, ("first.beancount", 19)), (True, ("second.beancount", 3))],
)
def test_equal_date_matches_keep_input_order(reverse_order, expected):
    rules = (
        option(7, r"Expenses:", "unrelated.beancount", 14),
        option(7, r"Assets:", "first.beancount", 20),
        option(7, r"Assets:Cash$", "second.beancount", 4),
    )
    options = rules[::-1] if reverse_order else rules

    assert find_insert_position(opening(), options, DEFAULT_FILE) == expected


@pytest.mark.parametrize(
    ("last_posting_rule_day", "expected"),
    [
        (5, ("food.beancount", 24)),
        (10, ("bank.beancount", 39)),
        (11, ("bank.beancount", 39)),
    ],
)
def test_transaction_checks_postings_in_reverse_order(last_posting_rule_day, expected):
    entry = transaction("Assets:Cash", "Assets:Bank", "Expenses:Food")
    options = (
        option(9, r"Assets:Cash$", "cash.beancount", 30),
        option(last_posting_rule_day, r"Expenses:Food$", "food.beancount", 25),
        option(8, r"Assets:Bank$", "bank.beancount", 40),
        option(2, r"Expenses:Food$" if last_posting_rule_day == 5 else r"Expenses:Rent$", "old.beancount", 50),
    )

    assert find_insert_position(entry, options, DEFAULT_FILE) == expected


def test_transaction_can_match_first_posting_after_unmatched_last_posting():
    entry = transaction("Assets:Cash", "Expenses:Food")
    options = (option(9, r"Assets:Cash$", "cash.beancount", 6),)

    assert find_insert_position(entry, options, DEFAULT_FILE) == (
        "cash.beancount",
        5,
    )


def test_transaction_without_postings_defaults_even_with_catch_all_option():
    options = (option(9, r".*"),)

    assert find_insert_position(transaction(), options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )
