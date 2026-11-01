from datetime import date
from decimal import Decimal
from io import BytesIO
from urllib.error import URLError

import pytest

from cambio import cotacoes


def test_interpreta_par_data_e_decimal():
    result = cotacoes.interpretar_cotacao(
        {"base": "USD", "quote": "BRL", "rate": "5.12345", "date": "2026-01-02"}, "USD")
    assert result == cotacoes.Cotacao("USD", Decimal("5.12345"), date(2026, 1, 2))


@pytest.mark.parametrize("mudanca", [{"base": "EUR"}, {"quote": "USD"}, {"rate": 0},
                                     {"rate": "NaN"}, {"date": "2026-02-31"}, {"rate": True}])
def test_rejeita_resposta_invalida(mudanca):
    dados = {"base": "USD", "quote": "BRL", "rate": "5.2", "date": "2026-01-02"}
    with pytest.raises(cotacoes.ErroCotacao):
        cotacoes.interpretar_cotacao(dados | mudanca, "USD")


def test_consulta_endereco_com_timeout_sem_perder_decimais(monkeypatch):
    def abrir(pedido, timeout):
        assert pedido.full_url == "https://api.frankfurter.dev/v2/rate/usd/brl"
        assert timeout == 3
        return BytesIO(b'{"base":"USD","quote":"BRL","rate":5.12345,"date":"2026-01-02"}')
    monkeypatch.setattr(cotacoes, "urlopen", abrir)
    assert cotacoes.buscar_cotacao("USD", timeout=3).taxa == Decimal("5.12345")


def test_trata_falha_de_conexao(monkeypatch):
    def falhar(*args, **kwargs):
        raise URLError("offline")
    monkeypatch.setattr(cotacoes, "urlopen", falhar)
    with pytest.raises(cotacoes.ErroCotacao, match="conexão"):
        cotacoes.buscar_cotacao("EUR")


def test_demo_identifica_dados_ficticios():
    assert "fictícios" in cotacoes.cotacao_demonstracao("USD").fonte
