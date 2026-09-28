"""Saída autoral fixa para testar o fluxo; não foi gerada por um agente."""

import pytest

from agenda.preco import calcular_preco
from agenda.reserva import Reserva


def test_precos_por_duracao_e_periodo():
    assert calcular_preco(Reserva(30, "diurno")) == 20.0
    assert calcular_preco(Reserva(60, "noturno")) == 60.0


def test_desconto_inclui_duas_horas():
    assert calcular_preco(Reserva(90, "diurno")) == 60.0
    assert calcular_preco(Reserva(120, "diurno")) == 72.0
    assert calcular_preco(Reserva(150, "noturno")) == 135.0


@pytest.mark.parametrize("minutos", [0, -30, 45])
def test_duracao_invalida(minutos):
    with pytest.raises(ValueError):
        calcular_preco(Reserva(minutos, "diurno"))


def test_periodo_desconhecido():
    with pytest.raises(ValueError):
        calcular_preco(Reserva(60, "madrugada"))
