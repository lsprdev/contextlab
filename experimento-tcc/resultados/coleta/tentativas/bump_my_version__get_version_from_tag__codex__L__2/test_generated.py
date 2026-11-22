import re

import pytest

from bumpversion.scm.models import SCMConfig


DOTTED_VERSION = r"\d+\.\d+\.\d+"


def make_config(tag_name: str, parse_pattern: str) -> SCMConfig:
    return SCMConfig(
        tag=True,
        push_tag=False,
        sign_tags=False,
        tag_name=tag_name,
        allow_dirty=False,
        commit=False,
        message="",
        parse_pattern=parse_pattern,
    )


@pytest.mark.parametrize(
    ("tag_name", "parse_pattern", "tag", "expected"),
    [
        pytest.param("v{new_version}", DOTTED_VERSION, "v01.2.003", "01.2.003", id="preserves-version-text"),
        pytest.param("v{new_version}", DOTTED_VERSION, "1.2.3", None, id="requires-prefix"),
        pytest.param("v{new_version}", DOTTED_VERSION, "V1.2.3", None, id="case-sensitive-by-default"),
        pytest.param("v{new_version}", DOTTED_VERSION, "v1x2x3", None, id="requires-literal-version-dots"),
        pytest.param("v{new_version}", DOTTED_VERSION, "v1.2", None, id="rejects-incomplete-version"),
        pytest.param("v{new_version}", DOTTED_VERSION, "", None, id="empty-tag"),
        pytest.param(
            "v{new_version}", DOTTED_VERSION, "refs/tags/v1.2.3+build", "1.2.3", id="searches-within-tag"
        ),
        pytest.param(
            "v{new_version}", DOTTED_VERSION, "vbad/v2.4.6/v7.8.9", "2.4.6", id="first-successful-match"
        ),
        pytest.param(
            "release.[stable]+(v){new_version}",
            DOTTED_VERSION,
            "release.[stable]+(v)3.4.5",
            "3.4.5",
            id="literal-prefix-metacharacters",
        ),
        pytest.param(
            "rel.{new_version}", DOTTED_VERSION, "relX3.4.5", None, id="prefix-dot-is-literal"
        ),
        pytest.param(
            "v{new_version}-stable", DOTTED_VERSION, "v3.4.5-dev", "3.4.5", id="template-suffix-is-optional"
        ),
        pytest.param(
            "v{new_version}-copy-{new_version}",
            DOTTED_VERSION,
            "v3.4.5",
            "3.4.5",
            id="prefix-ends-at-first-placeholder",
        ),
        pytest.param(
            "release-", DOTTED_VERSION, "release-3.4.5", "3.4.5", id="entire-template-is-prefix-without-placeholder"
        ),
        pytest.param("release-", DOTTED_VERSION, "3.4.5", None, id="prefix-required-without-placeholder"),
        pytest.param(
            "{new_version}-stable", DOTTED_VERSION, "3.4.5", "3.4.5", id="placeholder-at-start"
        ),
        pytest.param(
            "v{new_version}", r"\\d+\\.\\d+\.\d+", "v12.34.56", "12.34.56", id="mixed-backslash-escaping"
        ),
        pytest.param(
            "Release-{new_version}",
            r"(?i)\d+\.\d+rc\d+",
            "RELEASE-3.4RC2-extra",
            "3.4RC2",
            id="ignore-case-applies-to-prefix-and-version",
        ),
        pytest.param(
            "v{new_version}", r"(?s)\d+.\d+", "v12\n34", "12\n34", id="dotall-version"
        ),
        pytest.param(
            "release # {new_version}", r"(?x) \d+ \. \d+ ", "release # 3.4", "3.4", id="verbose-literal-prefix"
        ),
        pytest.param(
            "v{new_version}", r"(?m)\d+\.\d+$", "v3.4\nmetadata", "3.4", id="multiline-end-anchor"
        ),
        pytest.param(
            "v{new_version}", r"\d+\.\d+$", "v3.4-extra", None, id="respects-version-end-anchor"
        ),
        pytest.param(
            "v{new_version}", r"\d+\.\d+|nightly-\d+", "vnightly-42", "nightly-42", id="alternative-with-prefix"
        ),
        pytest.param(
            "v{new_version}", r"\d+\.\d+|nightly-\d+", "nightly-42", None, id="every-alternative-requires-prefix"
        ),
        pytest.param(
            "v{new_version}",
            r"(?P<major>\d+)\.(?P<minor>\d+)(?:-rc(\d+))?",
            "v12.34-rc5",
            "12.34-rc5",
            id="returns-full-version-with-inner-captures",
        ),
        pytest.param("v{new_version}", r"\d*", "v", "", id="empty-version-match"),
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