from collections import UserDict
from types import SimpleNamespace

import pytest

from bumpversion.exceptions import FormattingError
from bumpversion.versioning.models import Version
from bumpversion.versioning.serialization import serialize


class NumericComponent(int):
    func = SimpleNamespace(optional_value=0)

    @property
    def value(self):
        return int(self)


@pytest.fixture
def version():
    return Version(
        version_spec=None,
        components={
            "major": NumericComponent(2),
            "minor": NumericComponent(7),
            "patch": NumericComponent(0),
        },
    )


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        pytest.param(
            ["{major}", "{major}.{minor}.{patch}"],
            "2.7.0",
            id="all-required-fields-outrank-fewer-fields",
        ),
        pytest.param(
            ["{major}.{patch}", "{minor}.{major}"],
            "7.2",
            id="all-required-fields-break-a-tie-in-field-count",
        ),
        pytest.param(
            ["{major}.{minor}.{patch}", "release-{major}.{minor}.{major}.{major}"],
            "release-2.7.2.2",
            id="count-distinct-fields-rather-than-occurrences-or-length",
        ),
        pytest.param(
            ["{major}.{minor}-{tag}", "{major}.{minor}"],
            "2.7",
            id="context-fields-count-toward-format-size",
        ),
        pytest.param(
            ["release-{major}.{minor}-{tag}", "{major}.{minor}.{patch}"],
            "release-2.7-final",
            id="equal-field-count-keeps-input-order",
        ),
        pytest.param(
            ["{major}.{minor}.{patch}", "release-{major}.{minor}-{tag}"],
            "2.7.0",
            id="reversing-equally-ranked-formats-changes-the-winner",
        ),
        pytest.param(
            ["{major}.{minor}-{missing}", "{major}"],
            "2",
            id="missing-field-disqualifies-an-otherwise-preferred-format",
        ),
        pytest.param(
            ["{major}.{patch}", "{tag}", "{minor}"],
            "final",
            id="fallback-uses-field-count-and-order-without-partial-coverage-bonus",
        ),
        pytest.param(
            ["{major}-{missing}", "literal"],
            "literal",
            id="literal-is-a-renderable-fallback",
        ),
    ],
)
def test_serialize_selects_format(version, patterns, expected):
    assert serialize(version, patterns, {"tag": "final"}) == expected


def test_serialize_merges_context_without_mutating_it(version):
    context = UserDict({"major": 91, "patch": 88, "serial": 0, "prefix": "v"})
    original_context = context.copy()

    result = serialize(
        version,
        ["{prefix}{major:02d}.{minor}.{patch}-{serial:03d}"],
        context,
    )

    assert result == "v02.7.0-000"
    assert context == original_context


def test_serialize_can_omit_all_optional_components():
    version = Version(
        version_spec=None,
        components={"patch": NumericComponent(0)},
    )

    assert serialize(version, ["{patch}", ""], {}) == ""


def test_serialize_formats_only_the_selected_pattern(version):
    class Unformattable:
        def __format__(self, format_spec):
            raise AssertionError("An unselected field was formatted")

    result = serialize(
        version,
        ["{major}.{minor}-{extra}", "{major}.{minor}"],
        {"extra": Unformattable()},
    )

    assert result == "2.7"


@pytest.mark.parametrize(
    "patterns",
    [
        pytest.param([], id="no-patterns"),
        pytest.param(["{major}.{missing}", "{other}"], id="no-renderable-patterns"),
    ],
)
def test_serialize_raises_formatting_error_when_no_pattern_can_render(version, patterns):
    with pytest.raises(FormattingError) as exc_info:
        serialize(version, patterns, {})

    message = str(exc_info.value)
    assert "Could not find a valid serialization format" in message
    assert repr(patterns) in message
    assert repr(version) in message
