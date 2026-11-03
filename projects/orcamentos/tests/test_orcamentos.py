from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError

from orcamentos.orcamentos import calcular_orcamento
from orcamentos.schemas import Pedido


def pedido(preco="100.00", quantidade=2, **kwargs):
    return Pedido(itens=[{"descricao": "Livro", "preco_unitario": preco, "quantidade": quantidade}], **kwargs)


@pytest.mark.parametrize("preco,cupom,entrega,desconto,frete,total", [
    ("100.00", None, "padrao", "0.00", "15.00", "115.00"),
    ("199.99", None, "padrao", "0.00", "15.00", "214.99"),
    ("200.00", None, "padrao", "0.00", "0.00", "200.00"),
    ("200.01", None, "padrao", "0.00", "0.00", "200.01"),
    ("200.00", "DESC10", "padrao", "20.00", "15.00", "195.00"),
    ("250.00", "DESC10", "padrao", "25.00", "0.00", "225.00"),
    ("250.00", "DESC10", "expressa", "25.00", "25.00", "250.00"),
    ("1.05", "DESC10", "padrao", "0.11", "15.00", "15.94"),
])
def test_calcula_politicas_e_limites(preco, cupom, entrega, desconto, frete, total):
    result = calcular_orcamento(pedido(preco, 1, cupom=cupom, entrega=entrega))
    assert result.subtotal == Decimal(preco)
    assert result.desconto == Decimal(desconto)
    assert result.frete == Decimal(frete)
    assert result.total == Decimal(total)


def test_soma_itens_sem_modificar_pedido_e_isola_precisao():
    value = Pedido(itens=[{"descricao": "A", "preco_unitario": "12.34", "quantidade": 2},
                         {"descricao": "B", "preco_unitario": "0.01", "quantidade": 3}])
    original = value.model_dump()
    with localcontext() as context:
        context.prec = 2
        result = calcular_orcamento(value)
        assert context.prec == 2
    assert result.subtotal == Decimal("24.71")
    assert result.total == Decimal("39.71")
    assert value.model_dump() == original


@pytest.mark.parametrize("cupom", ["desc10", "DESC20", " DESC10"])
def test_rejeita_cupom_desconhecido(cupom):
    with pytest.raises(ValueError, match="Cupom desconhecido"):
        calcular_orcamento(pedido(cupom=cupom))


@pytest.mark.parametrize("cupom", [None, "", "   "])
def test_cupom_vazio_equivale_a_sem_desconto(cupom):
    value = pedido(cupom=cupom)
    result = calcular_orcamento(value)
    assert value.cupom is None
    assert result.desconto == Decimal("0.00")
    assert result.frete == Decimal("0.00")
    assert result.total == Decimal("200.00")


@pytest.mark.parametrize("field,value", [("preco_unitario", "0"), ("preco_unitario", "-1"),
    ("preco_unitario", "NaN"), ("preco_unitario", "Infinity"), ("preco_unitario", "1.005"),
    ("preco_unitario", "1000000.01"), ("quantidade", 0), ("quantidade", -1),
    ("quantidade", True), ("quantidade", 1.5), ("quantidade", "2"), ("quantidade", 1001),
    ("descricao", "  ")])
def test_valida_contrato_dos_itens(field, value):
    item = {"descricao": "Livro", "preco_unitario": "10.00", "quantidade": 1, field: value}
    with pytest.raises(ValidationError):
        Pedido(itens=[item])


def test_rejeita_lista_vazia_e_modalidade_desconhecida():
    with pytest.raises(ValidationError):
        Pedido(itens=[])
    with pytest.raises(ValidationError):
        pedido(entrega="inexistente")
