from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from fava.core.budgets import Budget, BudgetError, parse_budgets
from fava.util.date import INTERVALS


def custom(line, *values, kind="budget", day=date(2024, 2, 29)):
    return SimpleNamespace(
        type=kind,
        date=day,
        meta={"filename": "budgets.bean", "lineno": line},
        values=[SimpleNamespace(value=value) for value in values],
    )


def amount(number, currency="USD"):
    return SimpleNamespace(number=Decimal(number), currency=currency)


@pytest.mark.parametrize(
    "entries",
    [[], [custom(1, kind="Budget"), custom(2, kind="budget-note")]],
    ids=["empty", "unrelated-directives"],
)
def test_no_budget_directives_produce_no_budgets_or_errors(entries):
    budgets, errors = parse_budgets(entries)

    assert budgets == {}
    assert list(errors) == []


@pytest.mark.parametrize("period", sorted(INTERVALS))
def test_recognizes_registered_intervals_case_insensitively(period):
    account = "Expenses:Books"
    entry = custom(3, account, period.upper(), amount("12.345", "EUR"))

    budgets, errors = parse_budgets([entry])

    assert list(errors) == []
    assert budgets == {
        account: [Budget(account, entry.date, INTERVALS[period], Decimal("12.345"), "EUR")]
    }
    assert budgets[account][0].period is INTERVALS[period]
    assert isinstance(budgets[account][0].number, Decimal)


def test_converts_interval_value_to_text_before_normalizing():
    class MonthlyValue:
        def __str__(self):
            return "MoNtHlY"

    account = "Expenses:Books"
    entry = custom(4, account, MonthlyValue(), amount("25.00"))

    budgets, errors = parse_budgets([entry])

    assert list(errors) == []
    assert budgets == {
        account: [Budget(account, entry.date, INTERVALS["monthly"], Decimal("25.00"), "USD")]
    }


def test_groups_by_full_account_and_preserves_input_order_and_duplicates():
    account = "Expenses:Books"
    child = "Expenses:Books:Used"
    later = date(2024, 9, 1)
    earlier = date(2024, 1, 1)
    first = custom(5, account, "monthly", amount("100.01"), day=later)
    child_entry = custom(6, child, "monthly", amount("0", "GBP"), "extra")
    second = custom(7, account, "monthly", amount("-9.25", "EUR"), day=earlier)
    third = custom(8, account, "monthly", amount("7.50"), day=earlier)

    budgets, errors = parse_budgets([first, child_entry, second, third, first])

    monthly = INTERVALS["monthly"]
    first_budget = Budget(account, later, monthly, Decimal("100.01"), "USD")
    assert list(errors) == []
    assert budgets == {
        account: [
            first_budget,
            Budget(account, earlier, monthly, Decimal("-9.25"), "EUR"),
            Budget(account, earlier, monthly, Decimal("7.50"), "USD"),
            first_budget,
        ],
        child: [Budget(child, child_entry.date, monthly, Decimal("0"), "GBP")],
    }


@pytest.mark.parametrize("period", ["fortnight-of-moons", "", " monthly ", None])
def test_rejects_unrecognized_interval_before_reading_amount(period):
    entry = custom(9, "Expenses:Books", period)

    budgets, errors = parse_budgets([entry])

    assert budgets == {}
    assert list(errors) == [BudgetError(entry.meta, "Invalid interval for budget entry", entry)]
    assert type(errors[0]) is BudgetError


def test_reports_malformed_budgets_in_input_order_and_keeps_valid_budgets():
    account = "Expenses:Books"
    valid_first = custom(10, account, "monthly", amount("15"))
    no_values = custom(11)
    no_interval = custom(12, "Expenses:MissingInterval")
    wrong_interval = custom(13, "Expenses:InvalidInterval", "unknown", amount("8"))
    no_amount = custom(14, "Expenses:MissingAmount", "monthly")
    non_indexable = custom(15)
    non_indexable.values = None
    unhashable_account = custom(16, [account], "monthly", amount("9"))
    ignored = custom(17, kind="other")
    ignored.values = None
    valid_last = custom(18, account, "MONTHLY", amount("19", "CAD"))

    budgets, errors = parse_budgets([
        valid_first, no_values, no_interval, wrong_interval, no_amount,
        non_indexable, unhashable_account, ignored, valid_last,
    ])

    assert budgets == {
        account: [
            Budget(account, valid_first.date, INTERVALS["monthly"], Decimal("15"), "USD"),
            Budget(account, valid_last.date, INTERVALS["monthly"], Decimal("19"), "CAD"),
        ]
    }
    failed = "Failed to parse budget entry"
    assert list(errors) == [
        BudgetError(no_values.meta, failed, no_values),
        BudgetError(no_interval.meta, failed, no_interval),
        BudgetError(wrong_interval.meta, "Invalid interval for budget entry", wrong_interval),
        BudgetError(no_amount.meta, failed, no_amount),
        BudgetError(non_indexable.meta, failed, non_indexable),
        BudgetError(unhashable_account.meta, failed, unhashable_account),
    ]
    assert all(type(error) is BudgetError for error in errors)


def test_propagates_attribute_error_for_amount_without_currency():
    entry = custom(19, "Expenses:Books", "monthly", SimpleNamespace(number=Decimal("10")))

    with pytest.raises(AttributeError, match="currency"):
        parse_budgets([entry])