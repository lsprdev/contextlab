import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from contextlab.cli import main
from contextlab.viewer import ViewerError, build_site, collect, export, make_server, project_runs, render

HOSTILE = 'def test_x():\n    assert "</script><script>alert(1)</script><!--" != ""\n'


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")


def _run(root: Path) -> Path:
    """Execução mínima: uma tentativa avaliada, uma inválida e uma ainda não iniciada."""
    plan = [{"id": f"p__f__codex__{condition}__1", "order": order, "project": "p", "target": "f",
             "agent": "codex", "condition": condition, "repetition": 1}
            for order, condition in enumerate(("L", "R", "A"), 1)]
    _write(root / "run.json", {
        "config": {"phase": "pilot", "limits": {"context_chars": 1000, "tool_calls": 5},
                   "agents": [{"id": "codex", "kind": "codex", "model": "modelo-x"}],
                   "projects": [{"id": "p", "targets": [{"id": "f", "defects": []}]}]},
        "plan": plan, "lock_hash": "abc", "started_at": "2026-11-15T12:00:00+00:00"})
    first = root / plan[0]["id"]
    _write(first / "record.json", {
        "status": "finished", "preparation_seconds": 0.1, "started_at": "2026-11-15T12:00:01+00:00",
        "generation": {"status": "completed", "seconds": 12.5, "input_tokens": 900, "output_tokens": 300,
                       "version": "codex-cli 9", "usage": {"cached_input_tokens": 400, "reasoning_output_tokens": 20},
                       "context_stats": {"chars_used": 700, "initial_chars": 500, "budget": 1000, "tool_calls": 1},
                       "tool_log": [{"index": 1, "tool": "read_file", "arguments": {"path": "a.py"},
                                     "status": "ok", "delivered_chars": 200, "chars_after": 700}]},
        "evaluation": {"status": "completed", "approval": "pending_review", "approved": False,
                       "active_started": True, "reference_passed": False, "collected": 2,
                       "active_count": 2, "passed_count": 1, "failure_categories": ["assertion_failure"],
                       "coverage_raw": {"line_rate": 0.5, "line_covered": 1, "line_total": 2, "branch_total": 0},
                       "total_seconds": 1.5, "defects": [],
                       "original": {"raw": {"reports": [
                           {"nodeid": "::test_ok", "when": "setup", "outcome": "passed"},
                           {"nodeid": "::test_ok", "when": "call", "outcome": "passed"},
                           {"nodeid": "::test_bad", "when": "call", "outcome": "failed",
                            "exception": "AssertionError", "message": "assert 1 == 2"}]}}}})
    _write(first / "test_generated.py", HOSTILE)
    _write(first / "prompt.txt", "Gere testes.")
    _write(first / "context.json", {"text": "### a.py\nVALOR = 1\n", "files": {"a.py": "VALOR = 1\n"},
                                    "snippets": [{"key": "a.py", "reason": "focal_file", "text": "VALOR = 1\n"}],
                                    "unresolved": [], "omitted": [], "equal_to_local": False})
    _write(root / plan[1]["id"] / "record.json", {
        "status": "invalid_submission", "submission_error": "Resposta vazia",
        "generation": {"status": "completed", "seconds": 3.0, "input_tokens": None, "output_tokens": None}})
    return root


def _listing(root: Path):
    return sorted((path.relative_to(root).as_posix(), path.stat().st_mtime_ns) for path in root.rglob("*"))


