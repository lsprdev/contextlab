import sqlite3

import pytest
from fastapi.testclient import TestClient

from orcamentos.api import create_app


def payload(**changes):
    return {"itens": [{"descricao": "Livro", "preco_unitario": "100.00", "quantidade": 2}],
            "cupom": "DESC10", "entrega": "padrao", **changes}


def test_cria_consulta_e_persiste_apos_recriar_aplicacao(tmp_path):
    path = tmp_path / "orcamentos.sqlite3"
    with TestClient(create_app(path)) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.post("/orcamentos", json=payload())
        assert response.status_code == 201
        data = response.json()
        assert {k: data[k] for k in ("subtotal", "desconto", "frete", "total")} == {
            "subtotal": "200.00", "desconto": "20.00", "frete": "15.00", "total": "195.00"}
        assert data["itens"] == payload()["itens"]
    with TestClient(create_app(path)) as another:
        restored = another.get(f"/orcamentos/{data['id']}")
        assert restored.status_code == 200
        assert restored.json() == data
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("SELECT total_centavos FROM orcamentos").fetchone() == (19500,)
        assert connection.execute("SELECT quantidade, preco_centavos FROM itens").fetchone() == (2, 10000)
    finally:
        connection.close()


@pytest.mark.parametrize("changes,status", [
    ({"cupom": "INVALIDO"}, 400), ({"itens": []}, 422), ({"entrega": "inexistente"}, 422),
    ({"itens": [{"descricao": "A", "preco_unitario": "-1", "quantidade": 1}]}, 422),
    ({"itens": [{"descricao": "A", "preco_unitario": "10.00", "quantidade": 0}]}, 422),
    ({"campo_extra": "não permitido"}, 422),
])
def test_entrada_invalida_nao_grava_orcamento(tmp_path, changes, status):
    path = tmp_path / "teste.sqlite3"
    with TestClient(create_app(path)) as client:
        assert client.post("/orcamentos", json=payload(**changes)).status_code == status
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("SELECT count(*) FROM orcamentos").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM itens").fetchone() == (0,)
    finally:
        connection.close()


@pytest.mark.parametrize("changes", [{}, {"cupom": None}, {"cupom": ""}, {"cupom": "   "}],
                         ids=["ausente", "null", "vazio", "espacos"])
def test_sem_cupom_cria_e_consulta_orcamento_sem_desconto(tmp_path, changes):
    body = payload()
    body.pop("cupom")
    body.update(changes)
    with TestClient(create_app(tmp_path / "sem-cupom.sqlite3")) as client:
        response = client.post("/orcamentos", json=body)
        assert response.status_code == 201
        data = response.json()
        assert data["cupom"] is None
        assert {key: data[key] for key in ("subtotal", "desconto", "frete", "total")} == {
            "subtotal": "200.00", "desconto": "0.00", "frete": "0.00", "total": "200.00"}
        restored = client.get(f"/orcamentos/{data['id']}")
        assert restored.status_code == 200
        assert restored.json() == data


def test_isola_bancos_e_retorna_404(tmp_path):
    with TestClient(create_app(tmp_path / "um.sqlite3")) as first, TestClient(create_app(tmp_path / "dois.sqlite3")) as second:
        identifier = first.post("/orcamentos", json=payload()).json()["id"]
        assert first.get(f"/orcamentos/{identifier}").status_code == 200
        assert second.get(f"/orcamentos/{identifier}").status_code == 404
        assert second.get("/orcamentos/abc").status_code == 422


def test_grava_texto_literal_e_preserva_ordem_dos_itens(tmp_path):
    items = [{"descricao": "Livro'); DROP TABLE itens; --", "preco_unitario": "2.35", "quantidade": 3},
             {"descricao": "Caneta", "preco_unitario": "1.00", "quantidade": 1}]
    with TestClient(create_app(tmp_path / "teste.sqlite3")) as client:
        response = client.post("/orcamentos", json=payload(itens=items, cupom=None))
        assert response.status_code == 201
        result = client.get(f"/orcamentos/{response.json()['id']}").json()
        assert result["itens"] == items
        assert result["subtotal"] == "8.05"
        assert result["total"] == "23.05"


def test_documentacao_publica_e_contrato(tmp_path):
    with TestClient(create_app(tmp_path / "teste.sqlite3")) as client:
        assert client.get("/docs").status_code == 200
        schema = client.get("/openapi.json").json()
        assert "post" in schema["paths"]["/orcamentos"]
        assert "get" in schema["paths"]["/orcamentos/{orcamento_id}"]
