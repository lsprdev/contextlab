from decimal import Decimal, localcontext

import pytest

from cambio.conversao import converter_para_brl


def test_converte_quantidade_pela_taxa():
    assert converter_para_brl(Decimal("10"), Decimal("5.20")) == Decimal("52.00")


def test_arredonda_metade_para_cima():
    assert converter_para_brl(Decimal("1"), Decimal("5.125")) == Decimal("5.13")


def test_aceita_zero():
    assert converter_para_brl(Decimal("0"), Decimal("5.20")) == Decimal("0.00")


def test_independe_da_precisao_decimal_do_chamador():
    with localcontext() as contexto:
        contexto.prec = 3
        assert converter_para_brl(Decimal("123.45"), Decimal("5.20")) == Decimal("641.94")


@pytest.mark.parametrize("valor,taxa", [("-1", "5"), ("NaN", "5"), ("Infinity", "5"),
                                        ("1", "0"), ("1", "-5"), ("1", "NaN"),
                                        ("1", "Infinity"), ("1e13", "5"), ("1", "1e7")])
def test_rejeita_valores_invalidos(valor, taxa):
    with pytest.raises(ValueError):
        converter_para_brl(Decimal(valor), Decimal(taxa))


def test_exige_decimal():
    with pytest.raises(TypeError):
        converter_para_brl(10.0, Decimal("5.20"))
