"""Referência do piloto (fora da amostra): fava.core.budgets.parse_budgets.

As diretivas `custom` são lidas pelo próprio Beancount a partir de texto; o
esperado é escrito à mão a partir da sintaxe documentada no alvo.
"""
import datetime
from decimal import Decimal

from beancount import loader

from fava.core.budgets import Budget, parse_budgets
from fava.util.date import Month, Week


def _customs(texto):
    entries, _, _ = loader.load_string(texto)
    return [e for e in entries if type(e).__name__ == "Custom"]


def test_orcamento_valido_e_agrupado_pela_conta():
    budgets, errors = parse_budgets(_customs('2015-04-09 custom "budget" Expenses:Books "monthly" 20.00 EUR\n'))
    assert errors == []
    assert dict(budgets) == {"Expenses:Books": [
        Budget("Expenses:Books", datetime.date(2015, 4, 9), Month, Decimal("20.00"), "EUR")]}


def test_varios_orcamentos_da_mesma_conta_ficam_em_ordem():
    texto = ('2015-01-01 custom "budget" Expenses:Food "weekly" 50 EUR\n'
             '2015-02-01 custom "budget" Expenses:Food "monthly" 200 EUR\n')
    budgets, errors = parse_budgets(_customs(texto))
    assert errors == []
    assert [(b.period, b.number) for b in budgets["Expenses:Food"]] == [(Week, Decimal(50)), (Month, Decimal(200))]


def test_intervalo_invalido_gera_erro_e_nenhum_orcamento():
    budgets, errors = parse_budgets(_customs('2015-04-09 custom "budget" Expenses:Books "decadal" 20 EUR\n'))
    assert dict(budgets) == {} and len(errors) == 1


def test_entrada_incompleta_gera_erro():
    budgets, errors = parse_budgets(_customs('2015-04-09 custom "budget" Expenses:Books "monthly"\n'))
    assert dict(budgets) == {} and len(errors) == 1


def test_custom_de_outro_tipo_e_ignorado():
    budgets, errors = parse_budgets(_customs('2015-04-09 custom "fava-option" "locale" "pt"\n'))
    assert dict(budgets) == {} and errors == []
