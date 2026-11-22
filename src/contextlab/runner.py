"""Uma entrega por trajetória; avaliação posterior nunca volta ao agente."""
from __future__ import annotations

import json
import hashlib
import re
import time
from pathlib import Path

from .manifest import (ManifestError, digest, implementation_hash, load_lock, now, plan,
                       runtime_fingerprint, snapshot, verify_lock, write_json)


def resolve_row(config: dict, row: dict):
    project = next(x for x in config["projects"] if x["id"] == row["project"])
    target = next(x for x in project["targets"] if x["id"] == row["target"])
    agent = next(x for x in config["agents"] if x["id"] == row["agent"])
    return project, target, agent


def evaluation_config(config: dict, trusted_local: bool) -> dict:
    result = {**config["evaluation"], "timeout_seconds": config["limits"]["evaluation_seconds"],
              "trusted_local": trusted_local}
    if result["backend"] == "local" and (config["phase"] != "demo" or not trusted_local):
        raise ManifestError("Avaliação local é somente para demo confiável com --trusted-local; use Docker para agentes")
    return result


def prompt_for(target: dict, context: dict, limits: dict | None = None) -> str:
    # O contrato é comum às estratégias e aos adaptadores disponíveis.
    # Os limites são informados a L, R e A com o mesmo texto: esgotá-los
    # encerra a sessão, e o agente não deve descobrir isso pela falha.
    http = target.get("test_kind", "unit") == "http"
    common = (
        ("Gere uma única suíte pytest de integração HTTP para a rota atendida pela função indicada.\n" if http else
         "Gere uma única suíte de testes unitários pytest para a função indicada.\n") +
        f"Arquivo: {target['path']}\nSímbolo: {target['symbol']}\nImport: {target['import']}\n"
        "Ambiente de avaliação: Python 3.11+, pytest 8.4.2.\n"
        "Use somente list_files, read_file e search para consultar os materiais permitidos.\n"
        "Não execute código, comandos ou testes; não consulte internet ou o avaliador.\n"
        "Não altere produção, não substitua nem faça mock da própria função alvo.\n"
        "Inclua verificações comportamentais; não use skip ou xfail para mascarar falhas.\n"
        "A avaliação acontecerá após esta sessão. Você não receberá resultados para reparo.\n"
        "Entregue uma resposta final com o código Python de um único arquivo, sem explicações.\n"
    )
    if limits is not None:
        common += (
            f"Limites desta sessão: {limits['context_chars']} caracteres de contexto, somando o material "
            f"inicial e as respostas das ferramentas, e {limits['tool_calls']} consultas.\n"
            "Ultrapassar um desses limites encerra a sessão sem entrega. Planeje as leituras e, em arquivos "
            "longos, use read_file com start_line e end_line.\n"
        )
    if http:
        common += (
            "Use fastapi.testclient.TestClient com a aplicação real, sem servidor externo ou acesso à rede.\n"
            "Exercite a função alvo por requisições HTTP; não chame diretamente o handler.\n"
            "Confira status HTTP e conteúdo das respostas. Não faça mock das regras nem da persistência.\n"
            "Use um arquivo SQLite real em tmp_path e a configuração pública da aplicação, com dados isolados por teste.\n"
            "Não dependa de fixtures reservadas nem de conftest.py do projeto; entregue a preparação no seu arquivo.\n"
        )
    if context["text"]:
        return common + "\nMaterial inicial permitido:\n" + context["text"]
    return common + "\nConsulte as ferramentas para escolher o contexto.\n"


def extract_submission(response: str) -> str:
    """Extrai sem corrigir, reformatar imports ou escolher após avaliação."""
    if not isinstance(response, str) or not response.strip():
        raise ValueError("Resposta vazia")
    stripped = response.strip()
    if stripped.startswith("```"):
        match = re.fullmatch(r"```(?:python|py)?[ \t]*\r?\n(.*?)\r?\n```", stripped, re.DOTALL)
        if not match or "```" in match.group(1):
            raise ValueError("Esperado exatamente um bloco Python sem texto adicional")
        return match.group(1) + "\n"
    if "```" in response:
        raise ValueError("Formato ambíguo: texto e/ou múltiplos blocos")
    return response


