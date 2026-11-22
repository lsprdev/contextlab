import os

import pytest

from dotenv.main import resolve_variables


@pytest.mark.parametrize("override", [False, True])
def test_empty_iterable_returns_no_bindings(monkeypatch, override):
    monkeypatch.setenv("DOTENV_TEST_EXTERNAL", "from environment")

    assert resolve_variables(iter(()), override=override) == {}


@pytest.mark.parametrize(
    ("override", "expected_reference"),
    [(False, "from environment"), (True, "from input")],
)
def test_override_controls_lookup_precedence_only(
    monkeypatch, override, expected_reference
):
    monkeypatch.setenv("DOTENV_TEST_SHARED", "from environment")
    monkeypatch.setenv("DOTENV_TEST_EXTERNAL", "external")
    monkeypatch.delenv("DOTENV_TEST_LOCAL", raising=False)
    monkeypatch.delenv("DOTENV_TEST_JOINED", raising=False)
    values = [
        ("DOTENV_TEST_SHARED", "from input"),
        ("DOTENV_TEST_LOCAL", "local"),
        (
            "DOTENV_TEST_JOINED",
            "[${DOTENV_TEST_SHARED}|${DOTENV_TEST_EXTERNAL}|${DOTENV_TEST_LOCAL}]",
        ),
    ]

    assert resolve_variables(values, override=override) == {
        "DOTENV_TEST_SHARED": "from input",
        "DOTENV_TEST_LOCAL": "local",
        "DOTENV_TEST_JOINED": f"[{expected_reference}|external|local]",
    }
    assert os.environ["DOTENV_TEST_SHARED"] == "from environment"
    assert os.environ["DOTENV_TEST_EXTERNAL"] == "external"
    assert "DOTENV_TEST_LOCAL" not in os.environ
    assert "DOTENV_TEST_JOINED" not in os.environ


@pytest.mark.parametrize("override", [False, True])
def test_defaults_distinguish_missing_empty_and_none(monkeypatch, override):
    for name in ("DOTENV_TEST_MISSING", "DOTENV_TEST_EMPTY", "DOTENV_TEST_NONE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DOTENV_TEST_PRESENT", "present")
    monkeypatch.setenv("DOTENV_TEST_ENV_EMPTY", "")
    values = [
        ("DOTENV_TEST_EMPTY", ""),
        ("DOTENV_TEST_NONE", None),
        ("MISSING", "<${DOTENV_TEST_MISSING}>"),
        ("DEFAULT", "<${DOTENV_TEST_MISSING:-fallback text}>"),
        ("EMPTY_DEFAULT", "<${DOTENV_TEST_MISSING:-}>"),
        ("EMPTY_VALUE", "<${DOTENV_TEST_EMPTY:-fallback}>"),
        ("NONE_VALUE", "<${DOTENV_TEST_NONE:-fallback}>"),
        ("PRESENT_VALUE", "<${DOTENV_TEST_PRESENT:-fallback}>"),
        ("EMPTY_ENV_VALUE", "<${DOTENV_TEST_ENV_EMPTY:-fallback}>"),
    ]

    assert resolve_variables(values, override=override) == {
        "DOTENV_TEST_EMPTY": "",
        "DOTENV_TEST_NONE": None,
        "MISSING": "<>",
        "DEFAULT": "<fallback text>",
        "EMPTY_DEFAULT": "<>",
        "EMPTY_VALUE": "<>",
        "NONE_VALUE": "<>",
        "PRESENT_VALUE": "<present>",
        "EMPTY_ENV_VALUE": "<>",
    }


@pytest.mark.parametrize(
    ("override", "expanded"), [(False, "environment|environment"), (True, "|")]
)
def test_empty_and_none_bindings_participate_in_precedence(
    monkeypatch, override, expanded
):
    monkeypatch.setenv("DOTENV_TEST_EMPTY", "environment")
    monkeypatch.setenv("DOTENV_TEST_NONE", "environment")
    values = [
        ("DOTENV_TEST_EMPTY", ""),
        ("DOTENV_TEST_NONE", None),
        ("RESULT", "${DOTENV_TEST_EMPTY:-fallback}|${DOTENV_TEST_NONE:-fallback}"),
    ]

    assert resolve_variables(values, override=override) == {
        "DOTENV_TEST_EMPTY": "",
        "DOTENV_TEST_NONE": None,
        "RESULT": expanded,
    }


