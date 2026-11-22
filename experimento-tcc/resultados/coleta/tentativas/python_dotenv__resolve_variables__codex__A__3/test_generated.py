import os

import pytest

from dotenv.main import resolve_variables


@pytest.mark.parametrize('override', [False, True])
def test_empty_input_returns_empty_mapping(override):
    assert resolve_variables(iter(()), override=override) == {}


@pytest.mark.parametrize(
    ('override', 'expected_shared'),
    [(False, 'process'), (True, 'file')],
)
def test_combines_environment_and_previous_bindings(monkeypatch, override, expected_shared):
    monkeypatch.setenv('DOTENV_TEST_SHARED', 'process')
    monkeypatch.setenv('DOTENV_TEST_PROCESS_ONLY', 'external')
    monkeypatch.delenv('DOTENV_TEST_FILE_ONLY', raising=False)
    monkeypatch.delenv('DOTENV_TEST_COMBINED', raising=False)
    values = [
        ('DOTENV_TEST_SHARED', 'file'),
        ('DOTENV_TEST_FILE_ONLY', 'local'),
        (
            'DOTENV_TEST_COMBINED',
            'start:${DOTENV_TEST_SHARED}/${DOTENV_TEST_PROCESS_ONLY}'
            '/${DOTENV_TEST_FILE_ONLY}/${DOTENV_TEST_SHARED}:end',
        ),
    ]

    result = resolve_variables(values, override=override)

    assert result == {
        'DOTENV_TEST_SHARED': 'file',
        'DOTENV_TEST_FILE_ONLY': 'local',
        'DOTENV_TEST_COMBINED': f'start:{expected_shared}/external/local/{expected_shared}:end',
    }
    assert os.environ['DOTENV_TEST_SHARED'] == 'process'
    assert os.environ['DOTENV_TEST_PROCESS_ONLY'] == 'external'
    assert 'DOTENV_TEST_FILE_ONLY' not in os.environ
    assert 'DOTENV_TEST_COMBINED' not in os.environ


@pytest.mark.parametrize(
    ('override', 'expected_none', 'expected_empty', 'expected_process_empty'),
    [(False, 'external-none', 'external-empty', ''), (True, '', '', 'local')],
)
def test_distinguishes_missing_empty_and_valueless_bindings(
    monkeypatch, override, expected_none, expected_empty, expected_process_empty
):
    monkeypatch.setenv('DOTENV_TEST_NONE', 'external-none')
    monkeypatch.setenv('DOTENV_TEST_EMPTY', 'external-empty')
    monkeypatch.setenv('DOTENV_TEST_PROCESS_EMPTY', '')
    monkeypatch.delenv('DOTENV_TEST_MISSING', raising=False)
    monkeypatch.delenv('DOTENV_TEST_LOCAL_NONE', raising=False)
    monkeypatch.delenv('DOTENV_TEST_LOCAL_EMPTY', raising=False)
    values = [
        ('DOTENV_TEST_NONE', None),
        ('DOTENV_TEST_EMPTY', ''),
        ('DOTENV_TEST_PROCESS_EMPTY', 'local'),
        ('DOTENV_TEST_LOCAL_NONE', None),
        ('DOTENV_TEST_LOCAL_EMPTY', ''),
        (
            'RESULT',
            '${DOTENV_TEST_MISSING:-fallback}|${DOTENV_TEST_MISSING}|'
            '${DOTENV_TEST_MISSING:-}|${DOTENV_TEST_NONE:-unused}|'
            '${DOTENV_TEST_EMPTY:-unused}|${DOTENV_TEST_PROCESS_EMPTY:-unused}|'
            '${DOTENV_TEST_LOCAL_NONE:-unused}|${DOTENV_TEST_LOCAL_EMPTY:-unused}',
        ),
    ]

    assert resolve_variables(values, override=override) == {
        'DOTENV_TEST_NONE': None,
        'DOTENV_TEST_EMPTY': '',
        'DOTENV_TEST_PROCESS_EMPTY': 'local',
        'DOTENV_TEST_LOCAL_NONE': None,
        'DOTENV_TEST_LOCAL_EMPTY': '',
        'RESULT': '|'.join(
            ('fallback', '', '', expected_none, expected_empty, expected_process_empty, '', '')
        ),
    }


