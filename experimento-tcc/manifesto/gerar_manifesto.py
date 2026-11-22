"""Gera manifesto/principal.json a partir de defeitos/candidatos.json.

Mantém o manifesto reproduzível: alvos, inclusões, referências e a testemunha
de cada defeito ficam declarados aqui, num só lugar.
"""
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DEFEITOS = {d["id"]: d for d in json.loads((AQUI.parent / "defeitos" / "candidatos.json").read_text())}
R = "tcc_referencia/"

PROJETOS = [
    {"id": "fava", "name": "Fava 1.30.16", "root": "../projetos/fava", "source_roots": ["src"],
     "runtime": ["src/fava/**/*.py"],
     "include": ["src/fava/__init__.py", "src/fava/helpers.py", "src/fava/core/**/*.py",
                 "src/fava/beans/**/*.py", "src/fava/util/**/*.py", "README.rst"],
     "targets": [
        ("calculate_budget", "src/fava/core/budgets.py", "calculate_budget", "fava.core.budgets",
         "test_ref_calculate_budget.py", {"FAV-01-sem-divisao": "test_orcamento_mensal_de_um_dia_e_a_parcela_diaria"}),
        ("group_entries_by_account", "src/fava/core/group_entries.py", "group_entries_by_account", "fava.core.group_entries",
         "test_ref_group_entries_by_account.py", {
             "FAV-02-sem-ordenar": "test_chaves_ficam_em_ordem_alfabetica",
             "FAV-02-transacao-no-lugar-do-par": "test_transacao_aparece_em_cada_conta_como_par_transacao_lancamento"}),
        ("find_insert_position", "src/fava/core/file.py", "find_insert_position", "fava.core.file",
         "test_ref_find_insert_position.py", {
             "FAV-03-data-estrita": "test_opcao_com_mesma_data_da_diretiva_e_ignorada",
             "FAV-03-sem-menos-um": "test_opcao_anterior_que_casa_retorna_arquivo_e_linha_anterior",
             "FAV-03-ordem-crescente": "test_entre_duas_opcoes_vale_a_mais_recente_em_qualquer_ordem"}),
     ]},
    {"id": "bump_my_version", "name": "bump-my-version 1.8.1", "root": "../projetos/bump-my-version", "source_roots": ["."],
     "runtime": ["bumpversion/**/*.py"],
     "include": ["bumpversion/__init__.py", "bumpversion/exceptions.py", "bumpversion/utils.py", "bumpversion/ui.py",
                 "bumpversion/versioning/**/*.py", "bumpversion/scm/**/*.py", "README.md"],
     "targets": [
        ("version_config_parse", "bumpversion/versioning/version_config.py", "VersionConfig.parse",
         "bumpversion.versioning.version_config", "test_ref_version_config_parse.py", {
             "BMV-01-erro-invertido": "test_cadeia_que_nao_corresponde_retorna_none",
             "BMV-01-sem-original": "test_guarda_a_cadeia_original"}),
        ("serialize", "bumpversion/versioning/serialization.py", "serialize",
         "bumpversion.versioning.serialization", "test_ref_serialize.py", {
             "BMV-02-partes-decrescente": "test_patch_zero_usa_o_formato_mais_curto",
             "BMV-02-sem-obrigatorias": "test_patch_diferente_de_zero_exige_o_formato_completo",
             "BMV-02-sem-copia": "test_contexto_do_chamador_nao_e_alterado"}),
        ("get_version_from_tag", "bumpversion/scm/models.py", "SCMConfig.get_version_from_tag",
         "bumpversion.scm.models", "test_ref_get_version_from_tag.py", {
             "BMV-03-sem-escape": "test_prefixo_e_tratado_como_texto_literal",
             "BMV-03-sem-flags": "test_marcacao_verbose_no_inicio_do_padrao_continua_valendo",
             "BMV-03-prefixo-errado": "test_modelo_com_sufixo_usa_so_o_prefixo"}),
     ]},
    {"id": "python_dotenv", "name": "python-dotenv 1.2.4", "root": "../projetos/python-dotenv", "source_roots": ["src"],
     "runtime": ["src/dotenv/**/*.py"],
     "include": ["src/dotenv/**/*.py", "README.md"],
     "targets": [
        ("parse_value", "src/dotenv/parser.py", "parse_value", "dotenv.parser", "test_ref_parse_value.py",
         {"DOT-01-sem-escapes": "test_aspas_duplas_decodificam_quebra_de_linha"}),
        ("parse_variables", "src/dotenv/variables.py", "parse_variables", "dotenv.variables", "test_ref_parse_variables.py",
         {"DOT-02-sem-literal-final": "test_literais_nas_duas_extremidades_e_valor_padrao"}),
        ("resolve_variables", "src/dotenv/main.py", "resolve_variables", "dotenv.main", "test_ref_resolve_variables.py",
         {"DOT-03-override-invertido": "test_conflito_entre_ambiente_e_arquivo_com_override_verdadeiro"}),
     ]},
    {"id": "python_stdnum", "name": "python-stdnum 2.2", "root": "../projetos/python-stdnum", "source_roots": ["."],
     "runtime": ["stdnum/**/*.py", "stdnum/**/*.dat"],
     "include": ["stdnum/__init__.py", "stdnum/exceptions.py", "stdnum/util.py", "stdnum/br/**/*.py",
                 "stdnum/es/**/*.py", "stdnum/isbn.py", "stdnum/ean.py", "stdnum/issn.py", "stdnum/ismn.py", "README.md"],
     "targets": [
        ("br_cpf_validate", "stdnum/br/cpf.py", "validate", "stdnum.br.cpf", "test_ref_cpf_validate.py",
         {"STD-01-sem-verificacao": "test_digito_verificador_errado"}),
        ("isbn_validate", "stdnum/isbn.py", "validate", "stdnum.isbn", "test_ref_isbn_validate.py",
         {"STD-02-ignora-conversao": "test_isbn10_com_conversao_vira_isbn13"}),
        ("es_nif_validate", "stdnum/es/nif.py", "validate", "stdnum.es.nif", "test_ref_nif_validate.py",
         {"STD-03-sem-nie": "test_nie_com_letra_errada_e_erro_de_verificacao"}),
     ]},
]


