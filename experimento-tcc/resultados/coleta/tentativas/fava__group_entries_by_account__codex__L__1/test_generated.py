from datetime import date
from unittest.mock import Mock, call

import fava.core.group_entries as group_entries_module
from fava.beans import abc
from fava.core.group_entries import TransactionPosting, group_entries_by_account


def test_empty_entries_return_an_empty_dict():
    result = group_entries_by_account(())

    assert type(result) is dict
    assert result == {}


def test_entries_without_accounts_leave_no_groups(monkeypatch):
    event = Mock(spec=abc.Event)
    transaction = Mock(spec=abc.Transaction, postings=[])
    get_accounts = Mock(return_value=set())
    monkeypatch.setattr(group_entries_module, "get_entry_accounts", get_accounts)

    assert group_entries_by_account([transaction, event]) == {}
    get_accounts.assert_called_once_with(event)


def test_groups_directives_and_each_posting_in_input_order(monkeypatch):
    cash = "Assets:Cash"
    wallet = "Assets:Cash:Wallet"
    expenses = "Expenses:Food"

    first_expense = Mock(spec=abc.Posting, account=expenses)
    cash_posting = Mock(spec=abc.Posting, account=cash)
    second_expense = Mock(spec=abc.Posting, account=expenses)
    later_wallet_posting = Mock(spec=abc.Posting, account=wallet)
    later_expense_posting = Mock(spec=abc.Posting, account=expenses)
    first_transaction = Mock(
        spec=abc.Transaction,
        date=date(2024, 2, 1),
        postings=[first_expense, cash_posting, second_expense],
    )
    second_transaction = Mock(
        spec=abc.Transaction,
        date=date(2024, 1, 2),
        postings=[later_wallet_posting, later_expense_posting],
    )
    pad = Mock(spec=abc.Pad, date=date(2024, 1, 1))
    note = Mock(spec=abc.Note, date=date(2024, 1, 3))
    commodity = Mock(spec=abc.Commodity)
    accounts_by_entry = {pad: {expenses, wallet}, note: {cash}, commodity: set()}
    get_accounts = Mock(side_effect=accounts_by_entry.__getitem__)
    monkeypatch.setattr(group_entries_module, "get_entry_accounts", get_accounts)

    result = group_entries_by_account(
        (first_transaction, pad, note, commodity, second_transaction, note)
    )

    assert list(result) == [cash, wallet, expenses]
    assert result == {
        cash: [TransactionPosting(first_transaction, cash_posting), note, note],
        wallet: [pad, TransactionPosting(second_transaction, later_wallet_posting)],
        expenses: [
            TransactionPosting(first_transaction, first_expense),
            TransactionPosting(first_transaction, second_expense),
            pad,
            TransactionPosting(second_transaction, later_expense_posting),
        ],
    }
    assert result[cash][1] is result[cash][2] is note
    assert result[wallet][0] is result[expenses][2] is pad
    for account, index, transaction, posting in (
        (cash, 0, first_transaction, cash_posting),
        (wallet, 1, second_transaction, later_wallet_posting),
        (expenses, 0, first_transaction, first_expense),
        (expenses, 1, first_transaction, second_expense),
        (expenses, 3, second_transaction, later_expense_posting),
    ):
        pair = result[account][index]
        assert isinstance(pair, TransactionPosting)
        assert pair.transaction is transaction
        assert pair.posting is posting

    assert get_accounts.call_args_list == [call(pad), call(note), call(commodity), call(note)]
