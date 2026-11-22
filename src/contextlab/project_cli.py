"""Interface por nome: orienta o usuário e delega ao protocolo existente."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import uuid

from rich.console import Console
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table

from .manifest import ManifestError, freeze, plan, safe_file, write_json
from .projects import (attempts, batch_folder, discover_targets, find_attempt, new_config,
                       project_folder, read_project, runs_folder, save_project)


def _table(console, columns, rows):
    rows = list(rows)
    table = Table(show_lines=False)
    for index, column in enumerate(columns):
        options = {"overflow": "fold"}
        if column == "ID":
            options.update(no_wrap=True, min_width=max([len(str(row[index])) for row in rows] or [2]))
        table.add_column(column, **options)
    for row in rows:
        from rich.text import Text
        table.add_row(*(Text(str(value)) for value in row))
    console.print(table)


def _ask(console, label, *, default=None, choices=None):
    if not sys.stdin.isatty():
        raise ManifestError(f"Falta configurar: {label}. Use um terminal interativo ou as opções de --help.")
    return Prompt.ask(label, default=default, choices=choices, console=console)


def _options(parser):
    parser.add_argument("--mode", choices=["demo", "pilot"])
    parser.add_argument("--conditions", choices=["L", "R", "A"], nargs="+")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--model", help="Identificador explícito do modelo do Codex")
    parser.add_argument("--auth-file", help="Caminho do login privado; nunca copiar a credencial para o projeto")
    parser.add_argument("--image", help="Imagem Docker do avaliador com dependências fixadas")


def create_parser():
    parser = argparse.ArgumentParser(prog="contextlab create", description="Cadastrar uma aplicação já existente em projects/NOME.")
    parser.add_argument("name")
    parser.add_argument("--target", help="Arquivo:símbolo, por exemplo src/cambio/conversao.py:converter_para_brl")
    parser.add_argument("--reference", action="append", help="Teste de referência relativo ao projeto (pode repetir)")
    parser.add_argument("--fixture-dir", default="tutorial", help="Pasta de entregas autorais do modo demo")
    _options(parser)
    return parser


def project_parser(name):
    parser = argparse.ArgumentParser(prog=f"contextlab {name}", description="Configuração e execuções deste projeto.")
    commands = parser.add_subparsers(dest="command", required=True)
    _options(commands.add_parser("configure", help="Ajustar modo, estratégias, repetições e modelo"))
    setup = commands.add_parser("setup", help="Preparar ou reutilizar a imagem Docker do avaliador")
    setup.add_argument("--dockerfile", help="Dockerfile personalizado, relativo à pasta do projeto")
    for command, help_text in [("plan", "Mostrar as tentativas planejadas, sem executar"),
                               ("runs", "Consultar execuções preservadas, sem repetir testes")]:
        commands.add_parser(command, help=help_text).add_argument("--json", action="store_true")
    context = commands.add_parser("context", help="Ver o material que ficará disponível ao agente")
    context.add_argument("--condition", choices=["L", "R", "A"], default="L")
    context.add_argument("--target", help="ID do alvo, obrigatório se houver mais de um")
    run = commands.add_parser("run", help="Validar, congelar e executar o plano")
    run.add_argument("--trusted-local", action="store_true", help="Autorizar avaliação local de testes autorais em demo")
    run.add_argument("--max-runs", type=int, help="Processar no máximo N tentativas nesta chamada; cada uma pode conter vários testes")
    run.add_argument("--resume", metavar="LOTE", help="Continuar um lote preservado sem regenerar entregas")
    serving = commands.add_parser("serve", help="Abrir o visualizador web das execuções, somente leitura")
    serving.add_argument("--batch", metavar="LOTE", help="Mostrar apenas um lote; por padrão, todos")
    from .cli import _serve_options
    _serve_options(serving)
    for command in ("show", "review"):
        sub = commands.add_parser(command, help="Inspecionar uma tentativa" if command == "show" else "Revisar uma tentativa")
        sub.add_argument("attempt", help="ID exibido por runs, no formato lote/01")
        if command == "show":
            display = sub.add_mutually_exclusive_group()
            display.add_argument("--code", action="store_true", help="Mostrar também o código entregue, após os resultados")
            display.add_argument("--json", action="store_true", help="Mostrar somente o JSON da avaliação mais recente")
        else:
            sub.add_argument("--reviewer")
            for flag in ("behavioral-assertions", "no-target-mock", "no-production-changes", "dependency-doubles", "http-requests"):
                sub.add_argument("--" + flag, choices=["yes", "no"])
            sub.add_argument("--defect-attribution", action="append", default=[], metavar="ID=yes|no")
            sub.add_argument("--trusted-local", action="store_true")
    return parser


def _settings(args, console, previous=None):
    old = previous or {}
    editing = previous is not None and any(getattr(args, key) is not None for key in
        ("mode", "conditions", "repetitions", "model", "auth_file", "image"))
    mode = args.mode or (old["phase"] if editing else _ask(
        console, "Modo: demo usa testes escritos; pilot chama o Codex",
        default=old.get("phase", "demo"), choices=["demo", "pilot"]))
    conditions = args.conditions
    if conditions is None:
        if editing:
            conditions = old["conditions"]
        else:
            answer = _ask(console, "Estratégias (separadas por vírgula)", default=",".join(old.get("conditions", ["L"])))
            conditions = [value.strip().upper() for value in answer.split(",")]
    repetitions = args.repetitions
    if repetitions is None:
        repetitions = old["repetitions"] if editing else int(_ask(console, "Repetições", default=str(old.get("repetitions", 1))))
    model = args.model
    if mode == "pilot" and not model:
        previous_model = (old.get("agents") or [{}])[0].get("model")
        model = previous_model if editing and previous_model else _ask(console, "Identificador do modelo do Codex", default=previous_model)
    return mode, conditions, repetitions, model


def create(args, console):
    folder = project_folder(args.name)
    if (folder / "contextlab.json").exists():
        raise ManifestError(f"Projeto já cadastrado. Use contextlab {args.name} configure; nenhum arquivo foi sobrescrito.")
    targets = discover_targets(folder)
    if not targets:
        raise ManifestError("Nenhuma função Python elegível encontrada no projeto.")
    if args.target:
        target = next((t for t in targets if f"{t['path']}:{t['symbol']}" == args.target), None)
        if target is None:
            raise ManifestError("Função não encontrada. Use caminho relativo:símbolo ou execute create interativamente.")
    else:
        _table(console, ["Opção", "Arquivo", "Função"], [(i, t["path"], t["symbol"]) for i, t in enumerate(targets, 1)])
        selection = int(_ask(console, "Função a testar", choices=[str(i) for i in range(1, len(targets) + 1)]))
        target = targets[selection - 1]
    references = args.reference
    if not references:
        references = [_ask(console, "Caminho do teste de referência (ex.: tests/test_conversao.py)")]
    mode, conditions, repetitions, model = _settings(args, console)
    config = new_config(folder, target, references, mode=mode, conditions=conditions, repetitions=repetitions,
                        model=model, fixture_dir=args.fixture_dir, image=args.image or "contextlab-evaluator:local")
    if mode == "pilot" and args.auth_file:
        config["agents"][0]["auth_file"] = args.auth_file
    path = save_project(folder, config)
    console.print(f"Projeto cadastrado: {path}", markup=False)
    console.print(f"Próximo passo: contextlab {args.name} plan")
    if mode == "pilot":
        console.print(f"Prepare a imagem do avaliador com: contextlab {args.name} setup")
    console.print("Limites iniciais são didáticos; não representam calibração para a coleta principal.")


def configure(folder, args, console):
    read_project(folder)
    config = json.loads(safe_file(folder, "contextlab.json").read_text())
    mode, conditions, repetitions, model = _settings(args, console, config)
    previous_agent = config["agents"][0]
    config.update(phase=mode, conditions=conditions, repetitions=repetitions)
    if mode == "pilot":
        config["agents"] = [{"id": "codex", "kind": "codex", "model": model}]
        auth = args.auth_file or (previous_agent.get("auth_file") if previous_agent["kind"] == "codex" else None)
        if auth:
            config["agents"][0]["auth_file"] = auth
    elif previous_agent["kind"] != "fixture":
        for target in config["projects"][0]["targets"]:
            safe_file(folder, f"tutorial/{folder.name}__{target['id']}.py")
        config["agents"] = [{"id": "fixture", "kind": "fixture", "fixture_dir": "tutorial"}]
    config["evaluation"]["backend"] = "local" if mode == "demo" else "docker"
    if args.image:
        config["evaluation"]["image"] = args.image
    save_project(folder, config, replace=True)
    console.print("Configuração atualizada. Os lotes anteriores conservam suas configurações e resultados.")
    if mode == "pilot":
        console.print(f"Próximo passo: contextlab {folder.name} setup")


def _state(row):
    if row["pending"]:
        return "Não iniciada" if row["record_status"] == "pending" else "Em andamento"
    if row["generation_infrastructure"] or row["evaluation_infrastructure"]:
        return "Falha de infraestrutura"
    return {"pending_review": "Aguardando revisão", "pending_evaluation": "Aguardando avaliação",
            "approved": "Aprovada", "rejected": "Reprovada"}.get(row["approval"], row["record_status"])


def list_runs(folder, args, console):
    rows = attempts(folder)
    if args.json:
        console.print_json(json.dumps(rows, ensure_ascii=False))
        return
    if not rows:
        console.print("Nenhuma tentativa registrada. Consulte plan antes de iniciar run.")
    else:
        _table(console, ["ID", "Função", "Modo", "Estratégia/rep.", "Situação"],
               [(r["attempt_id"], r["target"], r["phase"], f"{r['condition']}/{r['repetition']}",
                 _state(r)) for r in rows])
        console.print("Detalhes dos testes: contextlab " + folder.name + " show ID")
    for batch in sorted(runs_folder(folder).glob("*/batch.json")):
        if not (batch.parent / "results/run.json").exists():
            info = json.loads(batch.read_text())
            console.print(f"Lote {batch.parent.name}: {info['status']}; nenhuma geração iniciada.", markup=False)


def run_project(folder, args, console):
    from .runner import execute, validate_projects
    from .reporting import report_run
    from .context import build_context
    if args.max_runs is not None and args.max_runs < 1:
        raise ManifestError("--max-runs deve ser positivo.")
    if args.resume:
        batch = batch_folder(folder, args.resume)
        result = execute(batch / "protocol.lock.json", batch / "results", resume=True,
                         trusted_local=args.trusted_local, max_runs=args.max_runs)
    else:
        config = read_project(folder)
        if config["phase"] == "demo" and not args.trusted_local:
            raise ManifestError("Para testes autorais já inspecionados, acrescente --trusted-local. Pilotos Codex exigem Docker.")
        if config["phase"] == "pilot":
            from .adapters import doctor_agent
            readiness = doctor_agent(config["agents"][0])
            if not readiness.get("ready"):
                raise ManifestError("Codex indisponível: " + str(readiness.get("details")))
        for project in config["projects"]:
            for target in project["targets"]:
                for condition in config["conditions"]:
                    build_context(project, target, condition, config["limits"]["context_chars"])
        batch_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        batch = runs_folder(folder) / batch_id
        batch.mkdir(parents=True, exist_ok=False)
        write_json(batch / "batch.json", {"status": "validando referências"})
        console.print(f"Lote: {batch_id}")
        console.print("Validando referências e defeitos; depois será iniciada a geração.")
        try:
            validation = validate_projects(config, batch / "validation", args.trusted_local)
            if not all(item.get("valid") for item in validation["targets"].values()):
                raise ManifestError(f"Referências ou defeitos não passaram. Confira {batch / 'validation'}.")
            freeze(config, batch / "protocol.lock.json")
            result = execute(batch / "protocol.lock.json", batch / "results",
                             trusted_local=args.trusted_local, max_runs=args.max_runs)
        except BaseException:
            write_json(batch / "batch.json", {"status": "interrompido ou com falha; confira os registros"})
            raise
    report_run(batch / "results")
    write_json(batch / "batch.json", {"status": "execução encerrada", **result})
    console.print(f"Tentativas processadas: {result['processed_now']}. Para consultar: contextlab {folder.name} runs")
    console.print("Passar nos testes ainda exige revisão antes da aprovação.")


def show_attempt(path, console, *, code=False, raw_json=False):
    from .inspection import print_evaluation
    record = json.loads((path / "record.json").read_text())
    evaluation = record.get("reviewed_evaluation") or record.get("evaluation") or {}
    if raw_json:
        console.print_json(json.dumps(evaluation, ensure_ascii=False))
    else:
        print_evaluation(record, evaluation, console)
        submission = path / "test_generated.py"
        if code and submission.is_file():
            console.print("Código entregue", style="bold")
            console.print(Syntax(submission.read_text(), "python", line_numbers=True, word_wrap=True))
        console.print(f"Arquivos da tentativa: {path}", markup=False)
    return record, evaluation


def review_attempt(path, args, console):
    from .runner import review_trajectory
    from .reporting import report_run
    record, evaluation = show_attempt(path, console, code=True)
    # Retain the full diagnostic/defect evidence for the human review.
    console.print_json(json.dumps(evaluation, ensure_ascii=False))
    reviewer = args.reviewer or _ask(console, "Nome do responsável pela revisão")
    if not reviewer.strip():
        raise ManifestError("Identifique o responsável pela revisão.")
    decisions = {}
    for key, question in [("behavioral_assertions", "As asserções verificam o comportamento esperado?"),
                          ("no_target_mock", "A função alvo foi preservada, sem mock dela?"),
                          ("no_production_changes", "O código de produção foi preservado?")]:
        answer = getattr(args, key) or _ask(console, question, choices=["yes", "no"], default="no")
        decisions[key] = answer == "yes"
    # Marcação, não critério de aprovação: dublês das dependências são aceitos e analisados à parte.
    answer = args.dependency_doubles or _ask(
        console, "A suíte substitui dependências da função alvo por dublês (mock, stub, fake)?",
        choices=["yes", "no"], default="no")
    decisions["dependency_doubles"] = answer == "yes"
    if evaluation.get("test_kind") == "http":
        answer = args.http_requests or _ask(console, "O alvo foi exercitado via HTTP, com regras e SQLite reais, sem chamada direta ao handler?",
                                           choices=["yes", "no"], default="no")
        decisions["http_requests"] = answer == "yes"
    attribution = {}
    configured = {d["id"] for d in evaluation.get("defects", [])}
    for item in args.defect_attribution:
        name, separator, answer = item.partition("=")
        if not separator or answer not in {"yes", "no"} or name not in configured or name in attribution:
            raise ManifestError("Atribua somente defeitos já avaliados, usando ID=yes|no uma vez por defeito.")
        attribution[name] = answer == "yes"
    decisions["defect_attribution"] = attribution
    result = review_trajectory(path, reviewer.strip(), decisions, args.trusted_local)
    report_run(path.parent)
    console.print(f"Revisão registrada: {result['approval']}.")
    if any(d.get("status") == "pending_attribution" for d in result.get("defects", [])):
        console.print("Confira as falhas dos defeitos antes de registrar --defect-attribution ID=yes|no.")


def main(argv) -> int:
    console = Console()
    try:
        if argv[0] == "create":
            create(create_parser().parse_args(argv[1:]), console)
            return 0
        args = project_parser(argv[0]).parse_args(argv[1:])
        folder = project_folder(argv[0])
        if args.command == "configure":
            configure(folder, args, console)
        elif args.command == "setup":
            from .environment import setup_image
            config = read_project(folder)
            setup_image(folder, config, console, args.dockerfile)
            if config["evaluation"]["backend"] == "local":
                console.print("O projeto continua em demo local. Para usar Codex e Docker, configure o modo pilot.")
            else:
                console.print(f"Próximo passo: contextlab {folder.name} plan; depois contextlab {folder.name} run")
        elif args.command == "runs":
            list_runs(folder, args, console)
        elif args.command == "serve":
            from .cli import serve_command
            from .viewer import collect, load_prices, project_runs
            if args.batch:
                batch_folder(folder, args.batch)
            try:
                # Sem --prices, usa as tarifas mantidas ao lado da configuração do projeto, se existirem.
                default = folder / "precos.json"
                prices = load_prices(args.prices or (default if default.is_file() else None))
                title = read_project(folder)["projects"][0].get("name") or folder.name
                serve_command(lambda: collect(project_runs(folder, args.batch), title, prices), args,
                              announce=lambda text: console.print(text, markup=False, highlight=False, soft_wrap=True))
            except KeyboardInterrupt:
                console.print("\nVisualizador encerrado.")
        elif args.command in {"show", "review"}:
            path = find_attempt(folder, args.attempt)
            if args.command == "show":
                show_attempt(path, console, code=args.code, raw_json=args.json)
            else:
                review_attempt(path, args, console)
        elif args.command == "run":
            run_project(folder, args, console)
        else:
            config = read_project(folder)
            if args.command == "plan":
                rows = plan(config)
                if args.json:
                    console.print_json(json.dumps(rows, ensure_ascii=False))
                else:
                    console.print(f"{folder.name}: modo {config['phase']}, {len(rows)} tentativa(s). Nenhuma geração iniciada.")
                    _table(console, ["Ordem", "Função", "Agente", "Estratégia", "Repetição"],
                           [(r["order"], r["target"], r["agent"], r["condition"], r["repetition"]) for r in rows])
            elif args.command == "context":
                from .context import build_context
                project = config["projects"][0]
                targets = [t for t in project["targets"] if not args.target or t["id"] == args.target]
                if len(targets) != 1:
                    raise ManifestError("Escolha um alvo existente com --target ID.")
                context = build_context(project, targets[0], args.condition, config["limits"]["context_chars"])
                console.print(f"Estratégia {args.condition}; {len(context['files'])} arquivo(s)/trecho(s) disponíveis.")
                if context["text"]:
                    console.print(context["text"], markup=False, highlight=False)
                else:
                    console.print("\n".join(context["files"]), markup=False)
                if args.condition == "R" and context["equal_to_local"]:
                    console.print("Neste alvo, R não acrescentou material a L.")
        return 0
    except (ValueError, OSError, RuntimeError, KeyError) as exc:
        console.print(f"ContextLab: {exc}", style="red", markup=False)
        return 2
    except (KeyboardInterrupt, EOFError):
        console.print("\nInterrompido. Execuções já iniciadas permanecem registradas.")
        return 130