def fixture_generation(agent, project, target, context, limits) -> dict:
    from .broker import ContextBroker
    started = time.monotonic()
    broker = ContextBroker(context["files"], limits["context_chars"], context["text"], limits["tool_calls"])
    # Simula tráfego de ferramentas, nunca uma decisão ou desempenho de modelo.
    broker.call("list_files", {})
    if not context["text"]:
        broker.call("read_file", {"path": target["path"]})
    source = Path(agent["fixture_dir"]) / f"{project['id']}__{target['id']}.py"
    return {"status": "completed", "response": source.read_text(encoding="utf-8"),
            "input_tokens": None, "output_tokens": None, "seconds": time.monotonic() - started,
            "version": "authored-fixture-1", "tool_log": broker.log, "usage": broker.stats,
            "simulated": True, "details": "Teste autoral fixo; não é geração de agente."}


def validate_projects(config: dict, output: Path, trusted_local=False) -> dict:
    from .evaluation import validate_defects
    settings = evaluation_config(config, trusted_local)
    if output.exists():
        raise ManifestError("Diretório de validação já existe; preserve-o e use outro nome")
    output.mkdir(parents=True)
    result = {"schema_version": 1, "config_hash": digest(config), "source_hashes": snapshot(config),
              "created_at": now(), "implementation_hash": implementation_hash(),
              "runtime": runtime_fingerprint(config), "targets": {}}
    for project in config["projects"]:
        for target in project["targets"]:
            key = f"{project['id']}__{target['id']}"
            result["targets"][key] = validate_defects(project, target, output / key, settings)
    write_json(output / "validation.json", result)
    return result


