from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from fava.core.budgets import Budget, BudgetError, parse_budgets
from fava.util.date import INTERVALS


DEFAULT_DATE = date(2024, 2, 29)


def custom(kind, *values, on=DEFAULT_DATE, line=1):
    return SimpleNamespace(
        type=kind,
        date=on,
        meta={"filename": "budgets.beancount", "lineno": line},
        values=[SimpleNamespace(value=value) for value in values],
    )


def amount(number, currency):
    return SimpleNamespace(number=Decimal(number), currency=currency)


@pytest.mark.parametrize(
    "entries",
    [
        (),
        (custom("Budget"), custom("budget-extra"), custom("note")),
    ],
    ids=["empty", "unrelated-custom-directives"],
)
def test_no_budget_directives_produce_no_budgets_or_errors(entries):
    budgets, errors = parse_budgets(entries)

    assert budgets == {}
    assert not errors


@pytest.mark.parametrize("name", sorted(INTERVALS))
def test_parses_each_supported_interval_case_insensitively(name):
    entry = custom("budget", "Expenses:Books", name.upper(), amount("19.95", "EUR"))

    budgets, errors = parse_budgets([entry])

    assert not errors
    assert budgets == {
        "Expenses:Books": [
            Budget("Expenses:Books", DEFAULT_DATE, INTERVALS[name], Decimal("19.95"), "EUR"),
        ],
    }


def test_converts_interval_value_to_text_before_normalizing_case():
    class IntervalText:
        def __str__(self):
            return "MoNtHlY"

    entry = custom("budget", "Expenses:Books", IntervalText(), amount("5.25", "EUR"))

    budgets, errors = parse_budgets([entry])

    assert not errors
    assert budgets == {
        "Expenses:Books": [
            Budget("Expenses:Books", DEFAULT_DATE, INTERVALS["monthly"], Decimal("5.25"), "EUR"),
        ],
    }


def test_groups_budgets_by_account_and_preserves_order_and_duplicates():
    newer_date = date(2025, 1, 15)
    precise_number = "12345678901234567890.123456789"
    newer = custom(
        "budget", "Expenses:Books", "monthly", amount(precise_number, "USD"), on=newer_date,
    )
    child = custom("budget", "Expenses:Books:Digital", "monthly", amount("0", "CAD"))
    older = custom("budget", "Expenses:Books", "monthly", amount("-3.125", "EUR"), "extra")
    unrelated = custom("note", "Expenses:Books", "monthly", amount("100", "USD"))

    budgets, errors = parse_budgets([newer, child, unrelated, older, newer])

    monthly = INTERVALS["monthly"]
    newer_budget = Budget("Expenses:Books", newer_date, monthly, Decimal(precise_number), "USD")
    assert not errors
    assert budgets == {
        "Expenses:Books": [
            newer_budget,
            Budget("Expenses:Books", DEFAULT_DATE, monthly, Decimal("-3.125"), "EUR"),
            newer_budget,
        ],
        "Expenses:Books:Digital": [
            Budget("Expenses:Books:Digital", DEFAULT_DATE, monthly, Decimal("0"), "CAD"),
        ],
    }


def test_reports_errors_in_input_order_and_keeps_parsing_valid_entries():
    missing_interval = custom("budget", "Expenses:Books", line=20)
    invalid_interval = custom("budget", "Expenses:Other", "unsupported", line=21)
    valid = custom("budget", "Expenses:Books", "monthly", amount("2.50", "EUR"), line=22)
    missing_amount = custom("budget", "Expenses:Other", "monthly", line=23)
    padded_interval = custom(
        "budget", "Expenses:Other", " monthly ", amount("10", "EUR"), line=24,
    )
    invalid_values = custom("budget", line=25)
    invalid_values.values = None
    unhashable_account = custom("budget", [], "monthly", amount("1", "USD"), line=26)
    later_date = date(2024, 3, 1)
    later = custom(
        "budget", "Expenses:Books", "monthly", amount("3.75", "EUR"), on=later_date, line=27,
    )

    budgets, errors = parse_budgets([
        missing_interval,
        invalid_interval,
        valid,
        missing_amount,
        padded_interval,
        invalid_values,
        unhashable_account,
        later,
    ])

    monthly = INTERVALS["monthly"]
    assert budgets == {
        "Expenses:Books": [
            Budget("Expenses:Books", DEFAULT_DATE, monthly, Decimal("2.50"), "EUR"),
            Budget("Expenses:Books", later_date, monthly, Decimal("3.75"), "EUR"),
        ],
    }
    expected = [
        (missing_interval, "Failed to parse budget entry"),
        (invalid_interval, "Invalid interval for budget entry"),
        (missing_amount, "Failed to parse budget entry"),
        (padded_interval, "Invalid interval for budget entry"),
        (invalid_values, "Failed to parse budget entry"),
        (unhashable_account, "Failed to parse budget entry"),
    ]
    assert list(errors) == [BudgetError(entry.meta, message, entry) for entry, message in expected]
    for error, (entry, _) in zip(errors, expected, strict=True):
        assert isinstance(error, BudgetError)
        assert error.entry is entry


def test_attribute_error_from_a_non_amount_value_propagates():
    entry = custom("budget", "Expenses:Books", "monthly", Decimal("1.50"))

    with pytest.raises(AttributeError, match="number"):
        parse_budgets([entry])
