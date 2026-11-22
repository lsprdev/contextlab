import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    ('source', 'expected'),
    [
        pytest.param('', [], id='empty-input'),
        pytest.param('plain text\n  café ☃\t', [Literal('plain text\n  café ☃\t')], id='literal-only'),
        pytest.param('${NAME}', [Variable('NAME', None)], id='single-variable'),
        pytest.param('${}', [Variable('', None)], id='empty-name'),
        pytest.param('${:-fallback}', [Variable('', 'fallback')], id='empty-name-with-default'),
        pytest.param('${:-}', [Variable('', '')], id='empty-name-and-default'),
        pytest.param(
            '${A}${A:-}${A:-fallback}${A}',
            [Variable('A', None), Variable('A', ''), Variable('A', 'fallback'), Variable('A', None)],
            id='adjacent-variables-and-distinct-defaults',
        ),
        pytest.param(
            'α${FIRST} / ${SECOND:-two}\n${THIRD}ω',
            [Literal('α'), Variable('FIRST', None), Literal(' / '), Variable('SECOND', 'two'),
             Literal('\n'), Variable('THIRD', None), Literal('ω')],
            id='leading-intervening-and-trailing-literals',
        ),
        pytest.param('prefix${A}', [Literal('prefix'), Variable('A', None)], id='ends-with-variable'),
        pytest.param('${A}suffix', [Variable('A', None), Literal('suffix')], id='starts-with-variable'),
        pytest.param(
            '${ 9-é.雪/+$={\n\t }',
            [Variable(' 9-é.雪/+$={\n\t ', None)],
            id='name-preserves-punctuation-unicode-and-whitespace',
        ),
        pytest.param(
            '${KEY:--one:two:-three=$RAW{ # é\n\t }',
            [Variable('KEY', '-one:two:-three=$RAW{ # é\n\t ')],
            id='default-preserves-punctuation-unicode-and-whitespace',
        ),
        pytest.param(
            '$NAME ${A-default} ${B:+alt} ${C:?err} ${D:=value} ${E:word} ${F: -x} ${OPEN',
            [Literal('$NAME '), Variable('A-default', None),
             Literal(' ${B:+alt} ${C:?err} ${D:=value} ${E:word} ${F: -x} ${OPEN')],
            id='only-colon-dash-introduces-default',
        ),
        pytest.param(
            '${BROKEN:+oops ${OK} after ${UNFINISHED:-',
            [Literal('${BROKEN:+oops '), Variable('OK', None), Literal(' after ${UNFINISHED:-')],
            id='valid-match-between-malformed-fragments',
        ),
        pytest.param(
            r'\${A} $${B} "${C}"',
            [Literal('\\'), Variable('A', None), Literal(' $'), Variable('B', None),
             Literal(' "'), Variable('C', None), Literal('"')],
            id='backslashes-dollars-and-quotes-are-literal',
        ),
        pytest.param(
            '${OUTER:-${INNER:-fallback}}/${NEXT}',
            [Variable('OUTER', '${INNER:-fallback'), Literal('}/'), Variable('NEXT', None)],
            id='first-closing-brace-ends-default',
        ),
        pytest.param(
            '${KEY:-using\\}tail}',
            [Variable('KEY', 'using\\'), Literal('tail}')],
            id='backslash-does-not-escape-closing-brace',
        ),
        pytest.param(
            '${KEY\\:-default}',
            [Variable('KEY\\', 'default')],
            id='backslash-before-default-separator-is-part-of-name',
        ),
    ],
)
def test_parse_variables_yields_expected_atoms(source, expected):
    assert list(parse_variables(source)) == expected


def test_parse_variables_returns_an_iterator():
    atoms = parse_variables('before${NAME:-fallback}after')

    assert iter(atoms) is atoms
    assert next(atoms) == Literal('before')
    assert next(atoms) == Variable('NAME', 'fallback')
    assert next(atoms) == Literal('after')
    with pytest.raises(StopIteration):
        next(atoms)
