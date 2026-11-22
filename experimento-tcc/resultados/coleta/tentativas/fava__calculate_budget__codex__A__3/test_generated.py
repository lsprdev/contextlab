from datetime import date
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

import pytest

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import INTERVALS


ACCOUNT = 'Expenses:Food'


def make_budget(start, period, amount, currency='USD', account=ACCOUNT):
    return Budget(
        account, date.fromisoformat(start), INTERVALS[period], Decimal(amount), currency
    )


@pytest.mark.parametrize('has_related_budgets', [False, True], ids=['empty', 'related'])
def test_missing_account_returns_empty_mapping(has_related_budgets):
    budgets = {}
    if has_related_budgets:
        for account in ('Expenses', 'Expenses:Food:Groceries', 'Expenses:FoodCourt'):
            budgets[account] = [make_budget('2024-01-01', 'day', '50', account=account)]

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 2), date(2024, 1, 4)) == {}


def test_account_with_empty_budget_list_returns_empty_mapping():
    assert calculate_budget(
        {ACCOUNT: []}, ACCOUNT, date(2024, 1, 2), date(2024, 1, 4)
    ) == {}


@pytest.mark.parametrize('end_day', [10, 9], ids=['empty', 'reversed'])
def test_range_without_days_returns_empty_mapping(end_day):
    budgets = {ACCOUNT: [make_budget('2024-01-01', 'day', '15')]}

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 10), date(2024, 1, end_day)) == {}


def test_budget_starting_on_exclusive_end_does_not_contribute():
    budgets = {ACCOUNT: [make_budget('2024-01-05', 'day', '15')]}

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 1), date(2024, 1, 5)) == {}


def test_budget_starts_mid_range_and_excludes_the_last_day():
    budgets = {ACCOUNT: [make_budget('2024-01-03', 'day', '2.75')]}

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 1), date(2024, 1, 5)) == {
        'USD': Decimal('5.50'),
    }


@pytest.mark.parametrize(
    ('period', 'amount', 'start', 'end', 'expected'),
    [
        pytest.param('week', '10.50', '2024-02-03', '2024-02-07', '6.00', id='weekly'),
        pytest.param('month', '899', '2024-02-28', '2024-03-03', '120', id='leap-february'),
        pytest.param('month', '868', '2023-01-31', '2023-02-03', '90', id='common-february'),
        pytest.param('quarter', '8190', '2023-03-30', '2023-04-02', '272', id='quarter-change'),
        pytest.param('year', '133590', '2023-12-30', '2024-01-03', '1462', id='leap-year-change'),
    ],
)
def test_proration_uses_the_calendar_period_of_each_day(period, amount, start, end, expected):
    budgets = {ACCOUNT: [make_budget('2023-01-01', period, amount)]}

    result = calculate_budget(budgets, ACCOUNT, date.fromisoformat(start), date.fromisoformat(end))

    assert result == {'USD': Decimal(expected)}
    assert isinstance(result['USD'], Decimal)


def test_repeating_daily_fraction_uses_decimal_precision():
    budgets = {ACCOUNT: [make_budget('2024-01-01', 'week', '1')]}

    with localcontext(Context(prec=12, rounding=ROUND_HALF_EVEN)):
        result = calculate_budget(budgets, ACCOUNT, date(2024, 1, 3), date(2024, 1, 4))

    assert result == {'USD': Decimal('0.142857142857')}


def test_revisions_apply_from_their_start_date_and_keep_currencies_independent():
    budgets = {
        ACCOUNT: [
            make_budget('2024-01-01', 'month', '580'),
            make_budget('2024-02-28', 'day', '2.25', 'EUR'),
            make_budget('2024-02-29', 'month', '290'),
            make_budget('2024-03-01', 'week', '91'),
            make_budget('2024-03-03', 'day', '-1.50', 'EUR'),
            make_budget('2024-03-04', 'day', '100', 'GBP'),
        ],
        'Expenses:Food:Groceries': [
            make_budget('2024-01-01', 'day', '100', account='Expenses:Food:Groceries'),
        ],
    }

    result = calculate_budget(budgets, ACCOUNT, date(2024, 2, 27), date(2024, 3, 4))

    assert result == {'USD': Decimal('89'), 'EUR': Decimal('7.50')}


def test_last_entry_for_a_currency_wins_when_start_dates_are_equal():
    budgets = {
        ACCOUNT: [
            make_budget('2024-05-01', 'day', '3'),
            make_budget('2024-05-01', 'day', '8', 'EUR'),
            make_budget('2024-05-01', 'week', '35'),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, date(2024, 5, 1), date(2024, 5, 3)) == {
        'USD': Decimal('10'),
        'EUR': Decimal('16'),
    }


def test_zero_and_negative_totals_are_retained_for_active_currencies():
    budgets = {
        ACCOUNT: [
            make_budget('2024-05-01', 'day', '1.25'),
            make_budget('2024-05-01', 'day', '0', 'EUR'),
            make_budget('2024-05-01', 'day', '-0.50', 'GBP'),
            make_budget('2024-05-02', 'day', '-1.25'),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, date(2024, 5, 1), date(2024, 5, 3)) == {
        'USD': Decimal('0'),
        'EUR': Decimal('0'),
        'GBP': Decimal('-1.00'),
    }