def check_main_evidence(config: dict, evidence: dict) -> None:
    """Liga a declaração humana aos registros reais do piloto e das referências."""
    if config["phase"] != "main":
        return
    from .adapters import doctor_agent
    pilot_path = Path(evidence.get("pilot_run", ""))
    validation_path = Path(evidence.get("validation_dir", "")) / "validation.json"
    if not (pilot_path / "run.json").is_file() or not validation_path.is_file():
        raise ManifestError("Registros do piloto/validação ausentes")
    pilot = json.loads((pilot_path / "run.json").read_text())
    if pilot["config"]["phase"] != "pilot":
        raise ManifestError("Demonstração não substitui piloto com agentes reais")
    if pilot.get("implementation_hash") != implementation_hash() or pilot.get("runtime") != runtime_fingerprint(config):
        raise ManifestError("Piloto precisa usar a implementação e o ambiente atuais")
    main_targets = {(p["root"], t["path"], t["symbol"]) for p in config["projects"] for t in p["targets"]}
    if any((p["root"], t["path"], t["symbol"]) in main_targets for p in pilot["config"]["projects"] for t in p["targets"]):
        raise ManifestError("Alvos do piloto devem ser externos à matriz principal")
    if pilot["config"]["limits"] != config["limits"]:
        raise ManifestError("Os limites finais precisam de piloto com a mesma configuração")
    found = set()
    for row in pilot["plan"]:
        record_path = pilot_path / row["id"] / "record.json"
        if not record_path.is_file():
            continue
        record = json.loads(record_path.read_text())
        generation = record.get("generation") or {}
        if generation.get("status") != "completed" or (record.get("evaluation") or {}).get("status") != "completed":
            continue
        _, _, agent = resolve_row(pilot["config"], row)
        found.add((agent["kind"], row["condition"]))
    if found != {("codex", c) for c in ("L", "R", "A")}:
        raise ManifestError("Piloto não demonstra o Codex nas três condições com geração e avaliação completas")
    for agent in config["agents"]:
        matches = [a for a in pilot["config"]["agents"] if a["kind"] == agent["kind"]]
        if len(matches) != 1 or matches[0].get("model") != agent["model"]:
            raise ManifestError("Modelos da coleta devem coincidir com o piloto")
        doctor = doctor_agent(agent)
        if not doctor.get("ready"):
            raise ManifestError(f"Adaptador não está pronto: {agent['id']}: {doctor}")
        if evidence.get("agent_versions", {}).get(agent["id"]) != doctor.get("version"):
            raise ManifestError("Evidência deve registrar as versões verificadas por doctor")
        for row in pilot["plan"]:
            record_path = pilot_path / row["id"] / "record.json"
            if row["agent"] != matches[0]["id"] or not record_path.is_file():
                continue
            generation = json.loads(record_path.read_text()).get("generation") or {}
            if generation.get("status") == "completed" and generation.get("version") != doctor.get("version"):
                raise ManifestError("Versão atual do agente difere da exercitada no piloto")
    validation = json.loads(validation_path.read_text())
    if validation.get("implementation_hash") != implementation_hash() or validation.get("runtime") != runtime_fingerprint(config):
        raise ManifestError("Validação deve usar a implementação e o ambiente atuais")
    if validation.get("config_hash") != digest(config) or validation.get("source_hashes") != snapshot(config):
        raise ManifestError("Validação não corresponde à configuração e fontes principais")
    expected = {f"{p['id']}__{t['id']}" for p in config["projects"] for t in p["targets"]}
    if set(validation.get("targets", {})) != expected:
        raise ManifestError("Validação não cobre todos os alvos principais")
    if any(not item.get("valid", False) for item in validation["targets"].values()):
        raise ManifestError("Referências ou defeitos não validados")
    pilot_records = {p.parent.name: json.loads(p.read_text()) for p in sorted(pilot_path.glob("*/record.json"))}
    hashes = {"pilot_record_hash": digest({"header": pilot, "records": pilot_records}),
              "validation_hash": digest(validation)}
    for key, value in hashes.items():
        if key in evidence and evidence[key] != value:
            raise ManifestError("Evidências foram alteradas após congelamento")
        evidence[key] = value


def execute(lock_path: Path, output: Path, *, trusted_local=False, resume=False, max_runs=None) -> dict:
    try:
        import fcntl
    except ImportError as exc:
        raise ManifestError("Execução suportada em macOS/Linux; use Linux/WSL no Windows") from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    # flock is released by the OS even on interruption. Two CLI processes must
    # not start the same trajectory or mislabel an active worker as interrupted.
    with output.with_name(output.name + ".execution.lock").open("a") as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ManifestError("Esta execução já está em andamento em outro processo") from exc
        try:
            return _execute_run(lock_path, output, trusted_local=trusted_local, resume=resume, max_runs=max_runs)
        finally:
            fcntl.flock(guard, fcntl.LOCK_UN)


def _execute_run(lock_path: Path, output: Path, *, trusted_local=False, resume=False, max_runs=None) -> dict:
    from .context import build_context
    from .evaluation import evaluate_submission
    lock = load_lock(lock_path)
    config = lock["config"]
    settings = evaluation_config(config, trusted_local)
    if config["phase"] == "main":
        check_main_evidence(config, dict(lock["evidence"]))
    if output.exists() and not resume:
        raise ManifestError("Diretório já existe; use --resume para continuar sem regenerar entregas")
    output.mkdir(parents=True, exist_ok=True)
    header = output / "run.json"
    if header.exists():
        if json.loads(header.read_text())["lock_hash"] != lock["lock_hash"]:
            raise ManifestError("A execução existente pertence a outro lock")
    else:
        write_json(header, {**lock, "started_at": now(), "demonstration": config["phase"] == "demo"})
    completed = 0
    for row in lock["plan"]:
        destination = output / row["id"]
        retry = None
        if (destination / "record.json").exists():
            previous = json.loads((destination / "record.json").read_text())
            if previous.get("status") == "running":
                previous.update(status="interrupted", interruption="Execução anterior interrompida")
                write_json(destination / "record.json", previous)
            retry = retry_kind(previous, destination)
            if retry is None:
                continue
        if max_runs is not None and completed >= max_runs:
            break
        load_lock(lock_path)  # Detecta mudanças entre trajetórias.
        project, target, agent = resolve_row(config, row)
        if retry == "evaluation":
            _retry_evaluation(destination, project, target, settings, evaluate_submission)
        else:
            if retry == "generation":
                archived = _archive_for_retry(destination)
            _run_attempt(row, destination, config, lock, project, target, agent, settings,
                         build_context, evaluate_submission,
                         retry=None if retry is None else archived)
        completed += 1
    return {"run": str(output), "processed_now": completed, "planned": len(lock["plan"])}


