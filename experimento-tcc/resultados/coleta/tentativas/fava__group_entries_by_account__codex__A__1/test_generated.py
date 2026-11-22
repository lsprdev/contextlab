from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from beancount.core import data
from beancount.core.account import TYPE as ACCOUNT_TYPE
from beancount.core.amount import Amount

from fava.core.group_entries import TransactionPosting, group_entries_by_account


ENTRY_DATE = date(2024, 6, 15)


def make_posting(account, units):
    return data.Posting(account, Amount(Decimal(units), 'USD'), None, None, None, None)


def make_transaction(narration, postings, *, entry_date=ENTRY_DATE):
    return data.Transaction({}, entry_date, '*', None, narration, frozenset(), frozenset(), postings)


def test_empty_input_returns_empty_dict():
    result = group_entries_by_account([])

    assert isinstance(result, dict)
    assert result == {}
    with pytest.raises(KeyError):
        result['Assets:Missing']
    assert not result


def test_entries_without_accounts_create_no_groups():
    entries = (
        data.Event({}, ENTRY_DATE, 'location', 'Home'),
        data.Commodity({}, ENTRY_DATE, 'USD'),
        data.Custom({}, ENTRY_DATE, 'description', [
            SimpleNamespace(value='Assets:Cash', dtype=str),
        ]),
        make_transaction('No postings', []),
    )

    assert group_entries_by_account(entries) == {}


def test_groups_postings_and_directives_in_input_order_under_sorted_account_keys():
    cash = 'Assets:Cash'
    wallet = 'Assets:Cash:Wallet'
    income = 'Income:Salary'
    income_posting = make_posting(income, '-30')
    first_cash = make_posting(cash, '20')
    second_cash = make_posting(cash, '10')
    first_transaction = make_transaction('First in input', [income_posting, first_cash, second_cash])
    open_wallet = data.Open({}, ENTRY_DATE, wallet, None, None)
    close_cash = data.Close({}, date(2024, 6, 1), cash)
    wallet_posting = make_posting(wallet, '-5')
    third_cash = make_posting(cash, '5')
    second_transaction = make_transaction(
        'Second in input', [wallet_posting, third_cash], entry_date=date(2024, 5, 1)
    )
    event = data.Event({}, ENTRY_DATE, 'location', 'Home')
    entries = (first_transaction, open_wallet, event, close_cash, second_transaction)

    result = group_entries_by_account(entries)

    assert list(result) == [cash, wallet, income]
    assert result == {
        cash: [
            TransactionPosting(first_transaction, first_cash),
            TransactionPosting(first_transaction, second_cash),
            close_cash,
            TransactionPosting(second_transaction, third_cash),
        ],
        wallet: [open_wallet, TransactionPosting(second_transaction, wallet_posting)],
        income: [TransactionPosting(first_transaction, income_posting)],
    }
    assert result[cash][2] is close_cash
    assert result[wallet][0] is open_wallet
    for grouped, transaction, posting in (
        (result[cash][0], first_transaction, first_cash),
        (result[cash][1], first_transaction, second_cash),
        (result[cash][3], second_transaction, third_cash),
        (result[wallet][1], second_transaction, wallet_posting),
        (result[income][0], first_transaction, income_posting),
    ):
        assert isinstance(grouped, TransactionPosting)
        assert grouped.transaction is transaction
        assert grouped.posting is posting


def test_pad_and_custom_directives_contribute_once_per_account_occurrence():
    cash = 'Assets:Cash'
    savings = 'Assets:Savings'
    opening_balances = 'Equity:Opening-Balances'
    pad = data.Pad({}, ENTRY_DATE, cash, opening_balances)
    custom = data.Custom({}, ENTRY_DATE, 'allocation', [
        SimpleNamespace(value=savings, dtype=ACCOUNT_TYPE),
        SimpleNamespace(value='Assets:Ignored', dtype=str),
        SimpleNamespace(value=cash, dtype=ACCOUNT_TYPE),
        SimpleNamespace(value=savings, dtype=ACCOUNT_TYPE),
    ])
    same_account_pad = data.Pad({}, ENTRY_DATE, cash, cash)

    result = group_entries_by_account([pad, custom, same_account_pad])

    assert list(result) == [cash, savings, opening_balances]
    assert result == {
        cash: [pad, custom, same_account_pad, same_account_pad],
        savings: [custom, custom],
        opening_balances: [pad],
    }
    assert result[opening_balances][0] is pad
    assert all(entry is custom for entry in result[savings])


def test_repeated_input_entries_are_kept_and_calls_have_independent_groups():
    account = 'Assets:Cash'
    posting = make_posting(account, '1')
    transaction = make_transaction('Repeated transaction', [posting])
    opened = data.Open({}, ENTRY_DATE, account, None, None)
    closed = data.Close({}, ENTRY_DATE, account)

    first_result = group_entries_by_account([opened, transaction, opened, transaction])
    second_result = group_entries_by_account([closed])

    assert first_result == {
        account: [opened, TransactionPosting(transaction, posting), opened, TransactionPosting(transaction, posting)],
    }
    assert second_result == {account: [closed]}
