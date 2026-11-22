from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import INTERVALS


ACCOUNT = "Expenses:Food"
MONTHLY = INTERVALS["monthly"]


def monthly_budget(start, amount, currency="USD", *, account=ACCOUNT):
    return Budget(account, start, MONTHLY, Decimal(amount), currency)


def test_uses_only_the_requested_account():
    start = date(2024, 4, 1)
    budgets = {
        ACCOUNT: [monthly_budget(start, "75")],
        "Expenses": [monthly_budget(start, "300", account="Expenses")],
        "Expenses:Food:Dining": [
            monthly_budget(start, "600", "EUR", account="Expenses:Food:Dining"),
        ],
        "Expenses:FoodDelivery": [
            monthly_budget(start, "900", account="Expenses:FoodDelivery"),
        ],
    }

    result = calculate_budget(budgets, ACCOUNT, date(2024, 4, 9), date(2024, 4, 11))

    assert result == {"USD": Decimal("5")}
    assert isinstance(result["USD"], Decimal)


def test_missing_account_does_not_add_a_key():
    child = "Expenses:Food:Dining"
    start = date(2024, 4, 1)
    budgets = defaultdict(list, {child: [monthly_budget(start, "300", account=child)]})

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 4, 3)) == {}
    assert set(budgets) == {child}


def test_account_with_no_budget_entries():
    assert calculate_budget(
        {ACCOUNT: []}, ACCOUNT, date(2024, 4, 1), date(2024, 4, 3)
    ) == {}


@pytest.mark.parametrize("end_day", [9, 10], ids=["reversed", "empty"])
def test_range_with_no_days(end_day):
    budgets = {ACCOUNT: [monthly_budget(date(2024, 4, 1), "300")]}

    assert calculate_budget(
        budgets, ACCOUNT, date(2024, 4, 10), date(2024, 4, end_day)
    ) == {}


@pytest.mark.parametrize(
    ("from_day", "to_day", "expected"),
    [
        (8, 10, {}),
        (9, 11, {"USD": Decimal("3")}),
        (10, 13, {"USD": Decimal("9")}),
        (11, 14, {"USD": Decimal("11")}),
        (13, 14, {"USD": Decimal("5")}),
        (14, 15, {"USD": Decimal("5"), "GBP": Decimal("1")}),
    ],
)
def test_budget_starts_and_replacements_with_exclusive_end(from_day, to_day, expected):
    budgets = {
        ACCOUNT: [
            monthly_budget(date(2024, 4, 10), "90"),
            monthly_budget(date(2024, 4, 13), "150"),
            monthly_budget(date(2024, 4, 14), "30", "GBP"),
        ],
    }

    assert calculate_budget(
        budgets, ACCOUNT, date(2024, 4, from_day), date(2024, 4, to_day)
    ) == expected


def test_last_entry_for_a_currency_wins_on_the_same_start_date():
    start = date(2024, 4, 10)
    budgets = {
        ACCOUNT: [
            monthly_budget(start, "300"),
            monthly_budget(start, "120", "EUR"),
            monthly_budget(start, "60"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 4, 11)) == {
        "USD": Decimal("2"),
        "EUR": Decimal("4"),
    }


class SevenDayPeriod:
    def number_of_days(self, day):
        return 7


def test_currencies_keep_independent_rates_and_periods():
    budgets = {
        ACCOUNT: [
            monthly_budget(date(2024, 3, 20), "300"),
            monthly_budget(date(2024, 4, 9), "90"),
            monthly_budget(date(2024, 4, 10), "60", "EUR"),
            monthly_budget(date(2024, 4, 11), "0", "CAD"),
            Budget(ACCOUNT, date(2024, 4, 12), SevenDayPeriod(), Decimal("14"), "USD"),
            monthly_budget(date(2024, 4, 13), "-30", "EUR"),
            monthly_budget(date(2024, 4, 16), "30", "GBP"),
        ],
    }

    assert calculate_budget(
        budgets, ACCOUNT, date(2024, 4, 9), date(2024, 4, 16)
    ) == {
        "USD": Decimal("17"),
        "EUR": Decimal("3"),
        "CAD": Decimal("0"),
    }


@pytest.mark.parametrize(
    ("start", "date_from", "date_to", "amount", "expected"),
    [
        (date(2023, 1, 31), date(2023, 2, 27), date(2023, 3, 3), "868", "118"),
        (date(2024, 1, 31), date(2024, 2, 28), date(2024, 3, 3), "899", "120"),
        (date(2024, 4, 15), date(2024, 4, 30), date(2024, 5, 2), "930", "61"),
        (date(2024, 12, 1), date(2024, 12, 31), date(2025, 1, 2), "961", "62"),
    ],
    ids=["common-february", "leap-february", "april-to-may", "year-boundary"],
)
def test_monthly_rate_uses_the_calendar_month_of_each_day(
    start, date_from, date_to, amount, expected
):
    budgets = {ACCOUNT: [monthly_budget(start, amount)]}

    assert calculate_budget(budgets, ACCOUNT, date_from, date_to) == {
        "USD": Decimal(expected),
    }


def test_full_month_accumulates_the_monthly_amount():
    start = date(2024, 4, 1)
    budgets = {ACCOUNT: [monthly_budget(start, "15.75")]}

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 5, 1)) == {
        "USD": Decimal("15.75"),
    }


def test_fractional_daily_amounts_can_cancel_without_removing_the_currency():
    start = date(2024, 4, 20)
    budgets = {
        ACCOUNT: [
            monthly_budget(start, "15.75"),
            monthly_budget(start, "-0.30", "CHF"),
            monthly_budget(date(2024, 4, 22), "-31.50"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 4, 22)) == {
        "USD": Decimal("1.05"),
        "CHF": Decimal("-0.02"),
    }
    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 4, 23)) == {
        "USD": Decimal("0"),
        "CHF": Decimal("-0.03"),
    }
