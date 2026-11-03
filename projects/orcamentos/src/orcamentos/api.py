"""Rotas do OrçaAPI. Importar o módulo não cria banco nem inicia servidor."""
import os
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request

from orcamentos.orcamentos import calcular_orcamento
from orcamentos.repositorio import buscar_orcamento, inicializar_banco, salvar_orcamento
from orcamentos.schemas import OrcamentoSalvo, Pedido


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/orcamentos", status_code=201, response_model=OrcamentoSalvo)
def criar_orcamento(pedido: Pedido, request: Request) -> OrcamentoSalvo:
    """Calcula e salva um orçamento. Cupom desconhecido resulta em HTTP 400.

    O FastAPI valida o corpo antes desta chamada e retorna 422 quando inválido.
    Nos testes HTTP, use TestClient(create_app(tmp_path / 'teste.sqlite3')).
    Os dados passam pelas regras reais e são persistidos em SQLite real.
    """
    try:
        resumo = calcular_orcamento(pedido)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return salvar_orcamento(request.app.state.database_path, pedido, resumo)


@router.get("/orcamentos/{orcamento_id}", response_model=OrcamentoSalvo)
def consultar_orcamento(orcamento_id: int, request: Request) -> OrcamentoSalvo:
    result = buscar_orcamento(request.app.state.database_path, orcamento_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    return result


def create_app(database_path: str | Path | None = None) -> FastAPI:
    """Cria uma aplicação independente e inicializa o arquivo SQLite escolhido.

    Para testes, forneça um caminho em tmp_path. Para uso manual, o padrão é
    data/orcamentos.sqlite3 na pasta atual, ou a variável ORCAAPI_DB.
    Use um arquivo por teste; conexões separadas não compartilham ':memory:'.
    """
    path = Path(database_path if database_path is not None else os.environ.get("ORCAAPI_DB", "data/orcamentos.sqlite3"))
    if str(path) == ":memory:":
        raise ValueError("Use um arquivo SQLite; nos testes, crie-o em tmp_path.")
    inicializar_banco(path)
    app = FastAPI(title="OrçaAPI", version="0.1.0", description="Orçamentos didáticos com desconto, frete e SQLite.")
    app.state.database_path = path
    app.include_router(router)
    return app
