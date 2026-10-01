"""Deterministic context preparation. Source code is parsed, never imported.

The allowlist is a curation boundary, not a secret-detection guarantee. Documentation
must be explicitly named (no glob) and reviewed before freezing an experiment.
"""
from __future__ import annotations

import ast
import builtins
import fnmatch
import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Any


class ContextError(ValueError):
    """The requested context cannot meet the frozen protocol."""


_DENIED_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__",
                "tests", "test", "testes", "testing", "results", "runs", "outputs",
                "secrets", ".claude", ".codex", ".github", ".agents"}
_DENIED_NAMES = {"agents.md", "claude.md", "codex.md", "gemini.md", "skill.md", "conftest.py",
                 "credentials.json", "auth.json", "pytest.ini", "coverage.xml", ".coverage"}
_DOC_SUFFIXES = {".md", ".rst", ".txt"}
_TEST_TEXT = re.compile(r"(?m)^\s*(?:async\s+)?def\s+test_\w*\s*\(|\bpytest\.|\bunittest\.|\bimport\s+(?:pytest|unittest)\b")
_SECRET_TEXT = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-proj-|sk-ant-)[A-Za-z0-9_-]{16,}")


def _clean_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ContextError("Path must be a nonempty POSIX relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ContextError("Path escapes the project")
    return path.as_posix()


def _safe_path(root: Path, relative: str) -> Path:
    relative = _clean_path(relative)
    candidate = root / relative
    current = root
    for component in PurePosixPath(relative).parts:
        current = current / component
        if current.is_symlink():
            raise ContextError(f"Symlinks are forbidden: {relative}")
    try:
        candidate.resolve().relative_to(root)
    except ValueError as exc:
        raise ContextError("Path escapes the project") from exc
    return candidate


def _forbidden(path: str) -> str | None:
    p = PurePosixPath(path)
    parts = [part.lower() for part in p.parts]
    name = parts[-1]
    if any(part in _DENIED_DIRS or part.startswith(".") for part in parts[:-1]):
        return "reserved_directory"
    if (name in _DENIED_NAMES or name.startswith(".") or name.startswith("test_")
            or name.startswith("teste_") or name.endswith("_test.py")
            or p.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
            or "secret" in name or "credential" in name):
        return "reserved_file"
    if p.suffix.lower() not in {".py", *_DOC_SUFFIXES}:
        return "unsupported_file_type"
    return None


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or (pattern.startswith("**/") and fnmatch.fnmatchcase(path, pattern[3:]))


def sanitize_project(project: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Materialize an in-memory, hashed allowlist of production source and docs."""
    root_value = Path(project["root"])
    if root_value.is_symlink():
        raise ContextError("Project root cannot be a symlink")
    root = root_value.resolve(strict=True)
    includes = project.get("include", [])
    if not includes:
        raise ContextError("An explicit include allowlist is required")
    for pattern in includes:
        _clean_path(pattern)
    excludes = project.get("exclude", [])
    for pattern in excludes:
        _clean_path(pattern)
    explicit = {p for p in includes if not any(c in p for c in "*?[")}
    candidates: set[str] = set()
    for pattern in includes:
        for candidate in root.glob(pattern):
            if candidate.is_dir() and not candidate.is_symlink():
                continue
            candidates.add(candidate.relative_to(root).as_posix())
    files: dict[str, str] = {}
    manifest: list[dict[str, Any]] = []
    for relative in sorted(candidates):
        reason = _forbidden(relative)
        if any(_matches(relative, pattern) for pattern in excludes):
            reason = "explicit_exclusion"
        try:
            candidate = _safe_path(root, relative)
        except ContextError:
            reason = "symlink_or_escape"
            candidate = None
        if PurePosixPath(relative).suffix.lower() in _DOC_SUFFIXES and relative not in explicit:
            reason = reason or "documentation_requires_explicit_path"
        record: dict[str, Any] = {"path": relative, "status": "excluded"}
        if reason is None:
            try:
                raw = candidate.read_bytes()  # type: ignore[union-attr]
                text = raw.decode("utf-8")
                if "\x00" in text:
                    reason = "binary_content"
                elif _TEST_TEXT.search(text):
                    reason = "test_content"
                elif _SECRET_TEXT.search(text):
                    reason = "secret_pattern"
                else:
                    files[relative] = text
                    record.update(status="included", sha256=hashlib.sha256(raw).hexdigest(),
                                  chars=len(text), documentation_review_required=PurePosixPath(relative).suffix.lower() in _DOC_SUFFIXES)
            except (OSError, UnicodeError):
                reason = "unreadable_or_non_utf8"
        if reason:
            record["reason"] = reason
        manifest.append(record)
    return files, manifest


def _annotation_nodes(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.AST]:
    args = [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]
    if function.args.vararg:
        args.append(function.args.vararg)
    if function.args.kwarg:
        args.append(function.args.kwarg)
    nodes = [arg.annotation for arg in args if arg.annotation is not None]
    if function.returns is not None:
        nodes.append(function.returns)
    result: list[ast.AST] = []
    for node in nodes:
        result.append(node)
        # Forward references can also occur inside list["Customer"]. Literal
        # values may produce an unresolved record, but never execute code.
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                try:
                    result.append(ast.parse(child.value, mode="eval").body)
                except SyntaxError:
                    pass
    return result


def _references(nodes: list[ast.AST]) -> set[tuple[str, ...]]:
    references: set[tuple[str, ...]] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Attribute(self, node: ast.Attribute) -> None:
            parts = [node.attr]
            current = node.value
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                references.add(tuple([current.id, *reversed(parts)]))
            else:
                self.generic_visit(node)

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, ast.Load):
                references.add((node.id,))

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            # Defining a nested function evaluates defaults/decorators, but its
            # body belongs to another scope and is not a direct dependency.
            for child in [*node.decorator_list, *node.args.defaults,
                          *[value for value in node.args.kw_defaults if value is not None]]:
                self.visit(child)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            for child in [*node.decorator_list, *node.bases, *[item.value for item in node.keywords]]:
                self.visit(child)

    visitor = Visitor()
    for node in nodes:
        visitor.visit(node)
    return references


def _assigned_names(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return [part.id for target in targets for part in ast.walk(target) if isinstance(part, ast.Name) and isinstance(part.ctx, ast.Store)]
    return []


class _Index:
    def __init__(self, files: dict[str, str], source_roots: list[str]):
        self.files = files
        self.trees: dict[str, ast.Module] = {}
        self.modules: dict[str, set[str]] = {}
        self.path_module: dict[str, str] = {}
        self.defs: dict[str, dict[str, list[ast.AST]]] = {}
        self.bindings: dict[str, dict[str, tuple[str, tuple[str, ...]]]] = {}
        self.parse_errors: list[dict[str, str]] = []
        for path, text in files.items():
            if not path.endswith(".py"):
                continue
            try:
                self.trees[path] = ast.parse(text, filename=path)
            except SyntaxError as exc:
                self.parse_errors.append({"path": path, "reason": "syntax_error", "detail": str(exc)})
                continue
            possible = []
            for source_root in source_roots:
                source_root = _clean_path(source_root)
                try:
                    rel = PurePosixPath(path).relative_to(PurePosixPath(source_root))
                except ValueError:
                    continue
                parts = list(rel.with_suffix("").parts)
                if parts and parts[-1] == "__init__":
                    parts.pop()
                if parts:
                    name = ".".join(parts)
                    self.modules.setdefault(name, set()).add(path)
                    possible.append(name)
            if possible:
                self.path_module[path] = min(possible, key=lambda name: (len(name.split(".")), name))
        for path, tree in self.trees.items():
            self.defs[path] = {}
            for node in tree.body:
                for name in _assigned_names(node):
                    self.defs[path].setdefault(name, []).append(node)
            self.bindings[path] = self.imports(path, tree.body)

    def imports(self, path: str, nodes: list[ast.AST]) -> dict[str, tuple[str, tuple[str, ...]]]:
        result: dict[str, tuple[str, tuple[str, ...]]] = {}

        def bind(name, value):
            if name in result and result[name] != value:
                result[name] = ("", ())  # ambiguous alias: never guess
            else:
                result[name] = value

        module = self.path_module.get(path, "")
        package = module if path.endswith("/__init__.py") or path == "__init__.py" else module.rpartition(".")[0]
        for node in nodes:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # `import a.b` binds a; `import a.b as c` binds the full module.
                    bind(alias.asname or alias.name.split(".")[0], (alias.name if alias.asname else alias.name.split(".")[0], ()))
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = package.split(".") if package else []
                    if node.level > len(parts):
                        continue
                    prefix = parts[:len(parts) - node.level + 1]
                    imported = ".".join([*prefix, *([node.module] if node.module else [])])
                else:
                    imported = node.module or ""
                for alias in node.names:
                    if alias.name != "*":
                        bind(alias.asname or alias.name, (imported, (alias.name,)))
        return result

    def resolve(self, path: str, reference: tuple[str, ...], bindings=None, seen=None) -> tuple[str, ast.AST] | None:
        seen = set() if seen is None else seen
        key = (path, reference)
        if key in seen or len(seen) >= 32:
            return None
        seen.add(key)
        # Function-local imports shadow module definitions. `bindings` contains
        # only these local overrides; module bindings remain the fallback.
        locally_imported = bindings is not None and reference[0] in bindings
        definitions = [] if locally_imported else self.defs.get(path, {}).get(reference[0], [])
        if len(definitions) == 1:
            # Access to a class member carries the complete class. Dynamic values
            # and function-return attributes are deliberately not guessed.
            node = definitions[0]
            if len(reference) == 1 or isinstance(node, ast.ClassDef):
                return path, node
            return None
        if definitions:
            return None
        binding = (bindings[reference[0]] if locally_imported
                   else self.bindings.get(path, {}).get(reference[0]))
        if not binding:
            return None
        module, tail = binding
        parts = [*module.split("."), *tail, *reference[1:]]
        for split in range(len(parts), 0, -1):
            candidates = self.modules.get(".".join(parts[:split]), set())
            if len(candidates) != 1:
                continue
            destination = next(iter(candidates))
            remaining = tuple(parts[split:])
            if remaining:
                return self.resolve(destination, remaining, seen=seen)
        return None


def _snippet(path: str, node: ast.AST | None, text: str, reason: str) -> dict[str, Any]:
    if node is None:
        start, end = 1, max(1, len(text.splitlines()))
        snippet_text = text
        key = path
    else:
        decorators = getattr(node, "decorator_list", [])
        start = min([node.lineno, *[decorator.lineno for decorator in decorators]])
        end = node.end_lineno
        snippet_text = "".join(text.splitlines(keepends=True)[start - 1:end])
        key = f"{path}::L{start}-L{end}"
    return {"path": path, "start_line": start, "end_line": end, "reason": reason,
            "key": key, "text": snippet_text, "sha256": hashlib.sha256(snippet_text.encode()).hexdigest()}


def _render(snippets: list[dict[str, Any]]) -> str:
    return "\n\n".join(f"### {item['key']} (original lines {item['start_line']}-{item['end_line']})\n{item['text']}" for item in snippets)


def build_context(project: dict[str, Any], target: dict[str, Any], condition: str, budget: int) -> dict[str, Any]:
    """Build L/R packets or A's sanitized store; never truncate a definition.

    L is mandatory and must fit. R candidates are tried in path/line order,
    skipping complete candidates that do not fit. Imports used to find a
    definition may be followed, but dependencies of that definition are not.
    """
    if condition not in {"L", "R", "A"}:
        raise ContextError("Condition must be L, R or A")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 1:
        raise ContextError("Context budget must be a positive integer")
    files, manifest = sanitize_project(project)
    path = _clean_path(target["path"])
    if path not in files:
        raise ContextError(f"Target is absent from sanitized allowlist: {path}")
    index = _Index(files, project.get("source_roots", ["."]))
    if path not in index.trees:
        raise ContextError("Target is not valid Python source")
    current: Any = index.trees[path]
    for part in target["symbol"].split("."):
        matches = [node for node in current.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == part]
        if len(matches) != 1:
            raise ContextError(f"Target must identify one static function: {target['symbol']}")
        current = matches[0]
    if not isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise ContextError("Target must be a function or method")
    function = current
    result: dict[str, Any] = {"files": {}, "text": "", "snippets": [], "unresolved": list(index.parse_errors),
                              "omitted": [], "manifest": manifest, "equal_to_local": False}
    if condition == "A":
        result["files"] = files
        return result
    local = [_snippet(path, None, files[path], "focal_file")]
    used = {(path, 1, local[0]["end_line"])}
    builtins_set = set(dir(builtins)) | {"None", "True", "False"}

    def recover(references, reason, bindings=None, local_names=frozenset()):
        recovered = []
        for reference in sorted(references):
            if reference[0] in local_names:
                if len(reference) > 1:
                    result["unresolved"].append({"reference": ".".join(reference), "reason": "dynamic_attribute", "phase": reason})
                continue
            if (reference[0] in builtins_set and reference[0] not in index.defs[path]
                    and reference[0] not in index.bindings[path]
                    and reference[0] not in (bindings or {})):
                continue
            resolved = index.resolve(path, reference, bindings=bindings)
            if resolved is None:
                result["unresolved"].append({"reference": ".".join(reference), "reason": "not_statically_resolved", "phase": reason})
                continue
            source, node = resolved
            if source == path:
                continue  # already fully included
            snippet = _snippet(source, node, files[source], reason)
            identity = (source, snippet["start_line"], snippet["end_line"])
            if identity in used:
                continue
            used.add(identity)
            recovered.append(snippet)
        return sorted(recovered, key=lambda item: (item["path"], item["start_line"]))

    local.extend(recover(_references(_annotation_nodes(function)), "signature_type"))
    local_text = _render(local)
    if len(local_text) > budget:
        raise ContextError(f"Integral L context requires {len(local_text)} characters, budget is {budget}")
    selected = list(local)
    if condition == "R":
        args = [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]
        if function.args.vararg:
            args.append(function.args.vararg)
        if function.args.kwarg:
            args.append(function.args.kwarg)
        local_names = {arg.arg for arg in args}
        class Locals(ast.NodeVisitor):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    local_names.add(node.id)

            def visit_FunctionDef(self, node):
                local_names.add(node.name)

            visit_AsyncFunctionDef = visit_FunctionDef
            visit_ClassDef = visit_FunctionDef

        visitor = Locals()
        for node in function.body:
            visitor.visit(node)
        bindings = index.imports(path, function.body)
        local_names.difference_update(bindings)
        for snippet in recover(_references(function.body), "direct_dependency", bindings, local_names):
            candidate_text = _render([*selected, snippet])
            if len(candidate_text) <= budget:
                selected.append(snippet)
            else:
                result["omitted"].append({key: value for key, value in snippet.items() if key != "text"} | {"reason": "context_budget"})
        for node in ast.walk(function):
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                result["unresolved"].append({"reference": "*", "reason": "star_import"})
            if isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id in {"getattr", "eval", "exec", "__import__"}) or (isinstance(node.func, ast.Attribute) and node.func.attr == "import_module")):
                result["unresolved"].append({"reference": ast.unparse(node.func), "reason": "dynamic_reference"})
    result.update(files={snippet["key"]: snippet["text"] for snippet in selected}, text=_render(selected),
                  snippets=selected, equal_to_local=len(selected) == len(local))
    return result
