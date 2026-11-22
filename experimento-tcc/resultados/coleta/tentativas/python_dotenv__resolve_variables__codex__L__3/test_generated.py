import os

import pytest

from dotenv.main import resolve_variables


@pytest.mark.parametrize("override", [False, True])
def test_empty_iterable_returns_empty_mapping(override):
    assert resolve_variables(iter(()), override=override) == {}


@pytest.mark.parametrize("override", [False, True])
def test_preserves_none_empty_strings_and_literal_text(override):
    plain = "  café $NAME and $5\nsecond line\t"
    values = [("BARE", None), ("EMPTY", ""), ("PLAIN", plain)]

    assert resolve_variables(values, override=override) == {
        "BARE": None,
        "EMPTY": "",
        "PLAIN": plain,
    }


@pytest.mark.parametrize(
    ("override", "expected"),
    [(False, "before[process|process|process|external|local]after"),
     (True, "before[file|||external|local]after")],
)
def test_override_controls_precedence_for_each_reference(monkeypatch, override, expected):
    monkeypatch.setenv("SHARED", "process")
    monkeypatch.setenv("BARE", "process")
    monkeypatch.setenv("EMPTY", "process")
    monkeypatch.setenv("ENV_ONLY", "external")
    monkeypatch.delenv("LOCAL_ONLY", raising=False)
    values = [
        ("SHARED", "file"),
        ("BARE", None),
        ("EMPTY", ""),
        ("LOCAL_ONLY", "local"),
        ("RESULT", "before[${SHARED}|${BARE}|${EMPTY}|${ENV_ONLY}|${LOCAL_ONLY}]after"),
    ]

    assert resolve_variables(values, override=override) == {
        "SHARED": "file",
        "BARE": None,
        "EMPTY": "",
        "LOCAL_ONLY": "local",
        "RESULT": expected,
    }
    assert os.environ["SHARED"] == "process"
    assert os.environ["BARE"] == "process"
    assert os.environ["EMPTY"] == "process"
    assert os.environ["ENV_ONLY"] == "external"
    assert "LOCAL_ONLY" not in os.environ


@pytest.mark.parametrize("override", [False, True])
def test_defaults_distinguish_missing_from_present_values(monkeypatch, override):
    for name in ("MISSING", "BARE", "LOCAL_EMPTY", "LOCAL_VALUE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENV_EMPTY", "")
    monkeypatch.setenv("ENV_VALUE", "env")
    values = [
        ("BARE", None),
        ("LOCAL_EMPTY", ""),
        ("LOCAL_VALUE", "local"),
        ("RESULT", "|".join([
            "<${MISSING}>",
            "<${MISSING:-fallback value}>",
            "<${MISSING:-}>",
            "<${BARE:-fallback}>",
            "<${LOCAL_EMPTY:-fallback}>",
            "<${ENV_EMPTY:-fallback}>",
            "<${LOCAL_VALUE:-fallback}>",
            "<${ENV_VALUE:-fallback}>",
        ])),
    ]

    assert resolve_variables(values, override=override)["RESULT"] == (
        "<>|<fallback value>|<>|<>|<>|<>|<local>|<env>"
    )


@pytest.mark.parametrize("override", [False, True])
def test_resolves_one_shot_input_in_order_with_duplicate_keys(monkeypatch, override):
    monkeypatch.delenv("ITEM", raising=False)
    values = iter([
        ("BEFORE", "${ITEM:-unseen}"),
        ("ITEM", "${ITEM:-first}"),
        ("BETWEEN", "${ITEM}"),
        ("ITEM", "${ITEM}/second"),
        ("AFTER", "${ITEM}|${BETWEEN}|${ITEM}"),
    ])
    monkeypatch.delenv("BETWEEN", raising=False)

    assert list(resolve_variables(values, override=override).items()) == [
        ("BEFORE", "unseen"),
        ("ITEM", "first/second"),
        ("BETWEEN", "first"),
        ("AFTER", "first/second|first|first/second"),
    ]


@pytest.mark.parametrize("override", [False, True])
def test_first_assignment_can_reference_environment_with_its_own_name(monkeypatch, override):
    monkeypatch.setenv("ITEM", "external")

    assert resolve_variables([("ITEM", "${ITEM}/suffix")], override=override) == {
        "ITEM": "external/suffix",
    }


@pytest.mark.parametrize("override", [False, True])
def test_inserted_text_is_not_interpolated_again(monkeypatch, override):
    monkeypatch.setenv("TEMPLATE", "${INNER}")
    monkeypatch.setenv("INNER", "resolved")
    monkeypatch.delenv("STORED", raising=False)
    values = [("STORED", "<${TEMPLATE}>"), ("RESULT", "${STORED}${INNER}")]

    assert resolve_variables(values, override=override) == {
        "STORED": "<${INNER}>",
        "RESULT": "<${INNER}>resolved",
    }


@pytest.mark.parametrize("override", [False, True])
def test_reads_environment_as_input_is_consumed(monkeypatch, override):
    def values():
        monkeypatch.setenv("SOURCE", "first")
        yield "FIRST", "${SOURCE}"
        monkeypatch.setenv("SOURCE", "second")
        yield "SECOND", "${SOURCE}"
        monkeypatch.delenv("SOURCE")
        yield "THIRD", "${SOURCE:-missing}"

    assert resolve_variables(values(), override=override) == {
        "FIRST": "first",
        "SECOND": "second",
        "THIRD": "missing",
    }


@pytest.mark.parametrize("override", [False, True])
def test_resolved_values_do_not_leak_into_later_calls(monkeypatch, override):
    monkeypatch.delenv("LOCAL_ONLY", raising=False)

    first = resolve_variables([("LOCAL_ONLY", "first call")], override=override)
    second = resolve_variables([("RESULT", "${LOCAL_ONLY:-missing}")], override=override)

    assert first == {"LOCAL_ONLY": "first call"}
    assert second == {"RESULT": "missing"}
    assert "LOCAL_ONLY" not in os.environ