@pytest.mark.parametrize('override', [False, True])
def test_resolves_in_input_order_and_uses_latest_resolved_duplicate(monkeypatch, override):
    for key in ('DOTENV_TEST_ITEM', 'DOTENV_TEST_FIRST', 'DOTENV_TEST_LATER'):
        monkeypatch.delenv(key, raising=False)
    values = iter([
        ('DOTENV_TEST_FIRST', '${DOTENV_TEST_LATER:-early}'),
        ('DOTENV_TEST_ITEM', '${DOTENV_TEST_FIRST}-one'),
        ('CHECKPOINT', '${DOTENV_TEST_ITEM}'),
        ('DOTENV_TEST_LATER', 'late'),
        ('DOTENV_TEST_ITEM', '${DOTENV_TEST_ITEM}/${DOTENV_TEST_LATER}'),
        ('FINAL', '${DOTENV_TEST_ITEM}:${DOTENV_TEST_FIRST}'),
    ])

    assert list(resolve_variables(values, override=override).items()) == [
        ('DOTENV_TEST_FIRST', 'early'),
        ('DOTENV_TEST_ITEM', 'early-one/late'),
        ('CHECKPOINT', 'early-one'),
        ('DOTENV_TEST_LATER', 'late'),
        ('FINAL', 'early-one/late:early'),
    ]


@pytest.mark.parametrize(
    ('override', 'expected'),
    [(False, 'external/third'), (True, 'external/first/second/third')],
)
def test_self_reference_obeys_precedence_before_reassignment(monkeypatch, override, expected):
    monkeypatch.setenv('DOTENV_TEST_SELF', 'external')
    values = [
        ('DOTENV_TEST_SELF', '${DOTENV_TEST_SELF}/first'),
        ('DOTENV_TEST_SELF', '${DOTENV_TEST_SELF}/second'),
        ('DOTENV_TEST_SELF', '${DOTENV_TEST_SELF}/third'),
    ]

    assert resolve_variables(values, override=override) == {'DOTENV_TEST_SELF': expected}


@pytest.mark.parametrize('override', [False, True])
def test_reads_current_environment_as_the_iterable_yields(monkeypatch, override):
    key = 'DOTENV_TEST_CHANGING'
    monkeypatch.setenv(key, 'initial')

    def values():
        yield 'FIRST', '${DOTENV_TEST_CHANGING}'
        monkeypatch.setenv(key, 'updated')
        yield 'SECOND', '${DOTENV_TEST_CHANGING}'
        monkeypatch.delenv(key)
        yield 'THIRD', '${DOTENV_TEST_CHANGING:-gone}'

    assert resolve_variables(values(), override=override) == {
        'FIRST': 'initial',
        'SECOND': 'updated',
        'THIRD': 'gone',
    }


def test_preserves_literal_text_and_expands_each_placeholder_once(monkeypatch):
    monkeypatch.setenv('DOTENV_TEST_NESTED', '${DOTENV_TEST_INNER}')
    monkeypatch.setenv('DOTENV_TEST_INNER', 'inner')
    values = [
        ('LITERAL', '  café\n$DOTENV_TEST_INNER ${DOTENV_TEST_INNER  '),
        ('EXPANDED', ' [${DOTENV_TEST_NESTED}${DOTENV_TEST_INNER}]\n '),
    ]

    assert resolve_variables(values, override=True) == {
        'LITERAL': '  café\n$DOTENV_TEST_INNER ${DOTENV_TEST_INNER  ',
        'EXPANDED': ' [${DOTENV_TEST_INNER}inner]\n ',
    }


def test_bindings_do_not_carry_over_between_calls(monkeypatch):
    monkeypatch.delenv('DOTENV_TEST_PRIVATE', raising=False)

    first = resolve_variables([('DOTENV_TEST_PRIVATE', 'first')], override=True)
    second = resolve_variables([('READ', '${DOTENV_TEST_PRIVATE:-absent}')], override=True)

    assert first == {'DOTENV_TEST_PRIVATE': 'first'}
    assert second == {'READ': 'absent'}
