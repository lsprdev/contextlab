from datetime import date
from decimal import Decimal
from typing import NamedTuple

import pytest
from beancount.core import data
from beancount.core.account import TYPE as ACCOUNT_TYPE
from beancount.core.amount import Amount

from fava.core.group_entries import TransactionPosting, group_entries_by_account


DAY = date(2024, 3, 15)
CASH = "Assets:Cash"
WALLET = "Assets:Cash:Wallet"
FOOD = "Expenses:Food"
EQUITY = "Equity:Opening-Balances"


class CustomValue(NamedTuple):
    value: str
    dtype: object


def make_posting(account, units):
    return data.Posting(account, Amount(Decimal(units), "USD"), None, None, None, None)


def make_transaction(narration, *postings):
    return data.Transaction(
        {}, DAY, "*", None, narration, frozenset(), frozenset(), list(postings)
    )


def test_empty_input_returns_empty_mapping():
    result = group_entries_by_account([])

    assert result == {}
    with pytest.raises(KeyError):
        result[CASH]
    assert list(result) == []


def test_entries_without_accounts_produce_no_groups():
    commodity = data.Commodity({}, DAY, "USD")
    custom = data.Custom({}, DAY, "example", [CustomValue(CASH, str)])
    empty_transaction = make_transaction("No postings")

    assert group_entries_by_account([commodity, custom, empty_transaction]) == {}


def test_mixed_entries_preserve_input_order_and_wrap_each_original_posting():
    food_posting = make_posting(FOOD, "10")
    first_cash_posting = make_posting(CASH, "-3")
    wallet_posting = make_posting(WALLET, "-4")
    second_cash_posting = make_posting(CASH, "-3")
    purchase = make_transaction(
        "Purchase", food_posting, first_cash_posting, wallet_posting, second_cash_posting
    )
    note = data.Note({}, date(2024, 3, 1), CASH, "Cash note", frozenset(), frozenset())
    refund_posting = make_posting(CASH, "2")
    refund_offset = make_posting(FOOD, "-2")
    refund = make_transaction("Refund", refund_posting, refund_offset)
    closing = data.Close({}, DAY, CASH)
    commodity = data.Commodity({}, DAY, "USD")

    result = group_entries_by_account((purchase, note, commodity, refund, closing))

    assert list(result) == [CASH, WALLET, FOOD]
    cash_first, cash_second, grouped_note, cash_refund, grouped_closing = result[CASH]
    (wallet_item,) = result[WALLET]
    food_purchase, food_refund = result[FOOD]
    assert grouped_note is note
    assert grouped_closing is closing
    for item, transaction, posting in (
        (cash_first, purchase, first_cash_posting),
        (cash_second, purchase, second_cash_posting),
        (cash_refund, refund, refund_posting),
        (wallet_item, purchase, wallet_posting),
        (food_purchase, purchase, food_posting),
        (food_refund, refund, refund_offset),
    ):
        assert isinstance(item, TransactionPosting)
        assert item.transaction is transaction
        assert item.posting is posting


def test_pad_and_custom_group_under_each_referenced_account():
    pad = data.Pad({}, DAY, EQUITY, CASH)
    custom = data.Custom(
        {},
        DAY,
        "example",
        [
            CustomValue(EQUITY, ACCOUNT_TYPE),
            CustomValue(FOOD, str),
            CustomValue(WALLET, ACCOUNT_TYPE),
            CustomValue(EQUITY, ACCOUNT_TYPE),
        ],
    )

    result = group_entries_by_account([pad, custom])

    assert list(result) == [CASH, WALLET, EQUITY]
    (cash_pad,) = result[CASH]
    (wallet_custom,) = result[WALLET]
    equity_pad, first_equity_custom, second_equity_custom = result[EQUITY]
    assert cash_pad is equity_pad is pad
    assert wallet_custom is first_equity_custom is second_equity_custom is custom


def test_repeated_directive_is_preserved_and_calls_are_independent():
    opening = data.Open({}, DAY, CASH, ["USD"], None)
    closing = data.Close({}, DAY, CASH)

    first = group_entries_by_account([opening, opening])
    second = group_entries_by_account([closing])

    assert list(first) == list(second) == [CASH]
    first_occurrence, second_occurrence = first[CASH]
    (second_call_entry,) = second[CASH]
    assert first_occurrence is second_occurrence is opening
    assert second_call_entry is closing