# Regra de repetição (TCC, seção 6.1.3): uma tentativa interrompida por falha não
# atribuível ao agente é repetida uma única vez, no `run --resume`. O registro
# original é preservado e o motivo fica gravado. Falhas do próprio agente
# (limite, timeout, violação de protocolo, saída inválida) nunca são repetidas.
_RETRYABLE = {"infrastructure_error", "interrupted"}


def retry_kind(record: dict, destination: Path) -> str | None:
    """'generation', 'evaluation' ou None, conforme a falha e as repetições já feitas."""
    if record.get("retry") or record.get("evaluation_retry"):
        return None
    status = record.get("status")
    generation = record.get("generation") or {}
    delivered = (destination / "test_generated.py").is_file() and bool(record.get("submission_sha256"))
    evaluation = record.get("evaluation") or {}
    if delivered and generation.get("status") == "completed":
        # A entrega existe: repete-se só a avaliação, nunca a geração.
        if evaluation.get("status") in _RETRYABLE or (status in _RETRYABLE and not evaluation):
            return "evaluation"
        return None
    if status in _RETRYABLE and generation.get("status") in (None, *_RETRYABLE):
        return "generation"
    return None


def _failure_reason(record: dict) -> str:
    generation = record.get("generation") or {}
    evaluation = record.get("evaluation") or {}
    for value in (record.get("error"), record.get("interruption"), evaluation.get("error"),
                  *(generation.get("details") or [])):
        if isinstance(value, str) and value:
            return value
    return record.get("status") or "desconhecido"


def _archive_for_retry(destination: Path) -> dict:
    """Move a tentativa original para `original/`, intacta, e devolve o registro do motivo."""
    import shutil
    previous = json.loads((destination / "record.json").read_text())
    archive = destination / "original"
    archive.mkdir()
    for item in list(destination.iterdir()):
        if item != archive:
            shutil.move(str(item), archive / item.name)
    return {"kind": "generation", "reason": _failure_reason(previous), "previous_status": previous.get("status"),
            "previous_started_at": previous.get("started_at"), "original": "original/record.json", "at": now()}


def _retry_evaluation(destination: Path, project, target, settings, evaluate_submission) -> None:
    record = json.loads((destination / "record.json").read_text())
    submission = destination / "test_generated.py"
    if record.get("submission_sha256") != hashlib.sha256(submission.read_bytes()).hexdigest():
        raise ManifestError("A submissão foi alterada; a repetição da avaliação não autoriza reparar o teste")
    original = destination / "evaluation"
    if original.exists():
        original.rename(destination / "evaluation-original")
    record["evaluation_retry"] = {"kind": "evaluation", "reason": _failure_reason(record),
                                  "previous_status": record.get("status"), "previous_evaluation": record.get("evaluation"),
                                  "original": "evaluation-original" if (destination / "evaluation-original").exists() else None,
                                  "at": now()}
    try:
        record["evaluation"] = evaluate_submission(project, target, submission, destination / "evaluation", settings,
                                                   defects=target.get("defects", []))
        record["status"] = "finished"
    except Exception as exc:
        record.update(status="infrastructure_error", error=f"{type(exc).__name__}: {exc}")
    record["finished_at"] = now()
    write_json(destination / "record.json", record)


