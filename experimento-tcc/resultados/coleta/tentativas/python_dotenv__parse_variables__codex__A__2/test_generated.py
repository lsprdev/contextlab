import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('', [], id='empty-input'),
        pytest.param(' \tplain\ntext\r\n ', [Literal(' \tplain\ntext\r\n ')], id='literal-whitespace'),
        pytest.param('$NAME $9 $$ {NAME} }', [Literal('$NAME $9 $$ {NAME} }')], id='unbraced-text'),
        pytest.param('${NAME}', [Variable('NAME', None)], id='variable-only'),
        pytest.param('${NAME:-}', [Variable('NAME', '')], id='empty-default'),
        pytest.param('${}', [Variable('', None)], id='empty-name'),
        pytest.param('${:-fallback}', [Variable('', 'fallback')], id='empty-name-with-default'),
        pytest.param('pre${A}', [Literal('pre'), Variable('A', None)], id='leading-literal'),
        pytest.param('${A}post', [Variable('A', None), Literal('post')], id='trailing-literal'),
        pytest.param('${A}${B:-two}${A:-three}', [Variable('A', None), Variable('B', 'two'), Variable('A', 'three')], id='adjacent-and-repeated'),
        pytest.param(
            'prefix ${FIRST}/middle/${SECOND:-two} suffix',
            [Literal('prefix '), Variable('FIRST', None), Literal('/middle/'), Variable('SECOND', 'two'), Literal(' suffix')],
            id='all-literal-boundaries',
        ),
        pytest.param(
            '${9.café /$-{\nX}',
            [Variable('9.café /$-{\nX', None)],
            id='punctuation-and-newline-in-name',
        ),
        pytest.param(
            '${A:-  café:\n$OTHER:-{text\t}!',
            [Variable('A', '  café:\n$OTHER:-{text\t'), Literal('!')],
            id='punctuation-and-newline-in-default',
        ),
        pytest.param('${A:--x}', [Variable('A', '-x')], id='default-starting-with-hyphen'),
        pytest.param('${A-fallback}', [Variable('A-fallback', None)], id='hyphen-in-name'),
        pytest.param(r'\${A} $${B}', [Literal('\\'), Variable('A', None), Literal(' $'), Variable('B', None)], id='backslash-and-extra-dollar'),
        pytest.param('${A:-${B:-inner}}', [Variable('A', '${B:-inner'), Literal('}')], id='default-ends-at-first-closing-brace'),
        pytest.param('${A${B}}', [Variable('A${B', None), Literal('}')], id='opening-brace-in-name'),
        pytest.param('${A}:-fallback}', [Variable('A', None), Literal(':-fallback}')], id='closing-brace-ends-name'),
        pytest.param('${A', [Literal('${A')], id='unclosed-name'),
        pytest.param('${A:-fallback', [Literal('${A:-fallback')], id='unclosed-default'),
        pytest.param('${A:}', [Literal('${A:}')], id='colon-without-hyphen'),
        pytest.param('${A:+alt} ${B:=value} ${C:?error}', [Literal('${A:+alt} ${B:=value} ${C:?error}')], id='unsupported-operators'),
        pytest.param(
            '${BAD:oops${OK:-yes}/${NEXT}${OPEN:-tail',
            [Literal('${BAD:oops'), Variable('OK', 'yes'), Literal('/'), Variable('NEXT', None), Literal('${OPEN:-tail')],
            id='valid-matches-among-malformed-fragments',
        ),
    ],
)
def test_parse_variables_yields_ordered_atoms(value, expected):
    assert list(parse_variables(value)) == expected


def test_parse_variables_returns_an_independently_consumable_iterator():
    first = parse_variables('left${A}')
    second = parse_variables('${B}right')

    assert iter(first) is first
    assert next(first) == Literal('left')
    assert next(second) == Variable('B', None)
    assert next(first) == Variable('A', None)
    with pytest.raises(StopIteration):
        next(first)
    assert list(second) == [Literal('right')]


@pytest.mark.parametrize(
    ('environment', 'expected'),
    [
        ({}, 'pre:fallback||:post'),
        ({'A': 'provided', 'B': 'second', 'C': 'third'}, 'pre:provided|second|third:post'),
        ({'A': '', 'B': None, 'C': ''}, 'pre:||:post'),
        ({'A': None, 'B': '${A}', 'C': None}, 'pre:|${A}|:post'),
    ],
)
def test_parse_variables_atoms_resolve_against_supplied_environment(environment, expected):
    atoms = parse_variables('pre:${A:-fallback}|${B}|${C:-}:post')

    assert ''.join(atom.resolve(environment) for atom in atoms) == expected
