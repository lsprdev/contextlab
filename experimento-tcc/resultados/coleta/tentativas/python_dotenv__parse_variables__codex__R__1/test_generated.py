import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        pytest.param('', [], id='empty-input'),
        pytest.param('  plain\ntext  ', [Literal('  plain\ntext  ')], id='literal-only'),
        pytest.param('${A}', [Variable('A', None)], id='variable-only'),
        pytest.param('before${A}', [Literal('before'), Variable('A', None)], id='leading-literal'),
        pytest.param('${A}after', [Variable('A', None), Literal('after')], id='trailing-literal'),
        pytest.param(
            '  ${A}/\n${B:-fallback}  ',
            [Literal('  '), Variable('A', None), Literal('/\n'), Variable('B', 'fallback'), Literal('  ')],
            id='literal-spans-preserve-whitespace',
        ),
        pytest.param(
            '${A}${B:-fallback}${A:-}',
            [Variable('A', None), Variable('B', 'fallback'), Variable('A', '')],
            id='adjacent-variables-with-distinct-defaults',
        ),
        pytest.param(
            'p${X}q${X}r${X}s',
            [Literal('p'), Variable('X', None), Literal('q'), Variable('X', None), Literal('r'), Variable('X', None), Literal('s')],
            id='repeated-match-text-at-different-offsets',
        ),
        pytest.param('${}${:-fallback}${:-}', [Variable('', None), Variable('', 'fallback'), Variable('', '')], id='empty-names'),
        pytest.param('${ a.b-9/{c$=ç\n\t}', [Variable(' a.b-9/{c$=ç\n\t', None)], id='name-characters'),
        pytest.param(
            '${A:-  x:y:-$B={é\n\t }',
            [Variable('A', '  x:y:-$B={é\n\t ')],
            id='default-characters',
        ),
        pytest.param('${A:--}', [Variable('A', '-')], id='hyphen-in-default'),
        pytest.param('${A:-x}y}', [Variable('A', 'x'), Literal('y}')], id='default-stops-at-first-brace'),
        pytest.param('${A:-${B:-x}}', [Variable('A', '${B:-x'), Literal('}')], id='nested-looking-default'),
        pytest.param('${outer${inner}}', [Variable('outer${inner', None), Literal('}')], id='nested-looking-name'),
        pytest.param('$A $$A {A} $ {A} $', [Literal('$A $$A {A} $ {A} $')], id='dollar-and-brace-literals'),
        pytest.param(
            r'\${A} $${B}',
            [Literal('\\'), Variable('A', None), Literal(' $'), Variable('B', None)],
            id='backslash-and-extra-dollar-are-literal',
        ),
        pytest.param(
            '${A:x}${B:}${C-x adds text',
            [Literal('${A:x}${B:}${C-x adds text')],
            id='invalid-operator-and-unclosed-reference',
        ),
        pytest.param('${A-x}', [Variable('A-x', None)], id='hyphen-without-colon-is-part-of-name'),
        pytest.param('${A-}', [Variable('A-', None)], id='trailing-name-hyphen'),
        pytest.param('${A:-unfinished', [Literal('${A:-unfinished')], id='unclosed-default'),
        pytest.param(
            '${A:+x}${B-x}${C:?error}${D:=value}',
            [Literal('${A:+x}'), Variable('B-x', None), Literal('${C:?error}${D:=value}')],
            id='only-colon-hyphen-introduces-a-default',
        ),
        pytest.param(
            '${bad:${OK}}${NEXT}',
            [Literal('${bad:'), Variable('OK', None), Literal('}'), Variable('NEXT', None)],
            id='valid-matches-after-an-invalid-opening',
        ),
    ],
)
def test_parse_variables_yields_atoms_in_source_order(value, expected):
    atoms = parse_variables(value)

    assert iter(atoms) is atoms
    assert list(atoms) == expected


def test_parse_variables_yields_atoms_that_resolve_with_the_parsed_names_and_defaults():
    atoms = list(parse_variables('${present:-fallback}|${missing:-fallback}|${unset}|${empty:-fallback}|${none:-fallback}'))
    env = {'present': 'value', 'empty': '', 'none': None}

    assert ''.join(atom.resolve(env) for atom in atoms) == 'value|fallback|||'
