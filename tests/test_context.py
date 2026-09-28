import json
from pathlib import Path

import pytest

from contextlab.context import ContextError, build_context, sanitize_project


def project_at(tmp_path, files):
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return {"id": "demo", "root": str(tmp_path), "source_roots": ["."], "include": ["**/*.py", "docs/rules.md"], "exclude": []}


@pytest.fixture
def example(tmp_path):
    project = project_at(tmp_path, {
        "shop/__init__.py": "",
        "shop/freight.py": "from .customer import Customer as Person\nfrom .rates import rate as base_rate\n\ndef freight(weight: float, customer: Person) -> float:\n    return base_rate(weight) if customer.vip else 0\n",
        "shop/customer.py": "from dataclasses import dataclass\n\n@dataclass\nclass Customer:\n    vip: bool = False\n\ndef unrelated_secret():\n    return 123\n",
        "shop/rates.py": "from .values import BASE\n\ndef rate(weight):\n    return BASE + weight\n\ndef never_used():\n    return 999\n",
        "shop/values.py": "BASE = 5\n",
        "docs/rules.md": "VIP clients have a reduced rate.\n",
        "tests/test_freight.py": "def test_freight():\n    assert True\n",
    })
    target = {"id": "freight", "path": "shop/freight.py", "symbol": "freight", "import": "shop.freight:freight"}
    return project, target


def test_local_has_entire_focal_and_complete_signature_type_only(example):
    project, target = example
    packet = build_context(project, target, "L", 5000)
    assert packet["files"]["shop/freight.py"] == Path(project["root"], target["path"]).read_text()
    assert "@dataclass\nclass Customer" in packet["text"]
    assert "unrelated_secret" not in packet["text"]
    assert "def rate(" not in packet["text"]
    assert packet["equal_to_local"]
    json.dumps(packet)


def test_recovered_is_direct_not_transitive_and_deduplicated(example):
    project, target = example
    packet = build_context(project, target, "R", 5000)
    assert "def rate(weight)" in packet["text"]
    assert "BASE = 5" not in packet["text"]
    assert "never_used" not in packet["text"]
    assert sum(item["path"] == "shop/customer.py" for item in packet["snippets"]) == 1
    assert not packet["equal_to_local"]
    assert any(item["reference"] == "customer.vip" for item in packet["unresolved"])


def test_budget_keeps_local_integral_and_omits_whole_recovery(example):
    project, target = example
    local = build_context(project, target, "L", 5000)
    recovered = build_context(project, target, "R", len(local["text"]))
    assert recovered["text"] == local["text"]
    assert recovered["equal_to_local"]
    assert recovered["omitted"][0]["reason"] == "context_budget"
    with pytest.raises(ContextError, match="Integral L"):
        build_context(project, target, "L", len(local["text"]) - 1)


def test_autonomous_exposes_sanitized_snapshot_without_initial_code(example):
    project, target = example
    packet = build_context(project, target, "A", 10)
    assert packet["text"] == ""
    assert "shop/values.py" in packet["files"]
    assert "docs/rules.md" in packet["files"]
    assert "tests/test_freight.py" not in packet["files"]
    assert any(item["status"] == "excluded" for item in packet["manifest"])


def test_sanitization_rejects_symlinks_instructions_test_docs_and_secrets(tmp_path):
    project = project_at(tmp_path, {
        "good.py": "def good():\n    return 1\n",
        "AGENTS.md": "Instructions.",
        "docs/rules.md": "```python\ndef test_hidden():\n    assert True\n```",
        "docs/unreviewed.md": "Not explicitly allowlisted.",
        "credentials.json": "secret",
        ".git/config": "private",
        "embedded.py": "def test_reserved():\n    return 0",
        "private.py": "key = '-----BEGIN PRIVATE KEY-----'",
    })
    (tmp_path / "alias.py").symlink_to(tmp_path / "good.py")
    project["include"] = ["**/*", "docs/rules.md"]
    files, manifest = sanitize_project(project)
    assert files == {"good.py": "def good():\n    return 1\n"}
    reasons = {item["path"]: item.get("reason") for item in manifest}
    assert reasons["alias.py"] == "symlink_or_escape"
    assert reasons["docs/rules.md"] == "test_content"
    assert reasons["docs/unreviewed.md"] == "documentation_requires_explicit_path"


def test_rejects_traversal_allowlist_and_target(example):
    project, target = example
    target["path"] = "../outside.py"
    with pytest.raises(ContextError):
        build_context(project, target, "L", 5000)
    project["include"] = ["../*.py"]
    with pytest.raises(ContextError):
        sanitize_project(project)


def test_module_alias_src_layout_and_forward_annotation(tmp_path):
    project = project_at(tmp_path, {
        "src/pkg/__init__.py": "",
        "src/pkg/main.py": "import pkg.helpers as helpers\nfrom pkg.models import Customer\n\ndef run(c: list['Customer']):\n    return helpers.calc(c)\n",
        "src/pkg/helpers.py": "def calc(c):\n    return 7\n",
        "src/pkg/models.py": "class Customer:\n    pass\n",
    })
    project["source_roots"] = ["src"]
    target = {"path": "src/pkg/main.py", "symbol": "run"}
    packet = build_context(project, target, "R", 5000)
    assert "class Customer" in packet["text"]
    assert "def calc(c)" in packet["text"]


def test_no_execution_and_nested_body_not_retrieved(tmp_path):
    marker = tmp_path / "executed"
    project = project_at(tmp_path, {
        "main.py": f"from helpers import hidden, used\nopen({str(marker)!r}, 'w').write('bad')\n\ndef run():\n    def inner():\n        used = 1\n        return hidden()\n    return used()\n",
        "helpers.py": "def hidden():\n    return 42\n\ndef used():\n    return 7\n",
    })
    packet = build_context(project, {"path": "main.py", "symbol": "run"}, "R", 5000)
    assert not marker.exists()
    added = [item for item in packet["snippets"] if item["reason"] == "direct_dependency"]
    assert len(added) == 1
    assert added[0]["text"].startswith("def used")


def test_ambiguous_import_is_logged_not_guessed(tmp_path):
    project = project_at(tmp_path, {
        "main.py": "from a import value as v\nfrom b import value as v\n\ndef run():\n    return v()\n",
        "a.py": "def value():\n    return 1\n",
        "b.py": "def value():\n    return 2\n",
    })
    packet = build_context(project, {"path": "main.py", "symbol": "run"}, "R", 5000)
    assert packet["equal_to_local"]
    assert any(item.get("reference") == "v" for item in packet["unresolved"])


def test_same_file_dependency_already_present(example):
    project, target = example
    p = Path(project["root"], target["path"])
    p.write_text("def helper(x):\n    return x + 1\n\ndef freight(x):\n    return helper(x)\n")
    packet = build_context(project, target, "R", 5000)
    assert packet["equal_to_local"]
    assert len(packet["snippets"]) == 1
