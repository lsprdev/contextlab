"""Resumo do experimento do TCC para a página Experimento do site.

Lê só os registros publicados em `experimento-tcc/` (um `record.json` por
tentativa, o manifesto principal e a tabela de tarifas) e devolve um JSON
mínimo, sem código gerado, contextos ou caminhos locais.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import estimate_cost, load_prices


def _attempt(record: dict, rates: dict | None) -> dict:
    generation = record.get("generation") or {}
    initial = record.get("evaluation") or {}
    evaluation = record.get("reviewed_evaluation") or initial
    usage = generation.get("usage") or {}
    stats = generation.get("context_stats") or {}
    coverage = evaluation.get("coverage_main") or {}
    defects = evaluation.get("defects") or []
    approved = evaluation.get("approved") is True
    if record.get("status") == "limit":
        outcome = "limite de contexto"
    elif approved:
        outcome = "aprovada"
    elif evaluation.get("status") == "syntax_error":
        outcome = "erro de sintaxe"
    else:
        categories = evaluation.get("failure_categories") or []
        names = {"setup_error": "erro de preparação", "execution_error": "erro de execução",
                 "collection_error": "erro de coleta", "assertion_failure": "falha de asserção"}
        outcome = names.get(categories[0], categories[0]) if categories else "reprovada"
    return {
        "project": record["project"], "target": record["target"], "condition": record["condition"],
        "repetition": record["repetition"], "order": record["order"], "outcome": outcome, "approved": approved,
        "input_tokens": generation.get("input_tokens"), "output_tokens": generation.get("output_tokens"),
        "cached_input_tokens": usage.get("cached_input_tokens"),
        "cost": estimate_cost({**usage, "input_tokens": generation.get("input_tokens"),
                               "output_tokens": generation.get("output_tokens")}, rates),
        "context_chars": stats.get("chars_used"), "tool_calls": stats.get("tool_calls"),
        "generation_seconds": generation.get("seconds"),
        "evaluation_seconds": initial.get("total_seconds", initial.get("seconds")),
        "tests": evaluation.get("collected") if approved else None,
        "line_rate": coverage.get("line_rate") if approved else None,
        "branch_rate": coverage.get("branch_rate") if approved and coverage.get("branch_total") else None,
        "defects_total": len(defects) if approved else None,
        "defects_detected": sum(d.get("detected") is True for d in defects) if approved else None,
        "dependency_doubles": bool((evaluation.get("review") or {}).get("dependency_doubles")) if approved else None,
    }


def experiment_summary(folder: Path) -> dict:
    folder = Path(folder)
    prices = load_prices(folder / "precos.json")
    manifest = json.loads((folder / "manifesto" / "principal.json").read_text(encoding="utf-8"))
    agent = manifest["agents"][0]
    rates = (prices["modelos"] if prices else {}).get(agent["model"])
    records = [json.loads(p.read_text(encoding="utf-8"))
               for p in sorted((folder / "resultados" / "coleta" / "tentativas").glob("*/record.json"))]
    versions = sorted({(r.get("generation") or {}).get("version") for r in records} - {None})
    return {
        "config": {"model": agent["model"], "reasoning_effort": agent.get("reasoning_effort"),
                   "client": versions[0] if len(versions) == 1 else ", ".join(versions),
                   "limits": manifest["limits"], "seed": manifest["seed"], "repetitions": manifest["repetitions"],
                   "image": manifest["evaluation"]["image"], "contextlab": "v0.1.0"},
        "projects": [{"id": p["id"], "name": p["name"],
                      "targets": [{"id": t["id"], "symbol": t["import"].replace(":", ".")} for t in p["targets"]]}
                     for p in manifest["projects"]],
        "pricing": {k: prices[k] for k in ("moeda", "fonte", "consulta")} if prices else None,
        "rates": rates,
        "attempts": [_attempt(r, rates) for r in records],
    }
