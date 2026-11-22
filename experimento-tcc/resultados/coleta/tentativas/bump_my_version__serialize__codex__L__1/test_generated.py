from collections import UserDict
from types import SimpleNamespace

import pytest

from bumpversion.exceptions import FormattingError
from bumpversion.versioning.models import Version
from bumpversion.versioning.serialization import serialize


class Component(str):
    func = SimpleNamespace(optional_value="0")

    @property
    def value(self):
        return str(self)


@pytest.fixture
def version():
    return Version(
        version_spec=None,
        components={"major": Component("2"), "minor": Component("7"), "patch": Component("0")},
    )


def test_prefers_pattern_containing_every_required_component(version):
    patterns = ["{major}", "{minor}.{patch}", "{minor}.{major}"]

    assert serialize(version, patterns, {}) == "7.2"


def test_component_with_non_optional_value_becomes_required(version):
    patterns = ["{major}.{minor}", "{major}.{minor}.{patch}"]
    assert serialize(version, patterns, {}) == "2.7"

    version.components["patch"] = Component("4")

    assert serialize(version, patterns, {}) == "2.7.4"


@pytest.mark.parametrize("extra", ["patch", "channel"])
def test_prefers_fewer_fields_even_if_output_is_longer(version, extra):
    patterns = ["{major}.{minor}.{" + extra + "}", "release-build-{major}.{minor}"]

    assert serialize(version, patterns, {"channel": "rc"}) == "release-build-2.7"


def test_repeated_fields_count_once_and_ties_preserve_input_order(version):
    repeated = "z{major}.{minor}.{minor}"
    single = "a{minor}.{major}"

    assert serialize(version, [repeated, single], {}) == "z2.7.7"
    assert serialize(version, [single, repeated], {}) == "a7.2"


def test_ignores_pattern_with_missing_field_and_uses_version_values_over_context(version):
    context = UserDict({"major": "stale", "channel": "rc", "build": 5})
    patterns = ["{major}.{minor}-{missing}-{build}", "{major}.{minor}-{channel}-{build:03d}"]

    assert serialize(version, patterns, context) == "2.7-rc-005"
    assert context == {"major": "stale", "channel": "rc", "build": 5}


def test_falls_back_when_only_unrenderable_pattern_contains_all_required_fields(version):
    patterns = ["{major}.{minor}-{missing}", "{major}.{patch}", "v{minor}"]

    assert serialize(version, patterns, {}) == "v7"


@pytest.mark.parametrize(("pattern", "expected"), [("fixed", "fixed"), ("", "")])
def test_accepts_patterns_without_fields(version, pattern, expected):
    assert serialize(version, [pattern], {}) == expected


def test_renders_pattern_using_only_context(version):
    assert serialize(version, ["{channel}"], {"channel": "rc"}) == "rc"


def test_accepts_pattern_when_available_fields_match_exactly():
    version = Version(version_spec=None, components={"major": Component("2")})

    assert serialize(version, ["v{major}"], {}) == "v2"


@pytest.mark.parametrize("patterns", [[], ["{missing}", "{major}.{minor}-{unknown}"]])
def test_raises_formatting_error_when_no_pattern_is_renderable(version, patterns):
    context = {"channel": "rc"}

    with pytest.raises(FormattingError) as error:
        serialize(version, patterns, context)

    message = str(error.value)
    assert "Could not find a valid serialization format" in message
    assert repr(patterns) in message
    assert repr(version) in message
    assert context == {"channel": "rc"}
