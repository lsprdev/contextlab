# OrçaAPI — API didática de orçamentos

O OrçaAPI recebe itens, aplica desconto e frete e salva o orçamento em SQLite.
É o segundo projeto de aprendizado do ContextLab, depois do câmbio, e fica
fora da amostra principal do TCC.

## Abrir e usar

Na raiz do repositório, com Python 3.12 ou posterior:

```bash
source contextlab/.venv/bin/activate
python -m pip install -r projects/orcamentos/requirements-evaluator.txt -e projects/orcamentos
cd projects/orcamentos
uvicorn orcamentos.api:create_app --factory --reload
```

Abra **http://127.0.0.1:8000/docs**. A interface permite enviar requisições sem
instalar outro programa. Em `POST /orcamentos`, clique em **Try it out**,
substitua o corpo pelo exemplo e clique em **Execute**:

```json
{
  "itens": [{"descricao": "Livro", "preco_unitario": "100.00", "quantidade": 2}],
  "cupom": "DESC10",
  "entrega": "padrao"
}
```

O retorno tem status **201**, um `id`, os itens e estes valores:
`subtotal: "200.00"`, `desconto: "20.00"`, `frete: "15.00"`, `total: "195.00"`.
Use o `id` em `GET /orcamentos/{orcamento_id}` para consultar o registro salvo.
`GET /health` informa se a aplicação responde. Encerre o servidor com `Ctrl+C`.

O banco é criado automaticamente em `data/orcamentos.sqlite3`, relativo à pasta
onde o servidor foi iniciado. Os registros permanecem após reiniciar a API.
Para escolher outro arquivo, defina `ORCAAPI_DB` antes de iniciar o servidor.
Dados locais, caches e resultados do ContextLab ficam fora do Git.

## Regras e respostas

| Regra | Comportamento |
|---|---|
| Itens | De 1 a 100; descrição obrigatória, preço positivo até R$ 1.000.000,00 e quantidade inteira de 1 a 1.000. |
| Valores | Preços com até duas casas; envie texto decimal, como `"12.50"`. Valores monetários retornam como texto com duas casas. |
| Cupom | `DESC10` concede 10%; ausência, `null`, `""` ou somente espaços significam sem desconto e são salvos como `null`. Códigos preenchidos devem ser exatos. |
| Entrega padrão | R$ 15,00; gratuita quando o valor **após desconto** for pelo menos R$ 200,00. |
| Entrega expressa | R$ 25,00, independentemente do valor. |
| Arredondamento | Desconto arredondado para centavos, com metades para cima. |
| Erros | Cupom desconhecido: 400; corpo inválido: 422; orçamento inexistente: 404. |

O cálculo usa `Decimal`; o banco armazena dinheiro em centavos inteiros.
Orçamento e itens são gravados na mesma transação: se a gravação falhar,
nenhuma dessas partes fica salva pela metade.

## Entenda o código

```text
POST /orcamentos
  → api.py                 recebe e responde ao HTTP
  → schemas.py             valida os dados de entrada
  → orcamentos.py          calcula subtotal, desconto, frete e total
      → descontos.py       política de cupom
      → frete.py           política de entrega
  → repositorio.py         grava orçamento e itens no SQLite
```

O FastAPI valida o corpo antes de chamar a função da rota. A função
`calcular_orcamento` pode ser usada sem HTTP e sem banco. A fábrica
`create_app(caminho_do_banco)` permite criar uma aplicação com seu próprio
arquivo SQLite. Importar o módulo não inicia o servidor nem cria o banco.

| Pasta/arquivo | Finalidade |
|---|---|
| `src/orcamentos/` | Implementação da aplicação. |
| `tests/` | Testes escritos para conferir cálculos, HTTP, persistência e transação. |
| `tutorial/` | Duas entregas autorais pequenas para verificar o avaliador sem IA. |
| `contextlab.json` | Dois alvos, estratégias L/R/A e configurações do piloto. |
| `Dockerfile.evaluator` / `requirements-evaluator.txt` | Imagem com dependências fixadas para os testes. |
| `runs/` | Lotes do ContextLab; gerada e ignorada pelo Git. |

## Testes e banco de dados

Na raiz do repositório, com o ambiente ativo:

```bash
python -m pytest -q projects/orcamentos/tests
```

