from datetime import date
from unittest.mock import Mock

import pytest

from fava.beans import abc
from fava.core.group_entries import TransactionPosting, group_entries_by_account


def assert_posting_pair(pair, transaction, posting):
    assert isinstance(pair, TransactionPosting)
    assert pair.transaction is transaction
    assert pair.posting is posting


def test_empty_entries_return_an_empty_mapping():
    assert group_entries_by_account([]) == {}


def test_transaction_without_postings_adds_no_accounts():
    transaction = Mock(spec=abc.Transaction, postings=[])

    assert group_entries_by_account([transaction]) == {}


def test_groups_every_posting_in_input_order_under_its_full_account_name():
    first_cash = Mock(spec=abc.Posting, account="Assets:Cash")
    income = Mock(spec=abc.Posting, account="Income:Salary")
    second_cash = Mock(spec=abc.Posting, account="Assets:Cash")
    cash_reserve = Mock(spec=abc.Posting, account="Assets:Cash:Reserve")
    third_cash = Mock(spec=abc.Posting, account="Assets:Cash")
    first = Mock(
        spec=abc.Transaction,
        date=date(2024, 2, 1),
        postings=[income, first_cash, cash_reserve, second_cash],
    )
    second = Mock(
        spec=abc.Transaction,
        date=date(2024, 1, 1),
        postings=[third_cash],
    )

    grouped = group_entries_by_account([first, second, first])

    assert list(grouped) == ["Assets:Cash", "Assets:Cash:Reserve", "Income:Salary"]
    cash = grouped["Assets:Cash"]
    assert len(cash) == 5
    assert_posting_pair(cash[0], first, first_cash)
    assert_posting_pair(cash[1], first, second_cash)
    assert_posting_pair(cash[2], second, third_cash)
    assert_posting_pair(cash[3], first, first_cash)
    assert_posting_pair(cash[4], first, second_cash)

    for account, posting in [("Assets:Cash:Reserve", cash_reserve), ("Income:Salary", income)]:
        first_pair, repeated_pair = grouped[account]
        assert_posting_pair(first_pair, first, posting)
        assert_posting_pair(repeated_pair, first, posting)


def test_interleaves_directives_and_postings_for_each_account(monkeypatch):
    cash = "Assets:Cash"
    equity = "Equity:Opening-Balances"
    opening = Mock(spec=abc.Open, account=cash)
    pad = Mock(spec=abc.Pad, account=cash, source_account=equity)
    event = Mock(spec=abc.Event)
    closing = Mock(spec=abc.Close, account=cash)
    posting = Mock(spec=abc.Posting, account=cash)
    transaction = Mock(spec=abc.Transaction, postings=[posting])
    accounts_by_entry = {
        opening: (cash,),
        pad: (equity, cash),
        event: (),
        closing: (cash,),
    }
    monkeypatch.setattr(
        "fava.core.group_entries.get_entry_accounts", accounts_by_entry.__getitem__
    )

    grouped = group_entries_by_account((pad, opening, event, transaction, pad, closing))

    assert list(grouped) == [cash, equity]
    first_pad, first_open, pair, second_pad, last_close = grouped[cash]
    assert first_pad is pad
    assert first_open is opening
    assert_posting_pair(pair, transaction, posting)
    assert second_pad is pad
    assert last_close is closing
    first_source_pad, second_source_pad = grouped[equity]
    assert first_source_pad is pad
    assert second_source_pad is pad
    with pytest.raises(KeyError):
        grouped["Assets:Missing"]
