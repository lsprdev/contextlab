import pytest

from stdnum.exceptions import (
    InvalidChecksum,
    InvalidComponent,
    InvalidFormat,
    InvalidLength,
)
from stdnum.isbn import validate


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('0306406152', '0306406152'),
        (' \t0-306 40615-2\n', '0306406152'),
        ('306-40615-2', '0306406152'),
        ('0-8044-2957-x', '080442957X'),
        ('8044-2957-x', '080442957X'),
        ('123456789X', '123456789X'),
        ('9790000006', '9790000006'),
        ('0000000000', '0000000000'),
        ('\n978 0-306-40615 7\t', '9780306406157'),
        ('979-10-90636-07-1', '9791090636071'),
        ('9790000000001', '9790000000001'),
    ],
)
def test_validate_returns_compact_isbn_by_default(number, expected):
    assert validate(number) == expected
    assert validate(number, convert=False) == expected


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        ('0-306 40615-2', '9780306406157'),
        ('306-40615-2', '9780306406157'),
        ('0-8044-2957-x', '9780804429573'),
        ('8044-2957-x', '9780804429573'),
        ('123456789X', '9781234567897'),
        ('000000000', '9780000000002'),
        (' 978-0-306-40615-7 ', '9780306406157'),
        ('979 10 90636 07 1', '9791090636071'),
    ],
)
def test_validate_with_conversion_returns_compact_isbn13(number, expected):
    assert validate(number, convert=True) == expected


@pytest.mark.parametrize('convert', [False, True])
@pytest.mark.parametrize(
    ('number', 'error'),
    [
        ('X306406152', InvalidFormat),
        ('0/306406152', InvalidFormat),
        ('97803064061X7', InvalidFormat),
        ('978030640615X', InvalidFormat),
        ('12A4', InvalidFormat),
        ('12345670', InvalidLength),
        ('12345678901', InvalidLength),
        ('036000291452', InvalidLength),
        ('10012345000017', InvalidLength),
        ('0-306-40615-3', InvalidChecksum),
        ('306406153', InvalidChecksum),
        ('030640615X', InvalidChecksum),
        ('030640615?', InvalidChecksum),
        ('0804429570', InvalidChecksum),
        ('9780306406158', InvalidChecksum),
        ('9791090636072', InvalidChecksum),
        ('9770000000004', InvalidChecksum),
        ('9770000000003', InvalidComponent),
        ('9800000000007', InvalidComponent),
        ('4006381333931', InvalidComponent),
    ],
)
def test_validate_rejects_invalid_numbers(number, error, convert):
    with pytest.raises(error) as exc_info:
        validate(number, convert=convert)
    assert exc_info.type is error


@pytest.mark.parametrize('isbn', ['123456789X', '9781234567897', '9791090636071'])
def test_validate_detects_a_single_digit_change_at_each_body_position(isbn):
    for position, digit in enumerate(isbn[:-1]):
        replacement = str((int(digit) + 1) % 10)
        changed = isbn[:position] + replacement + isbn[position + 1:]
        with pytest.raises(InvalidChecksum):
            validate(changed)
