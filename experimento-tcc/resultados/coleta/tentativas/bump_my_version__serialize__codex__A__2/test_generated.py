from collections import UserDict

import pytest

from bumpversion.exceptions import FormattingError
from bumpversion.versioning.models import VersionComponentSpec, VersionSpec
from bumpversion.versioning.serialization import serialize


@pytest.fixture
def version_spec():
    return VersionSpec(
        {
            "major": VersionComponentSpec(),
            "minor": VersionComponentSpec(),
            "patch": VersionComponentSpec(),
            "stage": VersionComponentSpec(values=["dev", "final", "rc"], optional_value="final"),
        }
    )


@pytest.fixture
def version(version_spec):
    return version_spec.create_version({"major": "2", "minor": "7"})


def test_complete_pattern_beats_patterns_missing_required_components(version):
    patterns = ["{major}", "{minor}", "{patch}-{stage}", "{major}.{minor}.{patch}"]

    assert serialize(version, patterns, {}) == "2.7.0"


def test_unrenderable_patterns_are_filtered_before_ranking(version):
    patterns = ["{prefix}{major}.{minor}", "{major:0{width}d}.{minor}", "{stage}"]

    assert serialize(version, patterns, {"width": 3}) == "002.7"


@pytest.mark.parametrize(
    ("patch", "stage", "expected"),
    [
        ("0", "final", "2.7"),
        ("4", "final", "2.7.4"),
        ("0", "rc", "2.7-rc"),
        ("4", "dev", "2.7.4-dev"),
    ],
)
def test_component_values_determine_which_labels_are_required(version_spec, patch, stage, expected):
    version = version_spec.create_version({"major": "2", "minor": "7", "patch": patch, "stage": stage})
    patterns = ["{major}.{minor}.{patch}-{stage}", "{major}.{minor}.{patch}", "{major}.{minor}-{stage}", "{major}.{minor}"]

    assert serialize(version, patterns, {}) == expected


def test_ranking_counts_distinct_labels_instead_of_occurrences_or_output_length(version):
    patterns = ["{major}.{minor}{suffix}", "release-{major}.{minor}.{major}.{minor}"]

    assert serialize(version, patterns, {"suffix": "!"}) == "release-2.7.2.7"


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        (["long-name-{minor}.{major}", "{major}.{minor}"], "long-name-7.2"),
        (["{major}.{minor}", "long-name-{minor}.{major}"], "2.7"),
    ],
)
def test_equal_rank_uses_input_order(version, patterns, expected):
    original_patterns = patterns.copy()

    assert serialize(version, patterns, {}) == expected
    assert patterns == original_patterns


def test_fallback_ranks_renderable_patterns_when_all_omit_required_labels(version):
    patterns = ["{major}.{patch}", "{minor}/{stage}", "{build}", "{major}" ]

    assert serialize(version, patterns, {"build": "snapshot"}) == "snapshot"


def test_literal_fallback_is_rendered_with_escaped_braces(version):
    assert serialize(version, ["{major}.{minor}-{missing}", "{{snapshot}}"], {}) == "{snapshot}"


def test_empty_pattern_wins_when_no_components_are_required(version_spec):
    version = version_spec.create_version({})

    assert serialize(version, ["{major}", ""], {}) == ""


def test_fields_may_use_every_available_key(version_spec):
    version = version_spec.create_version({"major": "2", "minor": "7"})

    assert serialize(version, ["{major}.{minor}.{patch}-{stage}{suffix}"], {"suffix": ""}) == "2.7.0-final"


@pytest.mark.parametrize("mapping_type", [dict, UserDict])
def test_formatting_merges_context_without_mutating_it(version, mapping_type):
    original_context = {"major": 99, "minor": "wrong", "prefix": "", "build": 0, "tag": "rc"}
    context = mapping_type(original_context)
    pattern = "{{{prefix}{major:03d}.{minor:02d}}}+{build:02d}-{tag!r}"

    assert serialize(version, [pattern], context) == "{002.07}+00-'rc'"
    assert dict(context) == original_context


def test_only_the_selected_pattern_is_formatted(version):
    patterns = ["{major:invalid}.{minor}.{patch}", "{major}.{minor}"]

    assert serialize(version, patterns, {}) == "2.7"


@pytest.mark.parametrize("patterns", [[], ["{major}.{minor}{suffix}", "{missing}"]])
def test_no_renderable_pattern_raises_formatting_error(version, patterns):
    context = {"major": "original"}

    with pytest.raises(FormattingError) as error:
        serialize(version, patterns, context)

    assert "Could not find a valid serialization format" in str(error.value)
    assert repr(patterns) in str(error.value)
    assert repr(version) in str(error.value)
    assert context == {"major": "original"}
