from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

from fava.beans import abc
from fava.beans.account import ACCOUNT_TYPE
from fava.core.group_entries import TransactionPosting, group_entries_by_account


def test_empty_input_returns_an_empty_dict():
    grouped = group_entries_by_account([])

    assert type(grouped) is dict
    assert grouped == {}


def test_entries_without_accounts_create_no_groups():
    commodity = Mock(spec=abc.Commodity, currency="USD")
    event = Mock(spec=abc.Event)
    empty_transaction = Mock(spec=abc.Transaction, postings=[])
    custom = Mock(
        spec=abc.Custom,
        values=[SimpleNamespace(dtype=str, value="Assets:LooksLikeAnAccount")],
    )

    assert group_entries_by_account((commodity, event, empty_transaction, custom)) == {}


def test_transaction_postings_preserve_order_multiplicity_and_identity():
    first_food = Mock(spec=abc.Posting, account="Expenses:Food")
    checking = Mock(spec=abc.Posting, account="Assets:Checking")
    second_food = Mock(spec=abc.Posting, account="Expenses:Food")
    third_food = Mock(spec=abc.Posting, account="Expenses:Food")
    first_transaction = Mock(
        spec=abc.Transaction,
        date=date(2024, 6, 2),
        postings=[first_food, checking, second_food, first_food],
    )
    second_transaction = Mock(
        spec=abc.Transaction,
        date=date(2024, 6, 1),
        postings=[third_food],
    )

    grouped = group_entries_by_account((first_transaction, second_transaction))

    assert list(grouped) == ["Assets:Checking", "Expenses:Food"]
    assert len(grouped["Assets:Checking"]) == 1
    checking_pair = grouped["Assets:Checking"][0]
    assert isinstance(checking_pair, TransactionPosting)
    assert checking_pair.transaction is first_transaction
    assert checking_pair.posting is checking

    expected_food_pairs = [
        (first_transaction, first_food),
        (first_transaction, second_food),
        (first_transaction, first_food),
        (second_transaction, third_food),
    ]
    for pair, (transaction, posting) in zip(
        grouped["Expenses:Food"], expected_food_pairs, strict=True
    ):
        assert isinstance(pair, TransactionPosting)
        assert pair.transaction is transaction
        assert pair.posting is posting


def test_directives_and_postings_share_groups_in_input_order():
    cash = "Assets:Cash"
    equity = "Equity:Opening-Balances"
    food = "Expenses:Food"
    opening = Mock(spec=abc.Open, account=cash)
    padding = Mock(spec=abc.Pad, account=cash, source_account=equity)
    cash_posting = Mock(spec=abc.Posting, account=cash)
    food_posting = Mock(spec=abc.Posting, account=food)
    transaction = Mock(spec=abc.Transaction, postings=[cash_posting, food_posting])
    note = Mock(spec=abc.Note, account=equity)
    custom = Mock(
        spec=abc.Custom,
        values=[
            SimpleNamespace(dtype=ACCOUNT_TYPE, value=food),
            SimpleNamespace(dtype=str, value="Liabilities:Ignored"),
            SimpleNamespace(dtype=ACCOUNT_TYPE, value=cash),
            SimpleNamespace(dtype=ACCOUNT_TYPE, value=food),
        ],
    )
    closing = Mock(spec=abc.Close, account=cash)

    grouped = group_entries_by_account(
        [opening, padding, transaction, note, custom, closing]
    )

    expected = {
        cash: [opening, padding, TransactionPosting(transaction, cash_posting), custom, closing],
        equity: [padding, note],
        food: [TransactionPosting(transaction, food_posting), custom, custom],
    }
    assert grouped == expected
    assert grouped[cash][1] is grouped[equity][0] is padding
    assert grouped[cash][3] is grouped[food][1] is grouped[food][2] is custom


def test_account_keys_are_sorted_lexicographically_without_grouping_subaccounts():
    account_names = ["Assets:Wallet2", "Assets:Wallet:Cash", "Assets:Wallet10", "Assets:Wallet"]
    entries = [Mock(spec=abc.Open, account=account) for account in account_names]

    grouped = group_entries_by_account(entries)

    assert list(grouped) == [
        "Assets:Wallet",
        "Assets:Wallet10",
        "Assets:Wallet2",
        "Assets:Wallet:Cash",
    ]
    assert grouped == {account: [entry] for account, entry in zip(account_names, entries, strict=True)}


def test_calls_keep_separate_groups_for_the_same_account():
    account = "Assets:Cash"
    opening = Mock(spec=abc.Open, account=account)
    note = Mock(spec=abc.Note, account=account)

    first = group_entries_by_account([opening, opening])
    second = group_entries_by_account([note])

    assert first == {account: [opening, opening]}
    assert second == {account: [note]}
    assert first[account] is not second[account]