def test_collect_reads_records_without_writing(tmp_path):
    run = _run(tmp_path / "run")
    before = _listing(run)
    data = collect([("lote", run)], "exemplo")
    assert _listing(run) == before
    by_condition = {item["condition"]: item for item in data["attempts"]}
    assert [by_condition[c]["state"] for c in ("L", "R", "A")] == ["aguardando revisão", "reprovada", "pendente"]
    local = by_condition["L"]
    assert local["tokens"] == {"input": 900, "output": 300, "cached_input": 400, "reasoning_output": 20}
    assert local["model"] == "modelo-x" and local["tool_calls"] == 1 and local["context_chars"] == 700
    assert local["coverage"]["line_rate"] == 0.5 and local["coverage"]["primary"] is False
    assert {case["name"]: case["outcome"] for case in local["detail"]["cases"]} == {"test_ok": "passed", "test_bad": "failed"}
    assert local["detail"]["test_code"] == HOSTILE
    assert by_condition["R"]["detail"]["error"] == "Resposta vazia"
    # Tokens ausentes permanecem ausentes; a página não os converte em zero.
    assert by_condition["R"]["tokens"]["input"] is None
    assert str(tmp_path) not in json.dumps(data)


def test_generated_code_cannot_break_out_of_the_data_block(tmp_path):
    page = render(collect([("lote", _run(tmp_path / "run"))], "exemplo"))
    start = page.index('<script type="application/json" id="data">') + len('<script type="application/json" id="data">')
    block = page[start:page.index("</script>", start)]
    assert "<" not in block
    assert json.loads(block)["attempts"][0]["detail"]["test_code"] == HOSTILE
    assert "alert(1)" in block  # preservado como texto, apenas escapado


def test_export_never_overwrites(tmp_path):
    data = collect([("lote", _run(tmp_path / "run"))], "exemplo")
    destination = export(data, tmp_path / "saida" / "pagina.html")
    assert destination.read_text(encoding="utf-8").startswith("<!doctype html>")
    with pytest.raises(ViewerError, match="já existe"):
        export(data, destination)


def test_empty_or_missing_runs_are_reported(tmp_path):
    with pytest.raises(ViewerError, match="Nenhuma execução"):
        collect([("vazio", tmp_path)], "x")
    assert project_runs(tmp_path) == []


def test_project_runs_lists_batches_and_filters(tmp_path):
    _run(tmp_path / "runs" / "b1" / "results")
    _run(tmp_path / "runs" / "b2" / "results")
    (tmp_path / "runs" / "incompleto").mkdir()
    assert [name for name, _ in project_runs(tmp_path)] == ["b1", "b2"]
    assert [name for name, _ in project_runs(tmp_path, "b2")] == ["b2"]


def test_server_is_local_read_only_and_reflects_new_records(tmp_path):
    run = _run(tmp_path / "run")
    server = make_server(lambda: collect([("lote", run)], "exemplo"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(base + "/") as response:
            assert response.status == 200
            assert "default-src 'none'" in response.headers["Content-Security-Policy"]
            assert response.read().decode().startswith("<!doctype html>")
        with urllib.request.urlopen(base + "/data.json") as response:
            assert len(json.loads(response.read())["attempts"]) == 3
        for path in ("/run.json", "/../run.json", "/lote/p__f__codex__L__1/test_generated.py"):
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + path)
            assert error.value.code == 404
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(base + "/", data=b"x", method="POST"))
        assert error.value.code == 501
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(urllib.request.Request(base + "/", headers={"Host": "exemplo.invalid"}))
        assert error.value.code == 403
        # Um registro novo aparece no acesso seguinte, sem reiniciar o servidor.
        _write(run / "p__f__codex__A__1" / "record.json", {
            "status": "infrastructure_error", "generation": {"status": "infrastructure_error"}})
        with urllib.request.urlopen(base + "/data.json") as response:
            states = {item["condition"]: item["state"] for item in json.loads(response.read())["attempts"]}
        assert states["A"] == "infraestrutura"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_cli_exports_from_a_results_directory(tmp_path, capsys):
    run = _run(tmp_path / "run")
    destination = tmp_path / "pagina.html"
    assert main(["serve", str(run), "--export", str(destination)]) == 0
    assert destination.is_file() and "Página gravada" in capsys.readouterr().out
    assert main(["serve", str(tmp_path / "ausente"), "--export", str(tmp_path / "outra.html")]) == 2


