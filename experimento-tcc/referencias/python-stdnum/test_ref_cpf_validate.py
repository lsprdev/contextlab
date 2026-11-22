"""Referência STD-01: stdnum.br.cpf.validate.

O exemplo publicado 390.533.447-05 é conferido com um cálculo independente dos
dígitos verificadores (módulo 11, pesos 10..2 e 11..2), sem usar o auxiliar do
alvo. Cada caso de rejeição isola uma única causa.
"""
import pytest

from stdnum.br import cpf
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


def _digitos(base9):
    d1 = (11 - sum((10 - i) * int(c) for i, c in enumerate(base9))) % 11 % 10
    d2 = (11 - sum((11 - i) * int(c) for i, c in enumerate(base9 + str(d1)))) % 11 % 10
    return f"{d1}{d2}"


def test_calculo_independente_confere_o_exemplo_publicado():
    assert _digitos("390533447") == "05"


def test_exemplo_publicado_e_normalizado():
    assert cpf.validate("390.533.447-05") == "39053344705"


@pytest.mark.parametrize("entrada", ["39053344705", "390 533 447 05", " 390-533-447.05 "])
def test_separadores_permitidos(entrada):
    assert cpf.validate(entrada) == "39053344705"


def test_outro_cpf_com_digitos_calculados():
    base = "123456789"
    assert cpf.validate(base + _digitos(base)) == base + _digitos(base)


def test_digito_verificador_errado():
    with pytest.raises(InvalidChecksum):
        cpf.validate("390.533.447-06")


def test_primeiro_digito_verificador_errado():
    with pytest.raises(InvalidChecksum):
        cpf.validate("390.533.447-15")


def test_comprimento_inadequado():
    with pytest.raises(InvalidLength):
        cpf.validate("3905334470")


def test_caractere_nao_numerico():
    with pytest.raises(InvalidFormat):
        cpf.validate("3905334470A")


def test_separador_nao_permitido():
    with pytest.raises(InvalidFormat):
        cpf.validate("390/533/447-05")


def test_numero_zerado():
    with pytest.raises(InvalidFormat):
        cpf.validate("000.000.000-00")
