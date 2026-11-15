# ContextLab

O ContextLab organiza experimentos de geração de testes: prepara o contexto,
recebe um teste e o avalia separadamente. Comece pelo projeto **cambio**, já
cadastrado em `projects/cambio/contextlab.json`.

## Qual documentação abrir

- [Primeiro projeto](docs/PRIMEIRO_PROJETO.md): acompanhe uma execução de câmbio, passo a passo.
- [Segundo projeto: OrçaAPI](../projects/orcamentos/README.md): conheça a API com SQLite e prepare exercícios de cálculo e HTTP.
- [Referência de comandos](docs/COMANDOS.md): consulte todos os comandos, opções `--`, exemplos, revisão, uso local e Docker.
- [Arquivos de saída](docs/SAIDAS.md): entenda cada arquivo, as etapas do experimento e como explicar os resultados.
- [Uso por manifesto](docs/USO_POR_MANIFESTO.md): controle as etapas separadamente e prepare o protocolo completo.

## Comece aqui

Na raiz do repositório, prepare o ambiente uma vez:

```bash
python3 -m venv contextlab/.venv
source contextlab/.venv/bin/activate
python -m pip install -e ./contextlab -e ./projects/cambio
```

Nas próximas sessões, basta ativar esse ambiente. Primeiro, conheça a aplicação:

```bash
cambio --demo
```

O menu consulta e converte valores fictícios. Use `cambio` para consultar a
Frankfurter pela internet. A aplicação mostra a data das taxas diárias.

Depois, inspecione o experimento:

```bash
contextlab cambio plan
contextlab cambio context --condition L
```

O plano inicial tem **uma tentativa em L**, para `converter_para_brl`. O modo
`demo` do ContextLab utiliza um teste previamente escrito em `tutorial/`: não
chama IA. Isso permite aprender o fluxo antes de configurar um piloto real.

Após ler esse teste, execute a demonstração local e consulte o resultado:

```bash
contextlab cambio run --trusted-local
contextlab cambio runs
```

`--trusted-local` autoriza executar os testes autorais no ambiente virtual.
Testes produzidos pelo Codex exigem avaliação Docker. Uma tentativa que passa
fica aguardando revisão; aprovação não é automática.

Siga o [guia passo a passo](docs/PRIMEIRO_PROJETO.md) para abrir a entrega,
registrar a revisão e experimentar as três estratégias.

## Como o nome encontra a configuração

```text
contextlab cambio plan
           └── projects/cambio/contextlab.json

contextlab cambio runs
           └── projects/cambio/runs/<lote>/
```

Os comandos procuram `projects/` na pasta atual ou em seus ancestrais. Use-os
na raiz deste repositório ou em suas subpastas. Cada lote conserva configuração,
validação, entregas e resultados. Listar execuções não as repete.

| Comando | O que faz |
|---|---|
| `contextlab create NOME` | Cadastra uma aplicação Python já existente em `projects/NOME/`, sem sobrescrever configuração. |
| `contextlab NOME configure` | Orienta mudanças de modo, estratégias, repetições e modelo. |
| `contextlab NOME setup` | Confere o Docker e prepara ou reutiliza a imagem do avaliador. |
| `contextlab NOME plan` | Mostra as tentativas planejadas. |
| `contextlab NOME context --condition R` | Mostra o contexto de uma estratégia, sem chamar o agente. |
| `contextlab NOME run` | Valida referências, congela a configuração e executa. |
| `contextlab NOME runs` | Lista uma linha por tentativa, incluindo as não iniciadas. |
| `contextlab NOME show LOTE/01` | Mostra contagens, casos e falhas; `--code` inclui a entrega e `--json` exibe a avaliação técnica. |
| `contextlab NOME review LOTE/01` | Solicita a revisão e reavalia a mesma entrega. |

`plan` e `runs` aceitam `--json`. `run --max-runs 1` limita quantas tentativas
pendentes são processadas; `run --resume LOTE` continua o mesmo lote sem
regenerar entregas. O ID completo aparece em `runs`. Os comandos com caminhos de
manifesto continuam disponíveis no [guia completo](docs/USO_POR_MANIFESTO.md).

Para um piloto, o fluxo é `configure` → `setup` → `plan` → `run`. `setup`
substitui a construção manual da imagem: reutiliza uma existente e constrói a
base quando necessário. O Docker precisa estar ligado. Os contêineres de
avaliação continuam sendo criados e removidos pelo `run`, sem serviço permanente
por projeto. Dependências próprias exigem uma imagem/Dockerfile do projeto;
consulte [setup na referência](docs/COMANDOS.md#setup-preparar-a-imagem-do-avaliador).

## Onde encontrar cada coisa

| Local | Conteúdo |
|---|---|
| `../projects/cambio/` | Aplicação de câmbio, configuração e tutorial atual. |
| `../projects/orcamentos/` | OrçaAPI: API didática com SQLite, referências e configuração de piloto. |
| `src/contextlab/` | Código da ferramenta. |
| `tests/` | Testes automatizados do ContextLab. |
| `tests/fixtures/` | Pequenos projetos e manifestos usados pelos testes internos. |
| `docs/` | Guias de uso, avaliação e histórico de verificações. |
| `runs/` | Registros antigos, preservados nos locais originais. |
| `../projects/*/runs/` | Novos lotes executados pela interface por nome. |

Caches e ambientes virtuais são arquivos locais, fora do Git. Os exemplos
antigos de Loja e Agenda agora são fixtures internas dos testes.

## Relação com o TCC

Câmbio é um exercício autoral, fora da amostra. A coleta principal permanece em
**4 projetos × 3 funções × Codex × L/R/A × 3 repetições = 108 gerações**.
Fava, wger, python-dotenv e python-stdnum já foram escolhidos; sua preparação e
validação ainda estão pendentes, conforme o [status do TCC](../docs/STATUS.md).

Os atalhos por nome atendem demonstrações e pilotos de um projeto. O protocolo
principal continua reunindo os quatro projetos no mesmo manifesto, mantendo o
sorteio dos blocos e os critérios de congelamento. Os limites do tutorial não
são uma calibração para a pesquisa. Outros agentes ficam para trabalhos futuros.

## Desenvolvimento e detalhes

Na pasta `contextlab/`, com o ambiente ativado:

```bash
python -m pytest -q -p no:cacheprovider
```

- [Primeiro projeto](docs/PRIMEIRO_PROJETO.md)
- [Referência de todos os comandos e opções](docs/COMANDOS.md)
- [Comandos por manifesto e protocolo completo](docs/USO_POR_MANIFESTO.md)
- [Preparar outros projetos](docs/NOVOS_PROJETOS.md)
- [Avaliação e métricas](docs/AVALIACAO.md)
- [Adaptadores](docs/ADAPTERS.md)
- [Verificações e limites conhecidos](docs/VERIFICACAO.md)
