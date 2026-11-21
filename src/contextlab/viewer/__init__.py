"""Visualizador somente leitura dos registros de execução.

Fica em um subpacote para não participar do hash de implementação que o
congelamento confere: mudanças de apresentação não alteram o protocolo.
Nada é escrito nos diretórios de resultados, nenhuma entrega é reavaliada e o
servidor atende apenas requisições locais de leitura.
"""
from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path

_MAX_TEXT = 400_000  # Um texto maior é truncado na página, nunca no disco.
_PAGE = Path(__file__).with_name("page.html")
_DOCS = Path(__file__).with_name("docs.html")
# Motor das animações e as duas animações da documentação, por marcador.
_TOURS = {"<!--__CONTEXTLAB_TOUR__-->": "tour.html",
          "<!--__CONTEXTLAB_TOUR_PASSOS__-->": "tour-passos.html",
          "<!--__CONTEXTLAB_TOUR_CONTEXTO__-->": "tour-contexto.html"}
_MERMAID = Path(__file__).parent / "vendor" / "mermaid.min.js"
_SECURITY_HEADERS = {
    # 'self' atende apenas à biblioteca de diagramas servida pelo próprio visualizador.
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
                               "script-src 'self' 'unsafe-inline'; img-src data:; font-src data:; "
                               "base-uri 'none'; form-action 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class ViewerError(ValueError):
    """Não há registros legíveis para apresentar."""


def _json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _text(path: Path):
    """Conteúdo para exibição; arquivos ausentes ou ilegíveis ficam ausentes."""
    try:
        if path.is_symlink() or not path.is_file():
            return None
        value = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if len(value) > _MAX_TEXT:
        return value[:_MAX_TEXT] + f"\n\n[... truncado na visualização: {len(value)} caracteres no arquivo ...]"
    return value


def _state(row: dict) -> str:
    """Rótulo único por tentativa, na mesma lógica do relatório."""
    if row["pending"]:
        return "pendente"
    if row["generation_infrastructure"] or row["evaluation_infrastructure"]:
        return "infraestrutura"
    if row["approved"] is True:
        return "aprovada"
    if row["approval"] == "pending_review":
        return "aguardando revisão"
    if row["approved"] is False:
        return "reprovada"
    return "sem desfecho"


def _cases(evaluation: dict) -> list[dict]:
    """Um item por caso de teste, com a fase em que falhou quando for o caso."""
    reports = (((evaluation.get("original") or {}).get("raw") or {}).get("reports")) or []
    cases: dict[str, dict] = {}
    for report in reports:
        case = cases.setdefault(report["nodeid"], {"name": report["nodeid"].lstrip(":"), "outcome": None,
                                                    "phase": None, "exception": None, "message": None,
                                                    "expected_failure": False})
        case["expected_failure"] = case["expected_failure"] or bool(report.get("expected_failure"))
        failed = report["outcome"] == "failed"
        if failed and case["outcome"] != "failed":
            case.update(outcome="failed", phase=report["when"], exception=report.get("exception"),
                        message=report.get("message"))
        elif report["when"] == "call" and case["outcome"] is None:
            case["outcome"] = report["outcome"]
        elif report["outcome"] == "skipped" and case["outcome"] is None:
            case["outcome"] = "skipped"
    for case in cases.values():
        case["outcome"] = case["outcome"] or "not_run"
    return list(cases.values())


def _context(path: Path) -> dict | None:
    context = _json(path)
    if not isinstance(context, dict):
        return None
    snippets = [{"key": item.get("key"), "reason": item.get("reason"), "chars": len(item.get("text", ""))}
                for item in context.get("snippets", [])]
    return {
        "text": context.get("text") or "",
        "snippets": snippets,
        # Em A só os caminhos interessam: o que foi lido aparece nas consultas.
        "available": sorted(context.get("files", {})) if not context.get("text") else [],
        "unresolved": context.get("unresolved", []),
        "omitted": context.get("omitted", []),
        "equal_to_local": bool(context.get("equal_to_local")),
    }


def load_prices(path: Path | None) -> dict | None:
    """Tabela opcional de tarifas de API, em valor por milhão de tokens.

    O arquivo é mantido pelo pesquisador, com fonte e data da consulta. O valor
    calculado é uma estimativa: com login por assinatura não há cobrança por
    tentativa, e a página identifica o número como cenário de preço de API.
    """
    if path is None:
        return None
    try:
        prices = json.loads(Path(path).read_text(encoding="utf-8"))
        models = prices["modelos"]
        for name, rates in models.items():
            for key in ("entrada", "entrada_cache", "saida"):
                if isinstance(rates[key], bool) or not isinstance(rates[key], (int, float)) or rates[key] < 0:
                    raise ValueError(f"tarifa inválida em {name}: {key}")
        return {"moeda": str(prices.get("moeda", "USD")), "fonte": prices.get("fonte"),
                "consulta": prices.get("consulta"), "observacao": prices.get("observacao"), "modelos": models}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ViewerError(f"Arquivo de tarifas inválido ({path}): {exc}") from exc


def estimate_cost(usage: dict, rates: dict | None) -> float | None:
    """Estimativa por categoria de token, sem contar duas vezes a entrada em cache.

    Cache lido e cache escrito são partes da entrada; raciocínio é parte da saída.
    Sem tarifa para o modelo ou sem contagem de tokens, o custo fica ausente.
    """
    if not rates or not isinstance(usage.get("input_tokens"), int) or not isinstance(usage.get("output_tokens"), int):
        return None
    cached = usage.get("cached_input_tokens") or 0
    written = usage.get("cache_write_input_tokens") or 0
    plain = max(usage["input_tokens"] - cached - written, 0)
    total = (plain * rates["entrada"] + cached * rates["entrada_cache"]
             + written * rates.get("escrita_cache", rates["entrada"]) + usage["output_tokens"] * rates["saida"])
    return total / 1_000_000


def _attempt(run_dir: Path, row: dict, source: dict, models: dict, prices: dict | None = None) -> dict:
    folder = run_dir / row["id"]
    record = _json(folder / "record.json") or {}
    generation = record.get("generation") or {}
    evaluation = record.get("reviewed_evaluation") or record.get("evaluation") or {}
    usage = generation.get("usage") or {}
    stats = generation.get("context_stats") or {}
    coverage = evaluation.get("coverage_main") or evaluation.get("coverage_raw") or {}
    return {
        "key": f"{source['id']}/{row['id']}",
        "source": source["id"], "id": row["id"], "order": row["order"],
        "project": row["project"], "target": row["target"], "agent": row["agent"],
        "condition": row["condition"], "repetition": row["repetition"], "phase": row["phase"],
        "state": _state(row), "record_status": row["record_status"],
        "generation_status": row["generation_status"], "evaluation_status": row["evaluation_status"],
        "observable": row["observable"], "approval": row["approval"], "approved": row["approved"],
        "model": models.get(row["agent"]), "agent_version": generation.get("version"),
        "simulated": bool(generation.get("simulated")),
        "started_at": record.get("started_at"), "finished_at": record.get("finished_at"),
        "cases": {"collected": evaluation.get("collected"), "active": evaluation.get("active_count"),
                  "passed": evaluation.get("passed_count"), "skipped": evaluation.get("skipped_count"),
                  "xfail": evaluation.get("xfail_count")},
        "failure_categories": evaluation.get("failure_categories") or [],
        # A cobertura principal só existe para suíte aprovada; a diagnóstica é marcada.
        "coverage": {"line_rate": coverage.get("line_rate"), "branch_rate": coverage.get("branch_rate"),
                     "line_covered": coverage.get("line_covered"), "line_total": coverage.get("line_total"),
                     "branch_covered": coverage.get("branch_covered"), "branch_total": coverage.get("branch_total"),
                     "primary": bool(evaluation.get("coverage_main"))},
        "defects": [{"id": item.get("id"), "status": item.get("status"), "detected": item.get("detected"),
                     "eligible": item.get("eligible")} for item in evaluation.get("defects", [])],
        "detection_rate": row["detection_rate"],
        "seconds": {"preparation": row["preparation_seconds"], "generation": row["generation_seconds"],
                    "evaluation": row["evaluation_seconds"]},
        "cost": estimate_cost({**usage, "input_tokens": generation.get("input_tokens"),
                               "output_tokens": generation.get("output_tokens")},
                              ((prices or {}).get("modelos") or {}).get(models.get(row["agent"]))),
        "tokens": {"input": generation.get("input_tokens"), "output": generation.get("output_tokens"),
                   "cached_input": usage.get("cached_input_tokens"),
                   "reasoning_output": usage.get("reasoning_output_tokens")},
        "context_chars": stats.get("chars_used"), "initial_chars": stats.get("initial_chars"),
        "budget": stats.get("budget"), "tool_calls": stats.get("tool_calls"),
        "detail": {
            "prompt": _text(folder / "prompt.txt"),
            "test_code": _text(folder / "test_generated.py"),
            "response": None if (folder / "test_generated.py").is_file() else _text(folder / "response.txt"),
            "context": _context(folder / "context.json"),
            "tool_log": generation.get("tool_log") or [],
            "cases": _cases(evaluation),
            "review": record.get("review"),
            "error": record.get("error") or record.get("submission_error") or evaluation.get("error"),
            "generation_details": [item for item in generation.get("details") or [] if isinstance(item, str)],
            # Só a posição dentro da execução: a página exportada não expõe caminhos locais.
            "path": f"{source['id']}/{row['id']}",
        },
    }


def _public_config(config: dict) -> dict:
    """Manifesto congelado para exibição, sem caminhos da máquina de quem executou."""
    shown = json.loads(json.dumps(config))
    for agent in shown.get("agents", []):
        for key in ("auth_file", "fixture_dir", "binary"):
            if key in agent:
                agent[key] = "(caminho local omitido)"
    for project in shown.get("projects", []):
        project["root"] = "(pasta do projeto)"
    return shown


def collect(run_dirs: list[tuple[str, Path]], title: str | None, prices: dict | None = None) -> dict:
    """Lê os lotes indicados sem escrever, reavaliar ou exportar relatórios."""
    from ..reporting import read_report

    sources, attempts = [], []
    for label, run_dir in run_dirs:
        run_dir = Path(run_dir).resolve()
        if run_dir.is_symlink() or not (run_dir / "run.json").is_file():
            continue
        header = _json(run_dir / "run.json")
        if not isinstance(header, dict) or "plan" not in header or "config" not in header:
            continue
        report = read_report(run_dir)
        config = header["config"]
        source = {"id": label, "config": _public_config(config), "phase": config.get("phase"),
                  "demonstration": config.get("phase") == "demo", "lock_hash": header.get("lock_hash"),
                  "started_at": header.get("started_at"), "limits": config.get("limits"),
                  "planned": len(header["plan"])}
        models = {agent["id"]: agent.get("model") or agent.get("kind") for agent in config.get("agents", [])}
        sources.append(source)
        attempts.extend(_attempt(run_dir, row, source, models, prices) for row in report["rows"])
    if not sources:
        raise ViewerError("Nenhuma execução encontrada: informe um diretório com run.json ou um projeto com lotes em runs/.")
    if title is None:
        # Sem título explícito: o nome de exibição dos projetos congelados, ou o id deles.
        names = {project.get("name") or project["id"] for source in sources for project in source["config"].get("projects", [])}
        title = " · ".join(sorted(names)) if names else sources[0]["id"]
    return {"title": title, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sources": sources, "attempts": attempts,
            "pricing": prices}


def project_runs(folder: Path, batch: str | None = None) -> list[tuple[str, Path]]:
    """Lotes de projects/NOME/runs/, do mais antigo ao mais recente."""
    runs = folder / "runs"
    if runs.is_symlink() or not runs.is_dir():
        return []
    found = []
    for item in sorted(runs.iterdir()):
        results = item / "results"
        if item.is_symlink() or results.is_symlink() or not (results / "run.json").is_file():
            continue
        if batch is None or item.name == batch:
            found.append((item.name, results))
    return found


def render(data: dict, inline_assets: bool = True) -> str:
    """Página com dados, documentação e diagramas.

    Os dados entram como JSON inerte, nunca como HTML. A documentação é texto
    autoral do pacote. Com `inline_assets`, a biblioteca de diagramas é embutida
    e o arquivo abre sem servidor; sem ele, é pedida ao próprio visualizador.
    """
    payload = json.dumps(data, ensure_ascii=False)
    # Dentro de <script>, só "</" e "<!--" podem encerrar ou alterar o bloco.
    payload = payload.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    template = _PAGE.read_text(encoding="utf-8")
    if template.count("/*__CONTEXTLAB_DATA__*/") != 1:
        raise ViewerError("Modelo da página inválido")
    for marker in ("<!--__CONTEXTLAB_DOCS__-->", "<!--__CONTEXTLAB_MERMAID__-->"):
        if template.count(marker) != 1:
            raise ViewerError("Modelo da página inválido")
    if not inline_assets:
        script = '<script src="/assets/mermaid.min.js"></script>'
    elif _MERMAID.is_file():
        # "</script" dentro da biblioteca encerraria o bloco; a barra escapada é equivalente em JavaScript.
        script = "<script>" + _MERMAID.read_text(encoding="utf-8").replace("</script", "<\\/script") + "</script>"
    else:
        script = ""
    docs = _DOCS.read_text(encoding="utf-8")
    for marker, name in _TOURS.items():
        docs = docs.replace(marker, Path(__file__).with_name(name).read_text(encoding="utf-8"))
    template = template.replace("<!--__CONTEXTLAB_DOCS__-->", docs)
    template = template.replace("<!--__CONTEXTLAB_MERMAID__-->", script)
    return template.replace("/*__CONTEXTLAB_DATA__*/", payload)


REPOSITORY = "https://github.com/lsprdev/contextlab"


def build_site(destination: Path, repository: str = REPOSITORY) -> Path:
    """Site estático só com a documentação, para publicação.

    Usa o mesmo modelo do visualizador, sem registros de execução. A biblioteca
    de diagramas fica em `assets/`, servida pelo mesmo endereço da página.
    """
    destination = Path(destination)
    (destination / "assets").mkdir(parents=True, exist_ok=True)
    data = {"title": "ContextLab", "site": {"repository": repository},
            "sources": [], "attempts": [], "pricing": None}
    (destination / "index.html").write_text(render(data, inline_assets=False), encoding="utf-8")
    if _MERMAID.is_file():
        (destination / "assets" / "mermaid.min.js").write_bytes(_MERMAID.read_bytes())
    return destination / "index.html"


def export(data: dict, destination: Path) -> Path:
    destination = Path(destination)
    if destination.exists():
        raise ViewerError(f"O arquivo já existe: {destination}. Escolha outro nome para preservar o anterior.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render(data), encoding="utf-8")
    return destination


def make_server(load, port: int = 0) -> ThreadingHTTPServer:
    """Servidor local de leitura. `load` é chamado a cada acesso para refletir novos registros."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "ContextLabViewer"

        def log_message(self, *_args):  # Silencioso: o terminal mostra só o endereço.
            pass

        def _send(self, status: int, body: bytes, content_type: str):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for key, value in _SECURITY_HEADERS.items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self):
            # Um Host inesperado indica acesso por outro nome (DNS rebinding).
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host not in {"127.0.0.1", "localhost"}:
                return self._send(403, b"Acesso somente local.", "text/plain; charset=utf-8")
            path = self.path.split("?", 1)[0]
            if path == "/assets/mermaid.min.js" and _MERMAID.is_file():
                return self._send(200, _MERMAID.read_bytes(), "text/javascript; charset=utf-8")
            if path not in {"/", "/data.json"}:
                return self._send(404, b"Nao encontrado.", "text/plain; charset=utf-8")
            try:
                data = load()
            except (ValueError, OSError, KeyError) as exc:
                return self._send(500, f"Falha ao ler os registros: {exc}".encode(), "text/plain; charset=utf-8")
            if path == "/data.json":
                return self._send(200, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")
            self._send(200, render(data, inline_assets=False).encode(), "text/html; charset=utf-8")

        do_HEAD = do_GET

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def serve(load, port: int = 8765, open_browser: bool = True, announce=print) -> None:
    load()  # Falha antes de abrir a porta se não houver o que mostrar.
    try:
        server = make_server(load, port)
    except OSError as exc:
        raise ViewerError(f"Não foi possível usar a porta {port}: {exc}. Tente --port com outro número.") from exc
    address = f"http://127.0.0.1:{server.server_address[1]}/"
    announce(f"Visualizador em {address} (somente leitura). Recarregue a página para ver novos registros; Ctrl+C encerra.")
    if open_browser:
        import webbrowser
        webbrowser.open(address)
    try:
        server.serve_forever()
    finally:
        server.server_close()
