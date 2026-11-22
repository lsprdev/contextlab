import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning.models import Version, VersionComponentSpec
from bumpversion.versioning.version_config import VersionConfig


RELEASE_PATTERN = r"""
    v(?P<major>[0-9]+) \. (?P<minor>[0-9]+) \. (?P<patch>[0-9]+)
    # The release stage is optional.
    (?: - (?P<stage>alpha|beta|final) )?
"""


def make_config(pattern, components):
    return VersionConfig(
        parse=pattern,
        serialize=("{major}",),
        search="{current_version}",
        replace="{new_version}",
        part_configs=components,
    )


@pytest.fixture
def release_config():
    return make_config(
        RELEASE_PATTERN,
        {
            "major": VersionComponentSpec(),
            "minor": VersionComponentSpec(),
            "patch": VersionComponentSpec(),
            "stage": VersionComponentSpec(
                values=["alpha", "beta", "final"], optional_value="final"
            ),
        },
    )


@pytest.mark.parametrize(
    ("text", "raise_error", "expected"),
    [
        ("release v01.2.003-beta; next v9.8.7-alpha", False, ("01", "2", "003", "beta")),
        ("v0.12.4", True, ("0", "12", "4", "final")),
        ("v7.0.5-alpha", True, ("7", "0", "5", "alpha")),
    ],
)
def test_parse_returns_configured_version_and_preserves_input(
    release_config, text, raise_error, expected
):
    version = release_config.parse(text, raise_error=raise_error)

    assert isinstance(version, Version)
    assert version.version_spec is release_config.version_spec
    assert version.original == text
    assert {name: part.value for name, part in version.values().items()} == dict(
        zip(("major", "minor", "patch", "stage"), expected, strict=True)
    )
    assert version["stage"].is_optional is (expected[-1] == "final")


@pytest.mark.parametrize("text", [None, "", "not a version", "v1.2"])
def test_parse_failure_returns_none_or_raises_according_to_flag(release_config, text):
    assert release_config.parse(text) is None
    assert release_config.parse(text, raise_error=False) is None

    with pytest.raises(BumpVersionError) as error:
        release_config.parse(text, raise_error=True)

    assert str(error.value) == f"Unable to parse version {text} using {RELEASE_PATTERN}"


def test_parse_without_arguments_treats_input_as_missing(release_config):
    assert release_config.parse() is None
    with pytest.raises(BumpVersionError, match="Unable to parse version None"):
        release_config.parse(raise_error=True)


@pytest.mark.parametrize("pattern", [r"\A([0-9]+)\Z", ""])
def test_parse_requires_named_captures(pattern):
    config = make_config(pattern, {"major": VersionComponentSpec()})

    assert config.parse("42") is None
    with pytest.raises(BumpVersionError) as error:
        config.parse("42", raise_error=True)

    assert str(error.value) == f"Unable to parse version 42 using {pattern}"


def test_parse_applies_spec_to_empty_and_missing_captures():
    config = make_config(
        r"\Av(?P<major>[0-9]*)(?P<decoration>!)?\Z",
        {
            "major": VersionComponentSpec(first_value=1, optional_value="7"),
            "build": VersionComponentSpec(first_value=3),
        },
    )

    without_decoration = config.parse("v", raise_error=True)
    with_decoration = config.parse("v!", raise_error=True)
    for version in (without_decoration, with_decoration):
        assert isinstance(version, Version)
        assert {name: part.value for name, part in version.values().items()} == {
            "major": "7",
            "build": "3",
        }
    assert without_decoration.original == "v"
    assert with_decoration.original == "v!"


def test_parse_creates_independent_results(release_config):
    first = release_config.parse("v2.4.8-beta")
    second = release_config.parse("v2.4.8-beta")
    third = release_config.parse("v3.0.1")

    assert first is not second
    assert first["major"] is not second["major"]
    assert first.original == second.original == "v2.4.8-beta"
    assert first["major"].value == second["major"].value == "2"
    assert first["stage"].value == second["stage"].value == "beta"
    assert third.original == "v3.0.1"
    assert third["major"].value == "3"
    assert third["stage"].value == "final"


@pytest.mark.parametrize("raise_error", [False, True])
def test_parse_propagates_component_construction_errors(raise_error):
    config = make_config(
        r"\A(?P<major>[0-9]+)\Z",
        {"major": VersionComponentSpec(first_value="invalid")},
    )

    with pytest.raises(ValueError, match="first value invalid does not contain any digit"):
        config.parse("42", raise_error=raise_error)
