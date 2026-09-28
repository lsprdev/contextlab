def tarifa(zona: str) -> float:
    """Retorna a tarifa básica da região atendida."""
    valores = {"local": 10.0, "regional": 20.0, "nacional": 30.0}
    if zona not in valores:
        raise ValueError("Zona não atendida")
    return valores[zona]
