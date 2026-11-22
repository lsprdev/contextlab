import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('', [], id='empty-input'),
        pytest.param('  plain\ntext\t ', [Literal('  plain\ntext\t ')], id='literal-whitespace'),
        pytest.param('$NAME {NAME} $(NAME) ${OPEN', [Literal('$NAME {NAME} $(NAME) ${OPEN')], id='unmatched-syntax'),
        pytest.param('${NAME}', [Variable('NAME', None)], id='variable-only'),
        pytest.param('${NAME:-}', [Variable('NAME', '')], id='explicitly-empty-default'),
        pytest.param('${}', [Variable('', None)], id='empty-name'),
        pytest.param('${:-fallback}', [Variable('', 'fallback')], id='empty-name-with-default'),
        pytest.param('${:-}', [Variable('', '')], id='empty-name-and-default'),
        pytest.param('${A}tail', [Variable('A', None), Literal('tail')], id='variable-at-start'),
        pytest.param('head${A}', [Literal('head'), Variable('A', None)], id='variable-at-end'),
        pytest.param('head${A}middle${B:-fallback}tail\n', [Literal('head'), Variable('A', None), Literal('middle'), Variable('B', 'fallback'), Literal('tail\n')], id='literal-spans-around-variables'),
        pytest.param('${A}${A:-one}${A:-two}${A}', [Variable('A', None), Variable('A', 'one'), Variable('A', 'two'), Variable('A', None)], id='adjacent-matches-in-order'),
        pytest.param('${ 9-é.名#=\t\n }', [Variable(' 9-é.名#=\t\n ', None)], id='verbatim-name'),
        pytest.param('${A:-  one:two:-$B # x\nline { \t}', [Variable('A', '  one:two:-$B # x\nline { \t')], id='verbatim-default'),
        pytest.param('${A:+alt}|${A-default}|${A:bad}|${A:=x}|${A:?x}', [Literal('${A:+alt}|'), Variable('A-default', None), Literal('|${A:bad}|${A:=x}|${A:?x}')], id='only-colon-hyphen-introduces-default'),
        pytest.param('${BAD:invalid}${GOOD} ${OPEN:-', [Literal('${BAD:invalid}'), Variable('GOOD', None), Literal(' ${OPEN:-')], id='malformed-text-around-valid-match'),
        pytest.param(r'\${A}$${B}', [Literal('\\'), Variable('A', None), Literal('$'), Variable('B', None)], id='backslash-and-extra-dollar-are-literal'),
        pytest.param('${A:-${B}}${C}', [Variable('A', '${B'), Literal('}'), Variable('C', None)], id='default-ends-at-first-closing-brace'),
        pytest.param('${outer${inner}}', [Variable('outer${inner', None), Literal('}')], id='opening-brace-in-name'),
        pytest.param('${BAD:${GOOD}}', [Literal('${BAD:'), Variable('GOOD', None), Literal('}')], id='valid-match-inside-malformed-expression'),
    ],
)
def test_parse_variables_yields_expected_atoms(value, expected):
    assert list(parse_variables(value)) == expected


def test_parse_variables_returns_a_single_pass_iterator():
    atoms = parse_variables('before${KEY:-fallback}after')

    assert iter(atoms) is atoms
    assert next(atoms) == Literal('before')
    assert next(atoms) == Variable('KEY', 'fallback')
    assert next(atoms) == Literal('after')
    with pytest.raises(StopIteration):
        next(atoms)