Os testes de cálculo chamam a função diretamente. Os testes HTTP usam o
`TestClient` do FastAPI: enviam requisições à aplicação dentro do processo,
sem abrir servidor nem usar internet. Cada teste cria dados fictícios em um
**arquivo SQLite real e temporário**, usando `tmp_path` do pytest. As regras e
o banco não são mockados. Isso também permite testar persistência e isolamento.
O arquivo usado manualmente pelo servidor não participa desses testes.

## Usar no ContextLab

O cadastro já existe; não execute `create` novamente. Há dois exercícios:

| Alvo | Tipo | O que deve ser exercitado |
|---|---|---|
| `calcular_orcamento` | `unit` | Função de cálculo, sem HTTP ou banco. |
| `criar_orcamento` | `http` | Requisição à rota, regras reais e SQLite temporário. |

O plano tem **6 gerações**: 2 alvos × 3 estratégias × 1 repetição. Está em
`pilot`, agora com `gpt-6.1-sol`. O primeiro lote usou `gpt-6-luna`, como o
câmbio, e conserva sua configuração original. O caminho de login
em `auth_file` precisa existir na máquina; contém apenas o caminho, não o token.
Esse exercício não muda a matriz das 108 gerações.

`configure` altera somente o `contextlab.json` deste projeto. Suas opções valem
para os próximos lotes até outra alteração. Como o cadastro já foi entregue
pronto, não era necessário executar o assistente antes do primeiro `run`.
`run --resume LOTE` usa a configuração congelada do lote escolhido, mesmo que
o modelo no JSON atual já tenha mudado. Os detalhes estão na
[referência de configure](../../contextlab/docs/COMANDOS.md#configure-ajustar-o-cadastro).

Comece inspecionando, sem chamar IA:

```bash
contextlab orcamentos plan
contextlab orcamentos context --target calcular_orcamento --condition L
contextlab orcamentos context --target calcular_orcamento --condition R
contextlab orcamentos context --target calcular_orcamento --condition A
```

Em R, o cálculo recebe também as funções de desconto e frete. Em A, o agente
escolhe o que consultar nos sete arquivos de produção permitidos. Testes,
entregas de tutorial, banco e resultados ficam fora desse contexto. R segue
dependências diretas; não recupera recursivamente toda a aplicação.

Com Docker ligado, prepare a imagem específica do projeto:

```bash
contextlab orcamentos setup --dockerfile Dockerfile.evaluator
```

Essa imagem atende aos dois alvos e a todas as repetições. O comando reutiliza
a imagem quando ela já existe; não deixa servidor ou contêiner permanente.
Para iniciar **uma geração real com Codex**, que consome a conta configurada:

```bash
contextlab orcamentos run --max-runs 1
contextlab orcamentos runs
```

O plano é embaralhado: com a semente atual, a primeira tentativa é a rota HTTP
em L. `--max-runs 1` limita tentativas, não casos de teste. Para continuar o
mesmo lote, substitua `LOTE` pelo identificador recebido:

```bash
contextlab orcamentos run --resume LOTE --max-runs 1
contextlab orcamentos show LOTE/01 --code
contextlab orcamentos review LOTE/01
```

Passar na execução ainda exige revisão. No alvo HTTP há uma quarta pergunta:
a entrega realmente fez requisições com regras e SQLite reais? Chamar a função
da rota diretamente não satisfaz esse contrato. A cobertura continua sendo da
função alvo, não de toda a API. Os dois exercícios têm finalidades distintas;
não interprete a média conjunta como comparação de L/R/A. Não há defeitos
artificiais cadastrados neste projeto.

O [registro de preparação](../../docs/historico/ORCAAPI.md) acompanha a validação e a
[inspeção do primeiro lote L/R/A](../../docs/historico/EXERCICIO_ORCAAPI_LRA.md) explica
as seis entregas e as revisões pendentes. A [referência de comandos](../../contextlab/docs/COMANDOS.md)
explica as opções e a [documentação do FastAPI](https://fastapi.tiangolo.com/tutorial/testing/)
detalha o TestClient.

O [segundo piloto, com GPT-6.1 Sol](../../docs/historico/COMPARACAO_MODELOS_ORCAAPI.md),
registra a repetição das seis combinações com o modelo atual, preservando o
lote inicial com Luna.
