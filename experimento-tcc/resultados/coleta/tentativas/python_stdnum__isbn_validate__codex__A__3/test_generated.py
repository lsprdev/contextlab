import pytest

from stdnum.exceptions import InvalidChecksum, InvalidComponent, InvalidFormat, InvalidLength
from stdnum.isbn import validate


@pytest.mark.parametrize(
    ('number', 'canonical', 'isbn13'),
    [
        pytest.param('0306406152', '0306406152', '9780306406157', id='isbn10'),
        pytest.param('\t0-306 40615-2\n', '0306406152', '9780306406157', id='mixed-separators'),
        pytest.param('0-8044-2957-x', '080442957X', '9780804429573', id='lowercase-check-digit'),
        pytest.param('306-40615-2', '0306406152', '9780306406157', id='nine-character-sbn'),
        pytest.param('8044 2957 x', '080442957X', '9780804429573', id='sbn-with-x'),
        pytest.param('0000000000', '0000000000', '9780000000002', id='zero-check-digit'),
        pytest.param('978-0-306-40615-7', '9780306406157', '9780306406157', id='978-prefix'),
        pytest.param(' 979 10-90636-07 1 ', '9791090636071', '9791090636071', id='979-prefix'),
        pytest.param('９７８\u2011０\u00a0３０６\u2013４０６１５\u2212７', '9780306406157', '9780306406157', id='unicode-digits-and-separators'),
        pytest.param('9789999999991', '9789999999991', '9789999999991', id='group-and-publisher-unchecked'),
        pytest.param('9790000000001', '9790000000001', '9790000000001', id='entire-979-prefix-accepted'),
    ],
)
def test_validate_returns_canonical_isbn(number, canonical, isbn13):
    assert validate(number) == canonical
    assert validate(number, convert=False) == canonical
    assert validate(number, convert=True) == isbn13


@pytest.mark.parametrize('convert', [False, True])
@pytest.mark.parametrize(
    ('number', 'error'),
    [
        pytest.param('0-306-40615-3', InvalidChecksum, id='wrong-isbn10-check-digit'),
        pytest.param('030640615X', InvalidChecksum, id='unexpected-isbn10-x'),
        pytest.param('0804429570', InvalidChecksum, id='missing-isbn10-x'),
        pytest.param('030640615q', InvalidChecksum, id='isbn10-letter-in-check-position'),
        pytest.param('0304606152', InvalidChecksum, id='isbn10-transposed-body-digits'),
        pytest.param('306406153', InvalidChecksum, id='wrong-sbn-check-digit'),
        pytest.param('9780306406152', InvalidChecksum, id='isbn10-digit-used-for-isbn13'),
        pytest.param('9780304606157', InvalidChecksum, id='isbn13-transposed-body-digits'),
        pytest.param('9791090636072', InvalidChecksum, id='wrong-979-check-digit'),
        pytest.param('4006381333932', InvalidChecksum, id='checksum-before-prefix'),
        pytest.param('4006381333931', InvalidComponent, id='valid-ean-outside-bookland'),
        pytest.param('9770000000003', InvalidComponent, id='prefix-below-bookland'),
        pytest.param('9800000000007', InvalidComponent, id='prefix-above-bookland'),
        pytest.param('978030640615x', InvalidFormat, id='isbn13-x-in-check-position'),
        pytest.param('400638133393Q', InvalidFormat, id='format-before-prefix'),
        pytest.param('03064061X2', InvalidFormat, id='x-in-isbn10-body'),
        pytest.param('97803064061A7', InvalidFormat, id='letter-in-isbn13-body'),
        pytest.param('0/306/40615/2', InvalidFormat, id='slash-separators'),
        pytest.param('0306\t406152', InvalidFormat, id='internal-tab'),
        pytest.param('٠306406152', InvalidFormat, id='unmapped-unicode-digit'),
        pytest.param('ISBN 978-0-306-40615-7', InvalidFormat, id='isbn-label'),
        pytest.param('12a', InvalidFormat, id='format-before-length'),
        pytest.param('', InvalidFormat, id='empty'),
        pytest.param(' \t--\n', InvalidFormat, id='separators-only'),
        pytest.param('2', InvalidFormat, id='empty-body'),
        pytest.param(None, InvalidFormat, id='none'),
        pytest.param(b'0306406152', InvalidFormat, id='bytes'),
        pytest.param(9780306406157, InvalidFormat, id='integer'),
        pytest.param('12', InvalidLength, id='two-digits'),
        pytest.param('96385074', InvalidLength, id='valid-ean8'),
        pytest.param('97803064061', InvalidLength, id='eleven-digits'),
        pytest.param('978' + '0' * 8 + '2', InvalidLength, id='valid-twelve-digit-ean'),
        pytest.param('978' + '0' * 10 + '2', InvalidLength, id='valid-fourteen-digit-ean'),
        pytest.param('123456789012345', InvalidLength, id='fifteen-digits'),
    ],
)
def test_validate_rejects_invalid_isbn(number, error, convert):
    with pytest.raises(error) as caught:
        validate(number, convert=convert)
    assert type(caught.value) is error
