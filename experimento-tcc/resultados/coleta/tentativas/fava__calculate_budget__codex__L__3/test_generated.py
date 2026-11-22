from datetime import date
from decimal import Decimal

import pytest

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import INTERVALS


ACCOUNT = "Expenses:Books"
MONTHLY = INTERVALS["monthly"]


def test_missing_account_ignores_related_accounts():
    parent = "Expenses"
    child = f"{ACCOUNT}:Fiction"
    sibling = "Expenses:Bookshop"
    budgets = {
        name: [Budget(name, date(2024, 1, 1), MONTHLY, Decimal("31"), "USD")]
        for name in (parent, child, sibling)
    }

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 2), date(2024, 1, 5)) == {}
    assert set(budgets) == {parent, child, sibling}


def test_account_with_empty_budget_list():
    assert calculate_budget(
        {ACCOUNT: []}, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)
    ) == {}


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2024, 2, 8), date(2024, 2, 10), {}),
        (date(2024, 2, 8), date(2024, 2, 11), {"USD": Decimal("1")}),
        (date(2024, 2, 10), date(2024, 2, 11), {"USD": Decimal("1")}),
        (date(2024, 2, 11), date(2024, 2, 11), {}),
        (date(2024, 2, 12), date(2024, 2, 11), {}),
    ],
    ids=["starts-at-exclusive-end", "starts-inside-range", "starts-at-beginning", "empty", "reversed"],
)
def test_budget_activation_and_range_bounds(start, end, expected):
    budgets = {
        ACCOUNT: [Budget(ACCOUNT, date(2024, 2, 10), MONTHLY, Decimal("29"), "USD")]
    }

    assert calculate_budget(budgets, ACCOUNT, start, end) == expected


@pytest.mark.parametrize(
    ("start", "end", "monthly_amount", "expected_amount"),
    [
        (date(2024, 2, 28), date(2024, 3, 2), "899", "91"),
        (date(2023, 2, 27), date(2023, 3, 2), "868", "90"),
        (date(2024, 4, 29), date(2024, 5, 3), "930", "122"),
    ],
    ids=["leap-february-to-march", "common-february-to-march", "april-to-may"],
)
def test_monthly_budget_is_prorated_using_each_days_calendar_month(
    start, end, monthly_amount, expected_amount
):
    budgets = {
        ACCOUNT: [Budget(ACCOUNT, date(2023, 1, 17), MONTHLY, Decimal(monthly_amount), "EUR")]
    }

    assert calculate_budget(budgets, ACCOUNT, start, end) == {
        "EUR": Decimal(expected_amount)
    }


def test_revisions_replace_only_the_matching_currency_on_their_start_date():
    weekly = INTERVALS["weekly"]
    budgets = {
        ACCOUNT: [
            Budget(ACCOUNT, date(2024, 2, 1), MONTHLY, Decimal("29"), "USD"),
            Budget(ACCOUNT, date(2024, 2, 11), MONTHLY, Decimal("58"), "EUR"),
            Budget(ACCOUNT, date(2024, 2, 12), MONTHLY, Decimal("870"), "USD"),
            Budget(ACCOUNT, date(2024, 2, 12), weekly, Decimal("21"), "USD"),
            Budget(ACCOUNT, date(2024, 2, 13), MONTHLY, Decimal("0"), "CAD"),
            Budget(ACCOUNT, date(2024, 2, 15), weekly, Decimal("-7"), "USD"),
            Budget(ACCOUNT, date(2024, 2, 16), MONTHLY, Decimal("2900"), "USD"),
            Budget(ACCOUNT, date(2024, 2, 16), MONTHLY, Decimal("29"), "GBP"),
        ]
    }

    result = calculate_budget(budgets, ACCOUNT, date(2024, 2, 10), date(2024, 2, 16))

    # USD contributes 1, 1, 3, 3, 3, and -1. EUR contributes 2 on five days.
    assert result == {"USD": Decimal("10"), "EUR": Decimal("10"), "CAD": Decimal("0")}
    assert all(isinstance(amount, Decimal) for amount in result.values())


def test_proration_preserves_fractional_cents_and_negative_amounts():
    budgets = {
        ACCOUNT: [Budget(ACCOUNT, date(2024, 2, 1), MONTHLY, Decimal("-0.145"), "USD")]
    }

    assert calculate_budget(budgets, ACCOUNT, date(2024, 2, 2), date(2024, 2, 5)) == {
        "USD": Decimal("-0.015")
    }


def test_currency_is_retained_when_daily_amounts_cancel():
    budgets = {
        ACCOUNT: [
            Budget(ACCOUNT, date(2024, 1, 1), MONTHLY, Decimal("31"), "USD"),
            Budget(ACCOUNT, date(2024, 1, 2), MONTHLY, Decimal("-31"), "USD"),
        ]
    }

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)) == {
        "USD": Decimal("0")
    }
