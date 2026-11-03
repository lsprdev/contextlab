"""Entrega autoral para conferir o avaliador; não é geração por IA."""
from decimal import Decimal

from orcamentos.orcamentos import calcular_orcamento
from orcamentos.schemas import Pedido


def test_desconto_antes_da_faixa_de_frete():
    pedido = Pedido(itens=[{"descricao": "Livro", "preco_unitario": "100.00", "quantidade": 2}], cupom="DESC10")
    result = calcular_orcamento(pedido)
    assert result.desconto == Decimal("20.00")
    assert result.frete == Decimal("15.00")
    assert result.total == Decimal("195.00")
