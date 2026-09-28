from dataclasses import dataclass


@dataclass(frozen=True)
class Reserva:
    minutos: int
    periodo: str
