"""Entradas validadas e respostas públicas do OrçaAPI."""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ItemPedido(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    descricao: str = Field(min_length=1, max_length=120)
    preco_unitario: Decimal = Field(gt=0, le=1000000, max_digits=9, decimal_places=2, allow_inf_nan=False)
    quantidade: int = Field(gt=0, le=1000, strict=True)

    @field_serializer("preco_unitario")
    def serializar_preco(self, value: Decimal) -> str:
        return format(value, ".2f")


class Pedido(BaseModel):
    """Itens com descricao, preco_unitario (reais) e quantidade inteira positiva.

    Envie o preço como texto decimal com até duas casas, por exemplo "12.50".
    Cupom ausente, null, vazio ou só com espaços significa sem desconto.
    Códigos preenchidos devem ser exatos. A entrega padrão é "padrao".
    """
    model_config = ConfigDict(extra="forbid")

    itens: list[ItemPedido] = Field(min_length=1, max_length=100)
    cupom: str | None = Field(default=None, max_length=30,
                             description="Opcional: null, vazio ou espaços significam sem cupom. DESC10 concede 10%.")
    entrega: Literal["padrao", "expressa"] = "padrao"

    @field_validator("cupom", mode="before")
    @classmethod
    def normalizar_cupom_vazio(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ResumoOrcamento(BaseModel):
    subtotal: Decimal
    desconto: Decimal
    frete: Decimal
    total: Decimal

    @field_serializer("subtotal", "desconto", "frete", "total")
    def serializar_dinheiro(self, value: Decimal) -> str:
        return format(value, ".2f")


class OrcamentoSalvo(ResumoOrcamento):
    id: int
    itens: list[ItemPedido]
    cupom: str | None
    entrega: Literal["padrao", "expressa"]
