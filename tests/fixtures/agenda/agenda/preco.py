from agenda.reserva import Reserva
from agenda.tarifas import tarifa_hora


def calcular_preco(reserva: Reserva) -> float:
    """Calcula o preço de uma reserva em blocos inteiros de meia hora."""
    if reserva.minutos <= 0 or reserva.minutos % 30 != 0:
        raise ValueError("A duração deve ser positiva e múltipla de 30 minutos")

    total = reserva.minutos / 60 * tarifa_hora(reserva.periodo)
    if reserva.minutos >= 120:
        total *= 0.9
    return round(total, 2)
