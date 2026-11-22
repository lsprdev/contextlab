import re
from dataclasses import dataclass
from datetime import date

import pytest
from beancount.core.data import Posting

from fava.beans.abc import Open, Transaction
from fava.core.file import find_insert_position


DEFAULT_FILE = "main.beancount"
ENTRY_DATE = date(2025, 3, 15)


@dataclass(frozen=True)
class InsertOption:
    date: date
    re: re.Pattern[str]
    filename: str
    lineno: int


def option(day, pattern, filename, lineno):
    return InsertOption(date(2025, 3, day), re.compile(pattern), filename, lineno)


def open_account(account):
    return Open(
        meta={}, date=ENTRY_DATE, account=account, currencies=None, booking=None
    )


def transaction(*accounts):
    return Transaction(
        meta={},
        date=ENTRY_DATE,
        flag="*",
        payee=None,
        narration="Transfer",
        tags=frozenset(),
        links=frozenset(),
        postings=[Posting(account, None, None, None, None, None) for account in accounts],
    )


def test_empty_options_use_default_file():
    assert find_insert_position(open_account("Assets:Cash"), (), DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )


def test_entry_without_accounts_uses_default_even_with_catch_all():
    options = (option(14, r".*", "catch-all.beancount", 5),)

    assert find_insert_position(transaction(), options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )


def test_uses_latest_matching_prior_option_without_reordering_input():
    oldest = option(2, r"Assets:Cash$", "oldest.beancount", 71)
    latest = option(12, r"Assets:Cash$", "cash.beancount", 19)
    newer_nonmatch = option(14, r"Expenses:Food$", "food.beancount", 33)
    middle = option(8, r"Assets:Cash$", "middle.beancount", 50)
    options = [oldest, latest, newer_nonmatch, middle]

    assert find_insert_position(open_account("Assets:Cash"), options, DEFAULT_FILE) == (
        "cash.beancount",
        18,
    )
    assert options == [oldest, latest, newer_nonmatch, middle]


def test_ignores_matching_options_on_and_after_entry_date():
    options = (
        option(15, r"Assets:Cash$", "same-day.beancount", 42),
        option(14, r"Assets:Cash$", "prior.beancount", 7),
        option(16, r"Assets:Cash$", "future.beancount", 29),
    )

    assert find_insert_position(open_account("Assets:Cash"), options, DEFAULT_FILE) == (
        "prior.beancount",
        6,
    )


@pytest.mark.parametrize("day", [15, 16], ids=["same-day", "future"])
def test_no_earlier_matching_option_uses_default(day):
    options = (
        option(14, r"Assets:Bank$", "bank.beancount", 3),
        option(day, r"Assets:Cash$", "ineligible.beancount", 8),
    )

    assert find_insert_position(open_account("Assets:Cash"), options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )


def test_regex_can_match_a_prefix_and_first_line_maps_to_zero():
    options = (option(14, r"Assets:(Cash|Bank)", "assets.beancount", 1),)

    assert find_insert_position(
        open_account("Assets:Bank:Savings"), options, DEFAULT_FILE
    ) == ("assets.beancount", 0)


def test_regex_does_not_search_inside_account_name():
    options = (option(14, r"Cash$", "cash.beancount", 6),)

    assert find_insert_position(open_account("Assets:Cash"), options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )


def test_same_date_matching_options_keep_input_order():
    first = option(10, r"Assets:", "z-first.beancount", 27)
    second = option(10, r"Assets:Cash$", "a-second.beancount", 4)
    entry = open_account("Assets:Cash")

    assert find_insert_position(entry, (first, second), DEFAULT_FILE) == (
        "z-first.beancount",
        26,
    )
    assert find_insert_position(entry, (second, first), DEFAULT_FILE) == (
        "a-second.beancount",
        3,
    )


def test_last_posting_account_takes_priority_over_more_recent_options():
    entry = transaction("Assets:Cash", "Expenses:Food", "Liabilities:Card")
    options = (
        option(3, r"Liabilities:Card$", "old-card.beancount", 22),
        option(14, r"Assets:Cash$", "cash.beancount", 10),
        option(8, r"Liabilities:Card$", "card.beancount", 31),
        option(12, r"Expenses:Food$", "food.beancount", 45),
    )

    assert find_insert_position(entry, options, DEFAULT_FILE) == ("card.beancount", 30)


def test_checks_earlier_postings_when_last_has_no_eligible_option():
    entry = transaction("Assets:Cash", "Expenses:Food", "Liabilities:Card")
    options = (
        option(15, r"Liabilities:Card$", "card.beancount", 13),
        option(14, r"Assets:Cash$", "cash.beancount", 20),
        option(9, r"Expenses:Food$", "food.beancount", 38),
    )

    assert find_insert_position(entry, options, DEFAULT_FILE) == ("food.beancount", 37)
