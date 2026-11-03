"""Remove doctest examples from generation materials without executing them."""
from __future__ import annotations

import ast
import doctest
import json
import re


PREPARATION_VERSION = "doctest-1"
_DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
_FENCE = re.compile(r"^[ \t]*(?:`{3,}|~{3,}).*$", re.MULTILINE)


def strip_doctests(text: str) -> tuple[str, int]:
    """Blank prompts, continuations and expected output; retain line numbers.

    Markdown fences delimit examples rather than being expected output. Blank
    them only in the parser input so a closing fence cannot consume later prose.
    Invalid doctest formatting raises ValueError instead of exposing the example.
    """
    parser_text = _FENCE.sub("", text)
    examples = doctest.DocTestParser().get_examples(parser_text)
    lines = text.split("\n")
    for example in examples:
        end = example.lineno + example.source.count("\n") + example.want.count("\n")
        for index in range(example.lineno, min(end, len(lines))):
            lines[index] = ""
    return "\n".join(lines), len(examples)


def _literal(value: str, source_lines: int) -> str:
    # Decode/encode docstrings to handle raw strings, escaped newlines, and
    # adjacent literals alike. Prefer readable multiline documentation.
    if value.count("\n") == source_lines:
        body = json.dumps(value, ensure_ascii=False)[1:-1]
        body = re.sub(r"\\.", lambda match: "\n" if match[0] == r"\n" else match[0], body)
        return '"""' + body + '"""'
    # Escaped newlines need not correspond to physical source lines. Parentheses
    # preserve the original line count without placing newlines outside a string
    # expression, including in a one-line function or a concatenated docstring.
    return "(" + repr(value) + "\n" * source_lines + ")"


def prepare_documentation(text: str, *, python: bool) -> tuple[str, list[dict]]:
    """Return a prepared view and audit records; never rewrite source files."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    changes = []
    if normalized != text:
        changes.append({"kind": "newlines_to_lf"})
    text = normalized
    if not python:
        cleaned, count = strip_doctests(text)
        if count:
            changes.append({"kind": "documentation_doctests", "examples_removed": count,
                            "start_line": 1, "end_line": len(text.splitlines())})
        return cleaned, changes

    tree = ast.parse(text)
    raw = text.encode("utf-8")
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    replacements = []
    for owner in ast.walk(tree):
        if not isinstance(owner, _DOCSTRING_OWNERS):
            continue
        doc = ast.get_docstring(owner, clean=False)
        if doc is None:
            continue
        cleaned, count = strip_doctests(doc)
        if not count:
            continue
        node = owner.body[0].value
        start = offsets[node.lineno - 1] + node.col_offset
        end = offsets[node.end_lineno - 1] + node.end_col_offset
        replacement = _literal(cleaned, raw[start:end].count(b"\n")).encode("utf-8")
        replacements.append((start, end, replacement, {
            "kind": "docstring_doctests", "examples_removed": count,
            "start_line": node.lineno, "end_line": node.end_lineno,
        }))
    # AST columns are UTF-8 byte offsets. Work backwards to retain offsets even
    # when a replacement is shorter or Unicode occurs before a docstring.
    for start, end, replacement, _ in sorted(replacements, reverse=True):
        raw = raw[:start] + replacement + raw[end:]
    changes.extend(change for _, _, _, change in sorted(replacements))
    prepared = raw.decode("utf-8")
    if replacements:
        ast.parse(prepared)
    return prepared, changes
