from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from fava.beans import abc
from fava.beans.account import ACCOUNT_TYPE
from fava.core.group_entries import TransactionPosting, group_entries_by_account


class LedgerTransaction(abc.Transaction):
    flag = '*'
    payee = ''
    narration = 'Transfer'
    tags = frozenset()
    links = frozenset()
    postings = ()
    date = date(2024, 1, 1)
    meta = None

    def __init__(self, *postings, entry_date=date(2024, 1, 1)):
        self.postings = postings
        self.date = entry_date
        self.meta = {}


def assert_posting_pair(row, transaction, posting):
    assert isinstance(row, TransactionPosting)
    assert row.transaction is transaction
    assert row.posting is posting


def test_sorts_account_keys_and_preserves_entry_and_posting_order():
    wallet = 'Assets:Wallet'
    savings = 'Assets:Savings'
    expenses = 'Expenses:Food'
    opening = Mock(spec=abc.Open, account=wallet, date=date(2024, 1, 5))
    closing = Mock(spec=abc.Close, account=wallet, date=date(2024, 1, 2))
    first_wallet = SimpleNamespace(account=wallet, units=-25)
    second_wallet = SimpleNamespace(account=wallet, units=-25)
    food = SimpleNamespace(account=expenses, units=50)
    first = LedgerTransaction(first_wallet, food, second_wallet, entry_date=date(2024, 1, 4))
    savings_posting = SimpleNamespace(account=savings, units=10)
    last_wallet = SimpleNamespace(account=wallet, units=-10)
    second = LedgerTransaction(savings_posting, last_wallet, entry_date=date(2024, 1, 3))

    grouped = group_entries_by_account((opening, first, second, closing))

    assert list(grouped) == [savings, wallet, expenses]
    before, first_row, second_row, third_row, after = grouped[wallet]
    assert before is opening
    assert_posting_pair(first_row, first, first_wallet)
    assert_posting_pair(second_row, first, second_wallet)
    assert_posting_pair(third_row, second, last_wallet)
    assert after is closing
    savings_row, = grouped[savings]
    assert_posting_pair(savings_row, second, savings_posting)
    food_row, = grouped[expenses]
    assert_posting_pair(food_row, first, food)


def test_groups_pad_under_both_accounts_and_keeps_each_custom_account_occurrence():
    cash = 'Assets:Cash'
    source = 'Equity:Opening-Balances'
    reserve = 'Assets:Cash:Reserve'
    pad = Mock(spec=abc.Pad, account=cash, source_account=source)
    custom = Mock(
        spec=abc.Custom,
        values=[
            SimpleNamespace(value=reserve, dtype=ACCOUNT_TYPE),
            SimpleNamespace(value='Assets:Ignored', dtype=str),
            SimpleNamespace(value=cash, dtype=ACCOUNT_TYPE),
            SimpleNamespace(value=reserve, dtype=ACCOUNT_TYPE),
        ],
    )
    balance = Mock(spec=abc.Balance, account=cash)

    grouped = group_entries_by_account([pad, custom, balance])

    assert list(grouped) == [cash, reserve, source]
    cash_pad, cash_custom, cash_balance = grouped[cash]
    assert cash_pad is pad
    assert cash_custom is custom
    assert cash_balance is balance
    first_reserve, second_reserve = grouped[reserve]
    assert first_reserve is custom
    assert second_reserve is custom
    source_pad, = grouped[source]
    assert source_pad is pad


def test_ignores_accountless_directives_and_transactions_without_postings():
    event = Mock(spec=abc.Event)
    commodity = Mock(spec=abc.Commodity)
    custom = Mock(spec=abc.Custom, values=[SimpleNamespace(value='Assets:Cash', dtype=str)])

    assert group_entries_by_account([event, LedgerTransaction(), commodity, custom]) == {}


def test_empty_input_returns_a_dict_without_default_buckets():
    grouped = group_entries_by_account([])

    assert isinstance(grouped, dict)
    assert grouped == {}
    with pytest.raises(KeyError):
        grouped['Assets:Missing']
    assert grouped == {}


def test_repeated_transaction_occurrences_are_grouped_on_each_call():
    account = 'Assets:Cash'
    posting = SimpleNamespace(account=account, units=0)
    transaction = LedgerTransaction(posting)
    entries = [transaction, transaction]

    first = group_entries_by_account(entries)
    second = group_entries_by_account(entries)

    assert first is not second
    assert first[account] is not second[account]
    for grouped in (first, second):
        assert list(grouped) == [account]
        first_row, second_row = grouped[account]
        assert_posting_pair(first_row, transaction, posting)
        assert_posting_pair(second_row, transaction, posting)
