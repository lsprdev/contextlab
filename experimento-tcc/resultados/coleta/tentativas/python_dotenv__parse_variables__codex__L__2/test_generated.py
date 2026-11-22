import pytest

from dotenv.variables import Literal, Variable, parse_variables


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('', []),
        ('plain text', [Literal('plain text')]),
        (' \t\n ', [Literal(' \t\n ')]),
        ('$NAME $9 $# $(NAME) {NAME} ${OPEN', [Literal('$NAME $9 $# $(NAME) {NAME} ${OPEN')]),
        ('${NAME}', [Variable('NAME', None)]),
        ('${NAME:-}', [Variable('NAME', '')]),
        ('${NAME:-fallback}', [Variable('NAME', 'fallback')]),
        ('${}', [Variable('', None)]),
        ('${:-}', [Variable('', '')]),
        ('${:-fallback}', [Variable('', 'fallback')]),
        ('left${A}', [Literal('left'), Variable('A', None)]),
        ('${A}right', [Variable('A', None), Literal('right')]),
        ('${A}${B:-second}${A:-}', [Variable('A', None), Variable('B', 'second'), Variable('A', '')]),
        (
            'π\n${A} / ${B:-two}\t${C}\n終',
            [Literal('π\n'), Variable('A', None), Literal(' / '), Variable('B', 'two'),
             Literal('\t'), Variable('C', None), Literal('\n終')],
        ),
        ('${ 9-ü.$\t\n:-  one:two:-three #$x={\n }', [Variable(' 9-ü.$\t\n', '  one:two:-three #$x={\n ')]),
        ('${a{b}', [Variable('a{b', None)]),
        ('${A:word}${B-default}${C:=x}', [Literal('${A:word}'), Variable('B-default', None), Literal('${C:=x}')]),
        ('${A:+x}${A:?x}${A:}${A: -x}', [Literal('${A:+x}${A:?x}${A:}${A: -x}')]),
        ('${bad:word}${OK}${unfinished', [Literal('${bad:word}'), Variable('OK', None), Literal('${unfinished')]),
        ('${A:-${B}}', [Variable('A', '${B'), Literal('}')]),
        (r'\${X} $$${Y}', [Literal('\\'), Variable('X', None), Literal(' $$'), Variable('Y', None)]),
        ('${A}\x00${B:-\x00}', [Variable('A', None), Literal('\x00'), Variable('B', '\x00')]),
    ],
)
def test_parse_variables_yields_expected_atoms(value, expected):
    assert list(parse_variables(value)) == expected


def test_parse_variables_returns_an_iterator():
    atoms = parse_variables('head${NAME:-fallback}tail')

    assert iter(atoms) is atoms
    assert next(atoms) == Literal('head')
    assert next(atoms) == Variable('NAME', 'fallback')
    assert next(atoms) == Literal('tail')
    with pytest.raises(StopIteration):
        next(atoms)


@pytest.mark.parametrize(
    ('env', 'expected'),
    [
        ({}, 'left|fallback||right'),
        ({'A': 'actual', 'B': 'present', 'C': 'value'}, 'left|actual|present|valueright'),
        ({'A': '', 'B': None, 'C': None}, 'left|||right'),
        ({'A': None, 'B': '', 'C': 'other'}, 'left|||otherright'),
    ],
)
def test_parse_variables_atoms_resolve_in_order(env, expected):
    atoms = parse_variables('left|${A:-fallback}|${B:-}|${C}right')

    assert ''.join(atom.resolve(env) for atom in atoms) == expected