def _run_attempt(row, destination, config, lock, project, target, agent, settings,
                 build_context, evaluate_submission, retry=None) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    record = {"schema_version": 1, **row, "phase": config["phase"], "lock_hash": lock["lock_hash"],
              "started_at": now(), "status": "running", "generation": None, "evaluation": None}
    if retry:
        record["retry"] = retry
    write_json(destination / "record.json", record)
    try:
        started = time.monotonic()
        context = build_context(project, target, row["condition"], config["limits"]["context_chars"])
        record["preparation_seconds"] = time.monotonic() - started
        write_json(destination / "context.json", context)
        prompt = prompt_for(target, context, config["limits"])
        (destination / "prompt.txt").write_text(prompt, encoding="utf-8")
        if agent["kind"] == "fixture":
            generation = fixture_generation(agent, project, target, context, config["limits"])
        else:
            from .adapters import run_agent
            generation = run_agent(agent, prompt, context, destination / "agent", config["limits"])
        response = generation.pop("response", None)
        record["generation"] = generation
        if response is not None:
            (destination / "response.txt").write_text(response, encoding="utf-8")
        if generation["status"] == "completed":
            try:
                code = extract_submission(response)
            except ValueError as exc:
                record["submission_error"] = str(exc)
                record["status"] = "invalid_submission"
            else:
                submission = destination / "test_generated.py"
                submission.write_text(code, encoding="utf-8")
                record["submission_sha256"] = hashlib.sha256(submission.read_bytes()).hexdigest()
                # Persistir entrega antes de avaliar permite auditar interrupções.
                write_json(destination / "record.json", record)
                record["evaluation"] = evaluate_submission(
                    project, target, submission, destination / "evaluation", settings,
                    defects=target.get("defects", []))
                record["status"] = "finished"
        else:
            record["status"] = generation["status"]
    except KeyboardInterrupt:
        record.update(status="interrupted", interruption="Interrupção do operador")
        write_json(destination / "record.json", record)
        raise
    except Exception as exc:
        record.update(status="infrastructure_error", error=f"{type(exc).__name__}: {exc}")
    record["finished_at"] = now()
    write_json(destination / "record.json", record)


def review_trajectory(path: Path, reviewer: str, decisions: dict, trusted_local=False) -> dict:
    from .evaluation import evaluate_submission
    header = json.loads((path.parent / "run.json").read_text())
    # run.json preserves the complete lock plus these two run-only fields.
    frozen = verify_lock({key: value for key, value in header.items()
                          if key not in {"started_at", "demonstration"}})
    config = frozen["config"]
    record = json.loads((path / "record.json").read_text())
    if record.get("lock_hash") != frozen["lock_hash"]:
        raise ManifestError("A trajetória pertence a outro protocolo congelado")
    if not (path / "test_generated.py").is_file() or not record.get("evaluation"):
        raise ManifestError("Trajetória sem avaliação para revisar")
    if record.get("submission_sha256") != hashlib.sha256((path / "test_generated.py").read_bytes()).hexdigest():
        raise ManifestError("A submissão foi alterada; revisão não autoriza reparar o teste")
    project, target, _ = resolve_row(config, record)
    reviews = path / "reviews"
    reviews.mkdir(exist_ok=True)
    revision = reviews / f"{len(list(reviews.glob('review-*.json'))) + 1:03}"
    review = {**decisions, "reviewer": reviewer, "created_at": now()}
    result = evaluate_submission(project, target, path / "test_generated.py", revision,
                                 evaluation_config(config, trusted_local), defects=target.get("defects", []), review=review)
    write_json(reviews / f"review-{revision.name}.json", {"review": review, "evaluation": result})
    record["review"] = review
    record["reviewed_evaluation"] = result
    write_json(path / "record.json", record)
    return result
