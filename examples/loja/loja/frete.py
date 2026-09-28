from loja.cliente import Cliente
from loja.tarifas import tarifa


def calcular_frete(peso: float, zona: str, cliente: Cliente) -> float:
    """Calcula o valor do frete para um pacote de peso positivo."""
    if peso <= 0:
        raise ValueError("O peso deve ser positivo")

    base = tarifa(zona)
    total = base + max(0, peso - 1) * 3
    if cliente.vip and peso <= 5:
        total *= 0.8
    return round(total, 2)
