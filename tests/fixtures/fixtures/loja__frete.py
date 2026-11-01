"""Saída autoral fixa para testar o fluxo; não foi gerada por um agente."""

import pytest

from loja.cliente import Cliente
from loja.frete import calcular_frete


def test_frete_basico_e_excesso():
    cliente = Cliente("Cliente comum")
    assert calcular_frete(1, "local", cliente) == 10.0
    assert calcular_frete(2, "regional", cliente) == 23.0
    assert calcular_frete(1.5, "nacional", cliente) == 31.5


def test_vip_na_fronteira_e_fora_dela():
    cliente = Cliente("Cliente VIP", vip=True)
    assert calcular_frete(5, "local", cliente) == 17.6
    assert calcular_frete(6, "local", cliente) == 25.0


def test_entradas_invalidas():
    with pytest.raises(ValueError):
        calcular_frete(0, "local", Cliente("Cliente"))
    with pytest.raises(ValueError):
        calcular_frete(1, "exterior", Cliente("Cliente"))
