import pytest

from stdnum.br.cnpj import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('04252011000110', '04252011000110'),
        ('04.252.011/0001-10', '04252011000110'),
        (' \t04 .252-011 /0001 - 10\r\n', '04252011000110'),
        ('11.222.333/0001-81', '11222333000181'),
        ('12.ABC.345/01DE-35', '12ABC34501DE35'),
        ('12.aBc.345/01dE-35', '12ABC34501DE35'),
        ('a0000000000032', 'A0000000000032'),
        ('zzzzzzzzzzzz62', 'ZZZZZZZZZZZZ62'),
        ('00000000000191', '00000000000191'),
        ('00000000000604', '00000000000604'),
        ('00000000000F00', '00000000000F00'),
        ('10000000000064', '10000000000064'),
        ('11111111111180', '11111111111180'),
    ],
)
def test_validate_returns_compact_cnpj(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' \t-./\n',
        '@4252011000110',
        '04252_11000110',
        '04.252.011/0001-1!',
        'ABC!',
        '00000000000000',
        '00.000.000/0000-01',
        '000000000000',
        '000000000000000',
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat) as error:
        validate(number)
    assert error.type is InvalidFormat


@pytest.mark.parametrize(
    'number',
    [
        'A',
        '00000000000',
        '04.252.011/0001',
        '04.252.011/0001-1',
        '042520110001100',
        '12.abc.345/01de-350',
    ],
)
def test_validate_rejects_incorrect_compact_length(number):
    with pytest.raises(InvalidLength) as error:
        validate(number)
    assert error.type is InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '04.252.011/0001-20',
        '04.252.011/0001-11',
        '04252011000101',
        '04.252.011/0002-10',
        '12.abc.345/01de-45',
        '12.abc.345/01de-36',
        '12.abc.345/01de-A5',
        '12.abc.345/01de-3Z',
        '12.abc.345/01df-35',
        '11111111111111',
    ],
)
def test_validate_rejects_incorrect_check_digits(number):
    with pytest.raises(InvalidChecksum) as error:
        validate(number)
    assert error.type is InvalidChecksum
