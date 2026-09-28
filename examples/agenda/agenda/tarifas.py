def tarifa_hora(periodo: str) -> float:
    """Retorna a tarifa por hora do período solicitado."""
    valores = {"diurno": 40.0, "noturno": 60.0}
    if periodo not in valores:
        raise ValueError("Período não atendido")
    return valores[periodo]
