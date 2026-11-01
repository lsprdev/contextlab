"""Projetos locais: configuração por nome e leitura de execuções preservadas.

Não substitui o manifesto nem o executor científico. Os projetos de aprendizado
usam os mesmos validadores; a matriz principal continua no fluxo por manifesto.
"""
from __future__ import annotations

import ast
import json
import re
import tempfile
from pathlib import Path

from .manifest import ManifestError, load_config, safe_file


RESERVED = {"create", "projects", "plan", "doctor", "prepare", "validate", "freeze",
            "run", "review", "report", "help"}
_EXCLUDED = {"tests", "test", "reference", "tutorial", "runs", "__pycache__",
             ".venv", "venv", ".git", "build", "dist", "node_modules"}


def project_folder(name: str, cwd: Path | None = None) -> Path:
    if not re.fullmatch(r"[a-z][a-z0-9_-]*", name) or name in RESERVED:
        raise ManifestError("Use um nome como cambio ou meu-projeto, diferente dos comandos do ContextLab.")
    start = (cwd or Path.cwd()).resolve()
    for parent in (start, *start.parents):
        projects = parent / "projects"
        if projects.is_dir():
            folder = projects / name
            if projects.is_symlink() or folder.is_symlink():
                raise ManifestError("A pasta de projetos não pode ser um link simbólico.")
            if not folder.is_dir():
                raise ManifestError(f"Coloque primeiro o código da aplicação em {folder}.")
            return folder
    raise ManifestError("Execute na raiz do repositório que contém projects/ ou em uma de suas subpastas.")


def read_project(folder: Path) -> dict:
    path = safe_file(folder, "contextlab.json")
    config = load_config(path)
    if config["phase"] == "main" or len(config["projects"]) != 1:
        raise ManifestError("Este atalho atende demo/pilot de um projeto. Para a matriz principal, use o fluxo por manifesto.")
    project = config["projects"][0]
    if project["id"] != folder.name or Path(project["root"]) != folder.resolve():
        raise ManifestError("O id deve coincidir com a pasta e root deve apontar para o próprio projeto.")
    return config


def save_project(folder: Path, config: dict, *, replace: bool = False) -> Path:
    """Validate before changing the public file; create never overwrites it."""
    destination = folder / "contextlab.json"
    if destination.is_symlink():
        raise ManifestError("A configuração não pode ser um link simbólico.")
    serialized = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", dir=folder, encoding="utf-8") as temporary:
        temporary.write(serialized)
        temporary.flush()
        checked = load_config(temporary.name)
        if (checked["phase"] == "main" or len(checked["projects"]) != 1
                or checked["projects"][0]["id"] != folder.name
                or Path(checked["projects"][0]["root"]) != folder.resolve()):
            raise ManifestError("Configuração deve descrever este projeto em demo ou pilot.")
        if replace:
            # Keep the original untouched if validation fails.
            from .manifest import write_json
            write_json(destination, config)
        else:
            with destination.open("x", encoding="utf-8") as stream:
                stream.write(serialized)
    return destination


