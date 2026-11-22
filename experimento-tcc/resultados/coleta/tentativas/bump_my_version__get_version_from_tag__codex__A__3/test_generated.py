import re

import pytest

from bumpversion.scm.models import SCMConfig


VERSION_PATTERN = r"\d+\.\d+\.\d+"


def make_config(tag_name="v{new_version}", parse_pattern=VERSION_PATTERN):
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
    ("tag", "expected"),
    [
        ("v01.002.3", "01.002.3"),
        ("refs/tags/v1.2.3-5-gabc123", "1.2.3"),
        ("v0.1.2-v3.4.5", "0.1.2"),
        ("vbad-v3.4.5", "3.4.5"),
        ("1.2.3", None),
        ("v-1.2.3", None),
        ("v1x2x3", None),
        ("v1.2", None),
        ("V1.2.3", None),
        ("", None),
    ],
)
def test_extracts_first_matching_version(tag, expected):
    assert make_config().get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("tag_name", "tag", "expected"),
    [
        ("{new_version}", "build/1.2.3", "1.2.3"),
        ("{new_version}-stable", "1.2.3-other", "1.2.3"),
        ("rel-{new_version}-stable", "rel-1.2.3", "1.2.3"),
        ("rel-{new_version}-stable", "rel-1.2.3-beta", "1.2.3"),
        ("rel-{new_version}-{new_version}", "rel-1.2.3", "1.2.3"),
        ("rel-", "rel-1.2.3", "1.2.3"),
        ("rel-", "1.2.3", None),
        ("{project}/v{new_version}", "{project}/v1.2.3", "1.2.3"),
        ("{project}/v{new_version}", "project/v1.2.3", None),
        (r"rel[qa].+\v{new_version}", r"rel[qa].+\v1.2.3", "1.2.3"),
        (r"rel[qa].+\v{new_version}", "relaqxxv1.2.3", None),
    ],
)
def test_uses_literal_prefix_before_first_version_placeholder(tag_name, tag, expected):
    assert make_config(tag_name=tag_name).get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("parse_pattern", "tag", "expected"),
    [
        (r"\\d+\\.\\d+\.\d+", "v12.34.56-extra", "12.34.56"),
        (r"(?P<major>\d+)\.(\d+)\.(\d+)(?:-(?:rc|beta)\d+)?", "v10.2.3-rc4-extra", "10.2.3-rc4"),
        (r"dev|\d+", "v42!", "42"),
        (r"dev|\d+", "build42", None),
        (r"dev|\d+", "vdev!", "dev"),
        (r"\d+$", "v42-extra", None),
        (r"(?=end)", "vend", ""),
        (r"(?=end)", "vstop", None),
    ],
)
def test_applies_configured_version_pattern(parse_pattern, tag, expected):
    assert make_config(parse_pattern=parse_pattern).get_version_from_tag(tag) == expected


@pytest.mark.parametrize(
    ("tag_name", "parse_pattern", "tag", "expected"),
    [
        ("release-{new_version}", r"(?i)[a-z]+\d+", "RELEASE-RC12", "RC12"),
        ("release-{new_version}", r"(?i:[a-z]+)\d+", "release-RC12", "RC12"),
        ("release-{new_version}", r"(?i:[a-z]+)\d+", "RELEASE-RC12", None),
        ("Build # {new_version}", r"(?ix)[a-z]+ \\d+", "BUILD # RC12", "RC12"),
        ("Build # {new_version}", r"(?ix)[a-z]+ \d+", "BUILD#RC12", None),
        ("v{new_version}", r"(?m)\d+$", "v42\nnext", "42"),
        ("v{new_version}", r"(?s)A.B", "vA\nB!", "A\nB"),
        ("v{new_version}", r"\d+", "v١٢", "١٢"),
        ("v{new_version}", r"(?a)\d+", "v١٢", None),
    ],
)
def test_honors_regex_flags(tag_name, parse_pattern, tag, expected):
    config = make_config(tag_name=tag_name, parse_pattern=parse_pattern)
    assert config.get_version_from_tag(tag) == expected


def test_invalid_version_pattern_raises_regex_error():
    config = make_config(parse_pattern="[")

    with pytest.raises(re.error):
        config.get_version_from_tag("v1.2.3")
