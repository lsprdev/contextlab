import os

import pytest

from dotenv.main import resolve_variables


@pytest.mark.parametrize('override', [False, True])
def test_empty_input_returns_empty_mapping(monkeypatch, override):
    monkeypatch.setenv('RESOLVE_ENV_ONLY', 'ambient')

    assert resolve_variables(iter(()), override=override) == {}


@pytest.mark.parametrize(
    ('override', 'expected_shared', 'expected_null', 'expected_empty'),
    [
        (True, 'from-input', '', ''),
        (False, 'from-env', 'env-null', 'env-empty'),
    ],
)
def test_override_controls_reference_precedence_only(
    monkeypatch, override, expected_shared, expected_null, expected_empty
):
    monkeypatch.setenv('RESOLVE_SHARED', 'from-env')
    monkeypatch.setenv('RESOLVE_NULL', 'env-null')
    monkeypatch.setenv('RESOLVE_EMPTY', 'env-empty')
    monkeypatch.setenv('RESOLVE_ENV_ONLY', 'ambient')
    monkeypatch.delenv('RESOLVE_LOCAL', raising=False)
    monkeypatch.delenv('RESOLVE_OUTPUT', raising=False)
    original_environment = dict(os.environ)
    values = [
        ('RESOLVE_SHARED', 'from-input'),
        ('RESOLVE_NULL', None),
        ('RESOLVE_EMPTY', ''),
        ('RESOLVE_LOCAL', 'local'),
        (
            'RESOLVE_OUTPUT',
            '<${RESOLVE_SHARED}>|<${RESOLVE_NULL:-fallback}>|'
            '<${RESOLVE_EMPTY:-fallback}>|<${RESOLVE_ENV_ONLY}>|<${RESOLVE_LOCAL}>',
        ),
    ]

    assert resolve_variables(values, override=override) == {
        'RESOLVE_SHARED': 'from-input',
        'RESOLVE_NULL': None,
        'RESOLVE_EMPTY': '',
        'RESOLVE_LOCAL': 'local',
        'RESOLVE_OUTPUT': (
            f'<{expected_shared}>|<{expected_null}>|<{expected_empty}>|<ambient>|<local>'
        ),
    }
    assert dict(os.environ) == original_environment


@pytest.mark.parametrize('override', [False, True])
def test_defaults_distinguish_missing_names_from_existing_empty_values(monkeypatch, override):
    monkeypatch.delenv('RESOLVE_MISSING', raising=False)
    monkeypatch.delenv('RESOLVE_NO_VALUE', raising=False)
    monkeypatch.setenv('RESOLVE_EMPTY_ENV', '')
    monkeypatch.setenv('RESOLVE_PRESENT', 'actual')
    values = [
        ('RESOLVE_NO_VALUE', None),
        ('missing', 'a${RESOLVE_MISSING}b'),
        ('default', '${RESOLVE_MISSING:-two words}'),
        ('empty_default', '${RESOLVE_MISSING:-}'),
        ('present', '${RESOLVE_PRESENT:-fallback}'),
        ('none', '[${RESOLVE_NO_VALUE:-fallback}]'),
        ('empty_env', '[${RESOLVE_EMPTY_ENV:-fallback}]'),
    ]

    assert resolve_variables(values, override=override) == {
        'RESOLVE_NO_VALUE': None,
        'missing': 'ab',
        'default': 'two words',
        'empty_default': '',
        'present': 'actual',
        'none': '[]',
        'empty_env': '[]',
    }


@pytest.mark.parametrize('override', [False, True])
def test_resolves_in_input_order_using_latest_resolved_assignment(monkeypatch, override):
    monkeypatch.delenv('RESOLVE_STEP', raising=False)
    monkeypatch.delenv('RESOLVE_CHAIN', raising=False)
    values = iter([
        ('before', '${RESOLVE_STEP:-pending}'),
        ('RESOLVE_STEP', '${RESOLVE_STEP:-start}'),
        ('RESOLVE_CHAIN', '${RESOLVE_STEP}-middle'),
        ('RESOLVE_STEP', '${RESOLVE_CHAIN}+${RESOLVE_STEP}'),
        ('after', '${RESOLVE_STEP}/${RESOLVE_CHAIN}'),
        ('RESOLVE_STEP', None),
    ])

    result = resolve_variables(values, override=override)

    assert list(result.items()) == [
        ('before', 'pending'),
        ('RESOLVE_STEP', None),
        ('RESOLVE_CHAIN', 'start-middle'),
        ('after', 'start-middle+start/start-middle'),
    ]


@pytest.mark.parametrize('override', [False, True])
def test_expansion_preserves_literal_text_and_does_not_expand_substitutions_again(
    monkeypatch, override
):
    monkeypatch.setenv('RESOLVE_RAW', '${RESOLVE_WORD}')
    monkeypatch.setenv('RESOLVE_WORD', 'café')
    monkeypatch.delenv('RESOLVE_INTERMEDIATE', raising=False)
    values = [
        ('literal', '  $RESOLVE_WORD / ${RESOLVE_WORD  \n'),
        ('RESOLVE_INTERMEDIATE', '${RESOLVE_RAW}'),
        ('combined', 'α${RESOLVE_WORD}${RESOLVE_WORD}:${RESOLVE_INTERMEDIATE}\nω'),
    ]

    assert resolve_variables(values, override=override) == {
        'literal': '  $RESOLVE_WORD / ${RESOLVE_WORD  \n',
        'RESOLVE_INTERMEDIATE': '${RESOLVE_WORD}',
        'combined': 'αcafécafé:${RESOLVE_WORD}\nω',
    }


@pytest.mark.parametrize('override', [False, True])
def test_reads_environment_as_each_entry_is_yielded(monkeypatch, override):
    monkeypatch.delenv('RESOLVE_CHANGING', raising=False)

    def values():
        monkeypatch.setenv('RESOLVE_CHANGING', 'first')
        yield 'first', '${RESOLVE_CHANGING}'
        monkeypatch.setenv('RESOLVE_CHANGING', 'second')
        yield 'second', '${RESOLVE_CHANGING}'
        monkeypatch.delenv('RESOLVE_CHANGING')
        yield 'third', '${RESOLVE_CHANGING:-gone}'

    assert resolve_variables(values(), override=override) == {
        'first': 'first',
        'second': 'second',
        'third': 'gone',
    }


def test_resolved_values_are_local_to_each_call(monkeypatch):
    monkeypatch.delenv('RESOLVE_CALL_LOCAL', raising=False)

    first = resolve_variables([('RESOLVE_CALL_LOCAL', 'first')], override=True)
    second = resolve_variables([('next', '${RESOLVE_CALL_LOCAL:-missing}')], override=True)

    assert first == {'RESOLVE_CALL_LOCAL': 'first'}
    assert second == {'next': 'missing'}
