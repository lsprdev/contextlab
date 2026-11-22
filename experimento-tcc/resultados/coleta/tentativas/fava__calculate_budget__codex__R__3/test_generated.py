from datetime import date
from decimal import Decimal

import pytest

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import INTERVALS


ACCOUNT = "Expenses:Food"


def budget(start, number, currency="USD", period="monthly", account=ACCOUNT):
    return Budget(account, start, INTERVALS[period], Decimal(number), currency)


@pytest.mark.parametrize("include_empty_account", [False, True])
def test_only_uses_budgets_for_the_exact_account(include_empty_account):
    start = date(2024, 1, 1)
    budgets = {
        name: [budget(start, "310", account=name)]
        for name in ("Expenses", "Expenses:Food:Groceries", "Expenses:FoodDelivery")
    }
    if include_empty_account:
        budgets[ACCOUNT] = []

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 3)) == {}


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(date(2024, 1, 1), date(2024, 1, 1), id="empty"),
        pytest.param(date(2024, 1, 2), date(2024, 1, 1), id="reversed"),
    ],
)
def test_range_without_days_returns_no_currency_even_with_active_budget(start, end):
    budgets = {ACCOUNT: [budget(date(2023, 12, 1), "310")]}

    assert calculate_budget(budgets, ACCOUNT, start, end) == {}


def test_budget_starts_on_its_effective_date_and_end_is_exclusive():
    start = date(2024, 1, 10)
    effective = date(2024, 1, 12)
    budgets = {ACCOUNT: [budget(effective, "31.62")]}

    assert calculate_budget(budgets, ACCOUNT, start, effective) == {}

    result = calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 13))
    assert result == {"USD": Decimal("1.02")}
    assert isinstance(result["USD"], Decimal)


@pytest.mark.parametrize(
    ("start", "end", "monthly_amount", "expected"),
    [
        pytest.param(date(2023, 2, 28), date(2023, 3, 2), "868", "59", id="common-february"),
        pytest.param(date(2024, 2, 28), date(2024, 3, 2), "899", "91", id="leap-february"),
        pytest.param(date(2024, 4, 30), date(2024, 5, 2), "930", "61", id="april-to-may"),
    ],
)
def test_monthly_proration_uses_the_month_of_each_day(start, end, monthly_amount, expected):
    budgets = {ACCOUNT: [budget(date(2022, 1, 15), monthly_amount)]}

    assert calculate_budget(budgets, ACCOUNT, start, end) == {"USD": Decimal(expected)}


def test_budget_changes_apply_independently_by_currency():
    budgets = {
        ACCOUNT: [
            budget(date(2024, 1, 1), "310"),
            budget(date(2024, 1, 30), "21", "EUR", "weekly"),
            budget(date(2024, 1, 31), "140", period="weekly"),
            budget(date(2024, 2, 2), "870"),
            budget(date(2024, 2, 4), "290", "GBP"),
        ],
        "Expenses:Food:Groceries": [budget(date(2024, 1, 1), "3100", "CAD")],
    }

    result = calculate_budget(budgets, ACCOUNT, date(2024, 1, 29), date(2024, 2, 4))

    # USD accrues at each of the three rates for two days. EUR accrues for five days.
    assert result == {"USD": Decimal("120"), "EUR": Decimal("15")}


def test_last_entry_for_a_currency_wins_on_the_same_date():
    start = date(2024, 1, 7)
    budgets = {
        ACCOUNT: [
            budget(start, "310"),
            budget(start, "93", "EUR"),
            budget(start, "620"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 8)) == {
        "USD": Decimal("20"),
        "EUR": Decimal("3"),
    }


def test_negative_amounts_and_zero_totals_are_returned():
    start = date(2024, 1, 1)
    budgets = {
        ACCOUNT: [
            budget(start, "0", "GBP"),
            budget(start, "-62", "EUR"),
            budget(start, "31"),
            budget(date(2024, 1, 2), "-31"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 3)) == {
        "GBP": Decimal("0"),
        "EUR": Decimal("-4"),
        "USD": Decimal("0"),
    }
