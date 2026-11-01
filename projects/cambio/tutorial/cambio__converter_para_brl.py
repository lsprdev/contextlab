"""Entrega didática previamente escrita; não foi gerada por um modelo."""

from decimal import Decimal

import pytest

from cambio.conversao import converter_para_brl


def test_converte_para_reais():
    assert converter_para_brl(Decimal("10"), Decimal("5.20")) == Decimal("52.00")


def test_metade_de_centavo():
    assert converter_para_brl(Decimal("1"), Decimal("5.125")) == Decimal("5.13")


def test_taxa_zero_e_invalida():
    with pytest.raises(ValueError):
        converter_para_brl(Decimal("1"), Decimal("0"))
