import re
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from fava.beans.abc import Custom, Open, Pad, Posting, Transaction
from fava.beans.account import ACCOUNT_TYPE
from fava.core.file import find_insert_position


ENTRY_DATE = date(2024, 3, 1)
DEFAULT_FILENAME = "books/main.beancount"
BANK = "Assets:Bank:Checking"
CASH = "Assets:Cash"
FOOD = "Expenses:Food"


def rule(pattern, days_from_entry, filename, lineno):
    return SimpleNamespace(
        re=re.compile(pattern),
        date=ENTRY_DATE + timedelta(days=days_from_entry),
        filename=filename,
        lineno=lineno,
    )


def open_account():
    return Open({}, ENTRY_DATE, BANK, None, None)


def transaction(*accounts):
    return Transaction(
        {},
        ENTRY_DATE,
        "*",
        None,
        "Groceries",
        frozenset(),
        frozenset(),
        [Posting(account, None, None, None, None, None) for account in accounts],
    )


def test_uses_newest_matching_rule_strictly_before_entry_date():
    rules = [
        rule(BANK, -10, "old.beancount", 70),
        rule(BANK, 1, "future.beancount", 45),
        rule(BANK, -2, "selected.beancount", 14),
        rule(BANK, 0, "same-day.beancount", 30),
        rule(CASH, -1, "unrelated.beancount", 5),
        rule(BANK, -5, "intermediate.beancount", 42),
    ]
    original_order = tuple(rules)

    assert find_insert_position(open_account(), rules, DEFAULT_FILENAME) == (
        "selected.beancount",
        13,
    )
    assert tuple(rules) == original_order


def test_regex_matches_from_start_and_can_match_only_a_prefix():
    rules = (
        rule(r"Bank:Checking$", -1, "substring.beancount", 8),
        rule(r"Assets:(Bank|Cash):", -2, "prefix.beancount", 1),
    )

    assert find_insert_position(open_account(), rules, DEFAULT_FILENAME) == (
        "prefix.beancount",
        0,
    )


@pytest.mark.parametrize("reverse_order", [False, True])
def test_matching_rules_on_same_date_preserve_input_order(reverse_order):
    broad = rule(r"Assets:", -1, "z-assets.beancount", 29)
    specific = rule(BANK, -1, "a-bank.beancount", 3)
    if reverse_order:
        rules = (specific, broad)
        expected = ("a-bank.beancount", 2)
    else:
        rules = (broad, specific)
        expected = ("z-assets.beancount", 28)

    assert find_insert_position(open_account(), rules, DEFAULT_FILENAME) == expected


@pytest.mark.parametrize(
    ("cash_offset", "bank_offset", "expected"),
    [
        (-4, -3, ("cash.beancount", 19)),
        (0, -3, ("bank.beancount", 11)),
        (1, 0, ("food.beancount", 4)),
    ],
    ids=["last-posting", "middle-posting", "first-posting"],
)
def test_transaction_tries_posting_accounts_in_reverse_order(
    cash_offset, bank_offset, expected
):
    entry = transaction(FOOD, BANK, CASH)
    rules = (
        rule(BANK, bank_offset, "bank.beancount", 12),
        rule(FOOD, -1, "food.beancount", 5),
        rule(CASH, cash_offset, "cash.beancount", 20),
    )

    assert find_insert_position(entry, rules, DEFAULT_FILENAME) == expected


@pytest.mark.parametrize(
    ("account_pattern", "expected"),
    [
        (BANK, ("padded.beancount", 6)),
        (FOOD, ("source.beancount", 10)),
    ],
    ids=["padded-account-has-priority", "source-account-as-fallback"],
)
def test_pad_considers_both_accounts(account_pattern, expected):
    entry = Pad({}, ENTRY_DATE, BANK, CASH)
    rules = (
        rule(CASH, -1, "source.beancount", 11),
        rule(account_pattern, -2, "padded.beancount", 7),
    )

    assert find_insert_position(entry, rules, DEFAULT_FILENAME) == expected


def test_custom_considers_account_values_in_order_and_ignores_strings():
    entry = Custom(
        {},
        ENTRY_DATE,
        "routing",
        [
            SimpleNamespace(value=FOOD, dtype=str),
            SimpleNamespace(value=BANK, dtype=ACCOUNT_TYPE),
            SimpleNamespace(value=CASH, dtype=ACCOUNT_TYPE),
        ],
    )
    rules = (
        rule(FOOD, -1, "string.beancount", 4),
        rule(CASH, -2, "second-account.beancount", 8),
        rule(BANK, -3, "first-account.beancount", 15),
    )

    assert find_insert_position(entry, rules, DEFAULT_FILENAME) == (
        "first-account.beancount",
        14,
    )


@pytest.mark.parametrize(
    "rules",
    [
        (),
        (rule(CASH, -1, "cash.beancount", 3),),
        (
            rule(BANK, 0, "same-day.beancount", 4),
            rule(BANK, 1, "future.beancount", 5),
        ),
    ],
    ids=["no-rules", "no-account-match", "no-earlier-rule"],
)
def test_returns_default_filename_and_append_position_when_no_rule_applies(rules):
    assert find_insert_position(open_account(), rules, DEFAULT_FILENAME) == (
        DEFAULT_FILENAME,
        None,
    )


def test_transaction_without_postings_appends_to_default_file():
    rules = (rule(r".*", -1, "catch-all.beancount", 3),)

    assert find_insert_position(transaction(), rules, DEFAULT_FILENAME) == (
        DEFAULT_FILENAME,
        None,
    )
