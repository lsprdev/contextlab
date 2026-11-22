from collections import UserDict
from types import SimpleNamespace

import pytest

from bumpversion.exceptions import FormattingError
from bumpversion.versioning.models import Version
from bumpversion.versioning.serialization import serialize


class Component(str):
    def __new__(cls, value, optional_value="0"):
        component = super().__new__(cls, value)
        component.value = value
        component.func = SimpleNamespace(optional_value=optional_value)
        return component


@pytest.fixture
def version():
    return Version(
        version_spec=None,
        components={"major": Component("2"), "minor": Component("7"), "patch": Component("0")},
    )


@pytest.mark.parametrize("mapping_type", [dict, UserDict])
def test_version_values_override_context_without_mutating_it(version, mapping_type):
    original_context = {"major": "99", "minor": "88", "patch": "5", "build": 13}
    context = mapping_type(original_context)

    result = serialize(version, ["v{major}.{minor}.{patch}+{build:04d}"], context)

    assert result == "v2.7.0+0013"
    assert dict(context) == original_context
    assert version.values() == {"major": "2", "minor": "7", "patch": "0"}


def test_prefers_all_required_components_over_fewer_fields(version):
    patterns = ["{major}.{major}", "{prefix}{major}.{minor}"]

    assert serialize(version, patterns, {"prefix": "v"}) == "v2.7"


def test_optional_component_can_be_omitted_from_a_complete_pattern(version):
    patterns = ["{patch}", "{major}.{minor}.{patch}", "{major}.{minor}"]

    assert serialize(version, patterns, {}) == "2.7"


def test_component_with_nondefault_value_is_required():
    version = Version(
        version_spec=None,
        components={"major": Component("2"), "stage": Component("beta", optional_value="final")},
    )

    assert serialize(version, ["{major}", "{major}-{stage}"], {}) == "2-beta"


def test_counts_distinct_fields_even_when_the_pattern_and_output_are_longer(version):
    patterns = ["{major}.{minor}.{patch}", "release-{major}.{minor}-{major}.{minor}"]

    assert serialize(version, patterns, {}) == "release-2.7-2.7"


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        (["z-release-{major}.{minor}", "a-{minor}.{major}"], "z-release-2.7"),
        (["a-{minor}.{major}", "z-release-{major}.{minor}"], "a-7.2"),
    ],
)
def test_uses_input_order_to_break_ties(version, patterns, expected):
    assert serialize(version, patterns, {}) == expected


def test_ignores_an_unrenderable_pattern_that_would_otherwise_win(version):
    patterns = ["{major}.{minor}-{missing}", "{major}.{minor}.{patch}-{tag}"]

    assert serialize(version, patterns, {"tag": "rc"}) == "2.7.0-rc"


def test_uses_renderable_fallback_when_complete_pattern_is_unrenderable(version):
    patterns = ["{major}.{minor}-{missing}", "v{major}"]

    assert serialize(version, patterns, {}) == "v2"


def test_ranks_incomplete_patterns_by_distinct_field_count(version):
    patterns = ["{major}-{tag}", "patch-{patch}"]

    assert serialize(version, patterns, {"tag": "rc"}) == "patch-0"


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [("{{stable}}", "{stable}"), ("", "")],
)
def test_accepts_patterns_without_fields_when_all_components_are_optional(pattern, expected):
    version = Version(
        version_spec=None,
        components={"stage": Component("final", optional_value="final")},
    )

    assert serialize(version, ["{stage}", pattern], {}) == expected


def test_only_formats_the_selected_pattern(version):
    patterns = ["{major}.{minor}-{build:d}", "{major}.{minor}"]

    assert serialize(version, patterns, {"build": "nightly"}) == "2.7"


def test_propagates_a_formatting_error_from_the_selected_pattern(version):
    patterns = ["{major}.{minor}-{build:d}", "{major}.{minor}-{build}"]

    with pytest.raises(ValueError):
        serialize(version, patterns, {"build": "nightly"})


@pytest.mark.parametrize("patterns", [[], ["{major}.{minor}-{missing}", "{unknown}"]])
def test_raises_formatting_error_when_no_pattern_is_renderable(version, patterns):
    with pytest.raises(FormattingError) as error:
        serialize(version, patterns, {})

    assert repr(patterns) in str(error.value)
    assert repr(version) in str(error.value)
