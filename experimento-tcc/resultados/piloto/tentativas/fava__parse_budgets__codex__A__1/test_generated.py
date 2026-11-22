from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from beancount.core.amount import Amount
from beancount.core.data import Custom

from fava.core.budgets import Budget, BudgetError, parse_budgets
from fava.util.date import Day, Month, Quarter, Week, Year


def custom(*values, kind='budget', day=1, line=1):
    return Custom(
        {'filename': 'budgets.bean', 'lineno': line},
        date(2024, 2, day),
        kind,
        [SimpleNamespace(value=value) for value in values],
    )


class IntervalValue:
    def __str__(self):
        return 'MoNtHlY'


@pytest.mark.parametrize(
    ('interval', 'expected_period'),
    [
        ('day', Day),
        ('DAILY', Day),
        ('week', Week),
        ('Weekly', Week),
        ('month', Month),
        ('mOnThLy', Month),
        ('quarter', Quarter),
        ('QUARTERLY', Quarter),
        ('year', Year),
        ('YeArLy', Year),
        (IntervalValue(), Month),
    ],
)
def test_parse_budgets_resolves_intervals_and_preserves_fields(interval, expected_period):
    account = 'Expenses:Books'
    number = Decimal('12345678901234567890.123456789')
    entry = custom(account, interval, Amount(number, 'EUR'), day=29)

    budgets, errors = parse_budgets((entry,))

    assert not errors
    assert budgets == {account: [Budget(account, date(2024, 2, 29), expected_period, number, 'EUR')]}
    assert isinstance(budgets[account][0].number, Decimal)


def test_parse_budgets_groups_entries_in_input_order_and_keeps_repeats():
    books = 'Expenses:Books'
    travel = 'Expenses:Travel'
    later = custom(books, 'month', Amount(Decimal('19.25'), 'USD'), day=20)
    other = custom(travel, 'yearly', Amount(Decimal('0'), 'CHF'), day=15)
    earlier = custom(books, 'week', Amount(Decimal('-3.50'), 'EUR'), day=2)
    same_day = custom(books, 'day', Amount(Decimal('4'), 'USD'), 'extra', day=20)

    budgets, errors = parse_budgets([later, other, earlier, same_day, later])

    assert not errors
    assert budgets == {
        books: [
            Budget(books, later.date, Month, Decimal('19.25'), 'USD'),
            Budget(books, earlier.date, Week, Decimal('-3.50'), 'EUR'),
            Budget(books, same_day.date, Day, Decimal('4'), 'USD'),
            Budget(books, later.date, Month, Decimal('19.25'), 'USD'),
        ],
        travel: [Budget(travel, other.date, Year, Decimal('0'), 'CHF')],
    }


def test_parse_budgets_ignores_other_custom_types():
    amount = Amount(Decimal('10'), 'USD')
    budgets, errors = parse_budgets([
        custom('Expenses:Books', 'monthly', amount, kind='Budget'),
        custom('Expenses:Travel', 'monthly', amount, kind='budgets'),
        custom(kind='unrelated'),
    ])

    assert budgets == {}
    assert not errors


def test_parse_budgets_accepts_empty_input():
    budgets, errors = parse_budgets(())

    assert budgets == {}
    assert not errors


def test_parse_budgets_reports_errors_in_order_and_continues_parsing():
    account = 'Expenses:Books'
    amount = Amount(Decimal('10.25'), 'CAD')
    invalid_period = custom('Expenses:Travel', 'fortnightly', amount, line=10)
    before = custom(account, 'weekly', amount, day=3, line=11)
    missing_period = custom(account, line=12)
    missing_amount = custom(account, 'daily', line=13)
    unhashable_account = custom([account], 'daily', amount, line=14)
    after = custom(account, 'quarter', amount, day=8, line=15)
    empty_period = custom('Expenses:Other', '', amount, line=16)

    budgets, errors = parse_budgets([
        invalid_period,
        before,
        missing_period,
        missing_amount,
        unhashable_account,
        after,
        empty_period,
    ])

    assert budgets == {
        account: [
            Budget(account, before.date, Week, Decimal('10.25'), 'CAD'),
            Budget(account, after.date, Quarter, Decimal('10.25'), 'CAD'),
        ],
    }
    expected_errors = [
        (invalid_period, 'Invalid interval for budget entry'),
        (missing_period, 'Failed to parse budget entry'),
        (missing_amount, 'Failed to parse budget entry'),
        (unhashable_account, 'Failed to parse budget entry'),
        (empty_period, 'Invalid interval for budget entry'),
    ]
    assert len(errors) == len(expected_errors)
    for error, (entry, message) in zip(errors, expected_errors, strict=True):
        assert isinstance(error, BudgetError)
        assert error.source == entry.meta
        assert error.message == message
        assert error.entry is entry
