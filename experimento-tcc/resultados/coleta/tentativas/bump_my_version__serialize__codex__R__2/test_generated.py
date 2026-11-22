from dataclasses import dataclass

import pytest

from bumpversion.exceptions import FormattingError
from bumpversion.versioning.serialization import serialize


@dataclass
class VersionStub:
    components: dict[str, int]
    required: tuple[str, ...] = ()

    def values(self):
        return self.components.copy()

    def required_components(self):
        return list(self.required)


@pytest.fixture
def version():
    return VersionStub({'major': 3, 'minor': 8, 'patch': 0}, ('major', 'minor'))


def test_version_values_override_context_without_mutating_it(version):
    context = {'major': 99, 'label': 'build', 'width': 3}

    result = serialize(version, ['{{{label!r}}}-{major:0{width}d}.{minor:02d}'], context)

    assert result == "{'build'}-003.08"
    assert context == {'major': 99, 'label': 'build', 'width': 3}


def test_unrenderable_patterns_are_discarded_before_ranking(version):
    patterns = ['{major}.{minor}-{missing}', '{missing}', '{major}.{minor}-{label}']

    assert serialize(version, patterns, {'label': 'dev'}) == '3.8-dev'


def test_complete_pattern_beats_shorter_pattern_missing_a_required_part(version):
    patterns = ['{major}', '{major}.{patch}', '{major}.{minor}.{patch}']

    assert serialize(version, patterns, {}) == '3.8.0'


def test_incomplete_patterns_can_win_when_no_complete_pattern_is_renderable(version):
    patterns = ['{major}.{patch}', '{major}.{minor}-{missing}', '{minor}']

    assert serialize(version, patterns, {}) == '8'


def test_shortest_incomplete_pattern_can_omit_every_version_part(version):
    assert serialize(version, ['{major}', 'literal'], {}) == 'literal'


def test_ranking_uses_distinct_fields_instead_of_pattern_or_output_length(version):
    patterns = ['{major}.{minor}.{patch}', 'release-{major}.{minor}-{major}-{minor}']

    assert serialize(version, patterns, {}) == 'release-3.8-3-8'


@pytest.mark.parametrize(
    ('patterns', 'expected'),
    [
        (['z-release-{major}.{minor}', 'a{major}.{minor}'], 'z-release-3.8'),
        (['a{major}.{minor}', 'z-release-{major}.{minor}'], 'a3.8'),
    ],
)
def test_patterns_with_equal_rank_keep_input_order(version, patterns, expected):
    assert serialize(version, patterns, {}) == expected


def test_context_fields_count_when_ranking_renderable_patterns(version):
    patterns = ['{major}.{minor}-{label}', 'release-{major}.{minor}']

    assert serialize(version, patterns, {'label': 'dev'}) == 'release-3.8'


@pytest.mark.parametrize(('literal', 'expected'), [('', ''), ('{{release}}', '{release}')])
def test_zero_field_pattern_is_valid_when_all_components_are_optional(literal, expected):
    version = VersionStub({'patch': 0})

    assert serialize(version, ['{patch}', literal], {}) == expected


@pytest.mark.parametrize('patterns', [[], ['{missing}', '{major}.{minor}-{unknown}']])
def test_no_renderable_pattern_raises_formatting_error(version, patterns):
    context = {'label': 'dev'}

    with pytest.raises(FormattingError) as error:
        serialize(version, patterns, context)

    assert repr(patterns) in str(error.value)
    assert repr(version) in str(error.value)
    assert context == {'label': 'dev'}


def test_formatting_error_from_selected_pattern_propagates(version):
    patterns = ['{major:.2f}.{minor}', '{major}.{minor}']
    version.components['major'] = 'three'

    with pytest.raises(ValueError):
        serialize(version, patterns, {})
