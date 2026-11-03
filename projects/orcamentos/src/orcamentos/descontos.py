"""Política de cupons deste exercício."""
from decimal import Decimal, ROUND_HALF_UP, localcontext


def calcular_desconto(subtotal: Decimal, cupom: str | None) -> Decimal:
    """Recebe subtotal validado. DESC10 dá 10%; None não aplica desconto.

    O código do cupom é exato, sem normalização. Um código desconhecido gera
    ValueError. O desconto é arredondado para centavos, com metades para cima.
    """
    if cupom is None:
        return Decimal("0.00")
    if cupom != "DESC10":
        raise ValueError("Cupom desconhecido.")
    with localcontext() as context:
        context.prec = 28
        return (subtotal * Decimal("0.10")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
