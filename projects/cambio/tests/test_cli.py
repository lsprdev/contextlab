from decimal import Decimal

import pytest

from cambio.cli import ler_valor, main


def test_valor_com_virgula():
    assert ler_valor(" 10,50 ") == Decimal("10.50")


@pytest.mark.parametrize("texto", ["NaN", "Infinity", "-1", "1.000,00", "abc", "1e30"])
def test_valor_invalido(texto):
    with pytest.raises(ValueError):
        ler_valor(texto)


def test_menu_demo_consulta_converte_e_sai(monkeypatch, capsys):
    entradas = iter(["1", "2", "USD", "10", "0"])
    monkeypatch.setattr("builtins.input", lambda *args: next(entradas))
    assert main(["--demo"]) == 0
    texto = capsys.readouterr().out
    assert "fictícias" in texto and "52,00" in texto and "Até a próxima" in texto