def test_viewer_files_are_outside_the_frozen_implementation_hash():
    """Mudanças de apresentação não devem invalidar pilotos nem protocolos congelados."""
    import contextlab.viewer as viewer

    package = Path(viewer.__file__).parent.parent
    hashed = set(package.glob("*.py"))  # mesma seleção de manifest.implementation_hash
    assert package / "cli.py" in hashed
    assert Path(viewer.__file__) not in hashed
    assert Path(viewer.__file__).with_name("page.html").is_file()


def test_cost_is_an_estimate_by_token_category_and_stays_absent_without_data(tmp_path):
    from contextlab.viewer import estimate_cost, load_prices

    rates = {"entrada": 2.0, "entrada_cache": 0.1, "escrita_cache": 2.5, "saida": 10.0}
    usage = {"input_tokens": 1_000_000, "cached_input_tokens": 400_000, "cache_write_input_tokens": 100_000,
             "output_tokens": 50_000, "reasoning_output_tokens": 20_000}
    # 500 mil sem cache, 400 mil lidos do cache e 100 mil escritos; raciocínio já está na saída.
    assert estimate_cost(usage, rates) == pytest.approx(1.0 + 0.04 + 0.25 + 0.5)
    assert estimate_cost(usage, None) is None
    assert estimate_cost({"input_tokens": None, "output_tokens": 10}, rates) is None

    prices = tmp_path / "precos.json"
    _write(prices, {"moeda": "USD", "fonte": "https://exemplo.invalid", "consulta": "2026-11-15",
                    "modelos": {"modelo-x": rates}})
    data = collect([("lote", _run(tmp_path / "run"))], "exemplo", load_prices(prices))
    by_condition = {item["condition"]: item for item in data["attempts"]}
    assert by_condition["L"]["cost"] == pytest.approx((500 * 2.0 + 400 * 0.1 + 300 * 10.0) / 1_000_000)
    assert by_condition["R"]["cost"] is None  # tokens ausentes não viram custo zero
    assert data["pricing"]["consulta"] == "2026-11-15"
    assert collect([("lote", tmp_path / "run")], "exemplo")["pricing"] is None

    _write(prices, {"modelos": {"modelo-x": {"entrada": -1, "entrada_cache": 0, "saida": 1}}})
    with pytest.raises(ViewerError, match="tarifas inválido"):
        load_prices(prices)


def test_page_embeds_documentation_and_optional_diagram_library(tmp_path):
    data = collect([("lote", _run(tmp_path / "run"))], "exemplo")
    standalone = render(data)
    served = render(data, inline_assets=False)
    for page in (standalone, served):
        assert "__CONTEXTLAB_" not in page
        for section in ("doc-visao", "doc-contexto", "doc-geracao", "doc-avaliacao", "doc-revisao",
                        "doc-json", "doc-comandos", "doc-arquivos", "doc-passos"):
            assert f'id="{section}"' in page
        assert page.count('class="mermaid-src"') >= 6
        # A animação do passo a passo vem embutida, com as logos em SVG local.
        assert page.count('id="tour"') == 1 and 'id="tour-docker"' in page and 'id="tour-python"' in page
        # O motor vem uma vez, antes das duas animações que o usam.
        assert page.count("window.contextlabTour =") == 1 and page.count('id="tour-contexto"') == 1
        assert page.index("window.contextlabTour =") < page.index('id="tour-contexto"') < page.index('id="tour"')
    # A página exportada abre sem servidor; a servida pede a biblioteca ao próprio visualizador.
    assert '<script src="/assets/mermaid.min.js"></script>' in served
    assert "/assets/mermaid.min.js" not in standalone and len(standalone) > len(served) + 1_000_000
    assert "http://" not in served.split("<script>", 1)[1] and "https://cdn" not in served


