import re
from datetime import date
from decimal import Decimal
from itertools import permutations
from types import SimpleNamespace

import pytest
from beancount.core import data
from beancount.core.account import TYPE as ACCOUNT_TYPE
from beancount.core.amount import Amount

from fava.core.fava_options import InsertEntryOption
from fava.core.file import find_insert_position


ENTRY_DATE = date(2024, 1, 10)
DEFAULT_FILENAME = "default.bean"
META = {"filename": "original.bean", "lineno": 80}


def option(when, pattern, filename, lineno):
    return InsertEntryOption(when, re.compile(pattern), filename, lineno)


@pytest.fixture
def entry():
    return data.Close(META, ENTRY_DATE, "Assets:Bank:Checking")


@pytest.fixture
def transaction():
    postings = [
        data.Posting("Assets:Bank:Checking", Amount(Decimal("-25"), "USD"), None, None, None, None),
        data.Posting("Expenses:Food", Amount(Decimal("15"), "USD"), None, None, None, None),
        data.Posting("Expenses:Books", Amount(Decimal("10"), "USD"), None, None, None, None),
    ]
    return data.Transaction(META, ENTRY_DATE, "*", None, "Purchase", frozenset(), frozenset(), postings)


def test_no_options_returns_default_file_and_append_position(entry):
    assert find_insert_position(entry, (), DEFAULT_FILENAME) == (DEFAULT_FILENAME, None)


def test_nonmatching_pattern_returns_default_file_and_append_position(entry):
    options = (option(date(2024, 1, 9), r"Expenses:.*", "expenses.bean", 4),)

    assert find_insert_position(entry, options, DEFAULT_FILENAME) == (DEFAULT_FILENAME, None)


@pytest.mark.parametrize("ineligible_date", [ENTRY_DATE, date(2024, 1, 11)], ids=["same-day", "future"])
def test_only_options_strictly_before_entry_are_eligible(entry, ineligible_date):
    ineligible = option(ineligible_date, r"Assets:", "ineligible.bean", 20)
    earlier = option(date(2024, 1, 9), r"Assets:", "earlier.bean", 8)

    assert find_insert_position(entry, (ineligible,), DEFAULT_FILENAME) == (DEFAULT_FILENAME, None)
    assert find_insert_position(entry, (earlier, ineligible), DEFAULT_FILENAME) == ("earlier.bean", 7)


def test_newest_matching_option_wins_regardless_of_input_order(entry):
    oldest_match = option(date(2023, 12, 31), r"Assets:", "old.bean", 50)
    newest_match = option(date(2024, 1, 2), r"Assets:Bank:", "chosen.bean", 3)
    newer_miss = option(date(2024, 1, 9), r"Liabilities:", "other.bean", 20)

    for ordering in permutations((oldest_match, newest_match, newer_miss)):
        options = list(ordering)
        assert find_insert_position(entry, options, DEFAULT_FILENAME) == ("chosen.bean", 2)
        assert options == list(ordering)


def test_same_date_matching_options_preserve_input_priority(entry):
    when = date(2024, 1, 9)
    broad = option(when, r"Assets:", "broad.bean", 17)
    specific = option(when, r"Assets:Bank:Checking$", "specific.bean", 4)

    assert find_insert_position(entry, (broad, specific), DEFAULT_FILENAME) == ("broad.bean", 16)
    assert find_insert_position(entry, (specific, broad), DEFAULT_FILENAME) == ("specific.bean", 3)


def test_regex_matches_from_start_without_requiring_entire_account(entry):
    substring = option(date(2024, 1, 9), r"Bank:Checking$", "substring.bean", 12)
    prefix = option(date(2024, 1, 8), r"Assets:(Bank|Cash)", "prefix.bean", 1)

    assert find_insert_position(entry, (substring, prefix), DEFAULT_FILENAME) == ("prefix.bean", 0)


def test_directive_without_accounts_returns_default_even_with_wildcard():
    entry = data.Commodity(META, ENTRY_DATE, "USD")
    options = (option(date(2024, 1, 9), r".*", "wildcard.bean", 12),)

    assert find_insert_position(entry, options, DEFAULT_FILENAME) == (DEFAULT_FILENAME, None)


def test_last_posting_takes_priority_over_newer_options_for_earlier_postings(transaction):
    options = (
        option(date(2024, 1, 9), r"Assets:", "bank.bean", 30),
        option(date(2024, 1, 8), r"Expenses:Food$", "food.bean", 20),
        option(date(2024, 1, 4), r"Expenses:Books$", "older-books.bean", 10),
        option(date(2024, 1, 6), r"Expenses:Books$", "books.bean", 18),
    )

    assert find_insert_position(transaction, options, DEFAULT_FILENAME) == ("books.bean", 17)


def test_transaction_tries_earlier_postings_when_later_ones_have_no_eligible_match(transaction):
    bank = option(date(2024, 1, 9), r"Assets:", "bank.bean", 30)
    food = option(date(2024, 1, 7), r"Expenses:Food$", "food.bean", 20)
    same_day_books = option(ENTRY_DATE, r"Expenses:Books$", "books.bean", 11)

    assert find_insert_position(transaction, (bank, same_day_books, food), DEFAULT_FILENAME) == ("food.bean", 19)
    assert find_insert_position(transaction, (bank, same_day_books), DEFAULT_FILENAME) == ("bank.bean", 29)


def test_pad_prefers_target_account_and_can_fall_back_to_source_account():
    entry = data.Pad(META, ENTRY_DATE, "Assets:Bank:Checking", "Equity:Opening-Balances")
    source = option(date(2024, 1, 9), r"Equity:", "source.bean", 9)
    target = option(date(2024, 1, 5), r"Assets:", "target.bean", 20)

    assert find_insert_position(entry, (source, target), DEFAULT_FILENAME) == ("target.bean", 19)
    assert find_insert_position(entry, (source,), DEFAULT_FILENAME) == ("source.bean", 8)


def test_custom_considers_account_values_in_order_and_ignores_strings():
    entry = data.Custom(
        META,
        ENTRY_DATE,
        "allocation",
        [
            SimpleNamespace(value="Income:Salary", dtype=str),
            SimpleNamespace(value="Assets:Bank:Checking", dtype=ACCOUNT_TYPE),
            SimpleNamespace(value="Expenses:Food", dtype=ACCOUNT_TYPE),
        ],
    )
    text = option(date(2024, 1, 9), r"Income:", "text.bean", 7)
    first_account = option(date(2024, 1, 3), r"Assets:", "first.bean", 11)
    second_account = option(date(2024, 1, 8), r"Expenses:", "second.bean", 30)

    assert find_insert_position(entry, (text, second_account, first_account), DEFAULT_FILENAME) == ("first.bean", 10)
    assert find_insert_position(entry, (text, second_account), DEFAULT_FILENAME) == ("second.bean", 29)
    assert find_insert_position(entry, (text,), DEFAULT_FILENAME) == (DEFAULT_FILENAME, None)
