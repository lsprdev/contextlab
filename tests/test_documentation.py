import ast
import hashlib
import json
import pytest

from contextlab.broker import ContextBroker
from contextlab.context import ContextError, build_context, sanitize_project
from contextlab.evaluation import _copy_project


def project_at(root, files):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return {"id": "example", "root": str(root), "source_roots": ["."],
            "include": ["*.py", "rules.md"], "exclude": [],
            "evaluation_include": ["*.py"]}


@pytest.mark.parametrize("condition", ["L", "R", "A"])
def test_examples_are_absent_from_packets_reads_and_searches(tmp_path, condition):
    project = project_at(tmp_path, {
        "main.py": '''from models import Item
from helpers import helper

def focal(item: Item):
    """Preserve this description.

    >>> focal("INPUT_SENTINEL")
    'OUTPUT_SENTINEL'

    Preserve this explanation too.
    """
    return helper(item.value)
''',
        "models.py": '''class Item:
    """The signature type.

    >>> Item()
    'TYPE_SENTINEL'
    """
    value = 1
''',
        "helpers.py": '''def helper(value):
    """The real dependency.

    >>> helper(5)
    'DEPENDENCY_SENTINEL'
    """
    return value * 2
''',
        "rules.md": "Explanatory prose.\n\n>>> focal(5)\n'DOC_SENTINEL'\n\nMore prose.\n",
    })
    packet = build_context(project, {"path": "main.py", "symbol": "focal"}, condition, 10000)
    broker = ContextBroker(packet["files"], 100000, initial_text=packet["text"])
    delivered = packet["text"] + "".join(broker.call("read_file", {"path": path}) for path in packet["files"])
    for hidden in ["INPUT_SENTINEL", "OUTPUT_SENTINEL", "TYPE_SENTINEL", "DEPENDENCY_SENTINEL", "DOC_SENTINEL"]:
        assert hidden not in delivered
        assert json.loads(broker.call("search", {"query": hidden}))["matches"] == []
    assert "Preserve this description." in delivered
    assert "Preserve this explanation too." in delivered
    assert "return helper(item.value)" in delivered
    if condition in {"L", "R"}:
        assert "class Item:" in packet["text"]
    if condition == "R":
        assert "return value * 2" in packet["text"]
        snippet = next(s for s in packet["snippets"] if s["path"] == "helpers.py")
        assert snippet["start_line"] == 1
        assert snippet["end_line"] == 7
    if condition == "A":
        assert packet["text"] == ""
        assert "More prose." in packet["files"]["rules.md"]


def test_module_class_nested_and_async_docstrings_preserve_code_and_locations(tmp_path):
    source = '''"""Descrição do módulo.

>>> [n * 2 for n in range(2)]
[0, 2]

Mais explicação.
"""
CONSTANT = ">>> ordinary string data"
# >>> ordinary code comment
class Example:
    """Descrição da classe.

    >>> Example()
    OBJECT_SENTINEL
    """
    async def method(self):
        """Descrição assíncrona.

        >>> for i in range(2):
        ...     print(i)
        0
        1

        Depois do exemplo.
        """
        def nested():
            """Descrição interna.

            >>> nested()
            Traceback (most recent call last):
                ...
            ValueError: ERROR_SENTINEL
            """
            return 7
        return nested()
'''
    project = project_at(tmp_path, {"main.py": source})
    files, _ = sanitize_project(project)
    prepared = files["main.py"]
    assert "SENTINEL" not in prepared
    assert "Mais explicação." in prepared and "Depois do exemplo." in prepared
    assert 'CONSTANT = ">>> ordinary string data"' in prepared
    assert "# >>> ordinary code comment" in prepared
    assert source.count("\n") == prepared.count("\n")

    def code_without_doc_values(text):
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node, clean=False) is not None:
                    node.body[0].value.value = "documentation"
        return tree

    original_ast = code_without_doc_values(source)
    prepared_ast = code_without_doc_values(prepared)
    assert ast.dump(original_ast) == ast.dump(prepared_ast)
    assert [(n.name, n.lineno, n.end_lineno) for n in ast.walk(original_ast) if isinstance(n, ast.FunctionDef)] == [
        (n.name, n.lineno, n.end_lineno) for n in ast.walk(prepared_ast) if isinstance(n, ast.FunctionDef)]


