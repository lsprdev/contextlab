import re

import pytest

from bumpversion.scm.models import SCMConfig


def make_config(tag_name: str, parse_pattern: str) -> SCMConfig:
    return SCMConfig(
        tag=True,
        push_tag=False,
        sign_tags=False,
        tag_name=tag_name,
        allow_dirty=False,
        commit=False,
        message="Bump version",
        parse_pattern=parse_pattern,
    )


@pytest.mark.parametrize(
    ("tag_name", "parse_pattern", "tag", "expected"),
    [
        pytest.param(
            "v{new_version}", r"\d+\.\d+\.\d+", "v01.02.003", "01.02.003",
            id="preserves-version-text",
        ),
        pytest.param(
            "v{new_version}", r"\d+\.\d+\.\d+", "release-1.2.3", None,
            id="missing-prefix",
        ),
        pytest.param(
            "v{new_version}", r"\d+\.\d+\.\d+", "v1x2x3", None,
            id="version-does-not-match",
        ),
        pytest.param(
            "rel.[LTS]+(stable)/{new_version}", r"\d+", "rel.[LTS]+(stable)/42", "42",
            id="literal-prefix-metacharacters",
        ),
        pytest.param(
            "release.{new_version}", r"\d+", "releaseX42", None,
            id="prefix-dot-is-literal",
        ),
        pytest.param(
            "v{new_version}", r"\d+\.\d+", "refs/tags/v1.2-build-v3.4", "1.2",
            id="first-match-with-surrounding-text",
        ),
        pytest.param(
            "v{new_version}-signed", r"\d+\.\d+", "v2.5-unsigned", "2.5",
            id="template-suffix-is-ignored",
        ),
        pytest.param(
            "v{new_version}-copy-{new_version}", r"\d+", "v7-copy-9", "7",
            id="first-placeholder-sets-prefix-boundary",
        ),
        pytest.param(
            "{new_version}-final", r"\d+\.\d+", "build/4.8", "4.8",
            id="empty-prefix",
        ),
        pytest.param(
            "release-", r"\d+", "release-42", "42",
            id="template-without-placeholder-is-a-prefix",
        ),
        pytest.param(
            "release-", r"\d+", "other-42", None,
            id="prefix-required-without-placeholder",
        ),
        pytest.param(
            "v{new_version}", r"\\d+\\.\\d+\\.\\d+", "v3.10.2", "3.10.2",
            id="normalizes-multiple-doubled-backslashes",
        ),
        pytest.param(
            "Release {new_version}", "(?ix) [a-z]+ \\. \\d+ # version\n", "rELEASE RC.12", "RC.12",
            id="inline-flags-apply-to-pattern-and-prefix",
        ),
        pytest.param(
            "Release {new_version}", r"[A-Z]+\.\d+", "release RC.12", None,
            id="prefix-is-case-sensitive-without-flags",
        ),
        pytest.param(
            "v{new_version}", r"(?:\d+\.\d+)|(?P<channel>nightly)-\d+", "vnightly-27", "nightly-27",
            id="entire-version-returned-with-inner-capture",
        ),
        pytest.param(
            "v{new_version}", r"\d+\.\d+|nightly-\d+", "nightly-27", None,
            id="prefix-required-for-second-alternative",
        ),
        pytest.param(
            "v{new_version}", r"\d*$", "v", "",
            id="empty-match-is-a-version",
        ),
        pytest.param(
            "v{new_version}", r"\d+$", "v42-extra", None,
            id="honors-pattern-end-anchor",
        ),
    ],
)
def test_get_version_from_tag(
    tag_name: str, parse_pattern: str, tag: str, expected: str | None
) -> None:
    config = make_config(tag_name, parse_pattern)

    assert config.get_version_from_tag(tag) == expected


def test_get_version_from_tag_raises_for_invalid_parse_pattern() -> None:
    config = make_config("v{new_version}", r"\d+[")

    with pytest.raises(re.error):
        config.get_version_from_tag("v42")
