"""Descriptive reporting with explicit missingness and paired focal units.

A trajectory is not an independent experimental subject: contrasts first
summarize each function and only then give equal weight to comparable functions.
No unavailable token count or unresolved review is converted to zero.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .manifest import digest, write_json

_INFRA = {"infrastructure_error", "interrupted"}
_PENDING = {"running", "pending", "not_started"}
_TASK_FAILURE = {"timeout", "limit", "budget_exceeded", "tool_limit", "protocol_violation",
                 "invalid_submission", "no_submission"}
_CSV_FIELDS = [
    "id", "order", "project", "target", "agent", "condition", "repetition", "phase", "demonstration",
    "record_status", "generation_status", "observable", "pending", "generation_infrastructure",
    "evaluation_status", "evaluation_infrastructure", "approval", "approved", "active_started",
    "reference_passed", "syntax_ok", "collected", "line_rate", "branch_rate", "preparation_seconds",
    "generation_seconds", "evaluation_seconds", "context_chars", "tool_calls", "input_tokens", "output_tokens", "detection_rate",
    "defects_configured", "defects_eligible", "defects_measured", "defects_detected", "detection_complete",
]


def _mean(values):
    values = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    return mean(values) if values else None


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _row(planned, record, config, target):
    generation = (record or {}).get("generation") or {}
    evaluation = (record or {}).get("reviewed_evaluation") or (record or {}).get("evaluation") or {}
    status = (record or {}).get("status", "pending")
    gen_status = generation.get("status")
    context_stats = generation.get("context_stats") or generation.get("usage") or {}
    # A completed generation remains observable even if its later evaluation
    # was interrupted or unavailable. A model response with bad format is also
    # an observation, unlike a transport outage before any response.
    observable = bool(gen_status == "completed" or gen_status in _TASK_FAILURE or status == "invalid_submission")
    pending = not record or (status in _PENDING and not observable)
    gen_infra = not observable and not pending and (status in _INFRA or gen_status in _INFRA)
    eval_status = evaluation.get("status")
    eval_infra = bool(observable and (eval_status in _INFRA or
                         (gen_status == "completed" and status in _INFRA and not evaluation)))
    approval = evaluation.get("approval")
    approved = None
    if observable:
        if status == "invalid_submission" or gen_status in _TASK_FAILURE:
            approval, approved = "rejected", False
        elif approval == "approved" and evaluation.get("approved") is True:
            approved = True
        elif approval == "rejected" or eval_status in {"syntax_error", "no_submission", "timeout"}:
            approved = False
        elif not evaluation:
            approval = "pending_evaluation"
    active = evaluation.get("active_started")
    passed = evaluation.get("reference_passed")
    if observable and approved is False and not evaluation:
        active, passed = False, False
    coverage = evaluation.get("coverage_main") or {}
    # Metrics in coverage_raw are diagnostics and must never substitute for
    # coverage of an approved suite in primary results.
    if approved is not True:
        coverage = {}
    return {
        **planned, "phase": config["phase"], "demonstration": config["phase"] == "demo",
        "record_status": status, "generation_status": gen_status,
        "observable": observable, "pending": bool(pending), "generation_infrastructure": bool(gen_infra),
        "evaluation_status": eval_status, "evaluation_infrastructure": eval_infra,
        "approval": approval, "approved": approved, "active_started": active,
        "reference_passed": passed, "syntax_ok": evaluation.get("syntax_ok"),
        "collected": evaluation.get("collected"), "line_rate": coverage.get("line_rate"),
        "branch_rate": coverage.get("branch_rate"),
        "preparation_seconds": (record or {}).get("preparation_seconds"),
        "generation_seconds": generation.get("seconds"),
        "evaluation_seconds": evaluation.get("total_seconds", evaluation.get("seconds")),
        "context_chars": context_stats.get("chars_used"), "tool_calls": context_stats.get("tool_calls"),
        "input_tokens": generation.get("input_tokens"), "output_tokens": generation.get("output_tokens"),
        "detection_rate": evaluation.get("detection_rate") if approved is True else None,
        "defects_configured": len(target.get("defects", [])),
        "defects_eligible": evaluation.get("defects_eligible"),
        "defects_measured": evaluation.get("defects_measured"),
        "defects_detected": evaluation.get("defects_detected"),
        "detection_complete": evaluation.get("detection_complete"),
        "defects": evaluation.get("defects", []),
    }


def _summary(rows):
    observable = [row for row in rows if row["observable"]]
    known = [row for row in observable if row["approved"] is not None]
    approved = [row for row in known if row["approved"]]
    pending = sum(row["pending"] for row in rows)
    unresolved = len(observable) - len(known)
    rates = {
        "planned": len(rows), "generation_observable": len(observable),
        "pending": pending,
        "generation_infrastructure": sum(row["generation_infrastructure"] for row in rows),
        "evaluation_infrastructure": sum(row["evaluation_infrastructure"] for row in rows),
        "approval_pending": sum(row["approval"] == "pending_review" for row in observable),
        "approval_unresolved": unresolved, "approved": len(approved),
        "approval_known_n": len(known), "approval_observable_n": len(observable),
        "approval_rate_known": _ratio(len(approved), len(known)),
        "approval_rate": _ratio(len(approved), len(observable)) if not pending and not unresolved else None,
        "approval_complete": bool(observable) and not pending and not unresolved,
        "generation_complete": len(observable) == len(rows),
    }
    for metric in ("active_started", "reference_passed"):
        measured = [row[metric] for row in observable if row[metric] is not None]
        rates[metric + "_known_n"] = len(measured)
        rates[metric + "_rate_known"] = _ratio(sum(measured), len(measured))
        rates[metric + "_rate"] = (_ratio(sum(measured), len(observable))
                                         if not pending and len(measured) == len(observable) else None)
    for metric in ("line_rate", "branch_rate", "detection_rate"):
        values = [row[metric] for row in approved if row[metric] is not None]
        rates[metric + "_approved"] = _mean(values)
        rates[metric + "_approved_n"] = len(values)
    rates["line_coverage_complete"] = bool(approved) and all(row["line_rate"] is not None for row in approved)
    rates["detection_complete"] = bool(approved) and all(row["detection_complete"] is True for row in approved)
    for metric in ("preparation_seconds", "generation_seconds", "evaluation_seconds", "context_chars", "tool_calls", "input_tokens", "output_tokens"):
        values = [row[metric] for row in observable if row[metric] is not None]
        rates[metric + "_mean"] = _mean(values)
        rates[metric + "_n"] = len(values)
        rates[metric + "_complete"] = bool(observable) and not pending and len(values) == len(observable)
    return rates


def _inventory_validation(header, rows):
    """Return reviewed inventory eligibility, never infer it from configuration."""
    eligibility = {}
    validation_path = Path((header.get("evidence") or {}).get("validation_dir", "")) / "validation.json"
    if validation_path.is_file():
        validation = _read(validation_path)
        if (validation.get("config_hash") == digest(header["config"]) and
                validation.get("source_hashes") == header.get("source_hashes")):
            for project in header["config"]["projects"]:
                for target in project["targets"]:
                    item = validation.get("targets", {}).get(f"{project['id']}__{target['id']}", {})
                    for defect in item.get("defects", []):
                        eligibility[(project["id"], target["id"], defect["id"])] = defect.get("eligible")
    for row in rows:
        for defect in row["defects"]:
            key = row["project"], row["target"], defect["id"]
            # A contradictory validation is retained as unknown, not silently
            # resolved by whichever trajectory happens to be listed last.
            if key in eligibility and eligibility[key] != defect.get("eligible"):
                eligibility[key] = None
            elif key not in eligibility:
                eligibility[key] = defect.get("eligible")
    return eligibility


def _defect_summary(rows, defect_id, validated):
    observable = [row for row in rows if row["observable"]]
    detected = 0
    known_n = 0
    denominator = 0
    infra = 0
    unresolved = 0
    timeouts = 0
    ineligible = 0
    for row in observable:
        if row["evaluation_infrastructure"]:
            infra += 1
            continue
        entry = next((entry for entry in row["defects"] if entry["id"] == defect_id), None)
        if row["approved"] is False:
            denominator += 1
            known_n += 1  # Invalid/rejected suites cannot detect this defect.
        elif row["approved"] is None:
            denominator += 1
            unresolved += 1
        elif not entry:
            denominator += 1
            unresolved += 1
        elif entry.get("eligible") is False:
            ineligible += 1
        elif entry.get("status") in _INFRA:
            infra += 1
        else:
            denominator += 1
            if entry.get("detected") is True or entry.get("detected") is False:
                known_n += 1
                detected += entry["detected"] is True
            else:
                unresolved += 1
                timeouts += entry.get("status") == "timeout"
    pending = sum(row["pending"] for row in rows)
    complete = bool(denominator) and not unresolved and not pending and validated is True and not ineligible
    return {
        "id": defect_id, "inventory_validated": validated,
        "planned": len(rows), "generation_observable": len(observable), "pending": pending,
        "generation_infrastructure": sum(row["generation_infrastructure"] for row in rows),
        "measurement_infrastructure_excluded": infra, "ineligible_excluded": ineligible,
        "observable_denominator": denominator, "known_n": known_n,
        "unresolved": unresolved, "timeouts": timeouts, "detected": detected,
        "rate_known": _ratio(detected, known_n) if validated is True else None,
        "rate_all_observable": _ratio(detected, denominator) if complete else None,
        "complete": complete,
    }


def _grouped(rows, fields):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row)
    return [{**dict(zip(fields, key)), **_summary(items)} for key, items in sorted(groups.items())]


def _contrasts(functions):
    by_agent = defaultdict(dict)
    for item in functions:
        by_agent[item["agent"]][(item["project"], item["target"], item["condition"])] = item
    result = []
    metrics = ("approval_rate", "line_rate_approved", "branch_rate_approved", "detection_rate_approved",
               "generation_seconds_mean", "context_chars_mean", "tool_calls_mean", "input_tokens_mean", "output_tokens_mean")
    for agent, entries in sorted(by_agent.items()):
        projects = sorted({key[0] for key in entries})
        units = sorted({key[:2] for key in entries})
        for scope in [*projects, None]:
            selected = [unit for unit in units if scope is None or unit[0] == scope]
            for left, right in (("L", "A"), ("R", "A"), ("R", "L")):
                for metric in metrics:
                    values = []
                    for project, target in selected:
                        a, b = entries.get((project, target, left)), entries.get((project, target, right))
                        if not a or not b or a.get(metric) is None or b.get(metric) is None:
                            continue
                        if metric == "line_rate_approved" and not (a["line_coverage_complete"] and b["line_coverage_complete"]):
                            continue
                        if metric == "detection_rate_approved" and not (a["detection_complete"] and b["detection_complete"]):
                            continue
                        values.append({"project": project, "target": target,
                                       "left": a[metric], "right": b[metric], "difference": a[metric] - b[metric]})
                    result.append({"project": scope, "agent": agent, "contrast": left + "-" + right,
                                   "metric": metric, "functions_planned": len(selected),
                                   "functions_comparable": len(values),
                                   "difference_equal_function_weight": _mean([value["difference"] for value in values]),
                                   "function_differences": values})
    return result


def _format(value):
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _markdown(report):
    lines = ["# Relatório ContextLab", ""]
    if report["demonstration"]:
        lines += ["**DEMONSTRAÇÃO AUTORAL: testes fixos, sem geração de modelo; estes resultados não são evidência do experimento.**", ""]
    lines += [f"Fase: `{report['phase']}`. Taxas variam de 0 a 1; `—` significa ausente ou não aplicável.", "",
              "## Coleta e aprovação", "",
              "| Projeto | Agente | Condição | Planejadas | Observáveis | Aprovadas / conhecidas | Taxa principal | Pendentes / infra geração | Revisões pendentes |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for item in report["groups"]:
        lines.append(f"| {item['project']} | {item['agent']} | {item['condition']} | {item['planned']} | {item['generation_observable']} | {item['approved']} / {item['approval_known_n']} | {_format(item['approval_rate'])} | {item['pending']} / {item['generation_infrastructure']} | {item['approval_pending']} |")
    lines += ["", "A taxa principal usa gerações observáveis; falhas de infraestrutura de geração são informadas separadamente. "
              "Trajetórias ainda não executadas e aprovações sem desfecho mantêm a taxa principal ausente. "
              "A taxa entre decisões conhecidas (`approval_rate_known`) tem denominador próprio no JSON. "
              "Revisão pendente não equivale a reprovação.", "", "## Qualidade condicionada à aprovação", "",
              "| Projeto | Agente | Condição | Linhas (n suítes) | Ramificações (n suítes) | Detecção (n suítes) |",
              "|---|---|---|---:|---:|---:|"]
    for item in report["groups"]:
        lines.append(f"| {item['project']} | {item['agent']} | {item['condition']} | {_format(item['line_rate_approved'])} ({item['line_rate_approved_n']}) | {_format(item['branch_rate_approved'])} ({item['branch_rate_approved_n']}) | {_format(item['detection_rate_approved'])} ({item['detection_rate_approved_n']}) |")
    lines += ["", "Cobertura bruta de suítes reprovadas não entra nesta tabela. Funções sem ramificações não recebem zero. "
              "Detecção depende da revisão e da medição completa do inventário elegível. "
              "Por defeito, saídas inválidas e suítes reprovadas contam zero; infraestrutura de avaliação é excluída e contada à parte. "
              "Timeout e atribuição pendente não são convertidos em detecção nem em zero conhecido.", "", "## Comparações pareadas por função", "",
              "| Agente | Contraste | Métrica | Funções comparáveis / previstas | Diferença média |",
              "|---|---|---|---:|---:|"]
    for item in report["contrasts"]:
        if item["project"] is None and item["metric"] in {"approval_rate", "line_rate_approved", "generation_seconds_mean"}:
            lines.append(f"| {item['agent']} | {item['contrast']} | {item['metric']} | {item['functions_comparable']} / {item['functions_planned']} | {_format(item['difference_equal_function_weight'])} |")
    lines += ["", "Cada diferença é calculada na mesma função; a síntese dá peso igual às funções comparáveis. "
              "Diferença positiva significa valor maior na condição à esquerda, não necessariamente melhor. "
              "A qualidade condicionada à aprovação usa somente funções com medidas comparáveis nos dois braços. "
              "As repetições não são tratadas como sujeitos independentes. Resultados detalhados por projeto, função e defeito estão no JSON.", "",
              "## Recursos e rastreabilidade", "",
              "`results.csv` contém uma linha por trajetória planejada, inclusive pendentes e falhas. "
              "Campos ausentes permanecem vazios; tokens indisponíveis não viram zero. "
              "Tempo de preparo, geração e avaliação são registrados separadamente. "
              "Caracteres entregues e chamadas de ferramentas vêm da auditoria efetiva; as médias de recursos informam n e completude. "
              "`report.json` preserva denominadores, inventário configurado/validado, completude e diferenças por função. "
              "Custos de assinatura não são convertidos em preços fictícios por chamada.", ""]
    return "\n".join(lines)


def read_report(run_dir: Path) -> dict:
    """Read all planned trajectories without writing or rerunning anything."""
    run_dir = Path(run_dir).resolve()
    header = _read(run_dir / "run.json")
    config = header["config"]
    targets = {(project["id"], target["id"]): target
               for project in config["projects"] for target in project["targets"]}
    rows = []
    for planned in header["plan"]:
        path = run_dir / planned["id"] / "record.json"
        record = _read(path) if path.is_file() else None
        rows.append(_row(planned, record, config, targets[planned["project"], planned["target"]]))
    functions = _grouped(rows, ("project", "target", "agent", "condition"))
    eligibility = _inventory_validation(header, rows)
    defect_groups = []
    for item in functions:
        target = targets[item["project"], item["target"]]
        selected = [row for row in rows if all(row[key] == item[key] for key in ("project", "target", "agent", "condition"))]
        for defect in target.get("defects", []):
            defect_groups.append({**{key: item[key] for key in ("project", "target", "agent", "condition")},
                                  **_defect_summary(selected, defect["id"], eligibility.get((item["project"], item["target"], defect["id"])))})
    report = {"schema_version": 1, "phase": config["phase"], "demonstration": config["phase"] == "demo",
              "lock_hash": header.get("lock_hash"), "summary": _summary(rows),
              "inventory": [{"project": project, "target": target, "id": defect["id"],
                             "validated": eligibility.get((project, target, defect["id"]))}
                            for (project, target), definition in targets.items() for defect in definition.get("defects", [])],
              "groups": _grouped(rows, ("project", "agent", "condition")), "functions": functions,
              "defects": defect_groups, "contrasts": _contrasts(functions), "rows": rows}
    return report


def report_run(run_dir: Path) -> dict:
    """Export the same read-only summary to CSV, JSON and Markdown."""
    run_dir = Path(run_dir).resolve()
    report = read_report(run_dir)
    with (run_dir / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["rows"])
    write_json(run_dir / "report.json", report)
    (run_dir / "report.md").write_text(_markdown(report), encoding="utf-8")
    return report
