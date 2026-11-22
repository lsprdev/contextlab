from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from fava.beans import abc
from fava.beans.account import ACCOUNT_TYPE
from fava.core.group_entries import TransactionPosting, group_entries_by_account


@dataclass(frozen=True)
class Posting:
    account: str


class LedgerTransaction(abc.Transaction):
    date = date(2024, 1, 1)
    meta = None
    flag = '*'
    payee = 'Store'
    narration = 'Purchase'
    postings = ()
    tags = frozenset()
    links = frozenset()

    def __init__(self, *postings):
        self.postings = postings


def test_groups_mixed_entries_in_input_and_posting_order():
    upper = 'Assets:Wallet:EUR'
    lower = 'Assets:Wallet:Eur'
    liability = 'Liabilities:Card'
    opening = Mock(spec=abc.Open, account=liability, date=date(2024, 1, 3))
    closing = Mock(spec=abc.Close, account=liability, date=date(2024, 1, 2))
    note = Mock(spec=abc.Note, account=upper, date=date(2024, 1, 4))
    first_card = Posting(liability)
    second_card = Posting(liability)
    lower_posting = Posting(lower)
    upper_posting = Posting(upper)
    last_card = Posting(liability)
    first = LedgerTransaction(first_card, lower_posting, second_card, upper_posting)
    second = LedgerTransaction(last_card)

    grouped = group_entries_by_account((opening, first, closing, note, second, first))

    assert list(grouped) == [upper, lower, liability]
    assert grouped == {
        upper: [TransactionPosting(first, upper_posting), note, TransactionPosting(first, upper_posting)],
        lower: [TransactionPosting(first, lower_posting), TransactionPosting(first, lower_posting)],
        liability: [
            opening,
            TransactionPosting(first, first_card),
            TransactionPosting(first, second_card),
            closing,
            TransactionPosting(second, last_card),
            TransactionPosting(first, first_card),
            TransactionPosting(first, second_card),
        ],
    }
    card_entries = grouped[liability]
    assert card_entries[0] is opening
    assert card_entries[3] is closing
    assert grouped[upper][1] is note
    for index, transaction, posting in (
        (1, first, first_card),
        (2, first, second_card),
        (4, second, last_card),
        (5, first, first_card),
        (6, first, second_card),
    ):
        item = card_entries[index]
        assert isinstance(item, TransactionPosting)
        assert item.transaction is transaction
        assert item.posting is posting
    for account, posting, indices in (
        (upper, upper_posting, (0, 2)),
        (lower, lower_posting, (0, 1)),
    ):
        for index in indices:
            item = grouped[account][index]
            assert isinstance(item, TransactionPosting)
            assert item.transaction is first
            assert item.posting is posting


def test_groups_pad_and_custom_under_each_account_occurrence():
    target = 'Assets:Cash'
    source = 'Equity:Opening-Balances'
    pad = Mock(spec=abc.Pad, account=target, source_account=source)
    custom = Mock(
        spec=abc.Custom,
        values=[
            SimpleNamespace(value=source, dtype=ACCOUNT_TYPE),
            SimpleNamespace(value='Assets:Ordinary-Text', dtype=str),
            SimpleNamespace(value=target, dtype=ACCOUNT_TYPE),
            SimpleNamespace(value=target, dtype=ACCOUNT_TYPE),
        ],
    )
    same_account_pad = Mock(spec=abc.Pad, account=source, source_account=source)

    grouped = group_entries_by_account([pad, custom, same_account_pad, pad])

    assert list(grouped) == [target, source]
    assert grouped == {
        target: [pad, custom, custom, pad],
        source: [pad, custom, same_account_pad, same_account_pad, pad],
    }
    assert all(item is custom for item in grouped[target][1:3])
    assert all(item is same_account_pad for item in grouped[source][2:4])


def test_empty_input_and_entries_without_accounts_produce_no_groups():
    event = Mock(spec=abc.Event)
    custom = Mock(spec=abc.Custom, values=[SimpleNamespace(value=42, dtype=int)])

    assert group_entries_by_account([]) == {}
    assert group_entries_by_account([event, LedgerTransaction(), custom]) == {}


def test_missing_account_raises_and_calls_have_independent_groups():
    account = 'Assets:Cash'
    entry = Mock(spec=abc.Open, account=account)
    first = group_entries_by_account([entry])
    second = group_entries_by_account([entry])

    with pytest.raises(KeyError):
        first['Assets:Missing']

    assert list(first) == [account]
    assert first == second == {account: [entry]}
    assert first is not second
    assert first[account] is not second[account]
