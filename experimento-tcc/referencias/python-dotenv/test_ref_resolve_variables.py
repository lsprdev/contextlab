"""Referência DOT-03: dotenv.main.resolve_variables.

O ambiente é controlado com monkeypatch e restaurado ao fim de cada caso. A
função devolve um mapa e não escreve em os.environ; `override` decide se, ao
resolver referências, vale o ambiente do processo ou o valor definido antes.
"""
import os

import pytest

from dotenv.main import resolve_variables


@pytest.fixture
def ambiente(monkeypatch):
    for nome in list(os.environ):
        if nome.startswith("TCCREF_"):
            monkeypatch.delenv(nome)
    return monkeypatch


def test_conflito_entre_ambiente_e_arquivo_com_override_verdadeiro(ambiente):
    ambiente.setenv("TCCREF_A", "ambiente")
    resultado = resolve_variables([("TCCREF_A", "arquivo"), ("TCCREF_B", "${TCCREF_A}")], override=True)
    assert resultado == {"TCCREF_A": "arquivo", "TCCREF_B": "arquivo"}


def test_conflito_entre_ambiente_e_arquivo_com_override_falso(ambiente):
    ambiente.setenv("TCCREF_A", "ambiente")
    resultado = resolve_variables([("TCCREF_A", "arquivo"), ("TCCREF_B", "${TCCREF_A}")], override=False)
    assert resultado == {"TCCREF_A": "arquivo", "TCCREF_B": "ambiente"}


@pytest.mark.parametrize("override", [True, False])
def test_definicao_anterior_e_usada_quando_nao_ha_conflito(ambiente, override):
    resultado = resolve_variables([("TCCREF_A", "1"), ("TCCREF_B", "${TCCREF_A}-x")], override=override)
    assert resultado == {"TCCREF_A": "1", "TCCREF_B": "1-x"}


@pytest.mark.parametrize("override", [True, False])
def test_variavel_do_ambiente_e_usada(ambiente, override):
    ambiente.setenv("TCCREF_HOST", "servidor")
    assert resolve_variables([("TCCREF_URL", "http://${TCCREF_HOST}/")], override=override) == {
        "TCCREF_URL": "http://servidor/"}


@pytest.mark.parametrize("override", [True, False])
def test_variavel_ausente_sem_padrao_vira_vazio(ambiente, override):
    assert resolve_variables([("TCCREF_X", "a${TCCREF_AUSENTE}b")], override=override) == {"TCCREF_X": "ab"}


@pytest.mark.parametrize("override", [True, False])
def test_variavel_ausente_com_padrao_usa_o_padrao(ambiente, override):
    assert resolve_variables([("TCCREF_X", "${TCCREF_AUSENTE:-padrao}")], override=override) == {
        "TCCREF_X": "padrao"}


@pytest.mark.parametrize("override", [True, False])
def test_referencia_repetida(ambiente, override):
    resultado = resolve_variables([("TCCREF_A", "x"), ("TCCREF_B", "${TCCREF_A}${TCCREF_A}")], override=override)
    assert resultado["TCCREF_B"] == "xx"


@pytest.mark.parametrize("override", [True, False])
def test_valor_none_permanece_none(ambiente, override):
    assert resolve_variables([("TCCREF_A", None)], override=override) == {"TCCREF_A": None}


@pytest.mark.parametrize("override", [True, False])
def test_referencia_a_valor_none_vira_vazio(ambiente, override):
    resultado = resolve_variables([("TCCREF_A", None), ("TCCREF_B", "[${TCCREF_A}]")], override=override)
    assert resultado["TCCREF_B"] == "[]"


def test_nao_escreve_em_os_environ(ambiente):
    resolve_variables([("TCCREF_NOVA", "valor")], override=True)
    assert "TCCREF_NOVA" not in os.environ
