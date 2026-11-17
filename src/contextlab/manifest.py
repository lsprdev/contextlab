"""Manifestos explícitos, matriz pareada e congelamento sem parâmetros implícitos."""
from __future__ import annotations

import hashlib
import itertools
import importlib.metadata
import json
import platform
import random
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import __version__


class ManifestError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def safe_file(root: Path, relative: str) -> Path:
    part = Path(relative)
    if part.is_absolute() or ".." in part.parts:
        raise ManifestError(f"Caminho relativo inválido: {relative}")
    current = root
    for component in part.parts:
        current = current / component
        if current.is_symlink():
            raise ManifestError(f"Link simbólico não permitido: {relative}")
    result = current.resolve()
    if not result.is_relative_to(root.resolve()) or not result.is_file():
        raise ManifestError(f"Arquivo ausente ou fora do projeto: {relative}")
    return result


def selected_files(project: dict) -> list[Path]:
    root = Path(project["root"])
    patterns = project["include"] + project["evaluation_include"]
    selected = set()
    for pattern in patterns:
        if Path(pattern).is_absolute() or ".." in Path(pattern).parts:
            raise ManifestError(f"Padrão fora do projeto: {pattern}")
        for f in root.glob(pattern):
            if f.is_file() or f.is_symlink():
                selected.add(safe_file(root, f.relative_to(root).as_posix()))
    if not selected:
        raise ManifestError(f"Projeto sem arquivos selecionados: {project['id']}")
    return sorted(selected)


def snapshot(config: dict) -> dict:
    return {
        p["id"]: {
            f.relative_to(Path(p["root"])).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in selected_files(p)
        }
        for p in config["projects"]
    }


def implementation_hash() -> str:
    root = Path(__file__).parent
    return digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob("*.py"))})


def runtime_fingerprint(config: dict) -> dict:
    result = {"python": platform.python_version(), "system": platform.system(),
              "pytest": importlib.metadata.version("pytest"), "coverage": importlib.metadata.version("coverage")}
    if config["evaluation"]["backend"] == "docker":
        try:
            image = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}",
                                    config["evaluation"]["image"]], capture_output=True, text=True,
                                   timeout=15, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise ManifestError("Construa a imagem Docker antes de congelar o manifesto") from exc
        if not image.startswith("sha256:"):
            raise ManifestError("Não foi possível identificar a imagem do avaliador")
        result["evaluation_image_id"] = image
    return result


def _identifier(value) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", value))


def _unique(items, name):
    ids = [x.get("id") for x in items]
    if not ids or any(not _identifier(x) for x in ids) or len(ids) != len(set(ids)):
        raise ManifestError(f"IDs ausentes, inválidos ou repetidos em {name}")


def load_config(path: str | Path) -> dict:
    path = Path(path).resolve()
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        if config.get("schema_version") != 1:
            raise ManifestError("schema_version deve ser 1")
        if config["phase"] not in {"demo", "pilot", "main"}:
            raise ManifestError("phase deve ser demo, pilot ou main")
        if not isinstance(config["seed"], int):
            raise ManifestError("seed inteiro é obrigatório")
        if type(config["repetitions"]) is not int or config["repetitions"] < 1:
            raise ManifestError("repetitions deve ser positivo")
        conditions = config["conditions"]
        if not conditions or len(set(conditions)) != len(conditions) or set(conditions) - {"L", "R", "A"}:
            raise ManifestError("conditions deve conter condições distintas L/R/A")
        for key in ("context_chars", "tool_calls", "generation_seconds", "evaluation_seconds"):
            if type(config["limits"][key]) is not int or config["limits"][key] < 1:
                raise ManifestError(f"Defina explicitamente um limite inteiro positivo: {key}")
        if config["evaluation"]["backend"] not in {"local", "docker"}:
            raise ManifestError("evaluation.backend deve ser local ou docker")
        _unique(config["agents"], "agents")
        for agent in config["agents"]:
            if agent["kind"] not in {"fixture", "codex", "claude"}:
                raise ManifestError("Agente desconhecido")
            if config["phase"] == "demo" and agent["kind"] != "fixture":
                raise ManifestError("A fase demo usa somente fixtures; clientes reais exigem pilot ou main")
            if agent["kind"] == "fixture":
                if config["phase"] != "demo":
                    raise ManifestError("Fixtures autorais são permitidas somente em demo")
                agent["fixture_dir"] = str((path.parent / agent["fixture_dir"]).resolve())
            elif not agent.get("model"):
                raise ManifestError("Fixe explicitamente o modelo do agente")
            if agent.get("auth_file"):
                agent["auth_file"] = str((path.parent / Path(agent["auth_file"]).expanduser()).resolve())
        _unique(config["projects"], "projects")
        seen_roots = set()
        for project in config["projects"]:
            root = (path.parent / project["root"]).resolve()
            if not root.is_dir():
                raise ManifestError(f"Projeto ausente: {root}")
            project["root"] = str(root)
            if "name" in project and (not isinstance(project["name"], str) or not project["name"].strip()):
                raise ManifestError(f"name deve ser um texto não vazio em {project['id']}")
            if root in seen_roots:
                raise ManifestError("Projetos diferentes devem apontar para raízes diferentes")
            seen_roots.add(root)
            for key in ("include", "evaluation_include", "source_roots"):
                if not isinstance(project[key], list) or not project[key] or not all(isinstance(x, str) for x in project[key]):
                    raise ManifestError(f"Defina lista não vazia {key} em {project['id']}")
            for source in project["source_roots"]:
                if Path(source).is_absolute() or ".." in Path(source).parts:
                    raise ManifestError("source_roots deve estar dentro do projeto")
            _unique(project["targets"], "targets")
            identities = [(t.get("path"), t.get("symbol")) for t in project["targets"]]
            if len(set(identities)) != len(identities):
                raise ManifestError("IDs diferentes não podem representar a mesma função")
            files = {f.relative_to(root).as_posix() for f in selected_files(project)}
            for target in project["targets"]:
                if target.get("test_kind", "unit") not in {"unit", "http"}:
                    raise ManifestError("test_kind deve ser unit ou http")
                if config["phase"] == "main" and target.get("test_kind", "unit") != "unit":
                    raise ManifestError("Testes HTTP pertencem aos pilotos; a coleta principal mantém testes unitários")
                safe_file(root, target["path"])
                if target["path"] not in files or not target["symbol"] or ":" not in target["import"]:
                    raise ManifestError("Alvo exige arquivo incluído, símbolo e import no formato modulo:simbolo")
                if not target.get("reference_tests"):
                    raise ManifestError("Todo alvo exige ao menos um teste de referência")
                for test in target["reference_tests"]:
                    if test.split("::")[0] not in files:
                        raise ManifestError(f"Referência fora de evaluation_include: {test}")
                defects = target.get("defects", [])
                if defects:
                    _unique(defects, "defects")
                for defect in defects:
                    if defect["path"] not in files or not defect["old"] or defect["old"] == defect["new"]:
                        raise ManifestError("Defeito exige arquivo incluído e alteração não vazia")
                    if defect["witness"].split("::")[0] not in files:
                        raise ManifestError("Testemunho fora de evaluation_include")
        if config["phase"] == "main":
            if (len(config["projects"]) != 4 or any(len(p["targets"]) != 3 for p in config["projects"])
                    or {a["kind"] for a in config["agents"]} != {"codex"}
                    or len(config["agents"]) != 1 or set(conditions) != {"L", "R", "A"}
                    or config["repetitions"] != 3):
                raise ManifestError("O protocolo principal exige 4 projetos × 3 alvos × 1 agente Codex × L/R/A × 3 repetições = 108 gerações")
            if config["evaluation"]["backend"] != "docker":
                raise ManifestError("A coleta principal exige avaliação Docker")
        return config
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Manifesto incompleto ou inválido: {exc}") from exc