@pytest.mark.parametrize("override", [False, True])
def test_one_pass_resolution_uses_latest_preceding_binding(monkeypatch, override):
    monkeypatch.delenv("DOTENV_TEST_CHAIN", raising=False)
    monkeypatch.delenv("DOTENV_TEST_SNAPSHOT", raising=False)
    values = iter(
        [
            ("BEFORE", "${DOTENV_TEST_CHAIN:-forward}"),
            ("DOTENV_TEST_CHAIN", "${DOTENV_TEST_CHAIN:-first}"),
            ("DOTENV_TEST_SNAPSHOT", "${DOTENV_TEST_CHAIN}/saved"),
            ("DOTENV_TEST_CHAIN", "${DOTENV_TEST_CHAIN}/second"),
            ("AFTER", "${DOTENV_TEST_CHAIN}|${DOTENV_TEST_SNAPSHOT}"),
            ("DOTENV_TEST_CHAIN", None),
            ("AFTER_UNSET", "<${DOTENV_TEST_CHAIN:-fallback}>"),
        ]
    )

    resolved = resolve_variables(values, override=override)

    assert list(resolved.items()) == [
        ("BEFORE", "forward"),
        ("DOTENV_TEST_CHAIN", None),
        ("DOTENV_TEST_SNAPSHOT", "first/saved"),
        ("AFTER", "first/second|first/saved"),
        ("AFTER_UNSET", "<>"),
    ]


@pytest.mark.parametrize("override", [False, True])
def test_literal_text_and_adjacent_references_are_preserved(monkeypatch, override):
    monkeypatch.setenv("DOTENV_TEST_WORD", "café")
    values = [
        ("LITERAL", "  $DOTENV_TEST_WORD\nunfinished ${DOTENV_TEST_WORD"),
        ("MIXED", "Pré:${DOTENV_TEST_WORD}${DOTENV_TEST_WORD}\n:end  "),
    ]

    assert resolve_variables(values, override=override) == {
        "LITERAL": "  $DOTENV_TEST_WORD\nunfinished ${DOTENV_TEST_WORD",
        "MIXED": "Pré:cafécafé\n:end  ",
    }


@pytest.mark.parametrize("override", [False, True])
def test_substituted_text_is_not_expanded_again(monkeypatch, override):
    monkeypatch.setenv("DOTENV_TEST_RAW", "${DOTENV_TEST_INNER}")
    monkeypatch.setenv("DOTENV_TEST_INNER", "expanded")
    monkeypatch.delenv("DOTENV_TEST_COPY", raising=False)
    values = [
        ("DOTENV_TEST_COPY", "${DOTENV_TEST_RAW}"),
        ("RESULT", "${DOTENV_TEST_COPY}:${DOTENV_TEST_INNER}"),
    ]

    assert resolve_variables(values, override=override) == {
        "DOTENV_TEST_COPY": "${DOTENV_TEST_INNER}",
        "RESULT": "${DOTENV_TEST_INNER}:expanded",
    }


@pytest.mark.parametrize("override", [False, True])
def test_environment_is_read_as_each_binding_arrives(monkeypatch, override):
    name = "DOTENV_TEST_CHANGING"
    monkeypatch.setenv(name, "initial")

    def bindings():
        yield "FIRST", "${DOTENV_TEST_CHANGING:-missing}"
        monkeypatch.setenv(name, "updated")
        yield "SECOND", "${DOTENV_TEST_CHANGING:-missing}"
        monkeypatch.delenv(name)
        yield "THIRD", "${DOTENV_TEST_CHANGING:-missing}"

    assert resolve_variables(bindings(), override=override) == {
        "FIRST": "initial",
        "SECOND": "updated",
        "THIRD": "missing",
    }


def test_bindings_do_not_leak_between_calls(monkeypatch):
    monkeypatch.delenv("DOTENV_TEST_PREVIOUS", raising=False)

    first = resolve_variables([("DOTENV_TEST_PREVIOUS", "first call")], override=True)
    second = resolve_variables(
        [("RESULT", "${DOTENV_TEST_PREVIOUS:-missing}")], override=True
    )

    assert first == {"DOTENV_TEST_PREVIOUS": "first call"}
    assert second == {"RESULT": "missing"}
