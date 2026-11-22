import pytest

from stdnum.br.cpf import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('52998224725', '52998224725'),
        ('529.982.247-25', '52998224725'),
        ('529 982 247 25', '52998224725'),
        ('\t\n 529.982.247-25 \r\n', '52998224725'),
        ('-5.2 9-9.8 2-2.4 7-2.5-', '52998224725'),
        ('\t000.000.001-91\n', '00000000191'),
        ('00000003700', '00000003700'),
        ('12345678909', '12345678909'),
        ('11111111111', '11111111111'),
        ('99999999999', '99999999999'),
    ],
)
def test_validate_returns_compact_cpf(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' \t.-\n ',
        '0',
        '0000000000',
        '000.000.000-00',
        '000000000000',
        '529.982.247-2A',
        '5299822472x5',
        '5299822472',
        '+52998224725',
        '529982247_25',
        '529/982/247-25',
        '529\n98224725',
        '5299822472٥',
        '5299822472⁵',
    ],
)
def test_validate_rejects_invalid_format(number):
    with pytest.raises(InvalidFormat):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '1',
        '529.982.247-2',
        '529.982.247-250',
        '052998224725',
        '00.000.000-1',
    ],
)
def test_validate_rejects_incorrect_length_after_compacting(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '529.982.247-35',
        '529.982.247-26',
        '529.982.247-52',
        '62998224725',
        '00000000001',
        '00000003701',
        '00000003710',
    ],
)
def test_validate_rejects_incorrect_check_digits(number):
    with pytest.raises(InvalidChecksum):
        validate(number)


@pytest.mark.parametrize('body', ['529982247', '000000037', '123456789'])
def test_validate_accepts_only_the_correct_suffix(body):
    expected_suffix = {'529982247': '25', '000000037': '00', '123456789': '09'}[body]
    for value in range(100):
        suffix = f'{value:02d}'
        number = body + suffix
        if suffix == expected_suffix:
            assert validate(number) == number
        else:
            with pytest.raises(InvalidChecksum):
                validate(number)


def reference_check_digit(digits):
    remainder = sum(
        weight * int(digit) for weight, digit in enumerate(reversed(digits), start=2)
    ) % 11
    return '0' if remainder < 2 else str(11 - remainder)


@pytest.mark.parametrize('position', range(9))
@pytest.mark.parametrize('digit', '123456789')
def test_validate_applies_the_checksum_weights_at_each_position(position, digit):
    body = '0' * position + digit + '0' * (8 - position)
    first_check_digit = reference_check_digit(body)
    second_check_digit = reference_check_digit(body + first_check_digit)
    number = body + first_check_digit + second_check_digit

    assert validate(number) == number
