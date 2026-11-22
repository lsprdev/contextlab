import re

import pytest

from bumpversion.scm.models import SCMConfig


VERSION_PATTERN = r"\d+\.\d+\.\d+"


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
        pytest.param("v{new_version}", VERSION_PATTERN, "v01.2.003", "01.2.003", id="preserves-version-text"),
        pytest.param("v{new_version}", VERSION_PATTERN, "release-1.2.3", None, id="missing-prefix"),
        pytest.param("v{new_version}", VERSION_PATTERN, "V1.2.3", None, id="case-sensitive-by-default"),
        pytest.param("v{new_version}", VERSION_PATTERN, "v1x2x3", None, id="version-separators-are-literal"),
        pytest.param("v{new_version}", VERSION_PATTERN, "v1.2", None, id="incomplete-version"),
        pytest.param("v{new_version}", VERSION_PATTERN, "", None, id="empty-tag"),
        pytest.param(
            "v{new_version}", VERSION_PATTERN, "refs/tags/v1.2.3-extra", "1.2.3", id="searches-within-tag"
        ),
        pytest.param(
            "v{new_version}", VERSION_PATTERN, "vbad v1.2.3 v4.5.6", "1.2.3", id="first-successful-match"
        ),
        pytest.param(
            "release.[qa]+-{new_version}",
            VERSION_PATTERN,
            "release.[qa]+-1.2.3",
            "1.2.3",
            id="literal-prefix-with-regex-metacharacters",
        ),
        pytest.param(
            "release.[qa]+-{new_version}",
            VERSION_PATTERN,
            "releaseXqq-1.2.3",
            None,
            id="prefix-metacharacters-do-not-act-as-regex",
        ),
        pytest.param(
            "release-{new_version}-stable", VERSION_PATTERN, "release-1.2.3", "1.2.3", id="suffix-may-be-absent"
        ),
        pytest.param(
            "release-{new_version}-stable", VERSION_PATTERN, "release-1.2.3-beta", "1.2.3", id="suffix-may-differ"
        ),
        pytest.param(
            "v{new_version}-{new_version}", VERSION_PATTERN, "v1.2.3-4.5.6", "1.2.3", id="first-placeholder"
        ),
        pytest.param("build-", VERSION_PATTERN, "build-3.4.5", "3.4.5", id="template-without-placeholder"),
        pytest.param("build-", VERSION_PATTERN, "test-3.4.5", None, id="prefix-required-without-placeholder"),
        pytest.param("{new_version}-stable", VERSION_PATTERN, "2.3.4-dev", "2.3.4", id="empty-prefix"),
        pytest.param(
            "v{new_version}", r"\\d+\\.\\d+\\.\\d+", "v12.34.56", "12.34.56", id="doubled-backslashes"
        ),
        pytest.param(
            "release-{new_version}", r"(?i)\d+\.\d+rc\d+", "RELEASE-1.2RC3", "1.2RC3", id="global-ignore-case"
        ),
        pytest.param(
            "v{new_version}", r"(?is)\d+.*rc\d+", "V1\nRC2", "1\nRC2", id="combined-global-flags"
        ),
        pytest.param(
            "release # {new_version}", r"(?x)\d+ \. \d+", "release # 12.34", "12.34", id="verbose-flag-and-literal-prefix"
        ),
        pytest.param(
            "v{new_version}", r"\d+(?i:rc)\d+", "V1RC2 v3RC4", "3RC4", id="scoped-flag-leaves-prefix-case-sensitive"
        ),
        pytest.param(
            "v{new_version}",
            r"(?P<major>\d+)\.(\d+)(?:-rc\d+)?",
            "v12.34-rc5",
            "12.34-rc5",
            id="captures-entire-version-with-inner-groups",
        ),
        pytest.param("v{new_version}", r"\d+|dev", "dev vdev", "dev", id="prefix-applies-to-second-alternative"),
        pytest.param("v{new_version}", r"\d+|dev", "unrelated-dev", None, id="bare-alternative-does-not-match"),
        pytest.param("v{new_version}", r"\d+$", "v12-extra", None, id="version-pattern-end-anchor"),
        pytest.param("v{new_version}", r"\d*", "v", "", id="empty-version-is-a-successful-match"),
    ],
)
def test_get_version_from_tag(
    tag_name: str, parse_pattern: str, tag: str, expected: str | None
) -> None:
    config = make_config(tag_name, parse_pattern)

    assert config.get_version_from_tag(tag) == expected


def test_get_version_from_tag_raises_for_invalid_parse_pattern() -> None:
    config = make_config("v{new_version}", "[")

    with pytest.raises(re.error):
        config.get_version_from_tag("v1.2.3")
