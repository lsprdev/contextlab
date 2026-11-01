"""Readable, read-only views of the evaluation already stored in a record."""
from __future__ import annotations

from collections import Counter

from rich.table import Table
from rich.text import Text


_LABELS = {
    "passed": ("Passou", "green"),
    "failed": ("Falhou", "red"),
    "error": ("Erro", "red"),
    "skipped": ("Ignorado", "yellow"),
    "xfail": ("Marcado xfail", "yellow"),
    "incomplete": ("Incompleto", "yellow"),
}
_PHASES = {"setup": "preparação", "call": "execução", "teardown": "finalização"}


def case_results(report):
    """Combine setup/call/teardown into one row per collected pytest item.

    A passing call followed by a teardown failure is an error, not a pass.
    As in the evaluator, any xfail marker excludes a case from active passes.
    Missing phases never establish a pass.
    """
    grouped = {}
    for row in report.get("reports", []):
        grouped.setdefault(row["nodeid"], []).append(row)
    cases = []
    for nodeid, rows in grouped.items():
        failures = [r for r in rows if r["outcome"] == "failed"]
        calls = [r for r in rows if r["when"] == "call"]
        if any(r["when"] != "call" for r in failures):
            status = "error"
        elif any(r.get("expected_failure") for r in rows):
            status = "xfail"
        elif failures:
            status = "failed" if all(r.get("assertion_failure") for r in failures) else "error"
        elif any(r["outcome"] == "skipped" for r in rows):
            status = "skipped"
        elif calls and all(r["outcome"] == "passed" for r in rows) and {
            r["when"] for r in rows
        } >= {"setup", "call", "teardown"}:
            status = "passed"
        else:
            status = "incomplete"
        cases.append({"nodeid": nodeid, "status": status, "failures": failures})
    return cases


def _summary(cases):
    counts = Counter(case["status"] for case in cases)
    phrases = []
    for status, singular, plural in [
        ("passed", "passou", "passaram"), ("failed", "falhou", "falharam"),
        ("error", "com erro", "com erro"), ("skipped", "ignorado", "ignorados"),
        ("xfail", "marcado xfail", "marcados xfail"),
        ("incomplete", "incompleto", "incompletos"),
    ]:
        if counts[status]:
            count = counts[status]
            phrases.append(f"{count} {singular if count == 1 else plural}")
    return " · ".join(phrases)


def print_evaluation(record, evaluation, console):
    original = evaluation.get("original") or {}
    raw = original.get("raw") or {}
    cases = case_results(raw)
    console.print(_summary(cases) if cases else "Resultados por caso indisponíveis.", style="bold")
    approval = evaluation.get("approval")
    label = {"approved": "Aprovada", "rejected": "Reprovada",
             "pending_review": "Aguardando revisão", "not_applicable": "Não aplicável"}.get(
                 approval, "Sem decisão de aprovação")
    console.print(f"Situação da suíte: {label}.")
    console.print("Casos na versão original do projeto; cada linha corresponde a um caso, inclusive parâmetros.")
    collected = raw.get("collected", evaluation.get("collected"))
    if collected is not None:
        console.print(f"Coletados: {collected} · Com registro de execução: {len(cases)}")
        if collected > len(cases):
            console.print(f"{collected - len(cases)} caso(s) sem registro de execução; resultado desconhecido.")
    if cases:
        table = Table()
        table.add_column("Caso", overflow="fold")
        table.add_column("Resultado", no_wrap=True)
        for case in cases:
            label, style = _LABELS[case["status"]]
            table.add_row(Text(case["nodeid"].removeprefix("::")), Text(label, style=style))
        console.print(table)

    failures = [(case, row) for case in cases for row in case["failures"]]
    if failures:
        console.print("Detalhes das falhas e dos erros", style="bold")
    for case, row in failures:
        phase = _PHASES.get(row["when"], row["when"])
        console.print(f"{case['nodeid'].removeprefix('::')} — {phase}", markup=False, highlight=False)
        if row["when"] != "call":
            console.print(f"Ocorreu um erro na {phase} do caso.")
        elif row.get("assertion_failure"):
            console.print("Uma verificação do teste não foi satisfeita. Confira a expectativa e o comportamento do programa.")
        else:
            console.print("O teste encontrou uma exceção durante a execução.")
        console.print(row.get("message") or row.get("exception") or "Sem mensagem detalhada.",
                      markup=False, highlight=False)
    for error in raw.get("collection_errors", []):
        console.print("Erro ao coletar testes: " + str(error.get("nodeid", "")), markup=False)
        console.print(error.get("message") or "Sem mensagem detalhada.", markup=False, highlight=False)
    for message in dict.fromkeys(str(value) for value in
                                (record.get("error"), record.get("submission_error"),
                                 evaluation.get("error"), original.get("error"), raw.get("coverage_error")) if value):
        console.print(message, markup=False, highlight=False)
    if not evaluation:
        generation = record.get("generation") or {}
        console.print(f"Sem avaliação registrada. Geração: {generation.get('status', record.get('status', 'indisponível'))}.")
    elif evaluation.get("status") != "completed":
        console.print(f"Avaliação: {evaluation.get('status', 'indisponível')}. Não trate resultados ausentes como reprovações.")
    if approval == "rejected":
        console.print("A suíte não atendeu a todos os critérios de aprovação. Os casos que passaram continuam registrados.")
        if original.get("production_unchanged") is False:
            console.print("Foi detectada alteração no código de produção.")
        if evaluation.get("active_started") is False:
            console.print("Nenhum teste ativo iniciou a execução.")
        if (original.get("focal") or {}).get("executed") is False:
            console.print("Não foi registrada execução da função alvo.")
        review = evaluation.get("review") or {}
        for key, message in [("behavioral_assertions", "A revisão reprovou as verificações de comportamento."),
                             ("no_target_mock", "A revisão identificou substituição da função alvo por mock."),
                             ("no_production_changes", "A revisão identificou alteração da produção.")]:
            if review.get(key) is False:
                console.print(message)
    elif approval == "pending_review":
        console.print("Os critérios automáticos passaram; falta a inspeção humana para aprovar a suíte.")
    if any(case["status"] == "xfail" for case in cases):
        console.print("Casos marcados xfail ficam separados, mesmo quando passam; não contam como casos ativos aprovados.")
    if record.get("reviewed_evaluation"):
        console.print("Exibindo a avaliação da revisão mais recente; a avaliação inicial permanece preservada.")
