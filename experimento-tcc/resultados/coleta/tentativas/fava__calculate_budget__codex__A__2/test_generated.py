from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import INTERVALS


ACCOUNT = "Expenses:Food"


def budget(start, amount, *, currency="USD", period="daily", account=ACCOUNT):
    return Budget(
        account, date.fromisoformat(start), INTERVALS[period], Decimal(amount), currency
    )


def test_missing_account_ignores_descendants_without_inserting_key():
    child = f"{ACCOUNT}:Groceries"
    entries = defaultdict(list, {child: [budget("2024-01-01", "40", account=child)]})

    assert calculate_budget(entries, ACCOUNT, date(2024, 1, 1), date(2024, 1, 2)) == {}
    assert list(entries) == [child]


def test_only_the_requested_account_contributes():
    parent = "Expenses"
    child = f"{ACCOUNT}:Groceries"
    sibling = "Expenses:FoodDelivery"
    entries = {
        parent: [budget("2024-01-01", "100", account=parent)],
        ACCOUNT: [budget("2024-01-01", "4.25")],
        child: [budget("2024-01-01", "20", account=child)],
        sibling: [budget("2024-01-01", "10", currency="EUR", account=sibling)],
    }

    assert calculate_budget(entries, ACCOUNT, date(2024, 1, 1), date(2024, 1, 2)) == {
        "USD": Decimal("4.25")
    }


def test_account_with_no_budget_entries():
    assert calculate_budget(
        {ACCOUNT: []}, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)
    ) == {}


@pytest.mark.parametrize("end_day", [4, 5], ids=["reversed", "empty"])
def test_range_with_no_days_returns_no_currencies(end_day):
    entries = {ACCOUNT: [budget("2024-01-01", "14", period="weekly")]}

    assert calculate_budget(
        entries, ACCOUNT, date(2024, 1, 5), date(2024, 1, end_day)
    ) == {}


@pytest.mark.parametrize(
    ("end_day", "expected"),
    [(3, {}), (4, {"USD": Decimal("7.25")})],
    ids=["ends_at_activation", "includes_activation"],
)
def test_activation_and_exclusive_end(end_day, expected):
    entries = {ACCOUNT: [budget("2024-01-03", "7.25")]}

    assert calculate_budget(
        entries, ACCOUNT, date(2024, 1, 1), date(2024, 1, end_day)
    ) == expected


@pytest.mark.parametrize(
    ("period", "amount", "start", "end", "expected"),
    [
        pytest.param("weekly", "0.0007", "2024-01-06", "2024-01-09", "0.0003", id="week-boundary"),
        pytest.param("monthly", "868", "2023-02-28", "2023-03-02", "59", id="common-february"),
        pytest.param("monthly", "899", "2024-02-28", "2024-03-03", "120", id="leap-february"),
        pytest.param("monthly", "930", "2024-04-29", "2024-05-02", "92", id="april-to-may"),
        pytest.param("quarterly", "8190", "2023-03-30", "2023-04-03", "362", id="quarter-boundary"),
        pytest.param("yearly", "133590", "2023-12-31", "2024-01-03", "1096", id="year-boundary"),
    ],
)
def test_prorates_each_day_by_its_calendar_period(period, amount, start, end, expected):
    entries = {ACCOUNT: [budget("2023-01-15", amount, period=period)]}

    assert calculate_budget(
        entries, ACCOUNT, date.fromisoformat(start), date.fromisoformat(end)
    ) == {"USD": Decimal(expected)}


def test_midmonth_activation_uses_the_full_month_as_the_divisor():
    entries = {ACCOUNT: [budget("2024-04-29", "300", period="monthly")]}

    assert calculate_budget(entries, ACCOUNT, date(2024, 4, 27), date(2024, 5, 1)) == {
        "USD": Decimal("20")
    }


@pytest.mark.parametrize(
    ("start_day", "end_day", "expected"),
    [
        (2, 3, {"USD": Decimal("10")}),
        (3, 4, {"USD": Decimal("10"), "EUR": Decimal("2.5")}),
        (4, 5, {"USD": Decimal("20"), "EUR": Decimal("2.5")}),
        (5, 7, {"USD": Decimal("40"), "EUR": Decimal("-3")}),
        (2, 7, {"USD": Decimal("80"), "EUR": Decimal("2")}),
    ],
)
def test_budget_revisions_take_effect_independently_for_each_currency(
    start_day, end_day, expected
):
    entries = {
        ACCOUNT: [
            budget("2024-01-01", "70", period="weekly"),
            budget("2024-01-03", "2.5", currency="EUR"),
            budget("2024-01-04", "620", period="monthly"),
            budget("2024-01-05", "-1.5", currency="EUR"),
            budget("2024-01-07", "5", currency="GBP"),
        ]
    }

    assert calculate_budget(
        entries, ACCOUNT, date(2024, 1, start_day), date(2024, 1, end_day)
    ) == expected


def test_last_entry_for_the_same_date_and_currency_wins_even_if_zero():
    entries = {
        ACCOUNT: [
            budget("2024-01-01", "9"),
            budget("2024-01-02", "28", period="weekly"),
            budget("2024-01-02", "3.5", currency="EUR"),
            budget("2024-01-02", "0"),
        ]
    }

    result = calculate_budget(entries, ACCOUNT, date(2024, 1, 2), date(2024, 1, 4))

    assert result == {"USD": Decimal("0"), "EUR": Decimal("7")}
    with pytest.raises(KeyError):
        result["GBP"]


def test_offsetting_budget_amounts_leave_a_zero_currency_total():
    entries = {
        ACCOUNT: [budget("2024-01-01", "0.125"), budget("2024-01-02", "-0.125")]
    }

    assert calculate_budget(entries, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)) == {
        "USD": Decimal("0")
    }


def test_totals_preserve_decimal_precision_and_type():
    entries = {ACCOUNT: [budget("2024-01-01", "9007199254740993.0001")]}

    result = calculate_budget(entries, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3))

    assert result == {"USD": Decimal("18014398509481986.0002")}
    assert isinstance(result["USD"], Decimal)
