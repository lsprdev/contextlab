from datetime import date
from decimal import Decimal, localcontext

import pytest

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import INTERVALS


ACCOUNT = "Expenses:Books"


def make_budget(start, number, currency="USD", period="monthly", account=ACCOUNT):
    return Budget(account, start, INTERVALS[period], Decimal(number), currency)


def test_only_the_requested_account_contributes():
    start = date(2024, 1, 1)
    parent = "Expenses"
    child = "Expenses:Books:Used"
    budgets = {
        parent: [make_budget(start, "3100", account=parent)],
        ACCOUNT: [make_budget(start, "310")],
        child: [make_budget(start, "620", account=child)],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 4)) == {
        "USD": Decimal("30"),
    }
    assert calculate_budget(budgets, "Expenses:Food", start, date(2024, 1, 4)) == {}


def test_account_with_no_budget_entries_returns_empty_mapping():
    assert calculate_budget(
        {ACCOUNT: []}, ACCOUNT, date(2024, 1, 1), date(2024, 1, 4)
    ) == {}


def test_zero_day_range_returns_empty_mapping_even_with_an_active_budget():
    start = date(2024, 1, 1)
    budgets = {ACCOUNT: [make_budget(start, "310")]}

    assert calculate_budget(budgets, ACCOUNT, start, start) == {}


def test_budget_starts_on_its_effective_date_and_end_date_is_exclusive():
    budgets = {
        ACCOUNT: [
            make_budget(date(2024, 1, 3), "310"),
            make_budget(date(2024, 1, 5), "620", "EUR"),
        ],
    }
    start = date(2024, 1, 1)

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 3)) == {}
    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 5)) == {
        "USD": Decimal("20"),
    }
    assert calculate_budget(
        budgets, ACCOUNT, date(2024, 1, 5), date(2024, 1, 6)
    ) == {"USD": Decimal("10"), "EUR": Decimal("20")}


def test_versions_are_applied_independently_per_currency():
    budgets = {
        ACCOUNT: [
            make_budget(date(2024, 1, 1), "310"),
            make_budget(date(2024, 1, 2), "62", "EUR"),
            make_budget(date(2024, 1, 3), "620"),
            make_budget(date(2024, 1, 3), "930"),
            make_budget(date(2024, 1, 4), "155", "EUR"),
        ],
    }

    assert calculate_budget(
        budgets, ACCOUNT, date(2024, 1, 2), date(2024, 1, 6)
    ) == {"USD": Decimal("100"), "EUR": Decimal("14")}


@pytest.mark.parametrize(
    ("period", "number", "date_from", "date_to", "expected"),
    [
        pytest.param(
            "monthly", "868", date(2023, 2, 28), date(2023, 3, 2), "59",
            id="february-in-a-common-year",
        ),
        pytest.param(
            "monthly", "899", date(2024, 2, 28), date(2024, 3, 3), "120",
            id="february-in-a-leap-year",
        ),
        pytest.param(
            "monthly", "930", date(2024, 4, 30), date(2024, 5, 2), "61",
            id="thirty-day-to-thirty-one-day-month",
        ),
        pytest.param(
            "yearly", "133590", date(2024, 12, 31), date(2025, 1, 2), "731",
            id="leap-year-to-common-year",
        ),
    ],
)
def test_daily_rate_uses_the_calendar_period_containing_each_day(
    period, number, date_from, date_to, expected
):
    budgets = {
        ACCOUNT: [make_budget(date(2023, 1, 1), number, period=period)],
    }

    assert calculate_budget(budgets, ACCOUNT, date_from, date_to) == {
        "USD": Decimal(expected),
    }


def test_replacement_can_change_the_budget_period():
    budgets = {
        ACCOUNT: [
            make_budget(date(2024, 1, 1), "310"),
            make_budget(date(2024, 1, 3), "7320", period="yearly"),
        ],
    }

    assert calculate_budget(
        budgets, ACCOUNT, date(2024, 1, 2), date(2024, 1, 5)
    ) == {"USD": Decimal("50")}


def test_partial_period_keeps_fractional_decimal_precision():
    start = date(2024, 1, 1)
    budgets = {ACCOUNT: [make_budget(start, "1")]}

    with localcontext() as context:
        context.prec = 28
        total = calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 2))
        expected = Decimal(1) / Decimal(31)

    assert total == {"USD": expected}
    assert isinstance(total["USD"], Decimal)


def test_zero_and_negative_totals_are_retained():
    start = date(2024, 1, 1)
    budgets = {
        ACCOUNT: [
            make_budget(start, "31", "USD"),
            make_budget(start, "-62", "EUR"),
            make_budget(start, "0", "GBP"),
            make_budget(date(2024, 1, 2), "-31", "USD"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 3)) == {
        "USD": Decimal("0"),
        "EUR": Decimal("-4"),
        "GBP": Decimal("0"),
    }
