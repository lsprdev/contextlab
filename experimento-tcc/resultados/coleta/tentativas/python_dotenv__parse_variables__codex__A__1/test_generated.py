from collections.abc import Iterator

import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('', [], id='empty-input'),
        pytest.param('plain text', [Literal('plain text')], id='literal-only'),
        pytest.param('$NAME and {NAME}', [Literal('$NAME and {NAME}')], id='bare-forms'),
        pytest.param('${NAME}', [Variable('NAME', None)], id='absent-default'),
        pytest.param('${NAME:-}', [Variable('NAME', '')], id='empty-default'),
        pytest.param('${NAME:-fallback}', [Variable('NAME', 'fallback')], id='nonempty-default'),
        pytest.param('${}', [Variable('', None)], id='empty-name'),
        pytest.param('${:-}', [Variable('', '')], id='empty-name-and-default'),
        pytest.param('${:-fallback}', [Variable('', 'fallback')], id='empty-name-with-default'),
        pytest.param('left${A}', [Literal('left'), Variable('A', None)], id='leading-literal'),
        pytest.param('${A}right', [Variable('A', None), Literal('right')], id='trailing-literal'),
        pytest.param(
            'pre${A} / ${B:-bee}\n${C}post',
            [Literal('pre'), Variable('A', None), Literal(' / '), Variable('B', 'bee'),
             Literal('\n'), Variable('C', None), Literal('post')],
            id='multiple-matches-with-gaps',
        ),
        pytest.param(
            '${X:-one}${X}${X:-two}',
            [Variable('X', 'one'), Variable('X', None), Variable('X', 'two')],
            id='adjacent-repeated-names',
        ),
        pytest.param(
            '😀${ 9-á.b /$\t\r\n }終',
            [Literal('😀'), Variable(' 9-á.b /$\t\r\n ', None), Literal('終')],
            id='name-characters-preserved',
        ),
        pytest.param(
            '${A:- café:$B/a{b:-second\t\r\n }',
            [Variable('A', ' café:$B/a{b:-second\t\r\n ')],
            id='default-characters-preserved',
        ),
        pytest.param('${A:--}', [Variable('A', '-')], id='default-starts-with-dash'),
        pytest.param('${A-fallback}', [Variable('A-fallback', None)], id='dash-in-name'),
        pytest.param('${A:}', [Literal('${A:}')], id='colon-alone-is-invalid'),
        pytest.param('${A:=x}', [Literal('${A:=x}')], id='unsupported-operator'),
        pytest.param('${A: -x}', [Literal('${A: -x}')], id='split-default-delimiter'),
        pytest.param('${OPEN', [Literal('${OPEN')], id='unclosed-name'),
        pytest.param('${OPEN:-partial', [Literal('${OPEN:-partial')], id='unclosed-default'),
        pytest.param(
            '${BAD:+no}${OK}${OPEN:-partial',
            [Literal('${BAD:+no}'), Variable('OK', None), Literal('${OPEN:-partial')],
            id='valid-match-between-malformed-forms',
        ),
        pytest.param(
            '${BAD:+${OK}}',
            [Literal('${BAD:+'), Variable('OK', None), Literal('}')],
            id='valid-match-inside-invalid-form',
        ),
        pytest.param(
            '${A:-${B:-fallback}}tail',
            [Variable('A', '${B:-fallback'), Literal('}tail')],
            id='default-ends-at-first-closing-brace',
        ),
        pytest.param(
            '${outer${inner}}',
            [Variable('outer${inner', None), Literal('}')],
            id='opening-brace-in-name',
        ),
        pytest.param(
            r'\${A} $$${B}',
            [Literal('\\'), Variable('A', None), Literal(' $$'), Variable('B', None)],
            id='backslash-and-extra-dollars-are-literal',
        ),
    ],
)
def test_parse_variables_atoms(value, expected):
    assert list(parse_variables(value)) == expected


def test_parse_variables_returns_independent_iterators():
    first = parse_variables('pre${A}post')
    second = parse_variables('${B:-bee}')

    assert isinstance(first, Iterator)
    assert iter(first) is first
    assert next(first) == Literal('pre')
    assert list(second) == [Variable('B', 'bee')]
    assert next(first) == Variable('A', None)
    assert next(first) == Literal('post')
    with pytest.raises(StopIteration):
        next(first)


@pytest.mark.parametrize(
    ('env', 'expected'),
    [
        pytest.param({}, '<fallback>|<>', id='missing-keys'),
        pytest.param({'A': 'set', 'B': 'other'}, '<set>|<other>', id='present-keys'),
        pytest.param({'A': '', 'B': None}, '<>|<>', id='empty-value'),
        pytest.param({'A': None, 'B': ''}, '<>|<>', id='none-value'),
        pytest.param({'A': '${B}', 'B': 'other'}, '<${B}>|<other>', id='verbatim-value'),
    ],
)
def test_parsed_atoms_resolve_in_order(env, expected):
    atoms = parse_variables('<${A:-fallback}>|<${B}>')
    assert ''.join(atom.resolve(env) for atom in atoms) == expected
