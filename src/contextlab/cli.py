"""CLI explícita; todos os limites do experimento vêm do manifesto."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .manifest import ManifestError, freeze, load_config, plan, write_json


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="contextlab", description="Experimentos L/R/A de geração de testes unitários",
        epilog="Uso por projeto: contextlab create NOME; contextlab NOME configure|setup|plan|context|run|runs|show|review|serve. Os comandos acima mantêm o acesso por manifesto.")
    commands = result.add_subparsers(dest="command", required=True)
    for name, help_text in (("plan", "Exibir matriz sorteada, sem chamadas de IA"),
                            ("doctor", "Verificar binários, versões e opções dos adaptadores")):
        p = commands.add_parser(name, help=help_text)
        p.add_argument("manifest", type=Path)
    prepare = commands.add_parser("prepare", help="Inspecionar contexto permitido de um alvo")
    prepare.add_argument("manifest", type=Path)
    prepare.add_argument("--project", required=True)
    prepare.add_argument("--target", required=True)
    prepare.add_argument("--condition", choices=["L", "R", "A"], required=True)
    prepare.add_argument("--out", type=Path, required=True)
    validation = commands.add_parser("validate", help="Executar referências e testemunhos dos defeitos")
    validation.add_argument("manifest", type=Path)
    validation.add_argument("--out", type=Path, required=True)
    validation.add_argument("--trusted-local", action="store_true", help="Somente demonstrações com código autoral confiável")
    freezing = commands.add_parser("freeze", help="Congelar fontes, configuração e ordem da matriz")
    freezing.add_argument("manifest", type=Path)
    freezing.add_argument("--out", type=Path, required=True)
    freezing.add_argument("--evidence", type=Path, help="Declarações de revisão e caminhos de piloto/validação para main")
    running = commands.add_parser("run", help="Gerar uma entrega e avaliar cada trajetória; sem reparos")
    running.add_argument("lock", type=Path)
    running.add_argument("--out", type=Path, required=True)
    running.add_argument("--trusted-local", action="store_true")
    running.add_argument("--resume", action="store_true", help="Pular trajetórias já registradas, sem regenerá-las")
    running.add_argument("--max-runs", type=int, help="Executar no máximo N trajetórias pendentes, mantendo a matriz")
    reviewing = commands.add_parser("review", help="Registrar inspeção humana e reavaliar a mesma entrega")
    reviewing.add_argument("trajectory", type=Path)
    reviewing.add_argument("--reviewer", required=True)
    for key in ("behavioral-assertions", "no-target-mock", "no-production-changes"):
        reviewing.add_argument("--" + key, choices=["yes", "no"], required=True)
    reviewing.add_argument("--dependency-doubles", choices=["yes", "no"], required=True,
                           help="Marca se a suíte substitui dependências da função alvo por dublês; não decide a aprovação")
    reviewing.add_argument("--http-requests", choices=["yes", "no"], help="Revisão adicional dos alvos HTTP de piloto")
    reviewing.add_argument("--defect-attribution", action="append", default=[], metavar="ID=yes|no")
    reviewing.add_argument("--trusted-local", action="store_true")
    reporting = commands.add_parser("report", help="Exportar CSV, JSON e relatório com denominadores")
    reporting.add_argument("run_dir", type=Path)
    serving = commands.add_parser("serve", help="Abrir o visualizador web dos registros, somente leitura")
    serving.add_argument("run_dir", type=Path, help="Diretório de resultados que contém run.json")
    _serve_options(serving)
    return result


def _serve_options(command) -> None:
    command.add_argument("--port", type=int, default=8765, help="Porta local (padrão: 8765)")
    command.add_argument("--no-open", action="store_true", help="Não abrir o navegador automaticamente")
    command.add_argument("--prices", type=Path, metavar="TARIFAS.json",
                         help="Tarifas de API por milhão de tokens, para estimar o custo de cada tentativa")
    command.add_argument("--export", type=Path, metavar="ARQUIVO.html",
                         help="Gravar uma página autossuficiente em vez de iniciar o servidor")


def serve_command(load, args, announce=print) -> None:
    """Compartilhado pelos fluxos por manifesto e por projeto; nunca escreve nos registros."""
    from .viewer import export, serve
    if args.export:
        announce(f"Página gravada em {export(load(), args.export.resolve())}")
    else:
        serve(load, port=args.port, open_browser=not args.no_open, announce=announce)


def _execute(args):
    from .runner import (check_main_evidence, execute, review_trajectory, validate_projects)
    if args.command in {"plan", "doctor", "prepare", "validate", "freeze"}:
        config = load_config(args.manifest)
    if args.command == "plan":
        rows = plan(config)
        return {"phase": config["phase"], "planned": len(rows), "trajectories": rows}
    if args.command == "doctor":
        from .adapters import doctor_agent
        return {a["id"]: ({"ready": True, "simulated": True, "details": "Fixture autoral; sem modelo"}
                          if a["kind"] == "fixture" else doctor_agent(a)) for a in config["agents"]}
    if args.command == "prepare":
        from .context import build_context
        project = next((p for p in config["projects"] if p["id"] == args.project), None)
        target = next((t for t in project["targets"] if t["id"] == args.target), None) if project else None
        if target is None:
            raise ManifestError("Projeto/alvo não encontrado no manifesto")
        if args.out.exists():
            raise ManifestError("Destino já existe; use outro diretório")
        context = build_context(project, target, args.condition, config["limits"]["context_chars"])
        write_json(args.out / "context.json", context)
        (args.out / "initial.txt").write_text(context["text"], encoding="utf-8")
        return {"output": str(args.out), "initial_chars": len(context["text"]),
                "files": list(context["files"]), "unresolved": context["unresolved"], "omitted": context["omitted"]}
    if args.command == "validate":
        return validate_projects(config, args.out.resolve(), args.trusted_local)
    if args.command == "freeze":
        from .context import build_context
        # Reprovar antecipadamente o arquivo focal maior que o orçamento.
        for project in config["projects"]:
            for target in project["targets"]:
                for condition in config["conditions"]:
                    build_context(project, target, condition, config["limits"]["context_chars"])
        evidence = json.loads(args.evidence.read_text()) if args.evidence else None
        if evidence:
            for key in ("pilot_run", "validation_dir"):
                if evidence.get(key):
                    evidence[key] = str((args.evidence.resolve().parent / Path(evidence[key]).expanduser()).resolve())
        if config["phase"] == "main":
            check_main_evidence(config, evidence or {})
        lock = freeze(config, args.out.resolve(), evidence)
        return {"lock": str(args.out), "lock_hash": lock["lock_hash"], "planned": len(lock["plan"])}
    if args.command == "run":
        if args.max_runs is not None and args.max_runs < 1:
            raise ManifestError("--max-runs deve ser positivo")
        return execute(args.lock.resolve(), args.out.resolve(), trusted_local=args.trusted_local,
                       resume=args.resume, max_runs=args.max_runs)
    if args.command == "review":
        attribution = {}
        for item in args.defect_attribution:
            if "=" not in item or item.rsplit("=", 1)[1] not in {"yes", "no"}:
                raise ManifestError("Use --defect-attribution ID=yes ou ID=no")
            key, value = item.rsplit("=", 1)
            if key in attribution:
                raise ManifestError("Atribuição duplicada")
            attribution[key] = value == "yes"
        decisions = {key: getattr(args, key) == "yes" for key in
                     ("behavioral_assertions", "no_target_mock", "no_production_changes")}
        decisions["defect_attribution"] = attribution
        decisions["dependency_doubles"] = args.dependency_doubles == "yes"
        if args.http_requests is not None:
            decisions["http_requests"] = args.http_requests == "yes"
        return review_trajectory(args.trajectory.resolve(), args.reviewer, decisions, args.trusted_local)
    if args.command == "report":
        from .reporting import report_run
        return report_run(args.run_dir.resolve())


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    from .projects import RESERVED
    if argv and (argv[0] == "create" or (not argv[0].startswith("-") and argv[0] not in RESERVED)):
        from .project_cli import main as project_main
        return project_main(argv)
    args = parser().parse_args(argv)
    try:
        if args.command == "serve":
            from .viewer import collect, load_prices
            run_dir = args.run_dir.resolve()
            prices = load_prices(args.prices)
            serve_command(lambda: collect([(run_dir.name, run_dir)], None, prices), args)
            return 0
        result = _execute(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.command == "validate" and any(not x.get("valid") for x in result["targets"].values()):
            return 1
        if args.command == "doctor" and any(not x.get("ready") for x in result.values()):
            return 1
        return 0
    except (ValueError, OSError, RuntimeError, KeyError) as exc:
        print(f"ContextLab: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        if args.command == "serve":
            print("\nVisualizador encerrado.", file=sys.stderr)
            return 0
        print("Interrompido. A tentativa foi preservada, sem regeneração automática.", file=sys.stderr)
        return 130
