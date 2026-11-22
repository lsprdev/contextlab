import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('', [], id='empty'),
        pytest.param('  plain text\r\n\t ', [Literal('  plain text\r\n\t ')], id='literal-whitespace'),
        pytest.param('${NAME}', [Variable('NAME', None)], id='variable-only'),
        pytest.param('${NAME:-fallback}', [Variable('NAME', 'fallback')], id='nonempty-default'),
        pytest.param('${NAME:-}', [Variable('NAME', '')], id='empty-default'),
        pytest.param('${}', [Variable('', None)], id='empty-name'),
        pytest.param('${:-fallback}', [Variable('', 'fallback')], id='empty-name-with-default'),
        pytest.param('${:-}', [Variable('', '')], id='empty-name-and-default'),
        pytest.param('left${A}', [Literal('left'), Variable('A', None)], id='prefix-only'),
        pytest.param('${A}right', [Variable('A', None), Literal('right')], id='suffix-only'),
        pytest.param(
            '${A}${B:-two}${A}',
            [Variable('A', None), Variable('B', 'two'), Variable('A', None)],
            id='adjacent-variables-and-repeated-name',
        ),
        pytest.param(
            '  á🙂${A:-one}/ ${LONG_NAME}\n${A:-}fim\r\n',
            [
                Literal('  á🙂'),
                Variable('A', 'one'),
                Literal('/ '),
                Variable('LONG_NAME', None),
                Literal('\n'),
                Variable('A', ''),
                Literal('fim\r\n'),
            ],
            id='ordered-literal-and-variable-spans',
        ),
    ],
)
def test_parse_variables_emits_atoms_in_source_order(value, expected):
    assert list(parse_variables(value)) == expected


@pytest.mark.parametrize(
    'value',
    [
        '$NAME',
        '{NAME}',
        '$(NAME)',
        '$ {NAME}',
        '${',
        '${NAME',
        '${NAME:-fallback',
        '${NAME-default}',
        '${NAME:}',
        '${NAME: -fallback}',
        '${NAME:+alternate}',
        '${NAME:=assigned}',
        '${NAME:?error}',
        '${A:B:-fallback}',
    ],
)
def test_parse_variables_preserves_nonmatching_text_as_one_literal(value):
    # A hyphen without a colon can be part of a variable name.
    if value == '${NAME-default}':
        assert list(parse_variables(value)) == [Variable('NAME-default', None)]
    else:
        assert list(parse_variables(value)) == [Literal(value)]


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param(
            'a${BAD:word}b${OK}c${UNFINISHED:-',
            [Literal('a${BAD:word}b'), Variable('OK', None), Literal('c${UNFINISHED:-')],
            id='malformed-expressions-around-a-match',
        ),
        pytest.param(
            '${BAD:${OK}}',
            [Literal('${BAD:'), Variable('OK', None), Literal('}')],
            id='match-inside-malformed-expression',
        ),
        pytest.param(
            '${ 9-é.名\t\n$/{ # :- \t\n🙂:x:-y{# $BARE }',
            [Variable(' 9-é.名\t\n$/{ # ', ' \t\n🙂:x:-y{# $BARE ')],
            id='name-and-default-preserve-characters',
        ),
        pytest.param('${A:--}', [Variable('A', '-')], id='default-starts-with-hyphen'),
        pytest.param(
            '${OUTER:-${INNER:-fallback}}${NEXT}',
            [Variable('OUTER', '${INNER:-fallback'), Literal('}'), Variable('NEXT', None)],
            id='default-ends-at-first-closing-brace',
        ),
        pytest.param(
            '${OUTER${INNER}}',
            [Variable('OUTER${INNER', None), Literal('}')],
            id='opening-brace-is-allowed-in-name',
        ),
        pytest.param(
            r'\${A}$${B}',
            [Literal('\\'), Variable('A', None), Literal('$'), Variable('B', None)],
            id='backslash-and-extra-dollar-are-literal',
        ),
        pytest.param(
            r'${A:-a\}b}',
            [Variable('A', 'a\\'), Literal('b}')],
            id='backslash-does-not-escape-closing-brace',
        ),
    ],
)
def test_parse_variables_recognizes_delimiters(value, expected):
    assert list(parse_variables(value)) == expected


def test_parse_variables_returns_an_iterator():
    atoms = parse_variables('x${A}y')

    assert iter(atoms) is atoms
    assert next(atoms) == Literal('x')
    assert next(atoms) == Variable('A', None)
    assert next(atoms) == Literal('y')
    with pytest.raises(StopIteration):
        next(atoms)
