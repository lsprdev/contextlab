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
        ('\t 0-306 40615-2 \n', '0306406152'),
        (' 306-40615 2 ', '0306406152'),
        ('0-8044-2957-x', '080442957X'),
        ('8044 2957-x', '080442957X'),
        ('1861972717', '1861972717'),
        ('1500000000', '1500000000'),
        ('0000000019', '0000000019'),
        (' 978-0-306 40615-7 ', '9780306406157'),
        ('979-10-90636-07-1', '9791090636071'),
        ('9789999999991', '9789999999991'),
        ('9799999999990', '9799999999990'),
    ],
)
def test_validate_returns_compact_isbn_by_default(number, expected):
    assert validate(number) == expected


@pytest.mark.parametrize(
    ('number', 'isbn10', 'isbn13'),
    [
        ('0-306-40615-2', '0306406152', '9780306406157'),
        (' 306 40615-2 ', '0306406152', '9780306406157'),
        ('0 8044-2957-x', '080442957X', '9780804429573'),
        ('8044-2957-x', '080442957X', '9780804429573'),
        ('1861972717', '1861972717', '9781861972712'),
    ],
)
def test_validate_optionally_converts_isbn10(number, isbn10, isbn13):
    assert validate(number, convert=False) == isbn10
    assert validate(number, convert=True) == isbn13


@pytest.mark.parametrize(
    ('number', 'expected'),
    [
        (' 978-0-306 40615-7 ', '9780306406157'),
        (' 979 10-90636-07-1 ', '9791090636071'),
    ],
)
def test_validate_preserves_isbn13_when_conversion_is_requested(number, expected):
    assert validate(number, convert=True) == expected


@pytest.mark.parametrize('convert', [False, True])
@pytest.mark.parametrize(
    ('number', 'error'),
    [
        pytest.param('0306406153', InvalidChecksum, id='isbn10-check-digit'),
        pytest.param('030640615X', InvalidChecksum, id='isbn10-unexpected-x'),
        pytest.param('0804429570', InvalidChecksum, id='isbn10-expected-x'),
        pytest.param('030640615A', InvalidChecksum, id='isbn10-letter-in-check-position'),
        pytest.param('306-40615-3', InvalidChecksum, id='nine-digit-checksum'),
        pytest.param('978-0-306-40615-8', InvalidChecksum, id='978-checksum'),
        pytest.param('9791090636072', InvalidChecksum, id='979-checksum'),
        pytest.param('4006381333932', InvalidChecksum, id='ean-checksum-before-prefix'),
        pytest.param('9770000000003', InvalidComponent, id='prefix-below-bookland'),
        pytest.param('9800000000007', InvalidComponent, id='prefix-above-bookland'),
        pytest.param('4006381333931', InvalidComponent, id='valid-non-bookland-ean'),
        pytest.param('03064X6152', InvalidFormat, id='isbn10-x-in-body'),
        pytest.param('97803064X6157', InvalidFormat, id='isbn13-letter-in-body'),
        pytest.param('978030640615x', InvalidFormat, id='isbn13-letter-in-check-position'),
        pytest.param('0/306/40615/2', InvalidFormat, id='unsupported-separator'),
        pytest.param('123A', InvalidFormat, id='format-before-length'),
        pytest.param(' - ', InvalidFormat, id='empty-after-compaction'),
        pytest.param('12345678', InvalidLength, id='eight-digits'),
        pytest.param('12345678901', InvalidLength, id='eleven-digits'),
        pytest.param('978030640615', InvalidLength, id='twelve-digits'),
        pytest.param('97803064061570', InvalidLength, id='fourteen-digits'),
        pytest.param('1234X', InvalidLength, id='length-with-x-at-end'),
    ],
)
def test_validate_rejects_invalid_numbers(number, error, convert):
    with pytest.raises(error):
        validate(number, convert=convert)
