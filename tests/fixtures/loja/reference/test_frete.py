import pytest

from loja.cliente import Cliente
from loja.frete import calcular_frete


def test_limite_vip():
    assert calcular_frete(5, "local", Cliente("Ana", vip=True)) == 17.6


def test_acima_do_limite_vip():
    assert calcular_frete(6, "local", Cliente("Ana", vip=True)) == 25.0


def test_cliente_comum():
    assert calcular_frete(1, "regional", Cliente("Bia")) == 20.0


def test_peso_fracionario():
    assert calcular_frete(1.5, "nacional", Cliente("Caio")) == 31.5


@pytest.mark.parametrize("peso", [0, -1])
def test_peso_invalido(peso):
    with pytest.raises(ValueError, match="peso"):
        calcular_frete(peso, "local", Cliente("Davi"))


def test_zona_invalida():
    with pytest.raises(ValueError, match="Zona"):
        calcular_frete(1, "exterior", Cliente("Eva"))
