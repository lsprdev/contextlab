import re
from unittest.mock import Mock, call

import pytest

from bumpversion.exceptions import BumpVersionError
from bumpversion.versioning import serialization
from bumpversion.versioning.serialization import parse_version


@pytest.fixture(autouse=True)
def parser_logger(monkeypatch):
    logger = Mock(spec=['debug', 'indent', 'dedent'])
    monkeypatch.setattr(serialization, 'logger', logger)
    return logger


@pytest.mark.parametrize(
    ('version_string', 'parse_pattern'),
    [
        pytest.param('', r'(?P<major>\d*)', id='empty-version-with-zero-width-match'),
        pytest.param('', '(', id='empty-version-with-invalid-pattern'),
        pytest.param('1.2.3', '', id='empty-pattern'),
        pytest.param('', '', id='both-empty'),
    ],
)
def test_empty_input_returns_empty_dictionary_without_starting_parse(
    version_string, parse_pattern, parser_logger
):
    assert parse_version(version_string, parse_pattern) == {}
    parser_logger.indent.assert_not_called()


def test_returns_named_captures_as_strings_and_excludes_unnamed_captures():
    pattern = r'^(v)(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)-(?P<stage>[A-Za-z]+)$'

    assert parse_version('v007.00.09-RC', pattern) == {
        'major': '007',
        'minor': '00',
        'patch': '09',
        'stage': 'RC',
    }


def test_verbose_pattern_supports_comments_and_preserves_literal_hash_and_spaces():
    pattern = r'''
        ^ (?P<major>\d+)  # first numeric part
        \. (?P<minor>\d+) # second numeric part
        [ ] \# \  (?P<label>[A-Z]+) $
    '''

    assert parse_version('12.04 # RC', pattern) == {
        'major': '12',
        'minor': '04',
        'label': 'RC',
    }


def test_search_returns_first_match_inside_surrounding_text():
    assert parse_version('release v02.5 or v8.1 (stable)', r'v(?P<major>\d+)\.(?P<minor>\d+)') == {
        'major': '02',
        'minor': '5',
    }


@pytest.mark.parametrize(
    ('version_string', 'expected'),
    [
        ('1', {'major': '1', 'stage': '', 'serial': '', 'build': ''}),
        ('2-rc03', {'major': '2', 'stage': 'rc', 'serial': '03', 'build': ''}),
        ('3+007', {'major': '3', 'stage': '', 'serial': '', 'build': '007'}),
    ],
)
def test_unmatched_optional_groups_remain_in_result_as_empty_strings(version_string, expected):
    pattern = r'^(?P<major>\d+)(?:-(?P<stage>[a-z]+)(?P<serial>\d+)|\+(?P<build>\d+))?$'

    assert parse_version(version_string, pattern) == expected


def test_zero_width_match_can_return_named_captures():
    assert parse_version('v1', r'(?=(?P<prefix>v)(?P<empty>))') == {'prefix': 'v', 'empty': ''}


def test_whitespace_only_version_can_match_literal_whitespace():
    assert parse_version('  ', r'^(?P<spaces>[ ]+)$') == {'spaces': '  '}


def test_match_with_only_unnamed_groups_returns_empty_dictionary(parser_logger):
    assert parse_version('1.2', r'^(\d+)\.(\d+)$') == {}
    parser_logger.dedent.assert_called_once_with()


@pytest.mark.parametrize(
    ('version_string', 'pattern'),
    [
        ('release 1.2', r'^(?P<major>\d+)\.(?P<minor>\d+)$'),
        ('1x2', r'^(?P<major>\d+)\.(?P<minor>\d+)$'),
        ('RC1', r'^(?P<stage>rc)(?P<serial>\d+)$'),
    ],
)
def test_no_match_returns_empty_dictionary(version_string, pattern, parser_logger):
    assert parse_version(version_string, pattern) == {}
    assert any('does not parse' in args[0] and args[1:] == (pattern, version_string)
               for args, _ in parser_logger.debug.call_args_list)


@pytest.mark.parametrize('pattern', ['(', r'(?P<bad-name>\d+)', r'(?P<part>\d+)(?P<part>\d+)'])
def test_malformed_pattern_reports_original_pattern_and_chains_regex_error(pattern):
    with pytest.raises(BumpVersionError) as caught:
        parse_version('1.2', pattern)

    assert caught.value.message == f"'{pattern}' is not a valid regular expression."
    assert isinstance(caught.value.__cause__, re.error)


def test_success_logs_parsed_values_within_indentation(parser_logger):
    pattern = r'(?P<z>\d+)\.(?P<a>\d+)'

    assert parse_version('2.01', pattern) == {'z': '2', 'a': '01'}
    parser_logger.assert_has_calls([
        call.debug("Parsing version '%s' using regexp '%s'", '2.01', pattern),
        call.indent(),
        call.debug('Parsed the following values: %s', 'a=01, z=2'),
        call.dedent(),
    ])
