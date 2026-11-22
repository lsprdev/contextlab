import pytest

from stdnum.br.cnpj import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('11222333000181', '11222333000181'),
        ('04.252.011/0001-10', '04252011000110'),
        (' \t04 .252.011 / 0001 - 10\r\n', '04252011000110'),
        ('０４．２５２．０１１／０００１−１０', '04252011000110'),
        ('12ABC34501DE35', '12ABC34501DE35'),
        ('\t12.aBc.345/01dE-35\n', '12ABC34501DE35'),
        ('z0.000.000/0000-01', 'Z0000000000001'),
        ('00.000.000/000A-04', '00000000000A04'),
        ('00.000.000/000F-00', '00000000000F00'),
        ('00.000.000/0001-91', '00000000000191'),
        ('11111111111180', '11111111111180'),
        ('00.000.000/000١-91', '00000000000١91'),
        ('ß0.000.000/000-43', 'SS000000000043'),
    ],
)
def test_validate_returns_normalized_cnpj(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' .-/\t\n',
        '12ABC34501DE3!',
        '!12ABC34501DE3',
        '12ABC_4501DE35',
        '12ÁBC34501DE35',
        '12.ABC.345/01DE–3,5',
        '12ABC\t34501DE35',
        '12ABC34501DE35\nX',
        '12ABC34501DE35!',
        'A!',
        None,
        11222333000181,
        b'11222333000181',
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat) as exc:
        validate(number)
    assert exc.type is InvalidFormat


@pytest.mark.parametrize(
    'number',
    [
        '00000000000000',
        '00.000.000/0000-12',
        '00.000.000/0000-AB',
        '000000000000',
        '0000000000001',
        '000000000000123',
    ],
)
def test_validate_rejects_zero_base_before_length_or_checksum(number):
    with pytest.raises(InvalidFormat) as exc:
        validate(number)
    assert exc.type is InvalidFormat


@pytest.mark.parametrize(
    'number',
    [
        'A',
        '00000000000',
        '12ABC34501DE',
        '12.aBc.345/01de-3',
        '12.aBc.345/01de-350',
        '1122233300018100',
    ],
)
def test_validate_rejects_incorrect_normalized_length(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '11222333000191',
        '11222333000182',
        '11222333000118',
        '12.abc.345/01de-45',
        '12.abc.345/01de-36',
        '12ABC34501DF35',
        '12ABC34501DEA5',
        '12ABC34501DE3A',
    ],
)
def test_validate_rejects_incorrect_check_digits(number):
    with pytest.raises(InvalidChecksum):
        validate(number)
