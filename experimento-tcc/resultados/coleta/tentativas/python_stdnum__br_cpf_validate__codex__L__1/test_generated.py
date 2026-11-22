import pytest

from stdnum.br.cpf import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('52998224725', '52998224725'),
        ('529.982.247-25', '52998224725'),
        ('\t\n 529.982.247-25 \r\n', '52998224725'),
        ('-.5 29--98.2 2.47-2 5.-', '52998224725'),
        ('000.000.001-91', '00000000191'),
        ('00000000604', '00000000604'),
        ('00000001406', '00000001406'),
        ('12345678909', '12345678909'),
        ('11144477735', '11144477735'),
    ],
)
def test_validate_returns_compact_cpf(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize('digit', '123456789')
def test_validate_accepts_nonzero_repeated_digits_with_valid_checksum(digit):
    number = digit * 11
    assert validate(number) == number


def cpf_from_prefix(prefix):
    digits = [int(char) for char in prefix]
    for first_weight in (10, 11):
        total = sum(weight * digit for weight, digit in zip(range(first_weight, 1, -1), digits))
        remainder = total % 11
        digits.append(0 if remainder < 2 else 11 - remainder)
    return ''.join(str(digit) for digit in digits)


@pytest.mark.parametrize('position', range(9))
@pytest.mark.parametrize('digit', '123456789')
def test_validate_accepts_checksums_calculated_from_each_prefix_position(position, digit):
    prefix = '0' * position + digit + '0' * (8 - position)
    number = cpf_from_prefix(prefix)
    assert validate(number) == number


@pytest.mark.parametrize(
    ('prefix', 'valid_suffix'),
    [('529982247', '25'), ('000000001', '91'), ('123456789', '09')],
)
@pytest.mark.parametrize('suffix', [f'{value:02d}' for value in range(100)])
def test_validate_checks_both_check_digits(prefix, valid_suffix, suffix):
    number = prefix + suffix
    if suffix == valid_suffix:
        assert validate(number) == number
    else:
        with pytest.raises(InvalidChecksum) as error:
            validate(number)
        assert type(error.value) is InvalidChecksum


def test_validate_checks_checksum_after_removing_separators():
    with pytest.raises(InvalidChecksum) as error:
        validate(' 529.982.247-24 ')
    assert type(error.value) is InvalidChecksum


@pytest.mark.parametrize(
    'number',
    [
        '',
        ' .- \t\n',
        '0',
        '000.000.000-00',
        '000000000000',
        'abc',
        '529.982.247-2a',
        '529/982/247-25',
        '+52998224725',
        '529_982_24725',
    ],
)
def test_validate_rejects_empty_zero_and_nonnumeric_values_as_invalid_format(number):
    with pytest.raises(InvalidFormat) as error:
        validate(number)
    assert type(error.value) is InvalidFormat


@pytest.mark.parametrize(
    'number',
    ['1', '529982247', '529.982.247-2', '529.982.247-025', '000000000001'],
)
def test_validate_rejects_positive_numbers_with_wrong_compact_length(number):
    with pytest.raises(InvalidLength) as error:
        validate(number)
    assert type(error.value) is InvalidLength
