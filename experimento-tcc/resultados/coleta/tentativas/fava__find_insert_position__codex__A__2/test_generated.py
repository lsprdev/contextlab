import re
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from beancount.core import data
from beancount.core.account import TYPE as ACCOUNT_TYPE
from beancount.core.amount import Amount

from fava.core.fava_options import InsertEntryOption
from fava.core.file import find_insert_position


ENTRY_DATE = date(2024, 6, 15)
DEFAULT_FILE = 'main.beancount'


def make_option(day, pattern, filename, lineno):
    return InsertEntryOption(
        date=date(2024, 6, day),
        re=re.compile(pattern),
        filename=filename,
        lineno=lineno,
    )


@pytest.fixture
def checking_entry():
    return data.Close({}, ENTRY_DATE, 'Assets:Bank:Checking')


def test_uses_latest_matching_option_strictly_before_entry(checking_entry):
    options = [
        make_option(2, r'Assets:', 'old.beancount', 42),
        make_option(15, r'Assets:', 'same-day.beancount', 25),
        make_option(14, r'Expenses:', 'different-account.beancount', 84),
        make_option(16, r'Assets:', 'future.beancount', 12),
        make_option(10, r'Assets:Bank:', 'bank.beancount', 1),
        make_option(5, r'Assets:', 'older.beancount', 17),
    ]
    original_order = options.copy()

    assert find_insert_position(checking_entry, options, DEFAULT_FILE) == (
        'bank.beancount',
        0,
    )
    assert options == original_order


def test_matches_regex_at_start_and_accepts_a_prefix(checking_entry):
    options = (
        make_option(14, r'Bank:Checking$', 'substring.beancount', 10),
        make_option(13, r'Assets:(Broker|Bank):', 'prefix.beancount', 23),
        make_option(12, r'Assets:Bank:Checking$', 'exact.beancount', 35),
    )

    assert find_insert_position(checking_entry, options, DEFAULT_FILE) == (
        'prefix.beancount',
        22,
    )


def test_equal_dates_preserve_input_order(checking_entry):
    first = make_option(12, r'Assets:', 'z-assets.beancount', 29)
    second = make_option(12, r'Assets:Bank:', 'a-bank.beancount', 7)
    older = make_option(4, r'Assets:', 'old.beancount', 3)

    assert find_insert_position(
        checking_entry, (older, first, second), DEFAULT_FILE
    ) == ('z-assets.beancount', 28)
    assert find_insert_position(
        checking_entry, (older, second, first), DEFAULT_FILE
    ) == ('a-bank.beancount', 6)


@pytest.mark.parametrize(
    'options',
    [
        (),
        (make_option(14, r'Expenses:', 'expenses.beancount', 8),),
        (make_option(15, r'Assets:', 'same-day.beancount', 8),),
        (make_option(16, r'Assets:', 'future.beancount', 8),),
    ],
    ids=['no-options', 'no-regex-match', 'same-day-only', 'future-only'],
)
def test_falls_back_when_no_option_qualifies(checking_entry, options):
    assert find_insert_position(checking_entry, options, DEFAULT_FILE) == (
        DEFAULT_FILE,
        None,
    )


@pytest.mark.parametrize(
    ('patterns', 'expected'),
    [
        ((r'Assets:Cash$', r'Expenses:Fees$', r'Expenses:Food$'), ('last.beancount', 30)),
        ((r'Assets:Cash$', r'Expenses:Fees$', r'Income:'), ('middle.beancount', 20)),
        ((r'Assets:Cash$', r'Income:', r'Liabilities:'), ('first.beancount', 10)),
    ],
    ids=['last-posting', 'middle-posting', 'first-posting'],
)
def test_transaction_considers_postings_in_reverse_order(patterns, expected):
    entry = data.Transaction(
        {},
        ENTRY_DATE,
        '*',
        None,
        'Groceries',
        frozenset(),
        frozenset(),
        [
            data.Posting('Assets:Cash', Amount(Decimal('-12'), 'USD'), None, None, None, None),
            data.Posting('Expenses:Fees', Amount(Decimal('2'), 'USD'), None, None, None, None),
            data.Posting('Expenses:Food', Amount(Decimal('10'), 'USD'), None, None, None, None),
        ],
    )
    options = (
        make_option(12, patterns[0], 'first.beancount', 11),
        make_option(2, patterns[2], 'last.beancount', 31),
        make_option(8, patterns[1], 'middle.beancount', 21),
        make_option(15, r'Expenses:Food$', 'same-day.beancount', 41),
        make_option(5, r'Expenses:Food$', 'newer-food.beancount', 51)
        if patterns[2] == r'Expenses:Food$'
        else make_option(16, r'Expenses:Food$', 'future.beancount', 51),
    )
    if patterns[2] == r'Expenses:Food$':
        expected = ('newer-food.beancount', 50)

    assert find_insert_position(entry, options, DEFAULT_FILE) == expected


def test_pad_prefers_its_account_and_can_fall_back_to_its_source():
    entry = data.Pad({}, ENTRY_DATE, 'Assets:Cash', 'Equity:Opening-Balances')
    account_option = make_option(3, r'Assets:', 'assets.beancount', 5)
    source_option = make_option(14, r'Equity:', 'equity.beancount', 9)

    assert find_insert_position(
        entry, (source_option, account_option), DEFAULT_FILE
    ) == ('assets.beancount', 4)
    assert find_insert_position(entry, (source_option,), DEFAULT_FILE) == (
        'equity.beancount',
        8,
    )


def test_custom_uses_account_values_in_order_and_ignores_strings():
    entry = data.Custom(
        {},
        ENTRY_DATE,
        'example',
        [
            SimpleNamespace(value='Income:Salary', dtype=str),
            SimpleNamespace(value='Assets:Cash', dtype=ACCOUNT_TYPE),
            SimpleNamespace(value='Expenses:Food', dtype=ACCOUNT_TYPE),
        ],
    )
    string_option = make_option(14, r'Income:', 'income.beancount', 6)
    cash_option = make_option(4, r'Assets:', 'cash.beancount', 12)
    food_option = make_option(13, r'Expenses:', 'food.beancount', 18)

    assert find_insert_position(
        entry, (string_option, food_option, cash_option), DEFAULT_FILE
    ) == ('cash.beancount', 11)
    assert find_insert_position(entry, (string_option, food_option), DEFAULT_FILE) == (
        'food.beancount',
        17,
    )


def test_directive_without_accounts_falls_back_even_with_a_catchall():
    entry = data.Event({}, ENTRY_DATE, 'location', 'Assets:Cash')
    options = (make_option(10, r'.*', 'catchall.beancount', 24),)

    assert find_insert_position(entry, options, DEFAULT_FILE) == (DEFAULT_FILE, None)
