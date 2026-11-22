"""Triagem para a revisão humana: extrai de cada suíte aguardando revisão os
sinais dos critérios (asserções, simulação do alvo, dublês, produção intacta).
Não decide nada; aponta o que ler com atenção."""
import ast, json, re, sys
from pathlib import Path

lote = Path(sys.argv[1])
MOCK = re.compile(r"monkeypatch\.(setattr|setitem|delattr)|mock\.patch|patch\(|patch\.object|MagicMock|Mock\(|mocker\.|create_autospec")
for rec in sorted(lote.glob("*/record.json")):
    r = json.loads(rec.read_text()); e = r.get("evaluation") or {}
    if e.get("approval") != "pending_review":
        continue
    src = (rec.parent / "test_generated.py").read_text()
    tree = ast.parse(src)
    tests = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")]
    def checks(fn):
        s = ast.get_source_segment(src, fn) or ""
        return bool(re.search(r"\bassert\b|pytest\.raises|pytest\.warns|\.assert_\w+\(", s))
    no_assert = [t.name for t in tests if not checks(t)]
    trivial = re.findall(r"assert\s+(True|1)\b", src)
    skips = re.findall(r"pytest\.(skip|xfail)|@pytest\.mark\.(skip|xfail)", src)
    mocks = [l.strip() for l in src.splitlines() if MOCK.search(l)]
    sym = r["target"]
    target_sym = {"version_config_parse": "parse", "br_cpf_validate": "validate", "isbn_validate": "validate",
                  "es_nif_validate": "validate", "get_version_from_tag": "get_version_from_tag"}.get(sym, sym)
    target_mocked = [l for l in mocks if re.search(rf"['\".]{re.escape(target_sym)}['\"]?", l)]
    o = e.get("original") or {}
    print(json.dumps({"id": rec.parent.name, "testes": len(tests), "sem_assercao": no_assert[:5],
                      "triviais": len(trivial), "skip_xfail": len(skips), "dubles": mocks[:6],
                      "alvo_simulado?": target_mocked, "producao_intacta": o.get("production_unchanged"),
                      "alvo_executado": (e.get("coverage_raw") or {}).get("executed")}, ensure_ascii=False))
