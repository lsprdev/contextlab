import pytest

from stdnum.br.cpf import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    'number',
    [
        '52998224725',
        '11144477735',
        '01234567890',
        '12345678909',
        '00000001406',
        '00000001910',
        '10000000019',
        '01000000028',
        '00100000037',
        '00010000046',
        '00001000055',
        '00000100064',
        '00000010073',
        '00000001082',
        '00000000191',
    ],
)
def test_validate_returns_valid_digits_unchanged(number):
    assert validate(number) == number


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('529.982.247-25', '52998224725'),
        ('\t  012.345.678-90  \r\n', '01234567890'),
        ('529 982 247 25', '52998224725'),
        (' .52-9.98 2-2.47-2 5. ', '52998224725'),
    ],
)
def test_validate_returns_compact_form(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize('digit', '123456789')
def test_validate_accepts_positive_repeated_digits_with_matching_checksum(digit):
    number = digit * 11
    assert validate(number) == number


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' \t\r\n',
        ' . - . ',
        '0',
        '000.000.000-00',
        '000000000000',
        'X',
        '529.982.247-2X',
        '+52998224725',
        '529/982/247-25',
        '\u06652998224725',
    ],
)
def test_validate_rejects_invalid_format_before_length_or_checksum(number):
    with pytest.raises(InvalidFormat):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '1',
        '529982247',
        '529.982.247-2',
        '052998224725',
        '529.982.247-125',
        '1' * 30,
    ],
)
def test_validate_requires_eleven_digits_after_compacting(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize('position', range(11))
def test_validate_rejects_a_changed_digit_at_every_position(position):
    valid = '52998224725'
    changed_digit = str((int(valid[position]) + 1) % 10)
    number = valid[:position] + changed_digit + valid[position + 1:]
    with pytest.raises(InvalidChecksum):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        '529.982.247-52',
        '529.982.247-15',
        '529.982.247-24',
        '012.345.678-91',
        '123.456.789-19',
        '000.000.000-01',
    ],
)
def test_validate_rejects_incorrect_check_digits_after_compacting(number):
    with pytest.raises(InvalidChecksum):
        validate(number)
