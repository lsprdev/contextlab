"""Consulta das taxas diárias da Frankfurter; nenhuma chamada ocorre no import."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ErroCotacao(ValueError):
    """Falha de consulta ou resposta incompatível com o par solicitado."""


@dataclass(frozen=True)
class Cotacao:
    moeda: str
    taxa: Decimal
    data: date
    fonte: str = "Frankfurter"


def interpretar_cotacao(dados: dict, moeda: str) -> Cotacao:
    """Valida o par, a taxa positiva e a data retornados pela API."""
    if moeda not in {"USD", "EUR"}:
        raise ErroCotacao("Escolha USD ou EUR.")
    try:
        if dados["base"] != moeda or dados["quote"] != "BRL":
            raise ErroCotacao("A resposta não corresponde ao par solicitado.")
        taxa = Decimal(str(dados["rate"]))
        if not taxa.is_finite() or taxa <= 0 or taxa > Decimal("1e6"):
            raise ErroCotacao("A cotação recebida é inválida.")
        data = date.fromisoformat(dados["date"])
        return Cotacao(moeda, taxa, data)
    except (KeyError, TypeError, InvalidOperation, ValueError) as erro:
        raise ErroCotacao("O serviço retornou uma cotação inválida.") from erro


def buscar_cotacao(moeda: str, timeout: float = 10) -> Cotacao:
    """Busca a última taxa diária disponível para USD/BRL ou EUR/BRL."""
    if moeda not in {"USD", "EUR"}:
        raise ErroCotacao("Escolha USD ou EUR.")
    pedido = Request(
        f"https://api.frankfurter.dev/v2/rate/{moeda.lower()}/brl",
        headers={"User-Agent": "ContextLab-Cambio/0.1", "Accept": "application/json"},
    )
    try:
        with urlopen(pedido, timeout=timeout) as resposta:
            conteudo = resposta.read(65537)
        if len(conteudo) > 65536:
            raise ErroCotacao("A resposta do serviço excedeu o tamanho esperado.")
        dados = json.loads(conteudo, parse_float=Decimal)
    except HTTPError as erro:
        raise ErroCotacao(f"Serviço de câmbio indisponível (HTTP {erro.code}).") from erro
    except (URLError, TimeoutError, OSError) as erro:
        raise ErroCotacao("Não foi possível consultar o câmbio. Verifique a conexão e tente novamente.") from erro
    except (ValueError, UnicodeError) as erro:
        raise ErroCotacao("O serviço retornou uma resposta inválida.") from erro
    return interpretar_cotacao(dados, moeda)


def cotacao_demonstracao(moeda: str) -> Cotacao:
    """Dados fictícios e explícitos para usar o menu sem internet."""
    taxas = {"USD": Decimal("5.20"), "EUR": Decimal("6.10")}
    if moeda not in taxas:
        raise ErroCotacao("Escolha USD ou EUR.")
    return Cotacao(moeda, taxas[moeda], date(2026, 1, 1), "Simulação: valores fictícios")
