import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('', [], id='empty-input'),
        pytest.param(' \tOlá 🌿\n ', [Literal(' \tOlá 🌿\n ')], id='literal-preserves-whitespace'),
        pytest.param('$HOME $$ $() {HOME} $ {HOME}', [Literal('$HOME $$ $() {HOME} $ {HOME}')], id='unbraced-forms'),
        pytest.param('${HOME}', [Variable('HOME', None)], id='variable-only'),
        pytest.param('${HOME:-}', [Variable('HOME', '')], id='explicit-empty-default'),
        pytest.param('${}', [Variable('', None)], id='empty-name'),
        pytest.param('${:-fallback}', [Variable('', 'fallback')], id='empty-name-with-default'),
        pytest.param('${:-}', [Variable('', '')], id='empty-name-and-default'),
        pytest.param('before ${X}', [Literal('before '), Variable('X', None)], id='leading-literal'),
        pytest.param('${X} after', [Variable('X', None), Literal(' after')], id='trailing-literal'),
        pytest.param(
            '🌿${A} / ${LONG_NAME:-xyz}\n${A:-}!',
            [Literal('🌿'), Variable('A', None), Literal(' / '), Variable('LONG_NAME', 'xyz'),
             Literal('\n'), Variable('A', ''), Literal('!')],
            id='multiple-matches-at-different-offsets',
        ),
        pytest.param(
            '${X}${X:-one}${X:-two}',
            [Variable('X', None), Variable('X', 'one'), Variable('X', 'two')],
            id='adjacent-matches-with-repeated-name',
        ),
        pytest.param('${9.a-b /é\n}', [Variable('9.a-b /é\n', None)], id='name-preserves-punctuation-and-whitespace'),
        pytest.param(
            '${KEY:-  https://host:80/a{b # $HOME\n-:=  }tail',
            [Variable('KEY', '  https://host:80/a{b # $HOME\n-:=  '), Literal('tail')],
            id='default-preserves-punctuation-and-whitespace',
        ),
        pytest.param(
            '${A:-${B:-fallback}}',
            [Variable('A', '${B:-fallback'), Literal('}')],
            id='default-ends-at-first-closing-brace',
        ),
        pytest.param('${a{b$z}}', [Variable('a{b$z', None), Literal('}')], id='name-ends-at-first-closing-brace'),
        pytest.param(
            '${A-fallback}${B+word}${C?err}',
            [Variable('A-fallback', None), Variable('B+word', None), Variable('C?err', None)],
            id='unseparated-punctuation-belongs-to-name',
        ),
        pytest.param(
            '${A-fallback} ${B:word} ${C:=word} ${D:+word} ${E:?word} ${F: -word}',
            [Variable('A-fallback', None), Literal(' ${B:word} ${C:=word} ${D:+word} ${E:?word} ${F: -word}')],
            id='only-colon-minus-introduces-default',
        ),
        pytest.param(
            '${BAD:word} then ${GOOD} and ${OPEN:-unfinished',
            [Literal('${BAD:word} then '), Variable('GOOD', None), Literal(' and ${OPEN:-unfinished')],
            id='valid-match-between-malformed-forms',
        ),
        pytest.param('text ${UNCLOSED', [Literal('text ${UNCLOSED')], id='unterminated-name'),
        pytest.param(
            r'\${NAME} $$${OTHER}',
            [Literal('\\'), Variable('NAME', None), Literal(' $$'), Variable('OTHER', None)],
            id='backslash-and-extra-dollars-are-preserved',
        ),
    ],
)
def test_parse_variables(value, expected):
    assert list(parse_variables(value)) == expected


def test_parse_variables_can_be_consumed_incrementally():
    atoms = parse_variables('left${VALUE:-right}!')

    assert iter(atoms) is atoms
    assert next(atoms) == Literal('left')
    assert next(atoms) == Variable('VALUE', 'right')
    assert next(atoms) == Literal('!')
    with pytest.raises(StopIteration):
        next(atoms)
