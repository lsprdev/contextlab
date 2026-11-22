import pytest

from stdnum.br.cnpj import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('11222333000181', '11222333000181'),
        ('11.222.333/0001-81', '11222333000181'),
        ('04.252.011/0001-10', '04252011000110'),
        ('00.000.000/0001-91', '00000000000191'),
        ('12.ABC.345/01DE-35', '12ABC34501DE35'),
        ('\t\n 1 2-aBc.345/01 dE - 3 5 \r\n', '12ABC34501DE35'),
        ('zzzzzzzzzzzz62', 'ZZZZZZZZZZZZ62'),
    ],
)
def test_validate_returns_normalized_cnpj(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '00011000000006',
        '01000100000008',
        '00001010000060',
        '11111111111180',
        '90000000000001',
    ],
)
def test_validate_accepts_zero_check_digits(number):
    assert validate(number) == number


@pytest.mark.parametrize(
    ('position', 'check_digits'),
    list(enumerate(('64', '73', '82', '91', '25', '37', '46', '55', '64', '73', '82', '91'))),
)
def test_validate_checks_weights_at_each_base_position(position, check_digits):
    base = '0' * position + '1' + '0' * (11 - position)
    number = base + check_digits
    assert validate(number) == number


def test_validate_accepts_a_unicode_decimal_digit_in_the_base():
    result = validate('\u06611222333000181')
    assert len(result) == 14
    assert result[1:] == '1222333000181'


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' .-/ \t\n',
        '@1222333000181',
        '1122233300018@',
        '11222_33000181',
        '11222\t33000181',
        '11222\n33000181',
        '11222中33000181',
        '@1',
        '00000000000000',
        '00.000.000/0000-99',
        '000000000000',
        '000000000000000',
    ],
)
def test_validate_rejects_invalid_format_before_other_checks(number):
    with pytest.raises(InvalidFormat) as exc_info:
        validate(number)
    assert exc_info.type is InvalidFormat


@pytest.mark.parametrize(
    'number',
    [
        '1',
        '00000000000',
        '11.222.3330001',
        '1122233300018',
        '112223330001810',
        '12.abc.345/01de-3',
        '12.abc.345/01de-350',
    ],
)
def test_validate_rejects_incorrect_compact_length(number):
    with pytest.raises(InvalidLength) as exc_info:
        validate(number)
    assert exc_info.type is InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '11222333000191',
        '11222333000180',
        '11222333000118',
        '112223330001A1',
        '1122233300018A',
        '12.abc.345/01de-45',
        '12.abc.345/01de-34',
        '12.ABC.345/01DF-35',
        '11111111111111',
    ],
)
def test_validate_rejects_incorrect_check_digits(number):
    with pytest.raises(InvalidChecksum) as exc_info:
        validate(number)
    assert exc_info.type is InvalidChecksum
