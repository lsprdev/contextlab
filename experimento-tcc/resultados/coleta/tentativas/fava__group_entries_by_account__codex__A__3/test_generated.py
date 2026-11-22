from datetime import date
from typing import NamedTuple

import pytest
from beancount.core import data
from beancount.core.account import TYPE as ACCOUNT_TYPE

from fava.beans.create import posting
from fava.core.group_entries import TransactionPosting, group_entries_by_account


DAY = date(2024, 5, 10)
CASH = "Assets:Bank:Cash"
FOOD = "Expenses:Food"
SALARY = "Income:Salary"
EQUITY = "Equity:Opening-Balances"


class CustomValue(NamedTuple):
    value: str
    dtype: object


def make_transaction(day, *postings):
    return data.Transaction({}, day, "*", None, "Test transaction", frozenset(), frozenset(), list(postings))


def test_empty_input_produces_no_groups():
    assert group_entries_by_account([]) == {}


def test_entries_without_accounts_produce_no_groups():
    entries = (
        data.Event({}, DAY, "location", CASH),
        data.Commodity({}, DAY, "USD"),
        data.Custom({}, DAY, "report", [CustomValue(CASH, str)]),
        make_transaction(DAY),
    )

    assert group_entries_by_account(entries) == {}


def test_mixed_entries_keep_input_and_posting_order_with_sorted_account_keys():
    opened = data.Open({}, DAY, SALARY, None, None)
    first_food = posting(FOOD, "3 USD")
    cash_debit = posting(CASH, "-10 USD")
    second_food = posting(FOOD, "7 USD")
    purchase = make_transaction(DAY, first_food, cash_debit, second_food)
    closed = data.Close({}, date(2024, 5, 1), CASH)
    salary_debit = posting(SALARY, "-20 USD")
    cash_credit = posting(CASH, "20 USD")
    payday = make_transaction(date(2024, 5, 2), salary_debit, cash_credit)
    entries = [opened, purchase, closed, payday]

    grouped = group_entries_by_account(entries)

    assert list(grouped) == [CASH, FOOD, SALARY]
    assert grouped == {
        CASH: [TransactionPosting(purchase, cash_debit), closed, TransactionPosting(payday, cash_credit)],
        FOOD: [TransactionPosting(purchase, first_food), TransactionPosting(purchase, second_food)],
        SALARY: [opened, TransactionPosting(payday, salary_debit)],
    }
    assert grouped[CASH][1] is closed
    assert grouped[SALARY][0] is opened
    assert entries == [opened, purchase, closed, payday]
    assert purchase.postings == [first_food, cash_debit, second_food]
    with pytest.raises(KeyError):
        grouped["Assets:Bank"]


def test_equal_postings_remain_distinct_and_keep_their_original_objects():
    first = posting(FOOD, "5 USD")
    second = posting(FOOD, "5 USD")
    offset = posting(CASH, "-10 USD")
    transaction = make_transaction(DAY, first, offset, second)

    grouped = group_entries_by_account([transaction])

    first_pair, second_pair = grouped[FOOD]
    assert isinstance(first_pair, TransactionPosting)
    assert isinstance(second_pair, TransactionPosting)
    assert first_pair.transaction is transaction
    assert second_pair.transaction is transaction
    assert first_pair.posting is first
    assert second_pair.posting is second
    assert first_pair.posting is not second_pair.posting


def test_pad_and_custom_are_stored_under_each_referenced_account():
    pad = data.Pad({}, DAY, CASH, EQUITY)
    custom = data.Custom(
        {},
        DAY,
        "report",
        [
            CustomValue(SALARY, str),
            CustomValue(EQUITY, ACCOUNT_TYPE),
            CustomValue(FOOD, ACCOUNT_TYPE),
            CustomValue(EQUITY, ACCOUNT_TYPE),
        ],
    )

    grouped = group_entries_by_account([pad, custom])

    assert list(grouped) == [CASH, EQUITY, FOOD]
    assert grouped[CASH] == [pad]
    assert grouped[EQUITY] == [pad, custom, custom]
    assert grouped[FOOD] == [custom]
    assert grouped[CASH][0] is grouped[EQUITY][0] is pad
    assert grouped[EQUITY][1] is grouped[EQUITY][2] is grouped[FOOD][0] is custom


def test_repeated_directives_are_preserved_and_calls_are_independent():
    closed = data.Close({}, DAY, CASH)
    first = group_entries_by_account([closed, closed])
    second = group_entries_by_account([closed])

    assert first == {CASH: [closed, closed]}
    assert second == {CASH: [closed]}
    assert first[CASH][0] is first[CASH][1] is second[CASH][0] is closed
