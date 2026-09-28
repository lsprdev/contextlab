import pytest

from agenda.preco import calcular_preco
from agenda.reserva import Reserva


def test_limite_desconto():
    assert calcular_preco(Reserva(120, "diurno")) == 72.0


def test_antes_do_desconto():
    assert calcular_preco(Reserva(90, "diurno")) == 60.0


def test_acima_do_limite():
    assert calcular_preco(Reserva(150, "noturno")) == 135.0


def test_meia_hora_noturna():
    assert calcular_preco(Reserva(30, "noturno")) == 30.0


@pytest.mark.parametrize("minutos", [0, -30, 45])
def test_duracao_invalida(minutos):
    with pytest.raises(ValueError, match="duração"):
        calcular_preco(Reserva(minutos, "diurno"))


def test_periodo_invalido():
    with pytest.raises(ValueError, match="Período"):
        calcular_preco(Reserva(60, "madrugada"))
