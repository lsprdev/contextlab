"""Referência FAV-03: fava.core.file.find_insert_position.

Opções e diretivas construídas à mão; o esperado é deduzido das regras: só
valem opções com data anterior à da diretiva, a mais recente primeiro, a
expressão casa com `match` no início do nome e, em transações, as contas são
consideradas na ordem inversa dos lançamentos.
"""
import datetime
import re

from fava.beans import create
from fava.core.fava_options import InsertEntryOption
from fava.core.file import find_insert_position

D = datetime.date


def _opcao(data, padrao, arquivo, linha):
    return InsertEntryOption(data, re.compile(padrao), arquivo, linha)


def _transacao(data, *contas):
    postings = [create.posting(conta, f"{(-1) ** i * 10} EUR") for i, conta in enumerate(contas)]
    return create.transaction({}, data, "*", "loja", "compra", postings=postings)


def _nota(data, conta):
    return create.note({}, data, conta, "nota")


def test_sem_opcoes_usa_arquivo_padrao():
    assert find_insert_position(_nota(D(2024, 3, 10), "Expenses:Food"), [], "main.beancount") == ("main.beancount", None)


def test_opcao_nao_aplicavel_usa_arquivo_padrao():
    opcoes = [_opcao(D(2024, 3, 1), "Income:", "renda.beancount", 5)]
    assert find_insert_position(_nota(D(2024, 3, 10), "Expenses:Food"), opcoes, "main.beancount") == ("main.beancount", None)


def test_opcao_anterior_que_casa_retorna_arquivo_e_linha_anterior():
    opcoes = [_opcao(D(2024, 3, 1), "Expenses:Food", "gastos.beancount", 12)]
    assert find_insert_position(_nota(D(2024, 3, 10), "Expenses:Food"), opcoes, "main.beancount") == ("gastos.beancount", 11)


def test_opcao_com_mesma_data_da_diretiva_e_ignorada():
    opcoes = [_opcao(D(2024, 3, 10), "Expenses:Food", "gastos.beancount", 12)]
    assert find_insert_position(_nota(D(2024, 3, 10), "Expenses:Food"), opcoes, "main.beancount") == ("main.beancount", None)


def test_opcao_posterior_a_diretiva_e_ignorada():
    opcoes = [_opcao(D(2024, 3, 20), "Expenses:Food", "gastos.beancount", 12)]
    assert find_insert_position(_nota(D(2024, 3, 10), "Expenses:Food"), opcoes, "main.beancount") == ("main.beancount", None)


def test_entre_duas_opcoes_vale_a_mais_recente_em_qualquer_ordem():
    antiga = _opcao(D(2024, 1, 1), "Expenses:", "antigo.beancount", 3)
    recente = _opcao(D(2024, 3, 1), "Expenses:", "recente.beancount", 8)
    nota = _nota(D(2024, 3, 10), "Expenses:Food")
    assert find_insert_position(nota, [antiga, recente], "main.beancount") == ("recente.beancount", 7)
    assert find_insert_position(nota, [recente, antiga], "main.beancount") == ("recente.beancount", 7)


def test_expressao_e_ancorada_no_inicio_do_nome():
    opcoes = [_opcao(D(2024, 3, 1), "Food", "comida.beancount", 4)]
    assert find_insert_position(_nota(D(2024, 3, 10), "Expenses:Food"), opcoes, "main.beancount") == ("main.beancount", None)


def test_transacao_considera_a_ultima_conta_primeiro():
    txn = _transacao(D(2024, 3, 10), "Assets:Cash", "Expenses:Food")
    opcoes = [_opcao(D(2024, 3, 1), "Assets:", "ativos.beancount", 20),
              _opcao(D(2024, 2, 1), "Expenses:", "gastos.beancount", 30)]
    assert find_insert_position(txn, opcoes, "main.beancount") == ("gastos.beancount", 29)


def test_prioridade_da_conta_prevalece_sobre_a_data_da_opcao():
    txn = _transacao(D(2024, 3, 10), "Assets:Cash", "Expenses:Food")
    # A opção de Assets é mais recente, mas Expenses:Food vem primeiro na ordem inversa.
    opcoes = [_opcao(D(2024, 3, 5), "Assets:", "ativos.beancount", 20),
              _opcao(D(2024, 1, 1), "Expenses:", "gastos.beancount", 30)]
    assert find_insert_position(txn, opcoes, "main.beancount") == ("gastos.beancount", 29)
