import re
from datetime import date
from textwrap import dedent
from types import SimpleNamespace

import pytest
from beancount.parser import parser

from fava.core.file import find_insert_position


ENTRY_DATE = date(2024, 5, 15)
DEFAULT_FILE = "main.beancount"


def _parse_entry(source):
    entries, errors, _ = parser.parse_string(dedent(source).strip("\n") + "\n")
    assert not errors
    entry, = entries
    return entry


def _option(day, pattern, filename, lineno):
    return SimpleNamespace(
        date=date(2024, 5, day),
        re=re.compile(pattern),
        filename=filename,
        lineno=lineno,
    )


@pytest.fixture
def open_entry():
    return _parse_entry("2024-05-15 open Assets:Cash USD")


@pytest.fixture
def transaction():
    return _parse_entry(
        '''
        2024-05-15 * "Lunch"
          Expenses:Food  12 USD
          Liabilities:Card  -2 USD
          Assets:Cash  -10 USD
        '''
    )


@pytest.mark.parametrize("order", [(0, 1, 2), (2, 0, 1), (1, 2, 0)])
def test_selects_latest_matching_option_regardless_of_input_order(open_entry, order):
    candidates = (
        _option(3, r"Assets:Cash$", "old.beancount", 80),
        _option(12, r"Assets:Cash$", "chosen.beancount", 17),
        _option(8, r"Assets:Cash$", "middle.beancount", 4),
    )
    options = [candidates[index] for index in order]
    original_order = options.copy()

    assert find_insert_position(open_entry, options, DEFAULT_FILE) == (
        "chosen.beancount",
        16,
    )
    assert options == original_order


def test_uses_a_strictly_earlier_option(open_entry):
    options = (
        _option(15, r"Assets:Cash$", "same-day.beancount", 45),
        _option(16, r"Assets:Cash$", "future.beancount", 37),
        _option(14, r"Assets:Cash$", "previous-day.beancount", 1),
    )

    assert find_insert_position(open_entry, options, DEFAULT_FILE) == (
        "previous-day.beancount",
        0,
    )


def test_preserves_input_priority_for_options_on_the_same_date(open_entry):
    first = _option(10, r"Assets:", "z-first.beancount", 23)
    second = _option(10, r"Assets:Cash$", "a-second.beancount", 5)

    assert find_insert_position(open_entry, (first, second), DEFAULT_FILE) == (
        "z-first.beancount",
        22,
    )
    assert find_insert_position(open_entry, (second, first), DEFAULT_FILE) == (
        "a-second.beancount",
        4,
    )


def test_regex_matches_at_the_start_and_accepts_a_prefix(open_entry):
    options = (
        _option(14, r"Cash$", "substring.beancount", 40),
        _option(13, r"assets:", "lowercase.beancount", 30),
        _option(12, r"Assets:", "prefix.beancount", 7),
    )

    assert find_insert_position(open_entry, options, DEFAULT_FILE) == (
        "prefix.beancount",
        6,
    )


def test_last_transaction_posting_has_priority_over_newer_options(transaction):
    options = (
        _option(14, r"Expenses:Food$", "food.beancount", 21),
        _option(13, r"Liabilities:Card$", "card.beancount", 8),
        _option(4, r"Assets:Cash$", "cash.beancount", 36),
        _option(9, r"Assets:Cash$", "recent-cash.beancount", 13),
    )

    assert find_insert_position(transaction, options, DEFAULT_FILE) == (
        "recent-cash.beancount",
        12,
    )


def test_transaction_continues_to_earlier_postings(transaction):
    options = (
        _option(15, r"Assets:Cash$", "same-day-cash.beancount", 19),
        _option(14, r"Expenses:Food$", "food.beancount", 10),
    )

    assert find_insert_position(transaction, options, DEFAULT_FILE) == (
        "food.beancount",
        9,
    )


def test_pad_prefers_its_account_and_can_fall_back_to_its_source():
    entry = _parse_entry("2024-05-15 pad Assets:Cash Equity:Opening-Balances")
    account = _option(2, r"Assets:Cash$", "cash.beancount", 11)
    source = _option(14, r"Equity:Opening-Balances$", "equity.beancount", 24)

    assert find_insert_position(entry, (source, account), DEFAULT_FILE) == (
        "cash.beancount",
        10,
    )
    assert find_insert_position(entry, (source,), DEFAULT_FILE) == (
        "equity.beancount",
        23,
    )


def test_custom_uses_account_values_in_directive_order():
    entry = _parse_entry(
        '2024-05-15 custom "routing" "Assets:Ignored" Assets:Cash Expenses:Food'
    )
    options = (
        _option(14, r"Assets:Ignored$", "string.beancount", 4),
        _option(13, r"Expenses:Food$", "food.beancount", 16),
        _option(8, r"Assets:Cash$", "cash.beancount", 9),
    )

    assert find_insert_position(entry, options, DEFAULT_FILE) == (
        "cash.beancount",
        8,
    )


@pytest.mark.parametrize(
    "options",
    [
        (),
        (_option(14, r"Liabilities:", "unrelated.beancount", 7),),
        (_option(ENTRY_DATE.day, r"Assets:", "same-day.beancount", 7),),
        (_option(16, r"Assets:", "future.beancount", 7),),
    ],
    ids=["no-options", "no-account-match", "same-day-only", "future-only"],
)
def test_defaults_to_appending_when_no_option_qualifies(open_entry, options):
    assert find_insert_position(open_entry, options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )


def test_directive_without_accounts_uses_default_even_for_catch_all():
    entry = _parse_entry('2024-05-15 event "location" "Home"')
    options = (_option(14, r".*", "catch-all.beancount", 8),)

    assert find_insert_position(entry, options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )
