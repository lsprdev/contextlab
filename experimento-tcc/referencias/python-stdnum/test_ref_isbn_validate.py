"""Referência STD-02: stdnum.isbn.validate.

Exemplos publicados (1 85798218 5 e o EAN 7501031311309, dos testes do projeto)
e ISBNs clássicos com dígitos conferidos à mão: 0-306-40615-2 e 0-8044-2957-X.
"""
import pytest

from stdnum import isbn
from stdnum.exceptions import InvalidChecksum, InvalidComponent, InvalidFormat, InvalidLength


def test_isbn10_com_espacos_e_normalizado():
    assert isbn.validate("1 85798218 5") == "1857982185"


def test_isbn10_com_conversao_vira_isbn13():
    assert isbn.validate("1 85798218 5", convert=True) == "9781857982183"


def test_isbn13_com_hifens_e_normalizado():
    assert isbn.validate("978-1-85798-218-3") == "9781857982183"


def test_isbn13_com_conversao_permanece_igual():
    assert isbn.validate("978-1-85798-218-3", convert=True) == "9781857982183"


def test_isbn10_com_digito_x():
    # 1*0+2*8+3*0+4*4+5*4+6*2+7*9+8*5+9*7 = 230; 230 % 11 = 10 -> X.
    assert isbn.validate("0-8044-2957-X") == "080442957X"


def test_isbn10_com_x_minusculo_e_aceito():
    assert isbn.validate("080442957x") == "080442957X"


def test_nove_caracteres_recebem_zero_inicial():
    assert isbn.validate("306406152") == "0306406152"


def test_isbn10_com_digito_errado():
    with pytest.raises(InvalidChecksum):
        isbn.validate("1857982186")


def test_isbn13_com_digito_errado():
    with pytest.raises(InvalidChecksum):
        isbn.validate("9781857982184")


def test_ean_valido_sem_prefixo_de_isbn():
    with pytest.raises(InvalidComponent):
        isbn.validate("7501031311309")


def test_comprimento_invalido_apos_normalizacao():
    with pytest.raises(InvalidLength):
        isbn.validate("18579821850")


def test_letra_no_meio():
    with pytest.raises(InvalidFormat):
        isbn.validate("18579A2185")
