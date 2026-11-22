"""Referência STD-03: stdnum.es.nif.validate.

Aceitações e rejeições publicadas nos testes do projeto, uma por ramo: início
numérico (DNI), prefixos X/Y/Z (NIE), grupo K/L/M e entidades (CIF). Os
validadores auxiliares originais são mantidos.
"""
import pytest

from stdnum.es import nif
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength, ValidationError


@pytest.mark.parametrize("entrada", ["11111111H", "X1111111G", "L1111111G", "A11111119"])
def test_aceita_um_exemplo_de_cada_ramo(entrada):
    assert nif.validate(entrada) == entrada


@pytest.mark.parametrize("entrada", ["11111111T", "X1111111A", "L1111111C", "A11111118"])
def test_rejeita_a_variante_com_digito_errado_de_cada_ramo(entrada):
    with pytest.raises(ValidationError):
        nif.validate(entrada)


def test_dni_com_letra_errada_e_erro_de_verificacao():
    with pytest.raises(InvalidChecksum):
        nif.validate("11111111T")


def test_nie_com_letra_errada_e_erro_de_verificacao():
    with pytest.raises(InvalidChecksum):
        nif.validate("X1111111A")


def test_grupo_klm_com_letra_errada_e_erro_de_verificacao():
    with pytest.raises(InvalidChecksum):
        nif.validate("L1111111C")


@pytest.mark.parametrize(("entrada", "esperado"), [
    ("ES11111111H", "11111111H"),
    ("es 11111111-h", "11111111H"),
    (" x-1111111-g ", "X1111111G"),
])
def test_prefixo_do_pais_separadores_e_minusculas_sao_normalizados(entrada, esperado):
    assert nif.validate(entrada) == esperado


def test_comprimento_inadequado():
    with pytest.raises(InvalidLength):
        nif.validate("1111111H")


def test_caractere_invalido_no_meio():
    with pytest.raises(InvalidFormat):
        nif.validate("1111111AH")
