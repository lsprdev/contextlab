from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import INTERVALS


ACCOUNT = "Expenses:Books"
MONTHLY = INTERVALS["monthly"]


def monthly(start, amount, currency="USD", account=ACCOUNT):
    return Budget(account, start, MONTHLY, Decimal(amount), currency)


def test_missing_account_ignores_other_accounts_and_does_not_insert_key():
    child = ACCOUNT + ":Used"
    budgets = defaultdict(list, {child: [monthly(date(2024, 1, 1), "31", account=child)]})

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)) == {}
    assert set(budgets) == {child}


def test_account_with_empty_budget_list():
    assert calculate_budget({ACCOUNT: []}, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)) == {}


@pytest.mark.parametrize("end_day", [9, 10], ids=["reversed", "empty"])
def test_ranges_without_days_return_empty_mapping(end_day):
    budgets = {ACCOUNT: [monthly(date(2024, 1, 1), "31")]}

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 10), date(2024, 1, end_day)) == {}


def test_budget_starting_on_exclusive_end_date_is_inactive():
    budgets = {ACCOUNT: [monthly(date(2024, 1, 3), "31")]}

    assert calculate_budget(budgets, ACCOUNT, date(2024, 1, 1), date(2024, 1, 3)) == {}


def test_account_lookup_is_exact_and_first_active_day_is_included():
    parent = "Expenses"
    child = ACCOUNT + ":Used"
    budgets = {
        parent: [monthly(date(2024, 1, 1), "310", account=parent)],
        ACCOUNT: [monthly(date(2024, 1, 3), "3.10")],
        child: [monthly(date(2024, 1, 1), "620", account=child)],
    }

    result = calculate_budget(budgets, ACCOUNT, date(2024, 1, 1), date(2024, 1, 4))

    assert result == {"USD": Decimal("0.10")}
    assert isinstance(result["USD"], Decimal)
    with pytest.raises(KeyError):
        _ = result["EUR"]


def test_updates_replace_only_the_matching_currency_from_their_start_date():
    budgets = {
        ACCOUNT: [
            monthly(date(2024, 1, 1), "62"),
            monthly(date(2024, 1, 11), "93", "EUR"),
            monthly(date(2024, 1, 12), "155"),
            monthly(date(2024, 1, 14), "3.10", "GBP"),
            monthly(date(2024, 1, 15), "3100"),
        ],
    }

    result = calculate_budget(budgets, ACCOUNT, date(2024, 1, 10), date(2024, 1, 15))

    assert result == {"USD": Decimal("19"), "EUR": Decimal("12"), "GBP": Decimal("0.10")}


def test_last_entry_in_list_wins_for_same_currency_and_start_date():
    start = date(2024, 1, 1)
    budgets = {
        ACCOUNT: [monthly(start, "31"), monthly(start, "93", "EUR"), monthly(start, "62")],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 2)) == {
        "USD": Decimal("2"),
        "EUR": Decimal("3"),
    }


@pytest.mark.parametrize(
    ("year", "amount", "expected"),
    [(2023, "868", "90"), (2024, "899", "91")],
    ids=["common-year", "leap-year"],
)
def test_monthly_rate_uses_the_calendar_month_of_each_day(year, amount, expected):
    budgets = {ACCOUNT: [monthly(date(year, 1, 20), amount)]}

    result = calculate_budget(budgets, ACCOUNT, date(year, 1, 31), date(year, 2, 3))

    assert result == {"USD": Decimal(expected)}


class SevenDayPeriod:
    def number_of_days(self, day):
        return 7


def test_each_budget_uses_its_own_period():
    start = date(2024, 1, 1)
    budgets = {
        ACCOUNT: [
            monthly(start, "31"),
            Budget(ACCOUNT, start, SevenDayPeriod(), Decimal("14"), "EUR"),
            Budget(ACCOUNT, date(2024, 1, 2), SevenDayPeriod(), Decimal("21"), "USD"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 4)) == {
        "USD": Decimal("7"),
        "EUR": Decimal("6"),
    }


def test_active_currencies_keep_zero_and_negative_totals():
    start = date(2024, 1, 1)
    budgets = {
        ACCOUNT: [
            monthly(start, "31"),
            monthly(start, "0", "EUR"),
            monthly(start, "-3.10", "GBP"),
            monthly(date(2024, 1, 2), "-31"),
        ],
    }

    assert calculate_budget(budgets, ACCOUNT, start, date(2024, 1, 3)) == {
        "USD": Decimal("0"),
        "EUR": Decimal("0"),
        "GBP": Decimal("-0.20"),
    }
