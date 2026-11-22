"""Referência FAV-02: fava.core.group_entries.group_entries_by_account.

O mapa esperado é escrito à mão, conta por conta; o alvo não é usado para
produzir a expectativa.
"""
import datetime

from beancount.core import data

from fava.beans import create
from fava.core.group_entries import TransactionPosting, group_entries_by_account

D = datetime.date(2024, 3, 1)


def _transacao(*contas_valores):
    postings = [create.posting(conta, valor) for conta, valor in contas_valores]
    return create.transaction({}, D, "*", "loja", "compra", postings=postings)


def test_lista_vazia_retorna_mapa_vazio():
    assert group_entries_by_account([]) == {}


def test_transacao_aparece_em_cada_conta_como_par_transacao_lancamento():
    txn = _transacao(("Assets:Cash", "-10 EUR"), ("Expenses:Food", "10 EUR"))
    result = group_entries_by_account([txn])
    assert result == {
        "Assets:Cash": [TransactionPosting(txn, txn.postings[0])],
        "Expenses:Food": [TransactionPosting(txn, txn.postings[1])],
    }
    item = result["Expenses:Food"][0]
    assert item.transaction is txn
    assert item.posting.account == "Expenses:Food"


def test_dois_lancamentos_na_mesma_conta_geram_dois_pares():
    txn = _transacao(("Assets:Cash", "-4 EUR"), ("Assets:Cash", "-6 EUR"), ("Expenses:Food", "10 EUR"))
    result = group_entries_by_account([txn])
    assert result["Assets:Cash"] == [TransactionPosting(txn, txn.postings[0]),
                                     TransactionPosting(txn, txn.postings[1])]


def test_diretivas_que_nao_sao_transacao_entram_como_a_propria_diretiva():
    abertura = create.open({}, D, "Assets:Bank", ["EUR"])
    nota = create.note({}, D, "Assets:Bank", "conferido")
    saldo = create.balance({}, D, "Assets:Bank", "100 EUR")
    assert group_entries_by_account([abertura, nota, saldo]) == {"Assets:Bank": [abertura, nota, saldo]}


def test_pad_aparece_na_conta_e_na_conta_de_origem():
    pad = data.Pad({}, D, "Assets:Bank", "Equity:Opening-Balances")
    assert group_entries_by_account([pad]) == {"Assets:Bank": [pad], "Equity:Opening-Balances": [pad]}


def test_diretiva_sem_conta_nao_aparece():
    preco = data.Price({}, D, "EUR", create.amount("1.10 USD"))
    assert group_entries_by_account([preco]) == {}


def test_chaves_ficam_em_ordem_alfabetica():
    entradas = [create.open({}, D, conta, ["EUR"]) for conta in ("Income:Salary", "Assets:Bank", "Expenses:Food")]
    assert list(group_entries_by_account(entradas)) == ["Assets:Bank", "Expenses:Food", "Income:Salary"]


def test_ordem_das_diretivas_de_cada_conta_segue_a_entrada():
    nota_b = create.note({}, D, "Assets:Bank", "segunda")
    nota_a = create.note({}, D, "Assets:Bank", "primeira")
    txn = _transacao(("Assets:Bank", "-10 EUR"), ("Expenses:Food", "10 EUR"))
    assert group_entries_by_account([nota_b, txn, nota_a])["Assets:Bank"] == [
        nota_b, TransactionPosting(txn, txn.postings[0]), nota_a]
