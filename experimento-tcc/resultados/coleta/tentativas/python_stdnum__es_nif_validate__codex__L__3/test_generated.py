import pytest

from stdnum.es.nif import validate
from stdnum.exceptions import (
    InvalidChecksum,
    InvalidFormat,
    InvalidLength,
    ValidationError,
)


@pytest.mark.parametrize(
    'number',
    [
        '12345678Z',
        '01234567L',
        'X1234567L',
        'Y1234567X',
        'Z1234567R',
        'K1234567L',
        'L1234567L',
        'M1234567L',
        'M0000023T',
        'A58818501',
        'B99286320',
        'P1234567D',
        'N1234567D',
    ],
)
def test_validate_accepts_canonical_nif(number):
    assert validate(number) == number


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('\t e-s 12 345-678-z \r\n', '12345678Z'),
        ('es-y-123 4567-x', 'Y1234567X'),
        ('\n m 000-0023-t\t', 'M0000023T'),
        (' es-p 1234-567-d ', 'P1234567D'),
    ],
)
def test_validate_returns_compact_nif(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    'number',
    [
        '12345678A',
        'X1234567R',
        'Y1234567L',
        'Z1234567X',
        'K1234567D',
        'L1234567A',
        'M12345670',
        'A58818502',
        'B99286321',
        'P1234567E',
    ],
)
def test_validate_rejects_wrong_checksum(number):
    with pytest.raises(InvalidChecksum):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        'K123456S',
        'K12345678Z',
        'es-k 123-456-s',
    ],
)
def test_validate_requires_nine_characters_after_compaction(number):
    with pytest.raises(InvalidLength):
        validate(number)


@pytest.mark.parametrize(
    'number',
    [
        'K12A4567L',
        'K12A456L',
        'K+123456S',
        'K123_456S',
        'K12\t34567L',
        'K12ES34567L',
        'ESES12345678Z',
        'PT12345678Z',
    ],
)
def test_validate_checks_middle_digits_before_length_and_checksum(number):
    with pytest.raises(InvalidFormat):
        validate(number)


@pytest.mark.parametrize('number', ['', ' \t--\n', 'ES', 'I1234567L', '@1234567L'])
def test_validate_rejects_missing_number_or_unsupported_initial(number):
    with pytest.raises(ValidationError):
        validate(number)
