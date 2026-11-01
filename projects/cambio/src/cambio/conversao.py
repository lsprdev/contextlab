"""Conversão sem rede ou interface de terminal."""

from decimal import Decimal, ROUND_HALF_UP, localcontext


def converter_para_brl(valor: Decimal, cotacao: Decimal) -> Decimal:
    """Converte uma quantidade em moeda estrangeira para reais.

    Recebe Decimals finitos: quantidade não negativa e cotação positiva em
    reais por unidade estrangeira. Arredonda para centavos, com metades para
    cima. A consulta da cotação é responsabilidade de outra parte da aplicação.
    """
    if not isinstance(valor, Decimal) or not isinstance(cotacao, Decimal):
        raise TypeError("Valor e cotação devem ser Decimal.")
    if not valor.is_finite() or valor < 0:
        raise ValueError("O valor deve ser finito e não negativo.")
    if not cotacao.is_finite() or cotacao <= 0:
        raise ValueError("A cotação deve ser finita e positiva.")
    if valor > Decimal("1e12") or cotacao > Decimal("1e6"):
        raise ValueError("Valor ou cotação excede o limite da aplicação.")
    with localcontext() as contexto:
        contexto.prec = max(28, len(valor.as_tuple().digits) + len(cotacao.as_tuple().digits) + 4)
        return (valor * cotacao).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