@pytest.mark.parametrize("literal", [
    '"""Keep accented text: ação.\n\n>>> f()\nHIDDEN\n\nKeep final prose.\n"""',
    "r'''Keep accented text: ação.\n\n>>> f()\nHIDDEN\n\nKeep final prose.\n'''",
    '"Keep accented text: ação.\\n\\n>>> f()\\nHIDDEN\\n\\nKeep final prose."',
    '("Keep accented text: ação.\\n\\n"\n     ">>> f()\\nHIDDEN\\n\\nKeep final prose.")',
    '"Keep accented text: ação.\\n\\n\\x3e\\x3e\\x3e f()\\nHIDDEN\\n\\nKeep final prose."',
])
def test_literal_encodings_and_unicode_columns(tmp_path, literal):
    source = f"def função(): {literal}; return 'unchanged'\n"
    project = project_at(tmp_path, {"main.py": source})
    prepared = sanitize_project(project)[0]["main.py"]
    doc = ast.get_docstring(ast.parse(prepared).body[0], clean=False)
    assert "HIDDEN" not in prepared and ">>>" not in doc
    assert "Keep accented text: ação." in doc and "Keep final prose." in doc
    assert source.count("\n") == prepared.count("\n")
    assert "; return 'unchanged'" in prepared
    project_at(tmp_path, {"main.py": prepared})
    assert sanitize_project(project)[0]["main.py"] == prepared


def test_markdown_fences_tracebacks_and_prose_are_separated(tmp_path):
    doc = """A rule to preserve.

```pycon
>>> operation(
...     1,
... )
Traceback (most recent call last):
    ...
ValueError: HIDDEN
```
Prose immediately after the fence.

>>> print('another')
ANOTHER_HIDDEN

Final prose.
"""
    project = project_at(tmp_path, {"rules.md": doc})
    prepared = sanitize_project(project)[0]["rules.md"]
    assert "HIDDEN" not in prepared and ">>>" not in prepared and "Traceback" not in prepared
    assert "A rule to preserve." in prepared
    assert "Prose immediately after the fence." in prepared
    assert "Final prose." in prepared
    assert prepared.count("\n") == doc.count("\n")


def test_manifest_hashes_and_evaluator_keep_original_source(tmp_path):
    root = tmp_path / "source"
    marker = tmp_path / "must-not-execute"
    source = ('"""Preserve description.\r\n\r\n>>> import pytest\r\n'
              '>>> assert operation() == "HIDDEN"\r\n"""\r\n'
              f'open({str(marker)!r}, "w").write("executed")\r\n'
              'def operation():\r\n    return 3\r\n')
    project = project_at(root, {"main.py": source})
    files, manifest = sanitize_project(project)
    assert not marker.exists()
    assert "HIDDEN" not in files["main.py"] and "import pytest" not in files["main.py"]
    assert "\r" not in files["main.py"]
    record = manifest[0]
    assert record["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    assert record["sha256"] == hashlib.sha256(files["main.py"].encode()).hexdigest()
    assert record["source_sha256"] != record["sha256"]
    assert record["source_chars"] == len(source)
    assert record["chars"] == len(files["main.py"])
    assert record["preparation_version"]
    assert {t["kind"] for t in record["transformations"]} == {"newlines_to_lf", "docstring_doctests"}
    assert record["transformations"][1]["examples_removed"] == 2
    assert record["transformations"][1]["start_line"] == 1
    assert record["transformations"][1]["end_line"] == 5
    _copy_project(project, tmp_path / "evaluation")
    assert (root / "main.py").read_bytes() == source.encode()
    assert (tmp_path / "evaluation/main.py").read_bytes() == source.encode()


@pytest.mark.parametrize("source", [
    'def broken(:\n    """>>> secret_example()"""\n',
    '"""Description.\n\n    >>> first(\n   ... 1)\n    HIDDEN\n"""\n',
])
def test_unparseable_material_is_not_forwarded(tmp_path, source):
    project = project_at(tmp_path, {"main.py": source})
    with pytest.raises(ContextError, match="Cannot prepare documentation in main.py"):
        sanitize_project(project)
