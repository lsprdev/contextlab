import pytest

from stdnum.exceptions import (
    InvalidChecksum,
    InvalidComponent,
    InvalidFormat,
    InvalidLength,
)
from stdnum.isbn import validate


@pytest.mark.parametrize(
    ('number', 'compact', 'isbn13'),
    [
        pytest.param('0306406152', '0306406152', '9780306406157', id='isbn10'),
        pytest.param('\t 0-306 40615-2 \n', '0306406152', '9780306406157', id='isbn10-separators'),
        pytest.param('0-8044-2957-x', '080442957X', '9780804429573', id='lowercase-x'),
        pytest.param('123456789X', '123456789X', '9781234567897', id='nonzero-leading-digit'),
        pytest.param('306-40615 2', '0306406152', '9780306406157', id='missing-leading-zero'),
        pytest.param('8044-2957-x', '080442957X', '9780804429573', id='missing-zero-with-x'),
        pytest.param('9780306406157', '9780306406157', '9780306406157', id='isbn13-978'),
        pytest.param(' 978-0 306-40615 7 ', '9780306406157', '9780306406157', id='isbn13-separators'),
        pytest.param('979-10-90636-07-1', '9791090636071', '9791090636071', id='isbn13-979'),
        pytest.param('9790000000001', '9790000000001', '9790000000001', id='group-unchecked'),
    ],
)
def test_validate_returns_expected_representation(number, compact, isbn13):
    assert validate(number) == compact
    assert validate(number, convert=False) == compact
    assert validate(number, convert=True) == isbn13


@pytest.mark.parametrize('convert', [False, True])
@pytest.mark.parametrize(
    ('number', 'error'),
    [
        pytest.param('0306406153', InvalidChecksum, id='isbn10-wrong-check-digit'),
        pytest.param('0306416152', InvalidChecksum, id='isbn10-changed-body'),
        pytest.param('0804429570', InvalidChecksum, id='isbn10-x-required'),
        pytest.param('030640615X', InvalidChecksum, id='isbn10-unexpected-x'),
        pytest.param('030640615A', InvalidChecksum, id='isbn10-letter-as-check-digit'),
        pytest.param('306-40615-3', InvalidChecksum, id='missing-zero-wrong-check-digit'),
        pytest.param('978-0-306-40615-8', InvalidChecksum, id='isbn13-wrong-check-digit'),
        pytest.param('9791090636072', InvalidChecksum, id='isbn13-979-wrong-check-digit'),
        pytest.param('978030640615x', InvalidFormat, id='isbn13-x-as-check-digit'),
        pytest.param('03064X6152', InvalidFormat, id='isbn10-x-in-body'),
        pytest.param('97803064A6157', InvalidFormat, id='isbn13-letter-in-body'),
        pytest.param('978/0306406157', InvalidFormat, id='slash-in-body'),
        pytest.param('A123', InvalidFormat, id='format-before-length'),
        pytest.param('96385074', InvalidLength, id='ean8-length'),
        pytest.param('00306406152', InvalidLength, id='eleven-digits'),
        pytest.param('036000291452', InvalidLength, id='ean12-length'),
        pytest.param('09780306406157', InvalidLength, id='ean14-length'),
        pytest.param('4006381333931', InvalidComponent, id='ean13-non-bookland-prefix'),
        pytest.param('9770306406158', InvalidComponent, id='prefix-below-bookland'),
        pytest.param('9800306406152', InvalidComponent, id='prefix-above-bookland'),
        pytest.param('4006381333932', InvalidChecksum, id='checksum-before-prefix'),
        pytest.param('400638133393X', InvalidFormat, id='format-before-prefix'),
    ],
)
def test_validate_raises_expected_error(number, error, convert):
    with pytest.raises(error) as exc_info:
        validate(number, convert=convert)
    assert exc_info.type is error
