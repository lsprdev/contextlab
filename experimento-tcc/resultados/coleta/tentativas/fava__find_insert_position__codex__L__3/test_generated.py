import re
from dataclasses import dataclass
from datetime import date

import pytest

from fava.beans.abc import Open, Posting, Transaction
from fava.core.file import find_insert_position


ENTRY_DATE = date(2025, 4, 15)
DEFAULT_FILE = "main.beancount"


@dataclass(frozen=True)
class InsertOption:
    date: date
    re: re.Pattern[str]
    filename: str
    lineno: int


def option(day, pattern, filename, lineno, *, flags=0):
    return InsertOption(day, re.compile(pattern, flags), filename, lineno)


def opening(account="Assets:Cash"):
    return Open({}, ENTRY_DATE, account, None, None)


def transaction(*accounts):
    postings = [Posting(account, None, None, None, None, None) for account in accounts]
    return Transaction({}, ENTRY_DATE, "*", None, "Transfer", frozenset(), frozenset(), postings)


def test_chooses_latest_eligible_matching_option_from_unsorted_input():
    options = [
        option(date(2024, 12, 31), r"Assets:Cash", "old.beancount", 90),
        option(date(2025, 4, 15), r"Assets:Cash", "same-day.beancount", 30),
        option(date(2025, 4, 12), r"Assets:Cash", "cash.beancount", 17),
        option(date(2025, 4, 14), r"Assets:Bank", "bank.beancount", 50),
        option(date(2025, 4, 16), r"Assets:Cash", "future.beancount", 2),
        option(date(2025, 4, 1), r"Assets:Cash", "earlier.beancount", 60),
    ]
    original_order = options[:]

    assert find_insert_position(opening(), options, DEFAULT_FILE) == ("cash.beancount", 16)
    assert options == original_order


def test_keeps_input_order_for_matching_options_on_the_same_date():
    day = date(2025, 4, 14)
    first = option(day, r"Assets", "z-first.beancount", 1)
    second = option(day, r"Assets:Cash", "a-second.beancount", 9)

    assert find_insert_position(opening(), (first, second), DEFAULT_FILE) == ("z-first.beancount", 0)
    assert find_insert_position(opening(), (second, first), DEFAULT_FILE) == ("a-second.beancount", 8)


def test_matches_regex_at_start_without_requiring_the_whole_account():
    options = (
        option(date(2025, 4, 14), r"Checking$", "substring.beancount", 4),
        option(date(2025, 4, 13), r"assets:(checking|savings)", "bank.beancount", 12, flags=re.IGNORECASE),
    )

    assert find_insert_position(opening("Assets:Bank:Checking"), options, DEFAULT_FILE) == (DEFAULT_FILE, None)
    assert find_insert_position(opening("Assets:Checking:Household"), options, DEFAULT_FILE) == ("bank.beancount", 11)


def test_last_posting_takes_priority_over_a_newer_option_for_an_earlier_posting():
    entry = transaction("Assets:Cash", "Expenses:Food")
    options = (
        option(date(2025, 4, 14), r"Assets:Cash$", "cash.beancount", 8),
        option(date(2025, 3, 31), r"Expenses:Food$", "food.beancount", 42),
    )

    assert find_insert_position(entry, options, DEFAULT_FILE) == ("food.beancount", 41)


def test_checks_earlier_postings_in_reverse_order_when_last_has_no_eligible_match():
    entry = transaction("Assets:Cash", "Expenses:Food", "Liabilities:Card")
    options = (
        option(ENTRY_DATE, r"Liabilities:Card$", "card.beancount", 5),
        option(date(2025, 4, 14), r"Assets:Cash$", "cash.beancount", 8),
        option(date(2025, 4, 10), r"Expenses:Food$", "food.beancount", 42),
    )

    assert find_insert_position(entry, options, DEFAULT_FILE) == ("food.beancount", 41)


@pytest.mark.parametrize(
    "options",
    [
        (),
        (option(date(2025, 4, 14), r"Expenses", "expenses.beancount", 5),),
        (option(ENTRY_DATE, r"Assets", "same-day.beancount", 5),),
        (option(date(2025, 4, 16), r"Assets", "future.beancount", 5),),
    ],
    ids=["no-options", "no-regex-match", "same-day-only", "future-only"],
)
def test_returns_default_file_with_no_line_when_no_option_qualifies(options):
    assert find_insert_position(opening(), options, DEFAULT_FILE) == (DEFAULT_FILE, None)


def test_transaction_without_postings_uses_default_even_with_a_catch_all_option():
    options = (option(date(2025, 4, 14), r".*", "catch-all.beancount", 7),)

    assert find_insert_position(transaction(), options, DEFAULT_FILE) == (DEFAULT_FILE, None)
