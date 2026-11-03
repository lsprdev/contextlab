"""Política de entrega deste exercício."""
from decimal import Decimal


def calcular_frete(valor_apos_desconto: Decimal, entrega: str) -> Decimal:
    """Recebe o valor validado após desconto e devolve a tarifa em reais.

    Entrega padrão custa 15 e é gratuita a partir de 200, inclusive.
    Entrega expressa custa 25 em qualquer valor. Modalidade desconhecida
    gera ValueError. Não consulta transportadora nem serviço externo.
    """
    if entrega == "expressa":
        return Decimal("25.00")
    if entrega != "padrao":
        raise ValueError("Modalidade de entrega desconhecida.")
    if valor_apos_desconto >= Decimal("200.00"):
        return Decimal("0.00")
    return Decimal("15.00")
