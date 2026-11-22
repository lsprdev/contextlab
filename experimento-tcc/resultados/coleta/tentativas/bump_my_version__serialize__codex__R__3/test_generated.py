from collections import UserDict
from types import SimpleNamespace

import pytest

from bumpversion.exceptions import FormattingError
from bumpversion.versioning.models import Version
from bumpversion.versioning.serialization import serialize


class Component:
    def __init__(self, value, optional_value=None):
        self.value = value
        self.func = SimpleNamespace(optional_value=optional_value)

    def __str__(self):
        return str(self.value)

    def __format__(self, format_spec):
        return format(self.value, format_spec)


@pytest.fixture
def version():
    return Version(
        None,
        {"major": Component(2), "minor": Component(5), "patch": Component(0, optional_value=0)},
    )


def test_prefers_all_required_components_over_fewer_fields(version):
    patterns = ["literal", "{major}", "{minor}.{patch}", "v{major}.{minor}"]

    assert serialize(version, patterns, {}) == "v2.5"


def test_ranks_by_field_count_instead_of_pattern_or_output_length(version):
    patterns = ["{major}{minor}{patch}", "release-{major:04d}.{minor}"]

    assert serialize(version, patterns, {}) == "release-0002.5"


def test_repeated_fields_count_once_for_ranking(version):
    patterns = ["{major}.{minor}.{patch}", "{major}.{minor}-{major}.{minor}"]

    assert serialize(version, patterns, {}) == "2.5-2.5"


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        (["z-release-{major}.{minor}", "a{minor}.{major}"], "z-release-2.5"),
        (["a{minor}.{major}", "z-release-{major}.{minor}"], "a5.2"),
    ],
)
def test_uses_input_order_to_break_ties(version, patterns, expected):
    assert serialize(version, patterns, {}) == expected


def test_optional_components_depend_on_their_configured_values():
    version = Version(None, {"major": Component(0), "patch": Component(7, optional_value=7)})
    patterns = ["{patch}", "{major}.{patch}", "{major}"]

    assert serialize(version, patterns, {}) == "0"


def test_nondefault_optional_component_must_be_included_when_possible():
    version = Version(
        None,
        {"major": Component(2), "minor": Component(5), "patch": Component(3, optional_value=0)},
    )
    patterns = ["{major}.{minor}", "{major}.{minor}.{patch}"]

    assert serialize(version, patterns, {}) == "2.5.3"


def test_filters_missing_fields_before_breaking_ties(version):
    patterns = ["{major}.{minor}.{missing}", "{prefix}{major}.{minor}"]

    assert serialize(version, patterns, {"prefix": "v", "extra": "unused"}) == "v2.5"


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        (["{major}.{minor}.{missing}", "{major}.{patch}", "{minor}", "{major}"], "5"),
        (["{major}.{minor}", "{minor}"], "2.5"),
        (["{major}.{minor}.{missing}", "{major}", "literal"], "literal"),
    ],
)
def test_ranks_renderable_patterns_when_some_formats_cannot_be_used(version, patterns, expected):
    assert serialize(version, patterns, {}) == expected


@pytest.mark.parametrize("mapping_factory", [dict, UserDict])
def test_combines_context_with_version_values_without_mutating_context(version, mapping_factory):
    original = {"major": 91, "minor": 82, "prefix": "", "build": 0, "tag": "rc"}
    context = mapping_factory(original)
    patterns = ["{prefix}{major:03d}.{minor}+{build:02d}-{tag!r}"]

    assert serialize(version, patterns, context) == "002.5+00-'rc'"
    assert dict(context) == original


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [("{{major}}/{{missing}}", "{major}/{missing}"), ("", "")],
)
def test_accepts_field_free_formats(version, pattern, expected):
    assert serialize(version, ["{missing}", pattern], {}) == expected


@pytest.mark.parametrize("patterns", [[], ["{missing}", "{major}.{minor}.{unknown}"]])
def test_raises_formatting_error_when_no_pattern_is_renderable(version, patterns):
    context = {"major": 91, "prefix": "v"}

    with pytest.raises(FormattingError) as exc_info:
        serialize(version, patterns, context)

    message = str(exc_info.value)
    assert repr(patterns) in message
    assert repr(version) in message
    assert context == {"major": 91, "prefix": "v"}