def projeto(p):
    alvos, referencias = [], []
    for tid, path, symbol, module, ref, witnesses in p["targets"]:
        referencias.append(R + ref)
        defeitos = []
        for did, witness in witnesses.items():
            d = DEFEITOS[did]
            assert d["path"] == path or d["path"].startswith(path.rsplit("/", 1)[0]), did
            defeitos.append({"id": did, "path": d["path"], "old": d["old"], "new": d["new"],
                             "witness": f"{R}{ref}::{witness}"})
        alvos.append({"id": tid, "path": path, "symbol": symbol, "import": f"{module}:{symbol}",
                      "test_kind": "unit", "reference_tests": [R + ref], "defects": defeitos})
    # A visão do agente (include) é restrita; a avaliação precisa do pacote inteiro para importar.
    return {"id": p["id"], "name": p["name"], "root": p["root"], "source_roots": p["source_roots"],
            "include": p["include"], "evaluation_include": p["runtime"] + referencias, "targets": alvos}


# Piloto final: um alvo por projeto, fora da amostra, com a mesma configuração.
PILOTO = {
    "fava": ("parse_budgets", "src/fava/core/budgets.py", "parse_budgets", "fava.core.budgets",
             "piloto/test_piloto_parse_budgets.py"),
    "bump_my_version": ("parse_version", "bumpversion/versioning/serialization.py", "parse_version",
                        "bumpversion.versioning.serialization", "piloto/test_piloto_parse_version.py"),
    "python_dotenv": ("parse_stream", "src/dotenv/parser.py", "parse_stream", "dotenv.parser",
                      "piloto/test_piloto_parse_stream.py"),
    "python_stdnum": ("br_cnpj_validate", "stdnum/br/cnpj.py", "validate", "stdnum.br.cnpj",
                      "piloto/test_piloto_cnpj_validate.py"),
}


def projeto_piloto(p):
    tid, path, symbol, module, ref = PILOTO[p["id"]]
    alvo = {"id": tid, "path": path, "symbol": symbol, "import": f"{module}:{symbol}", "test_kind": "unit",
            "reference_tests": [R + ref], "defects": []}
    return {"id": p["id"], "name": p["name"], "root": p["root"], "source_roots": p["source_roots"],
            "include": p["include"], "evaluation_include": p["runtime"] + [R + ref], "targets": [alvo]}


manifesto = {
    "schema_version": 1, "phase": "main", "seed": 20261121, "conditions": ["L", "R", "A"], "repetitions": 3,
    # Limites provisórios: serão calibrados no piloto final e congelados.
    "limits": {"context_chars": 30000, "tool_calls": 20, "generation_seconds": 300, "evaluation_seconds": 60},
    "agents": [{"id": "codex", "kind": "codex", "model": "gpt-6.2-sol", "reasoning_effort": "medium",
                "auth_file": "~/.codex/auth.json"}],
    # ID imutável da imagem (avaliador/Dockerfile): o Docker Desktop às vezes perde a etiqueta
    # contextlab-tcc-avaliador:1, e o ID garante que a avaliação usa exatamente esta imagem.
    "evaluation": {"backend": "docker", "image": "sha256:5fae9b0d2ee16d23a270dc3650f469a27384f205d9dc4fa5bbde576ab2894f9c"},
    "projects": [projeto(p) for p in PROJETOS],
}
assert sum(len(t["defects"]) for p in manifesto["projects"] for t in p["targets"]) == len(DEFEITOS)
(AQUI / "principal.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n")
piloto = {**manifesto, "phase": "pilot", "repetitions": 1, "projects": [projeto_piloto(p) for p in PROJETOS]}
(AQUI / "piloto.json").write_text(json.dumps(piloto, ensure_ascii=False, indent=2) + "\n")
print("manifesto/principal.json e manifesto/piloto.json gerados")
