import pytest

from stdnum.br.cpf import validate
from stdnum.exceptions import InvalidChecksum, InvalidFormat, InvalidLength


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('52998224725', '52998224725'),
        ('529.982.247-25', '52998224725'),
        ('529 982 247 25', '52998224725'),
        ('\t\n529.982.247-25\r\n', '52998224725'),
        (' -5.2-9 9.8-2 2.4-7 2.5- ', '52998224725'),
        ('012.345.678-90', '01234567890'),
        ('111.444.777-35', '11144477735'),
        ('123.456.789-09', '12345678909'),
    ],
)
def test_validate_returns_compact_cpf(raw, expected):
    assert validate(raw) == expected


@pytest.mark.parametrize('digit', '123456789')
def test_validate_accepts_positive_repeated_digits_with_matching_checksum(digit):
    number = digit * 11
    assert validate(number) == number


@pytest.mark.parametrize(
    'number',
    [
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
def test_validate_checks_each_position_of_the_base(number):
    assert validate(number) == number


@pytest.mark.parametrize(
    'raw',
    [
        '',
        ' \t\n ',
        ' .--. ',
        '0',
        '0000000000',
        '00000000000',
        '000000000000',
        ' 000.000.000-00 ',
        'x',
        '529.982.247-2x',
        '529.982.247/25',
        '529.982.247_25',
        '+52998224725',
        '52998224725x',
    ],
)
def test_validate_raises_invalid_format_for_empty_zero_or_nonnumeric_input(raw):
    with pytest.raises(InvalidFormat) as error:
        validate(raw)
    assert error.type is InvalidFormat


@pytest.mark.parametrize(
    'raw',
    [
        '1',
        '0000000001',
        '529.982.247-2',
        '052998224725',
        '529.982.247-250',
    ],
)
def test_validate_raises_invalid_length_after_compacting(raw):
    with pytest.raises(InvalidLength) as error:
        validate(raw)
    assert error.type is InvalidLength


@pytest.mark.parametrize(
    'raw',
    ['529.982.247-35', ' 529.982.247-26 ', '529.982.247-52', '000.000.000-01'],
)
def test_validate_raises_invalid_checksum_for_formatted_input(raw):
    with pytest.raises(InvalidChecksum) as error:
        validate(raw)
    assert error.type is InvalidChecksum


@pytest.mark.parametrize(
    ('base', 'expected_suffix'),
    [
        ('529982247', '25'),
        ('000000006', '04'),
        ('000000014', '06'),
        ('000000018', '30'),
        ('000000019', '10'),
    ],
)
@pytest.mark.parametrize('suffix', [f'{value:02d}' for value in range(100)])
def test_validate_accepts_only_the_matching_pair_of_check_digits(
    base, expected_suffix, suffix
):
    number = base + suffix
    if suffix == expected_suffix:
        assert validate(number) == number
    else:
        with pytest.raises(InvalidChecksum) as error:
            validate(number)
        assert error.type is InvalidChecksum
