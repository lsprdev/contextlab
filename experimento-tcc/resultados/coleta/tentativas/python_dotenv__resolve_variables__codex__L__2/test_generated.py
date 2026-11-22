import os

import pytest

from dotenv.main import resolve_variables


@pytest.mark.parametrize("override", [False, True])
def test_empty_input_does_not_include_environment(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_EXTERNAL", "external")

    assert resolve_variables(iter(()), override=override) == {}


@pytest.mark.parametrize("override", [False, True])
def test_preserves_none_empty_and_literal_values(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_VALUELESS", "external")
    monkeypatch.setenv("RESOLVE_TEST_EMPTY", "external")
    monkeypatch.setenv("RESOLVE_TEST_WORD", "expanded")
    values = [
        ("RESOLVE_TEST_VALUELESS", None),
        ("RESOLVE_TEST_EMPTY", ""),
        ("TEXT", "  café\nsegunda linha\t "),
        ("BARE", "$RESOLVE_TEST_WORD"),
        ("UNCLOSED", "before ${RESOLVE_TEST_WORD"),
    ]

    result = resolve_variables(values, override=override)

    assert list(result.items()) == values


@pytest.mark.parametrize(
    ("override", "expected"),
    [(False, "environment"), (True, "file")],
    ids=["environment-first", "file-first"],
)
def test_precedence_with_both_sources_available(monkeypatch, override, expected):
    monkeypatch.setenv("RESOLVE_TEST_SHARED", "environment")
    monkeypatch.setenv("RESOLVE_TEST_EXTERNAL", "external")
    monkeypatch.delenv("RESOLVE_TEST_LOCAL", raising=False)
    values = [
        ("RESOLVE_TEST_SHARED", "file"),
        ("RESOLVE_TEST_LOCAL", "local"),
        (
            "COMBINED",
            "<${RESOLVE_TEST_SHARED:-fallback}/${RESOLVE_TEST_EXTERNAL}/"
            "${RESOLVE_TEST_LOCAL}/${RESOLVE_TEST_SHARED}>",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_SHARED": "file",
        "RESOLVE_TEST_LOCAL": "local",
        "COMBINED": f"<{expected}/external/local/{expected}>",
    }


@pytest.mark.parametrize("override", [False, True])
def test_missing_reference_defaults_and_present_empty_values(monkeypatch, override):
    monkeypatch.delenv("RESOLVE_TEST_MISSING", raising=False)
    monkeypatch.delenv("RESOLVE_TEST_NO_VALUE", raising=False)
    monkeypatch.delenv("RESOLVE_TEST_LOCAL_EMPTY", raising=False)
    monkeypatch.setenv("RESOLVE_TEST_ENV_EMPTY", "")
    values = [
        ("RESOLVE_TEST_NO_VALUE", None),
        ("RESOLVE_TEST_LOCAL_EMPTY", ""),
        (
            "MISSING",
            "[${RESOLVE_TEST_MISSING}][${RESOLVE_TEST_MISSING:-fallback text}]"
            "[${RESOLVE_TEST_MISSING:-}]",
        ),
        (
            "PRESENT",
            "[${RESOLVE_TEST_NO_VALUE:-fallback}][${RESOLVE_TEST_LOCAL_EMPTY:-fallback}]"
            "[${RESOLVE_TEST_ENV_EMPTY:-fallback}]",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_NO_VALUE": None,
        "RESOLVE_TEST_LOCAL_EMPTY": "",
        "MISSING": "[][fallback text][]",
        "PRESENT": "[][][]",
    }


@pytest.mark.parametrize(
    ("override", "expected"),
    [(False, "[external][external][]"), (True, "[][][local]")],
    ids=["environment-first", "file-first"],
)
def test_precedence_uses_key_presence_for_empty_and_none(monkeypatch, override, expected):
    monkeypatch.setenv("RESOLVE_TEST_NONE", "external")
    monkeypatch.setenv("RESOLVE_TEST_EMPTY", "external")
    monkeypatch.setenv("RESOLVE_TEST_ENV_EMPTY", "")
    values = [
        ("RESOLVE_TEST_NONE", None),
        ("RESOLVE_TEST_EMPTY", ""),
        ("RESOLVE_TEST_ENV_EMPTY", "local"),
        (
            "COMBINED",
            "[${RESOLVE_TEST_NONE:-default}][${RESOLVE_TEST_EMPTY:-default}]"
            "[${RESOLVE_TEST_ENV_EMPTY:-default}]",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_NONE": None,
        "RESOLVE_TEST_EMPTY": "",
        "RESOLVE_TEST_ENV_EMPTY": "local",
        "COMBINED": expected,
    }


@pytest.mark.parametrize("override", [False, True])
def test_resolves_in_input_order_with_forward_and_repeated_assignments(
    monkeypatch, override
):
    monkeypatch.delenv("RESOLVE_TEST_VERSION", raising=False)
    monkeypatch.delenv("RESOLVE_TEST_BEFORE", raising=False)
    values = iter([
        ("RESOLVE_TEST_BEFORE", "${RESOLVE_TEST_VERSION:-early}"),
        ("RESOLVE_TEST_VERSION", "${RESOLVE_TEST_VERSION:-first}"),
        ("SNAPSHOT", "${RESOLVE_TEST_VERSION}"),
        ("RESOLVE_TEST_VERSION", "${RESOLVE_TEST_VERSION}-second"),
        ("AFTER", "${RESOLVE_TEST_BEFORE}/${RESOLVE_TEST_VERSION}"),
    ])

    result = resolve_variables(values, override=override)

    assert list(result.items()) == [
        ("RESOLVE_TEST_BEFORE", "early"),
        ("RESOLVE_TEST_VERSION", "first-second"),
        ("SNAPSHOT", "first"),
        ("AFTER", "early/first-second"),
    ]


@pytest.mark.parametrize("override", [False, True])
def test_substituted_text_is_not_expanded_again(monkeypatch, override):
    monkeypatch.setenv("RESOLVE_TEST_RAW", "${RESOLVE_TEST_INNER}")
    monkeypatch.setenv("RESOLVE_TEST_INNER", "inner")
    monkeypatch.delenv("RESOLVE_TEST_COPY", raising=False)
    values = [
        ("RESOLVE_TEST_COPY", "${RESOLVE_TEST_RAW}"),
        ("COMBINED", "${RESOLVE_TEST_COPY}:${RESOLVE_TEST_INNER}"),
    ]

    assert resolve_variables(values, override=override) == {
        "RESOLVE_TEST_COPY": "${RESOLVE_TEST_INNER}",
        "COMBINED": "${RESOLVE_TEST_INNER}:inner",
    }


@pytest.mark.parametrize("override", [False, True])
def test_reads_environment_as_each_assignment_is_yielded(monkeypatch, override):
    key = "RESOLVE_TEST_CHANGING"
    monkeypatch.setenv(key, "initial")

    def assignments():
        yield "FIRST", "${RESOLVE_TEST_CHANGING}"
        monkeypatch.setenv(key, "updated")
        yield "SECOND", "${RESOLVE_TEST_CHANGING}"
        monkeypatch.delenv(key)
        yield "THIRD", "${RESOLVE_TEST_CHANGING:-fallback}"

    assert resolve_variables(assignments(), override=override) == {
        "FIRST": "initial",
        "SECOND": "updated",
        "THIRD": "fallback",
    }


@pytest.mark.parametrize("override", [False, True])
def test_assignments_do_not_leak_into_environment_or_later_calls(monkeypatch, override):
    existing = "RESOLVE_TEST_EXISTING"
    new = "RESOLVE_TEST_NEW"
    monkeypatch.setenv(existing, "original")
    monkeypatch.delenv(new, raising=False)

    first = resolve_variables([(existing, "replacement"), (new, "new")], override)
    second = resolve_variables(
        [("CHECK", "${RESOLVE_TEST_EXISTING}/${RESOLVE_TEST_NEW:-missing}")],
        override,
    )

    assert first == {existing: "replacement", new: "new"}
    assert second == {"CHECK": "original/missing"}
    assert os.environ[existing] == "original"
    assert new not in os.environ
