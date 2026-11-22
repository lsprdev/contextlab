from collections import UserDict
from dataclasses import dataclass

import pytest

from bumpversion.exceptions import FormattingError
from bumpversion.versioning.serialization import serialize


@dataclass
class VersionStub:
    parts: dict[str, int | str]
    required: tuple[str, ...]

    def values(self):
        return self.parts.copy()

    def required_components(self):
        return list(self.required)


def test_formats_version_values_and_context_without_mutating_context():
    version = VersionStub({'major': 3, 'minor': 7}, ('major', 'minor'))
    context = UserDict({'major': 99, 'prefix': 'release', 'unused': 'keep'})
    before = dict(context)

    result = serialize(version, ['{prefix!r}:{major:02d}.{minor:03d}'], context)

    assert result == "'release':03.007"
    assert dict(context) == before
    assert version.parts == {'major': 3, 'minor': 7}


def test_prefers_all_required_components_before_minimizing_label_count():
    version = VersionStub(
        {'major': 2, 'minor': 5, 'suffix': 'rc'}, ('major', 'minor')
    )
    patterns = ['{major}', '{major}.{minor}-{suffix}', '{major}.{minor}']

    assert serialize(version, patterns, {}) == '2.5'
    assert patterns == ['{major}', '{major}.{minor}-{suffix}', '{major}.{minor}']


def test_ignores_patterns_with_missing_labels_even_when_they_cover_required_parts():
    version = VersionStub({'major': 2, 'minor': 5}, ('major', 'minor'))
    patterns = ['{major}.{minor}{missing}', 'v{major}']

    assert serialize(version, patterns, {}) == 'v2'


def test_falls_back_to_fewest_labels_when_no_pattern_covers_all_required_parts():
    version = VersionStub(
        {'major': 2, 'minor': 5, 'patch': 8}, ('major', 'minor', 'patch')
    )
    patterns = ['{major}.{minor}', 'patch-{patch}']

    assert serialize(version, patterns, {}) == 'patch-8'


def test_counts_distinct_labels_including_labels_supplied_by_context():
    version = VersionStub({'major': 2}, ('major',))
    patterns = ['{major}{channel}', 'release-{major}/{major}/{major}']

    assert serialize(version, patterns, {'channel': 'a'}) == 'release-2/2/2'


@pytest.mark.parametrize(
    ('patterns', 'expected'),
    [
        (['release-{major:03d}', 'v{major}'], 'release-002'),
        (['v{major}', 'release-{major:03d}'], 'v2'),
    ],
)
def test_breaks_equal_label_count_ties_by_input_order(patterns, expected):
    version = VersionStub({'major': 2}, ('major',))

    assert serialize(version, patterns, {}) == expected


@pytest.mark.parametrize(
    ('literal_pattern', 'expected'),
    [('{{stable}}', '{stable}'), ('', '')],
)
def test_accepts_zero_label_patterns_when_no_components_are_required(literal_pattern, expected):
    version = VersionStub({'stage': 'stable'}, ())

    assert serialize(version, ['{stage}', literal_pattern], {}) == expected


def test_accepts_pattern_whose_labels_exactly_match_the_available_keys():
    version = VersionStub({'major': 2}, ('major',))

    assert serialize(version, ['{major}'], {}) == '2'


@pytest.mark.parametrize(
    'patterns',
    [[], ['{major}.{missing}', '{unknown}']],
    ids=['no-patterns', 'all-patterns-missing-labels'],
)
def test_raises_formatting_error_when_no_pattern_is_renderable(patterns):
    version = VersionStub({'major': 2}, ('major',))
    context = {'prefix': 'v'}

    with pytest.raises(FormattingError) as error:
        serialize(version, patterns, context)

    message = str(error.value)
    assert repr(patterns) in message
    assert repr(version) in message
    assert context == {'prefix': 'v'}
