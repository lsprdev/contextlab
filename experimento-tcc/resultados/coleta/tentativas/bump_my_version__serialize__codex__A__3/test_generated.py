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
        }
    )


@pytest.fixture
def version(version_spec):
    return version_spec.create_version({"major": "2", "minor": "7", "patch": "0"})


def test_formats_version_parts_and_context_without_mutating_inputs(version):
    patterns = ["{{{project!s}}} v{major:03d}.{minor:02d}+{build:04x}"]
    context = UserDict({"project": "widget", "major": 99, "build": 26})
    original_context = context.copy()
    original_patterns = patterns.copy()

    assert serialize(version, patterns, context) == "{widget} v002.07+001a"
    assert context == original_context
    assert patterns == original_patterns
    assert version["major"].value == "2"


@pytest.mark.parametrize(
    ("patch", "expected"),
    [("0", "2.7"), ("3", "2.7.3")],
    ids=["optional-patch", "required-patch"],
)
def test_prefers_formats_containing_all_required_components(version_spec, patch, expected):
    version = version_spec.create_version({"major": "2", "minor": "7", "patch": patch})
    patterns = ["{major}", "{major}.{minor}.{patch}", "{major}.{minor}"]

    assert serialize(version, patterns, {}) == expected


def test_ignores_unrenderable_formats_even_when_they_cover_required_parts(version):
    patterns = ["{major}.{minor}-{missing}", "v{major}"]

    assert serialize(version, patterns, {}) == "v2"


def test_uses_fewest_labels_when_every_renderable_format_omits_a_required_part(version):
    patterns = ["{major}.{patch}", "minor={minor}", "major={major}"]

    assert serialize(version, patterns, {}) == "minor=7"


def test_counts_context_fields_in_pattern_size(version):
    patterns = ["{prefix}{major}.{minor}", "version-{major}.{minor}"]

    assert serialize(version, patterns, {"prefix": ""}) == "version-2.7"


def test_counts_each_label_once_regardless_of_repetition_or_output_length(version):
    patterns = ["{major}.{minor}.{patch}", "release-{major}.{minor}-{major}-{minor}"]

    assert serialize(version, patterns, {}) == "release-2.7-2-7"


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        (["release-{major}.{minor}", "{minor}.{major}"], "release-2.7"),
        (["{minor}.{major}", "release-{major}.{minor}"], "7.2"),
    ],
    ids=["longer-first", "shorter-first"],
)
def test_breaks_ties_by_input_order(version, patterns, expected):
    assert serialize(version, patterns, {}) == expected


@pytest.mark.parametrize(
    ("literal", "expected"),
    [("{{stable}}", "{stable}"), ("", "")],
    ids=["escaped-braces", "empty-pattern"],
)
def test_accepts_a_pattern_without_fields_when_all_components_are_optional(version_spec, literal, expected):
    version = version_spec.create_version({"major": "0", "minor": "0", "patch": "0"})

    assert serialize(version, ["{major}.{minor}", literal], {}) == expected


def test_can_render_an_optional_component_when_the_only_format_uses_it(version):
    assert serialize(version, ["{major}.{minor}.{patch}"], {}) == "2.7.0"


def test_context_field_presence_is_independent_of_value_truthiness(version):
    patterns = ["{major}.{minor}-{build}-{tag}-{marker!r}", "{major}"]
    context = {"build": 0, "tag": "", "marker": None}

    assert serialize(version, patterns, context) == "2.7-0--None"


@pytest.mark.parametrize(
    "patterns",
    [[], ["{major}.{minor}-{channel}", "{unknown}"]],
    ids=["no-patterns", "all-patterns-missing-fields"],
)
def test_raises_formatting_error_when_no_pattern_is_renderable(version, patterns):
    context = {"project": "widget"}

    with pytest.raises(FormattingError, match="Could not find a valid serialization format") as error:
        serialize(version, patterns, context)

    assert repr(patterns) in str(error.value)
    assert repr(version) in str(error.value)
    assert context == {"project": "widget"}


def test_propagates_invalid_format_specifier_from_selected_pattern(version):
    patterns = ["{major:Q}.{minor}", "{major}.{minor}.{patch}"]

    with pytest.raises(ValueError, match="Unknown format code"):
        serialize(version, patterns, {})