def discover_targets(folder: Path) -> list[dict]:
    source = folder / "src" if (folder / "src").is_dir() else folder
    result = []
    for path in sorted(source.rglob("*.py")):
        relative = path.relative_to(folder)
        if any(part in _EXCLUDED or part.startswith(".") for part in relative.parts):
            continue
        safe_file(folder, relative.as_posix())
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        module_parts = list(path.relative_to(source).with_suffix("").parts)
        if module_parts[-1] == "__init__":
            module_parts.pop()
        if not module_parts or any(not part.isidentifier() for part in module_parts):
            continue
        for node in tree.body:
            nodes = [(node, node.name)] if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else []
            if isinstance(node, ast.ClassDef):
                nodes = [(method, f"{node.name}.{method.name}") for method in node.body
                         if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for function, symbol in nodes:
                if function.body[0].lineno == function.lineno:
                    continue
                identifier = re.sub(r"[^a-zA-Z0-9_-]", "_", symbol.replace(".", "-"))
                if not identifier[0].isalnum():
                    identifier = "alvo" + identifier
                result.append({"id": identifier, "path": relative.as_posix(),
                               "symbol": symbol, "import": ".".join(module_parts) + ":" + symbol})
    return result


def new_config(folder: Path, target: dict, references: list[str], *, mode: str,
               conditions: list[str], repetitions: int, model: str | None = None,
               fixture_dir: str = "tutorial", image: str = "contextlab-evaluator:local") -> dict:
    if mode == "demo":
        relative = f"{fixture_dir}/{folder.name}__{target['id']}.py"
        safe_file(folder, relative)
        agents = [{"id": "fixture", "kind": "fixture", "fixture_dir": fixture_dir}]
    else:
        if not model or model == "SUBSTITUA_PELO_MODELO_CODEX":
            raise ManifestError("Informe o identificador do modelo do Codex com --model.")
        agents = [{"id": "codex", "kind": "codex", "model": model}]
    for reference in references:
        safe_file(folder, reference.split("::")[0])
    source = "src" if (folder / "src").is_dir() else "."
    # Enumerate actual production files. Do not offer tests or the tutorial to A.
    production = sorted({t["path"] for t in discover_targets(folder)})
    base = folder / source
    for path in base.rglob("*.py"):
        relative = path.relative_to(folder)
        if not any(part in _EXCLUDED or part.startswith(".") for part in relative.parts):
            production.append(relative.as_posix())
    production = sorted(set(production))
    return {"schema_version": 1, "phase": mode, "seed": 42,
            "conditions": conditions, "repetitions": repetitions,
            "limits": {"context_chars": 30000, "tool_calls": 20,
                       "generation_seconds": 120, "evaluation_seconds": 20},
            "agents": agents,
            "evaluation": {"backend": "local" if mode == "demo" else "docker", "image": image},
            "projects": [{"id": folder.name, "root": ".", "source_roots": [source],
                          "include": production,
                          "evaluation_include": sorted(set(production + [r.split("::")[0] for r in references])),
                          "targets": [{**target, "reference_tests": references, "defects": []}]}]}


def runs_folder(folder: Path) -> Path:
    result = folder / "runs"
    if result.is_symlink():
        raise ManifestError("runs/ não pode ser um link simbólico.")
    return result


def batch_folder(folder: Path, batch: str) -> Path:
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", batch):
        raise ManifestError("Identificador de lote inválido.")
    result = runs_folder(folder) / batch
    if result.is_symlink() or not result.is_dir():
        raise ManifestError("Lote não encontrado neste projeto.")
    return result


def attempts(folder: Path) -> list[dict]:
    """Read existing reports; listing never re-evaluates or writes report files."""
    from .reporting import read_report
    rows = []
    for batch in sorted(runs_folder(folder).glob("*/")):
        if batch.is_symlink():
            continue
        results = batch / "results"
        if not (results / "run.json").is_file():
            continue
        if results.is_symlink():
            raise ManifestError("Diretório de resultados não pode ser um link simbólico.")
        report = read_report(results)
        for row in report["rows"]:
            rows.append({**row, "attempt_id": f"{batch.name}/{row['order']:02}", "batch": batch.name})
    return rows


def find_attempt(folder: Path, identifier: str) -> Path:
    try:
        batch, order = identifier.split("/")
        if not order.isdecimal():
            raise ValueError
        results = batch_folder(folder, batch) / "results"
        if results.is_symlink():
            raise ManifestError("Diretório de resultados não pode ser um link simbólico.")
        header = json.loads(safe_file(results, "run.json").read_text())
        row = next(row for row in header["plan"] if row["order"] == int(order))
        return safe_file(results, row["id"] + "/record.json").parent
    except ManifestError:
        raise
    except (ValueError, StopIteration) as exc:
        raise ManifestError("Use o ID completo exibido por runs, no formato lote/01.") from exc