def plan(config: dict) -> list[dict]:
    rows = []
    for project in config["projects"]:
        for target, agent, condition, repetition in itertools.product(
                project["targets"], config["agents"], config["conditions"], range(1, config["repetitions"] + 1)):
            row = {"project": project["id"], "target": target["id"], "agent": agent["id"],
                   "condition": condition, "repetition": repetition}
            row["id"] = f"{project['id']}__{target['id']}__{agent['id']}__{condition}__{repetition}"
            rows.append(row)
    rng = random.Random(config["seed"])
    if config["phase"] == "main":
        # Cada bloco conserva a mesma função e repetição nas três estratégias.
        blocks = {}
        for row in rows:
            key = (row["project"], row["target"], row["repetition"])
            blocks.setdefault(key, []).append(row)
        ordered_blocks = list(blocks.values())
        rng.shuffle(ordered_blocks)
        rows = []
        for block in ordered_blocks:
            rng.shuffle(block)
            rows.extend(block)
    else:
        rng.shuffle(rows)
    return [{"order": i + 1, **row} for i, row in enumerate(rows)]


def freeze(config: dict, path: Path, evidence: dict | None = None) -> dict:
    if path.exists():
        raise ManifestError("Lock já existe; use outro nome para preservar o protocolo congelado")
    if config["phase"] == "main":
        if not evidence or not evidence.get("reviewer"):
            raise ManifestError("Main exige evidência de piloto e revisão nominal")
        for check in ("isolation_verified", "docs_sanitized", "focal_mapping_verified", "budget_calibrated"):
            if evidence.get(check) is not True:
                raise ManifestError(f"Evidência principal pendente: {check}")
        if not evidence.get("pilot_run") or not evidence.get("validation_dir"):
            raise ManifestError("Evidência deve apontar pilot_run e validation_dir verificáveis")
    result = {"schema_version": 1, "artifact_version": __version__, "created_at": now(),
              "config": config, "config_hash": digest(config), "source_hashes": snapshot(config),
              "implementation_hash": implementation_hash(), "plan": plan(config), "evidence": evidence}
    result["runtime"] = runtime_fingerprint(config)
    result["lock_hash"] = digest(result)
    write_json(path, result)
    return result


def verify_lock(lock: dict) -> dict:
    """Apply the same integrity and environment checks to runs and reviews."""
    if lock.get("lock_hash") != digest({k: v for k, v in lock.items() if k != "lock_hash"}):
        raise ManifestError("Lock foi alterado")
    if lock["config_hash"] != digest(lock["config"]) or lock["source_hashes"] != snapshot(lock["config"]):
        raise ManifestError("Configuração ou arquivos mudaram após congelamento")
    if lock["implementation_hash"] != implementation_hash():
        raise ManifestError("Código do ContextLab mudou; gere outro lock após validar")
    if lock["runtime"] != runtime_fingerprint(lock["config"]):
        raise ManifestError("Python, dependências ou imagem Docker mudaram após congelamento")
    if lock["plan"] != plan(lock["config"]):
        raise ManifestError("Matriz ou ordem divergente do manifesto")
    return lock


def load_lock(path: Path) -> dict:
    return verify_lock(json.loads(path.read_text(encoding="utf-8")))
