"""Cálculo do orçamento, independente da rota e da persistência."""
from decimal import Decimal, ROUND_HALF_UP, localcontext

from orcamentos.descontos import calcular_desconto
from orcamentos.frete import calcular_frete
from orcamentos.schemas import Pedido, ResumoOrcamento


def calcular_orcamento(pedido: Pedido) -> ResumoOrcamento:
    """Calcula um Pedido já validado, aplicando cupom antes de calcular frete.

    Soma preço vezes quantidade, delega desconto e frete às políticas locais
    e retorna os quatro valores monetários em Decimal, com duas casas.
    Não salva no banco nem altera o pedido. Cupom desconhecido gera ValueError.
    """
    with localcontext() as context:
        context.prec = 28
        subtotal = sum((item.preco_unitario * item.quantidade for item in pedido.itens), Decimal("0"))
        subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        desconto = calcular_desconto(subtotal, pedido.cupom)
        base = subtotal - desconto
        frete = calcular_frete(base, pedido.entrega)
        return ResumoOrcamento(subtotal=subtotal, desconto=desconto, frete=frete, total=base + frete)
