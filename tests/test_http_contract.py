import json
from pathlib import Path

import pytest

from contextlab.manifest import ManifestError, load_config
from contextlab.runner import prompt_for


DEMO = Path(__file__).parent / "fixtures/demo.json"


def save_config(tmp_path, kind, phase="demo"):
    config = load_config(DEMO)
    config["projects"][0]["targets"][0]["test_kind"] = kind
    config["phase"] = phase
    if phase != "demo":
        config["agents"] = [{"id": "codex", "kind": "codex", "model": "fixed-model", "reasoning_effort": "medium"}]
        config["evaluation"]["backend"] = "docker"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    return path


def test_http_is_available_in_pilots_but_not_main_protocol(tmp_path):
    config = load_config(save_config(tmp_path, "http", "pilot"))
    assert config["projects"][0]["targets"][0]["test_kind"] == "http"
    with pytest.raises(ManifestError, match="coleta principal mantém testes unitários"):
        load_config(save_config(tmp_path, "http", "main"))


def test_unknown_test_kind_does_not_silently_generate_unit_tests(tmp_path):
    with pytest.raises(ManifestError, match="test_kind"):
        load_config(save_config(tmp_path, "htpp"))


@pytest.mark.parametrize("context", [{"text": "arquivo permitido"}, {"text": ""}])
def test_http_contract_changes_only_explicit_http_targets(context):
    target = {"path": "api.py", "symbol": "create", "import": "api:create"}
    unit = prompt_for(target, context)
    assert unit == prompt_for({**target, "test_kind": "unit"}, context)
    assert "testes unitários" in unit
    http = prompt_for({**target, "test_kind": "http"}, context)
    assert "integração HTTP" in http
    assert "não chame diretamente o handler" in http
    assert "tmp_path" in http
    assert "Não faça mock das regras nem da persistência" in http
    assert http.endswith(context["text"] or "Consulte as ferramentas para escolher o contexto.\n")


@pytest.mark.parametrize("context", [{"text": "arquivo permitido"}, {"text": ""}])
def test_prompt_states_the_same_session_limits_for_every_strategy(context):
    target = {"path": "api.py", "symbol": "create", "import": "api:create"}
    limits = {"context_chars": 30000, "tool_calls": 20, "generation_seconds": 120, "evaluation_seconds": 20}
    prompt = prompt_for(target, context, limits)
    assert "30000 caracteres de contexto" in prompt
    assert "20 consultas" in prompt
    assert "encerra a sessão sem entrega" in prompt
    # O aviso antecede o material inicial e só aparece quando há limites.
    assert prompt.index("Limites desta sessão") < prompt.index("\n", prompt.index("consultas."))
    if context["text"]:
        assert prompt.index("Limites desta sessão") < prompt.index("Material inicial permitido")
    assert "Limites desta sessão" not in prompt_for(target, context)
