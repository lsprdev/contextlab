"""Referência do piloto (fora da amostra): stdnum.br.cnpj.validate.

Exemplo publicado no módulo: 16.727.230/0001-97.
"""
import pytest

from stdnum.br import cnpj
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


def test_exemplo_publicado_e_normalizado():
    assert cnpj.validate("16.727.230/0001-97") == "16727230000197"


def test_digito_errado():
    with pytest.raises(InvalidChecksum):
        cnpj.validate("16.727.230/0001-98")


def test_comprimento_errado():
    with pytest.raises(InvalidLength):
        cnpj.validate("1672723000019")


def test_caractere_invalido_e_formato_invalido():
    with pytest.raises(InvalidFormat):
        cnpj.validate("16727230000#97")
