import pytest

from stdnum.exceptions import (
    InvalidChecksum,
    InvalidComponent,
    InvalidFormat,
    InvalidLength,
)
from stdnum.isbn import validate


@pytest.mark.parametrize(
    'number, compact, converted',
    [
        ('0-306-40615-2', '0306406152', '9780306406157'),
        ('\t 0 306-40615 2 \n', '0306406152', '9780306406157'),
        ('０－３０６－４０６１５－２', '0306406152', '9780306406157'),
        ('0\u20118044\u00a02957\u2013x', '080442957X', '9780804429573'),
        ('3-06-40615-2', '0306406152', '9780306406157'),
        ('8044 2957 x', '080442957X', '9780804429573'),
        ('0000000000', '0000000000', '9780000000002'),
        ('9780000003', '9780000003', '9789780000004'),
        (' 978-0 306-40615-7 ', '9780306406157', '9780306406157'),
        ('\n979-10-90636-07-1\t', '9791090636071', '9791090636071'),
        ('9780000000040', '9780000000040', '9780000000040'),
        ('9790000000001', '9790000000001', '9790000000001'),
    ],
)
def test_validate_returns_normalized_isbn(number, compact, converted):
    assert validate(number) == compact
    assert validate(number, convert=False) == compact
    assert validate(number, convert=True) == converted


@pytest.mark.parametrize('convert', [False, True])
@pytest.mark.parametrize(
    'number, expected_error',
    [
        pytest.param('0-306-40615-3', InvalidChecksum, id='isbn10-checksum'),
        pytest.param('306406153', InvalidChecksum, id='nine-digit-checksum'),
        pytest.param('0804429570', InvalidChecksum, id='isbn10-requires-x'),
        pytest.param('030640615x', InvalidChecksum, id='isbn10-unexpected-x'),
        pytest.param('030640615A', InvalidChecksum, id='isbn10-letter-check-digit'),
        pytest.param('978-0-306-40615-8', InvalidChecksum, id='isbn13-978-checksum'),
        pytest.param('9791090636072', InvalidChecksum, id='isbn13-979-checksum'),
        pytest.param('978030640615x', InvalidFormat, id='isbn13-letter-check-digit'),
        pytest.param('0X06406152', InvalidFormat, id='isbn10-x-in-body'),
        pytest.param('97803064061X7', InvalidFormat, id='isbn13-x-in-body'),
        pytest.param('٠306406152', InvalidFormat, id='unmapped-unicode-digit'),
        pytest.param('030640615٢', InvalidChecksum, id='isbn10-unmapped-check-digit'),
        pytest.param('978030640615٧', InvalidFormat, id='isbn13-unmapped-check-digit'),
        pytest.param('0.306406152', InvalidFormat, id='period-separator'),
        pytest.param('0\t306406152', InvalidFormat, id='internal-tab'),
        pytest.param('ISBN 978-0-306-40615-7', InvalidFormat, id='isbn-label'),
        pytest.param('4006381333931', InvalidComponent, id='valid-non-book-ean'),
        pytest.param('9779780000005', InvalidComponent, id='bookland-prefix-in-body'),
        pytest.param('9800000000007', InvalidComponent, id='prefix-above-979'),
        pytest.param('4006381333932', InvalidChecksum, id='checksum-before-prefix'),
        pytest.param('400638133393X', InvalidFormat, id='format-before-prefix'),
        pytest.param('96385074', InvalidLength, id='ean8'),
        pytest.param('03064061520', InvalidLength, id='eleven-digits'),
        pytest.param('036000291452', InvalidLength, id='upc12'),
        pytest.param('00036000291452', InvalidLength, id='gtin14'),
        pytest.param('978030640615700', InvalidLength, id='fifteen-digits'),
        pytest.param('12', InvalidLength, id='two-digits'),
        pytest.param('1234567X', InvalidLength, id='length-before-check-digit'),
        pytest.param('123A4567', InvalidFormat, id='body-format-before-length'),
        pytest.param('1', InvalidFormat, id='no-body-digits'),
        pytest.param(' - \t\n', InvalidFormat, id='empty-after-normalization'),
        pytest.param(None, InvalidFormat, id='none'),
        pytest.param(9780306406157, InvalidFormat, id='integer'),
        pytest.param(b'9780306406157', InvalidFormat, id='bytes'),
    ],
)
def test_validate_raises_specific_error(number, expected_error, convert):
    with pytest.raises(expected_error) as caught:
        validate(number, convert=convert)

    assert type(caught.value) is expected_error
