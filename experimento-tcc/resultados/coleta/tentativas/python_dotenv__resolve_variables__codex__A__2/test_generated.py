import os

import pytest

from dotenv.main import resolve_variables


@pytest.mark.parametrize("override", [True, False])
def test_empty_input_returns_empty_mapping(override):
    assert resolve_variables(iter(()), override=override) == {}


@pytest.mark.parametrize(
    ("override", "expected"),
    [(True, "file"), (False, "process")],
)
def test_override_controls_reference_precedence(monkeypatch, override, expected):
    monkeypatch.setenv("TEST_DOTENV_SHARED", "process")
    monkeypatch.setenv("TEST_DOTENV_PROCESS_ONLY", "from-process")
    monkeypatch.delenv("TEST_DOTENV_FILE_ONLY", raising=False)
    monkeypatch.delenv("TEST_DOTENV_RESULT", raising=False)
    values = [
        ("TEST_DOTENV_SHARED", "file"),
        ("TEST_DOTENV_FILE_ONLY", "from-file"),
        (
            "TEST_DOTENV_RESULT",
            "[${TEST_DOTENV_SHARED:-fallback}]"
            "${TEST_DOTENV_PROCESS_ONLY}/${TEST_DOTENV_FILE_ONLY}",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "TEST_DOTENV_SHARED": "file",
        "TEST_DOTENV_FILE_ONLY": "from-file",
        "TEST_DOTENV_RESULT": f"[{expected}]from-process/from-file",
    }
    assert os.environ["TEST_DOTENV_SHARED"] == "process"
    assert "TEST_DOTENV_FILE_ONLY" not in os.environ
    assert "TEST_DOTENV_RESULT" not in os.environ


@pytest.mark.parametrize("override", [True, False])
def test_missing_empty_and_valueless_references(monkeypatch, override):
    monkeypatch.setenv("TEST_DOTENV_EMPTY_ENV", "")
    monkeypatch.delenv("TEST_DOTENV_MISSING", raising=False)
    monkeypatch.delenv("TEST_DOTENV_NONE", raising=False)
    monkeypatch.delenv("TEST_DOTENV_EMPTY", raising=False)
    values = [
        ("TEST_DOTENV_NONE", None),
        ("TEST_DOTENV_EMPTY", ""),
        (
            "TEST_DOTENV_RESULT",
            "${TEST_DOTENV_MISSING}|${TEST_DOTENV_MISSING:-fallback: text}|"
            "${TEST_DOTENV_MISSING:-}|${TEST_DOTENV_NONE:-fallback}|"
            "${TEST_DOTENV_EMPTY:-fallback}|${TEST_DOTENV_EMPTY_ENV:-fallback}",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "TEST_DOTENV_NONE": None,
        "TEST_DOTENV_EMPTY": "",
        "TEST_DOTENV_RESULT": "|fallback: text||||",
    }


@pytest.mark.parametrize(
    ("override", "expected"),
    [(True, "<>"), (False, "<process>")],
)
def test_none_and_empty_assignments_participate_in_precedence(
    monkeypatch, override, expected
):
    monkeypatch.setenv("TEST_DOTENV_NONE", "process")
    monkeypatch.setenv("TEST_DOTENV_EMPTY", "process")
    values = [
        ("TEST_DOTENV_NONE", None),
        ("TEST_DOTENV_READ_NONE", "<${TEST_DOTENV_NONE:-fallback}>"),
        ("TEST_DOTENV_EMPTY", ""),
        ("TEST_DOTENV_READ_EMPTY", "<${TEST_DOTENV_EMPTY:-fallback}>"),
    ]

    assert resolve_variables(values, override=override) == {
        "TEST_DOTENV_NONE": None,
        "TEST_DOTENV_READ_NONE": expected,
        "TEST_DOTENV_EMPTY": "",
        "TEST_DOTENV_READ_EMPTY": expected,
    }


@pytest.mark.parametrize("override", [True, False])
def test_references_use_the_latest_prior_resolved_assignment(monkeypatch, override):
    monkeypatch.delenv("TEST_DOTENV_ITEM", raising=False)
    monkeypatch.delenv("TEST_DOTENV_BEFORE", raising=False)
    values = iter(
        [
            ("TEST_DOTENV_BEFORE", "${TEST_DOTENV_ITEM:-forward}"),
            ("TEST_DOTENV_ITEM", "${TEST_DOTENV_ITEM:-first}"),
            ("TEST_DOTENV_BETWEEN", "${TEST_DOTENV_ITEM}"),
            ("TEST_DOTENV_ITEM", "${TEST_DOTENV_ITEM}-second"),
            ("TEST_DOTENV_AFTER", "${TEST_DOTENV_BEFORE}/${TEST_DOTENV_ITEM}"),
        ]
    )

    assert list(resolve_variables(values, override=override).items()) == [
        ("TEST_DOTENV_BEFORE", "forward"),
        ("TEST_DOTENV_ITEM", "first-second"),
        ("TEST_DOTENV_BETWEEN", "first"),
        ("TEST_DOTENV_AFTER", "forward/first-second"),
    ]


@pytest.mark.parametrize("override", [True, False])
def test_literal_text_and_substituted_values_are_preserved(monkeypatch, override):
    monkeypatch.setenv("TEST_DOTENV_TOKEN", "${TEST_DOTENV_LEAF}")
    monkeypatch.setenv("TEST_DOTENV_LEAF", "leaf")
    monkeypatch.delenv("TEST_DOTENV_COPY", raising=False)
    values = [
        ("TEST_DOTENV_COPY", "${TEST_DOTENV_TOKEN}"),
        ("TEST_DOTENV_LITERAL", "  café $TEST_DOTENV_LEAF ${unfinished\n"),
        ("TEST_DOTENV_RESULT", " ${TEST_DOTENV_COPY}${TEST_DOTENV_LEAF}\n"),
    ]

    assert resolve_variables(values, override=override) == {
        "TEST_DOTENV_COPY": "${TEST_DOTENV_LEAF}",
        "TEST_DOTENV_LITERAL": "  café $TEST_DOTENV_LEAF ${unfinished\n",
        "TEST_DOTENV_RESULT": " ${TEST_DOTENV_LEAF}leaf\n",
    }


@pytest.mark.parametrize("override", [True, False])
def test_environment_is_read_as_each_input_pair_is_consumed(monkeypatch, override):
    monkeypatch.delenv("TEST_DOTENV_CHANGING", raising=False)

    def values():
        yield "TEST_DOTENV_BEFORE", "${TEST_DOTENV_CHANGING:-missing}"
        monkeypatch.setenv("TEST_DOTENV_CHANGING", "first")
        yield "TEST_DOTENV_FIRST", "${TEST_DOTENV_CHANGING}"
        monkeypatch.setenv("TEST_DOTENV_CHANGING", "second")
        yield "TEST_DOTENV_SECOND", "${TEST_DOTENV_CHANGING}"

    assert resolve_variables(values(), override=override) == {
        "TEST_DOTENV_BEFORE": "missing",
        "TEST_DOTENV_FIRST": "first",
        "TEST_DOTENV_SECOND": "second",
    }
