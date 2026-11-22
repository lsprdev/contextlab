from datetime import date
from decimal import Decimal, localcontext

import pytest

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import INTERVALS


ACCOUNT = "Expenses:Books"
CHILD = "Expenses:Books:Used"
MONTHLY = INTERVALS["monthly"]


def monthly_budget(start, amount, currency="USD", account=ACCOUNT):
    return Budget(account, start, MONTHLY, Decimal(amount), currency)


def test_calculate_budget_uses_only_the_exact_account():
    start = date(2024, 1, 10)
    end = date(2024, 1, 11)
    other = "Expenses:Bookshop"
    budgets = {
        CHILD: [monthly_budget(start, "620", account=CHILD)],
        other: [monthly_budget(start, "930", account=other)],
    }

    assert calculate_budget(budgets, ACCOUNT, start, end) == {}

    budgets[ACCOUNT] = [monthly_budget(start, "310")]
    assert calculate_budget(budgets, ACCOUNT, start, end) == {
        "USD": Decimal("10"),
    }


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(date(2024, 1, 3), date(2024, 1, 3), id="empty"),
        pytest.param(date(2024, 1, 4), date(2024, 1, 3), id="reversed"),
    ],
)
def test_calculate_budget_returns_no_amounts_for_a_range_without_days(start, end):
    budgets = {ACCOUNT: [monthly_budget(date(2024, 1, 1), "310")]}

    assert calculate_budget(budgets, ACCOUNT, start, end) == {}


def test_calculate_budget_returns_no_amounts_for_an_empty_budget_list():
    assert calculate_budget(
        {ACCOUNT: []}, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)
    ) == {}


def test_calculate_budget_includes_the_activation_day_and_excludes_the_end():
    activation = date(2024, 1, 3)
    budgets = {ACCOUNT: [monthly_budget(activation, "310")]}
    start = date(2024, 1, 1)

    assert calculate_budget(budgets, ACCOUNT, start, activation) == {}
    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 4)) == {
        "USD": Decimal("10"),
    }


@pytest.mark.parametrize(
    ("year", "february_last_day", "amount", "expected"),
    [
        pytest.param(2023, 28, "868", "59", id="common-year"),
        pytest.param(2024, 29, "899", "60", id="leap-year"),
    ],
)
def test_calculate_budget_prorates_using_each_days_calendar_month(
    year, february_last_day, amount, expected
):
    budgets = {ACCOUNT: [monthly_budget(date(year, 1, 15), amount)]}

    assert calculate_budget(
        budgets, ACCOUNT, date(year, 2, february_last_day), date(year, 3, 2)
    ) == {"USD": Decimal(expected)}


def test_calculate_budget_tracks_revisions_independently_for_each_currency():
    budgets = {
        ACCOUNT: [
            monthly_budget(date(2024, 1, 20), "899"),
            monthly_budget(date(2024, 1, 29), "310", "EUR"),
            monthly_budget(date(2024, 1, 31), "930", "EUR"),
            monthly_budget(date(2024, 1, 31), "620", "EUR"),
            monthly_budget(date(2024, 2, 1), "58", "EUR"),
            monthly_budget(date(2024, 2, 2), "-87", "GBP"),
            monthly_budget(date(2024, 2, 4), "2900", "EUR"),
            monthly_budget(date(2024, 2, 4), "290", "CHF"),
        ],
    }

    result = calculate_budget(budgets, ACCOUNT, date(2024, 1, 28), date(2024, 2, 4))

    assert result == {
        "USD": Decimal("209"),
        "EUR": Decimal("46"),
        "GBP": Decimal("-6"),
    }


def test_calculate_budget_retains_currencies_with_zero_totals():
    budgets = {
        ACCOUNT: [
            monthly_budget(date(2024, 1, 1), "31"),
            monthly_budget(date(2024, 1, 1), "0", "EUR"),
            monthly_budget(date(2024, 1, 2), "-31"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)) == {
        "USD": Decimal("0"),
        "EUR": Decimal("0"),
    }


def test_calculate_budget_accumulates_daily_decimal_amounts():
    budgets = {ACCOUNT: [monthly_budget(date(2024, 1, 1), "1")]}

    with localcontext(prec=6):
        result = calculate_budget(
            budgets, ACCOUNT, date(2024, 1, 1), date(2024, 1, 4)
        )

    assert result == {"USD": Decimal("0.0967743")}
    assert isinstance(result["USD"], Decimal)
