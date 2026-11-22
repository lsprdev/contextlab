import pytest

from dotenv.variables import Literal, Variable, parse_variables


def test_empty_input_yields_no_atoms():
    assert list(parse_variables("")) == []


@pytest.mark.parametrize(
    "value",
    [
        "ordinary text",
        " \tlinha 1\r\n雪\n ",
        "$NAME $(NAME) {NAME} $",
        "${NAME",
        "${NAME:-fallback",
        "${NAME-default} ${NAME=default}",
        "${NAME:default} ${NAME:+alternate} ${NAME:=assigned} ${NAME:?error}",
    ],
)
def test_text_without_expansions_is_preserved_as_one_literal(value):
    if value == "${NAME-default} ${NAME=default}":
        assert list(parse_variables(value)) == [
            Variable("NAME-default", None),
            Literal(" "),
            Variable("NAME=default", None),
        ]
    else:
        assert list(parse_variables(value)) == [Literal(value)]


@pytest.mark.parametrize(
    ("value", "name", "default"),
    [
        ("${NAME}", "NAME", None),
        ("${NAME:-}", "NAME", ""),
        ("${NAME:-fallback}", "NAME", "fallback"),
        ("${}", "", None),
        ("${:-}", "", ""),
        ("${:-fallback}", "", "fallback"),
        ("${9.na-me/é =x\t}", "9.na-me/é =x\t", None),
        ("${ a\nb\t:- \tfallback\n }", " a\nb\t", " \tfallback\n "),
        ("${NAME:--a:b:-c=$OTHER{d}", "NAME", "-a:b:-c=$OTHER{d"),
    ],
)
def test_expansion_preserves_name_and_optional_default(value, name, default):
    assert list(parse_variables(value)) == [Variable(name, default)]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "pré\n${A} / ${B:-two}\t${A:-}\n雪",
            [
                Literal("pré\n"),
                Variable("A", None),
                Literal(" / "),
                Variable("B", "two"),
                Literal("\t"),
                Variable("A", ""),
                Literal("\n雪"),
            ],
        ),
        ("${A}${B:-2}${A}", [Variable("A", None), Variable("B", "2"), Variable("A", None)]),
        ("x${A}", [Literal("x"), Variable("A", None)]),
        ("${A}x", [Variable("A", None), Literal("x")]),
        ("${A}x${B}", [Variable("A", None), Literal("x"), Variable("B", None)]),
        (
            "${BAD:+x}${OK} ${BAD:=y} ${OPEN:-",
            [Literal("${BAD:+x}"), Variable("OK", None), Literal(" ${BAD:=y} ${OPEN:-")],
        ),
        (
            r"\${A} $${B} $BARE",
            [Literal("\\"), Variable("A", None), Literal(" $"), Variable("B", None), Literal(" $BARE")],
        ),
        (
            "${OUTER:-${INNER:-backup}}${NEXT}",
            [Variable("OUTER", "${INNER:-backup"), Literal("}"), Variable("NEXT", None)],
        ),
        ("${A${B}}", [Variable("A${B", None), Literal("}")]),
        ("${A:-one}two}${B}", [Variable("A", "one"), Literal("two}"), Variable("B", None)]),
    ],
)
def test_atoms_preserve_source_order_and_literal_boundaries(value, expected):
    assert list(parse_variables(value)) == expected


def test_parse_variables_returns_a_single_pass_iterator():
    atoms = parse_variables("before${NAME:-fallback}after")

    assert iter(atoms) is atoms
    assert next(atoms) == Literal("before")
    assert next(atoms) == Variable("NAME", "fallback")
    assert next(atoms) == Literal("after")
    with pytest.raises(StopIteration):
        next(atoms)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, "[fallback]::"),
        ({"ITEM": "actual", "BARE": "set"}, "[actual]:actual:set"),
        ({"ITEM": "", "BARE": ""}, "[]::"),
        ({"ITEM": None, "BARE": None}, "[]::"),
    ],
)
def test_parsed_atoms_can_be_resolved_against_a_mapping(env, expected):
    atoms = parse_variables("[${ITEM:-fallback}]:${ITEM:-}:${BARE}")

    assert "".join(atom.resolve(env) for atom in atoms) == expected
