"""Referência DOT-02: dotenv.variables.parse_variables.

A função divide o texto em literais e referências ${NOME} ou ${NOME:-padrão},
sem consultar o ambiente.
"""
from dotenv.variables import Literal, Variable, parse_variables


def _itens(texto):
    return [(type(a).__name__, vars(a)) for a in parse_variables(texto)]


def test_texto_vazio_gera_sequencia_vazia():
    assert list(parse_variables("")) == []


def test_texto_comum_gera_um_literal():
    assert _itens("abc") == [("Literal", {"value": "abc"})]


def test_referencia_simples_gera_variavel_sem_padrao():
    assert _itens("${NOME}") == [("Variable", {"name": "NOME", "default": None})]


def test_literais_nas_duas_extremidades_e_valor_padrao():
    assert _itens("pre${NOME:-x}fim") == [
        ("Literal", {"value": "pre"}),
        ("Variable", {"name": "NOME", "default": "x"}),
        ("Literal", {"value": "fim"}),
    ]


def test_referencias_consecutivas():
    assert _itens("${A}${B}") == [
        ("Variable", {"name": "A", "default": None}),
        ("Variable", {"name": "B", "default": None}),
    ]


def test_padrao_vazio_e_diferente_de_sem_padrao():
    assert _itens("${A:-}") == [("Variable", {"name": "A", "default": ""})]


def test_referencia_incompleta_permanece_literal():
    assert _itens("${NOME") == [("Literal", {"value": "${NOME"})]


def test_dolar_sem_chaves_e_literal():
    assert _itens("$NOME") == [("Literal", {"value": "$NOME"})]


def test_resultado_e_um_iterador():
    resultado = parse_variables("a${B}")
    assert next(resultado) == Literal("a")
    assert next(resultado) == Variable("B", None)
