from datetime import date
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

import pytest

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import Day, Month, Quarter, Week, Year


ACCOUNT = "Expenses:Food"


def test_selects_the_exact_account():
    start = date(2024, 5, 1)
    end = date(2024, 5, 3)
    budgets = {
        "Expenses": [Budget("Expenses", start, Day, Decimal("60"), "USD")],
        ACCOUNT: [Budget(ACCOUNT, start, Day, Decimal("2.75"), "USD")],
        "Expenses:Food:Dining": [
            Budget("Expenses:Food:Dining", start, Day, Decimal("100"), "USD"),
        ],
        "Expenses:FoodDelivery": [
            Budget("Expenses:FoodDelivery", start, Day, Decimal("30"), "EUR"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, start, end) == {
        "USD": Decimal("5.50"),
    }
    assert calculate_budget(budgets, "Expenses:Foo", start, end) == {}


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(date(2024, 1, 3), date(2024, 1, 3), id="empty-range"),
        pytest.param(date(2024, 1, 4), date(2024, 1, 3), id="reversed-range"),
    ],
)
def test_no_days_in_requested_range(start, end):
    budgets = {ACCOUNT: [Budget(ACCOUNT, date(2024, 1, 1), Day, Decimal(5), "USD")]}

    assert calculate_budget(budgets, ACCOUNT, start, end) == {}


def test_account_with_no_budget_entries():
    assert calculate_budget(
        {ACCOUNT: []}, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)
    ) == {}


def test_budget_effective_at_exclusive_end_has_no_contribution():
    effective = date(2024, 1, 3)
    budgets = {ACCOUNT: [Budget(ACCOUNT, effective, Day, Decimal("3.25"), "EUR")]}

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 1), effective) == {}
    assert calculate_budget(budgets, ACCOUNT, effective, date(2024, 1, 4)) == {
        "EUR": Decimal("3.25"),
    }


def test_currency_budgets_start_and_change_independently():
    budgets = {
        ACCOUNT: [
            Budget(ACCOUNT, date(2024, 1, 10), Month, Decimal(290), "USD"),
            Budget(ACCOUNT, date(2024, 2, 28), Month, Decimal(899), "EUR"),
            Budget(ACCOUNT, date(2024, 2, 29), Week, Decimal(105), "USD"),
            Budget(ACCOUNT, date(2024, 3, 4), Day, Decimal(100), "USD"),
        ],
    }

    result = calculate_budget(budgets, ACCOUNT, date(2024, 2, 27), date(2024, 3, 4))

    assert result == {"USD": Decimal(80), "EUR": Decimal(149)}


def test_last_entry_on_same_date_replaces_only_its_currency():
    start = date(2024, 6, 10)
    budgets = {
        ACCOUNT: [
            Budget(ACCOUNT, start, Day, Decimal(10), "USD"),
            Budget(ACCOUNT, start, Day, Decimal("2.50"), "EUR"),
            Budget(ACCOUNT, start, Week, Decimal(-21), "USD"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 6, 12)) == {
        "USD": Decimal(-6),
        "EUR": Decimal(5),
    }


def test_keeps_currencies_with_zero_totals():
    start = date(2024, 7, 1)
    budgets = {
        ACCOUNT: [
            Budget(ACCOUNT, start, Day, Decimal(5), "USD"),
            Budget(ACCOUNT, start, Day, Decimal(0), "EUR"),
            Budget(ACCOUNT, date(2024, 7, 2), Day, Decimal(-5), "USD"),
        ],
    }

    result = calculate_budget(budgets, ACCOUNT, start, date(2024, 7, 3))

    assert result == {"USD": Decimal(0), "EUR": Decimal(0)}
    assert all(isinstance(total, Decimal) for total in result.values())


@pytest.mark.parametrize(
    ("period", "effective", "start", "end", "amount", "total"),
    [
        pytest.param(
            Month, date(2023, 2, 28), date(2023, 2, 27), date(2023, 3, 2),
            "868", "59", id="month-boundary-common-year",
        ),
        pytest.param(
            Quarter, date(2023, 1, 1), date(2023, 3, 31), date(2023, 4, 2),
            "8190", "181", id="quarter-boundary",
        ),
        pytest.param(
            Year, date(2023, 1, 1), date(2023, 12, 31), date(2024, 1, 2),
            "133590", "731", id="year-boundary-into-leap-year",
        ),
    ],
)
def test_prorates_using_the_calendar_period_of_each_day(
    period, effective, start, end, amount, total
):
    budgets = {ACCOUNT: [Budget(ACCOUNT, effective, period, Decimal(amount), "USD")]}

    assert calculate_budget(budgets, ACCOUNT, start, end) == {"USD": Decimal(total)}


def test_accumulates_daily_decimal_shares_at_current_precision():
    start = date(2024, 8, 1)
    budgets = {ACCOUNT: [Budget(ACCOUNT, start, Week, Decimal(1), "USD")]}

    with localcontext(Context(prec=6, rounding=ROUND_HALF_EVEN)):
        result = calculate_budget(budgets, ACCOUNT, start, date(2024, 8, 7))

    assert result == {"USD": Decimal("0.857142")}
    assert isinstance(result["USD"], Decimal)
