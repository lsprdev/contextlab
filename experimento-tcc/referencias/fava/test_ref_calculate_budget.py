"""Referência FAV-01: fava.core.budgets.calculate_budget.

Valores esperados calculados à mão a partir da regra documentada: cada dia do
intervalo [date_from, date_to) recebe a parcela number / dias do período do
orçamento vigente naquele dia, separada por moeda.
"""
import datetime
from decimal import Decimal

from fava.core.budgets import Budget, calculate_budget
from fava.util.date import Day, Month, Week

D = datetime.date


def test_conta_sem_orcamento_retorna_mapa_vazio():
    budgets = {"Expenses:Food": [Budget("Expenses:Food", D(2024, 3, 1), Day, Decimal(10), "EUR")]}
    assert calculate_budget(budgets, "Expenses:Rent", D(2024, 3, 1), D(2024, 3, 3)) == {}


def test_intervalo_vazio_retorna_mapa_vazio():
    budgets = {"Expenses:Food": [Budget("Expenses:Food", D(2024, 3, 1), Day, Decimal(10), "EUR")]}
    assert calculate_budget(budgets, "Expenses:Food", D(2024, 3, 2), D(2024, 3, 2)) == {}


def test_orcamento_diario_exclui_a_data_final():
    budgets = {"Expenses:Food": [Budget("Expenses:Food", D(2024, 3, 1), Day, Decimal(10), "EUR")]}
    # 1 e 2 de março; o dia 3 não entra.
    assert calculate_budget(budgets, "Expenses:Food", D(2024, 3, 1), D(2024, 3, 3)) == {"EUR": Decimal(20)}


def test_orcamento_mensal_de_um_dia_e_a_parcela_diaria():
    budgets = {"Expenses:Food": [Budget("Expenses:Food", D(2024, 3, 1), Month, Decimal(310), "EUR")]}
    # Março tem 31 dias: 310 / 31 = 10.
    assert calculate_budget(budgets, "Expenses:Food", D(2024, 3, 10), D(2024, 3, 11)) == {"EUR": Decimal(10)}


def test_orcamento_mensal_no_mes_inteiro_soma_o_valor_mensal():
    budgets = {"Expenses:Food": [Budget("Expenses:Food", D(2024, 1, 1), Month, Decimal(310), "EUR")]}
    assert calculate_budget(budgets, "Expenses:Food", D(2024, 3, 1), D(2024, 4, 1)) == {"EUR": Decimal(310)}


def test_fevereiro_de_ano_bissexto_tem_29_dias():
    budgets = {"Expenses:Food": [Budget("Expenses:Food", D(2024, 1, 1), Month, Decimal(290), "EUR")]}
    assert calculate_budget(budgets, "Expenses:Food", D(2024, 2, 5), D(2024, 2, 6)) == {"EUR": Decimal(10)}


def test_fevereiro_de_ano_comum_tem_28_dias():
    budgets = {"Expenses:Food": [Budget("Expenses:Food", D(2023, 1, 1), Month, Decimal(280), "EUR")]}
    assert calculate_budget(budgets, "Expenses:Food", D(2023, 2, 5), D(2023, 2, 6)) == {"EUR": Decimal(10)}


def test_orcamento_semanal_divide_por_sete():
    budgets = {"Expenses:Food": [Budget("Expenses:Food", D(2024, 3, 1), Week, Decimal(70), "EUR")]}
    assert calculate_budget(budgets, "Expenses:Food", D(2024, 3, 4), D(2024, 3, 7)) == {"EUR": Decimal(30)}


def test_mudanca_de_vigencia_no_meio_do_intervalo():
    budgets = {"Expenses:Food": [
        Budget("Expenses:Food", D(2024, 3, 1), Day, Decimal(10), "EUR"),
        Budget("Expenses:Food", D(2024, 3, 3), Day, Decimal(20), "EUR"),
    ]}
    # Dias 1 e 2 a 10; dias 3 e 4 a 20.
    assert calculate_budget(budgets, "Expenses:Food", D(2024, 3, 1), D(2024, 3, 5)) == {"EUR": Decimal(60)}


def test_orcamento_que_comeca_depois_do_intervalo_nao_conta():
    budgets = {"Expenses:Food": [Budget("Expenses:Food", D(2024, 3, 10), Day, Decimal(10), "EUR")]}
    assert calculate_budget(budgets, "Expenses:Food", D(2024, 3, 1), D(2024, 3, 5)) == {}


def test_moedas_sao_somadas_separadamente():
    budgets = {"Expenses:Food": [
        Budget("Expenses:Food", D(2024, 3, 1), Day, Decimal(10), "EUR"),
        Budget("Expenses:Food", D(2024, 3, 1), Day, Decimal(5), "USD"),
    ]}
    assert calculate_budget(budgets, "Expenses:Food", D(2024, 3, 1), D(2024, 3, 3)) == {
        "EUR": Decimal(20), "USD": Decimal(10)}
