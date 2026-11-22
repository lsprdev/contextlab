from unittest.mock import Mock

import pytest

from fava.beans import abc
from fava.core import group_entries
from fava.core.group_entries import TransactionPosting, group_entries_by_account


def test_empty_input_returns_empty_dict():
    grouped = group_entries_by_account([])

    assert isinstance(grouped, dict)
    assert grouped == {}


def test_entries_without_accounts_do_not_create_groups(monkeypatch):
    commodity = Mock(spec=abc.Commodity)
    transaction = Mock(spec=abc.Transaction, postings=[])
    get_accounts = Mock(return_value=set())
    monkeypatch.setattr(group_entries, 'get_entry_accounts', get_accounts)

    assert group_entries_by_account([commodity, transaction]) == {}
    get_accounts.assert_called_once_with(commodity)


def test_transactions_preserve_each_posting_and_its_parent():
    cash = 'Assets:Cash'
    food = 'Expenses:Food'
    food_posting = Mock(spec=abc.Posting, account=food)
    cash_posting = Mock(spec=abc.Posting, account=cash)
    other_food_posting = Mock(spec=abc.Posting, account=food)
    later_food_posting = Mock(spec=abc.Posting, account=food)
    first = Mock(
        spec=abc.Transaction,
        postings=[food_posting, cash_posting, other_food_posting, food_posting],
    )
    second = Mock(spec=abc.Transaction, postings=[later_food_posting])

    grouped = group_entries_by_account([first, second])

    assert list(grouped) == [cash, food]
    expected = {
        cash: [(first, cash_posting)],
        food: [
            (first, food_posting),
            (first, other_food_posting),
            (first, food_posting),
            (second, later_food_posting),
        ],
    }
    for account, pairs in expected.items():
        assert len(grouped[account]) == len(pairs)
        for item, (transaction, posting) in zip(grouped[account], pairs, strict=True):
            assert isinstance(item, TransactionPosting)
            assert item.transaction is transaction
            assert item.posting is posting


def test_mixed_entries_keep_input_order_in_each_sorted_account_group(monkeypatch):
    bank = 'Assets:Bank'
    checking = 'Assets:Bank:Checking'
    equity = 'Equity:Opening-Balances'
    opened = Mock(spec=abc.Open, account=checking)
    pad = Mock(spec=abc.Pad, account=checking, source_account=equity)
    closed = Mock(spec=abc.Close, account=bank)
    posting = Mock(spec=abc.Posting, account=checking)
    transaction = Mock(spec=abc.Transaction, postings=[posting])
    accounts = {opened: {checking}, pad: {checking, equity}, closed: {bank}}
    monkeypatch.setattr(group_entries, 'get_entry_accounts', accounts.__getitem__)

    grouped = group_entries_by_account((opened, transaction, pad, closed, opened))

    assert list(grouped) == [bank, checking, equity]
    assert grouped == {
        bank: [closed],
        checking: [opened, TransactionPosting(transaction, posting), pad, opened],
        equity: [pad],
    }
    assert grouped[checking][2] is pad
    assert grouped[equity][0] is pad
    with pytest.raises(KeyError):
        grouped['Assets:Missing']