def test_frozen_config_is_shown_without_local_paths(tmp_path):
    run = _run(tmp_path / "run")
    header = json.loads((run / "run.json").read_text())
    header["config"]["agents"][0]["auth_file"] = str(tmp_path / "segredo" / "auth.json")
    header["config"]["projects"][0]["root"] = str(tmp_path / "projeto")
    _write(run / "run.json", header)
    data = collect([("lote", run)], "exemplo")
    shown = data["sources"][0]["config"]
    assert shown["agents"][0]["auth_file"] == "(caminho local omitido)"
    assert shown["projects"][0]["root"] == "(pasta do projeto)"
    assert shown["agents"][0]["model"] == "modelo-x" and shown["limits"]["tool_calls"] == 5
    assert str(tmp_path) not in json.dumps(data)


def test_server_offers_only_the_bundled_diagram_library(tmp_path):
    run = _run(tmp_path / "run")
    server = make_server(lambda: collect([("lote", run)], "exemplo"))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urllib.request.urlopen(base + "/assets/mermaid.min.js") as response:
            assert response.headers["Content-Type"].startswith("text/javascript")
            assert len(response.read()) > 1_000_000
        with urllib.request.urlopen(base + "/") as response:
            assert "script-src 'self' 'unsafe-inline'" in response.headers["Content-Security-Policy"]
            assert '<script src="/assets/mermaid.min.js"></script>' in response.read().decode()
        for path in ("/assets/", "/assets/outro.js", "/assets/../__init__.py"):
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(base + path)
            assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_display_name_titles_the_page_and_never_replaces_the_identifier(tmp_path):
    from contextlab.manifest import ManifestError, load_config

    run = _run(tmp_path / "run")
    header = json.loads((run / "run.json").read_text())
    header["config"]["projects"][0]["name"] = "Projeto Ç"
    _write(run / "run.json", header)
    data = collect([("lote", run)], None)
    assert data["title"] == "Projeto Ç"
    assert {a["project"] for a in data["attempts"]} == {"p"}

    config = json.loads(Path(__file__).with_name("fixtures").joinpath("demo.json").read_text())
    config["projects"][0]["name"] = ""
    manifest = Path(__file__).with_name("fixtures") / "tmp-nome-vazio.json"
    try:
        manifest.write_text(json.dumps(config))
        with pytest.raises(ManifestError, match="name deve ser"):
            load_config(manifest)
    finally:
        manifest.unlink(missing_ok=True)


def test_build_site_publishes_only_documentation(tmp_path):
    index = build_site(tmp_path / "site")
    html = index.read_text(encoding="utf-8")
    data = json.loads(html.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0])
    assert data["site"] == {"repository": "https://github.com/lsprdev/contextlab"}
    assert data["attempts"] == [] and data["sources"] == []
    assert 'id="doc-visao"' in html and 'id="doc-comandos"' in html
    assert '<script src="/assets/mermaid.min.js"></script>' in html
    assert (tmp_path / "site" / "assets" / "mermaid.min.js").is_file()
    assert "/Users/" not in html
    # Sem a tela de execuções nem o tema decidido tarde: nada pisca ao abrir.
    assert 'id="nav-runs"' not in html and '<main id="view-runs" hidden>' in html
    assert '<main id="view-docs">' in html and '<body class="site">' in html
    assert html.index("contextlab-tema") < html.index("<style>")


def test_build_site_with_experiment_adds_page_without_local_data(tmp_path):
    root = Path(__file__).resolve().parents[1] / "experimento-tcc"
    if not (root / "resultados" / "coleta" / "tentativas").is_dir():
        pytest.skip("Material do experimento ausente")
    html = build_site(tmp_path / "site", experiment=root).read_text(encoding="utf-8")
    data = json.loads(html.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0])
    attempts = data["experiment"]["attempts"]
    assert len(attempts) == 108 and sum(a["approved"] for a in attempts) == 85
    assert '<button id="nav-exp">Experimento</button>' in html and 'id="view-exp"' in html
    serialized = json.dumps(data["experiment"])
    assert "/Users/" not in serialized and "/Volumes/" not in serialized and "test_code" not in serialized
