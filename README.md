# ContextLab

O ContextLab é uma ferramenta de linha de comando para conduzir experimentos de
**seleção de contexto na geração de testes unitários por agentes de
programação**. Para cada função escolhida, ele prepara o material que o agente
pode consultar, abre uma sessão do Codex, guarda o teste entregue e o avalia
depois, em um contêiner Docker separado. O ContextLab compara três estratégias:

| Estratégia | O que o agente recebe |
|---|---|
| **Local (L)** | O arquivo da função e os tipos necessários à assinatura. |
| **Recuperado (R)** | O pacote L mais as definições do projeto usadas diretamente pela função, encontradas por análise estática. |
| **Autônomo (A)** | Uma visão preparada do repositório, para o agente decidir o que listar, ler e buscar. |

O agente entrega uma única vez e não recebe erros de execução para corrigir. A
avaliação registra execução, aprovação após revisão humana, cobertura da
função, detecção de defeitos controlados, tempo, *tokens* e consultas. Cada
tentativa fica guardada com a configuração e os hashes de seus materiais, para
conferência posterior.

O ContextLab é o instrumento do Trabalho de Conclusão de Curso *Seleção de
contexto na geração de testes unitários por agentes de programação: uma
avaliação experimental* (Bacharelado em Sistemas de Informação, IFC Campus
Araquari, 2026).

## Requisitos

- **Python 3.11+** em macOS ou Linux (no Windows, use o WSL).
- **Docker**, para avaliar testes gerados por IA. A demonstração não precisa dele.
- **[Codex CLI](https://learn.chatgpt.com/docs/non-interactive-mode)** com login
  próprio, só para pilotos e experimentos com geração real.

## Instalação

```bash
git clone https://github.com/lsprdev/contextlab.git
cd contextlab
```

### Como comando global

Com o [pipx](https://pipx.pypa.io/), o comando `contextlab` fica disponível em
qualquer pasta do sistema:

```bash
pipx install -e .
contextlab --help
```

O `-e` (instalação editável) faz o comando usar o código desta pasta. Uma
alteração no código vale na hora, sem reinstalar. Mantenha a pasta clonada,
porque a imagem base do avaliador é construída a partir do
`Dockerfile.evaluator` dela.

### Em um ambiente virtual

É a forma indicada para rodar a demonstração e os testes do ContextLab:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e . -e ./projects/cambio
```

## Primeiros passos: demonstração sem IA

O projeto didático **câmbio**, em `projects/cambio/`, é uma pequena CLI de
conversão de moedas. Comece conhecendo a aplicação:

```bash
cambio --demo
```

A demonstração do ContextLab usa um teste já escrito, em
`projects/cambio/tutorial/`. Nenhum modelo é chamado. Coloque o projeto em modo
`demo`, com uma tentativa na estratégia L:

```bash
contextlab cambio configure --mode demo --conditions L --repetitions 1
contextlab cambio plan
contextlab cambio context --condition L
```

`plan` mostra as tentativas, e `context` mostra exatamente o que o agente
receberia. Execute e consulte o resultado:

```bash
contextlab cambio run --trusted-local
contextlab cambio runs
contextlab cambio show ID --code
```

`--trusted-local` permite avaliar no seu ambiente um teste escrito por você.
Testes gerados por IA são sempre avaliados no Docker. Passar nos testes deixa a
tentativa **aguardando revisão**, porque a aprovação exige a inspeção humana:

```bash
contextlab cambio review ID
contextlab cambio serve
```

`serve` abre no navegador uma página somente de leitura com as tentativas, os
casos de teste, o contexto entregue, as consultas e o consumo de cada
estratégia.

O [guia do primeiro projeto](docs/PRIMEIRO_PROJETO.md) percorre esse fluxo em
detalhe e mostra como experimentar R e A.

## Piloto com o Codex

Com o Docker ligado e o Codex instalado:

```bash
contextlab cambio configure --mode pilot --conditions L R A --model MODELO --auth-file ~/.codex/auth.json
contextlab cambio setup
contextlab cambio plan
contextlab cambio run --max-runs 1
```

- **`--model`:** fixa o modelo explicitamente.
- **`--auth-file`:** aponta o login do Codex. O ContextLab guarda só o caminho,
  nunca o conteúdo da credencial.
- **`setup`:** prepara a imagem do avaliador.
- **`--max-runs 1`:** processa uma tentativa por vez. Para continuar o mesmo
  lote, use `run --resume LOTE`.

## Usar com o seu projeto

Os comandos por nome procuram uma pasta `projects/` na pasta atual ou acima
dela. Cada projeto fica em `projects/NOME/`, com seu `contextlab.json`:

```bash
mkdir -p projects && cp -r /caminho/do/meu-projeto projects/meu-projeto
contextlab create meu-projeto
contextlab meu-projeto plan
```

`create` encontra as funções do código, sem executá-lo, e grava a configuração
inicial. Projetos com dependências próprias precisam de um Dockerfile, que o
`setup` recebe pela opção `--dockerfile`. Veja [Novos projetos](docs/NOVOS_PROJETOS.md).

Para experimentos com vários projetos, ordem sorteada e congelamento do
protocolo, use a interface por manifesto: `plan`, `doctor`, `prepare`,
`validate`, `freeze`, `run`, `review` e `report`. Ela está descrita em
[Uso por manifesto](docs/USO_POR_MANIFESTO.md).

## Comandos do fluxo por projeto

| Comando | O que faz |
|---|---|
| `contextlab create NOME` | Cadastra uma aplicação Python existente em `projects/NOME/`. |
| `contextlab NOME configure` | Ajusta modo, estratégias, repetições, modelo e imagem. |
| `contextlab NOME setup` | Confere o Docker e prepara ou reutiliza a imagem do avaliador. |
| `contextlab NOME plan` | Mostra as tentativas planejadas, sem chamar o agente. |
| `contextlab NOME context --condition R` | Mostra o contexto de uma estratégia. |
| `contextlab NOME run` | Valida referências, congela a configuração, gera e avalia. |
| `contextlab NOME runs` | Lista as tentativas e suas situações. |
| `contextlab NOME show ID` | Mostra casos e falhas; `--code` inclui a entrega. |
| `contextlab NOME review ID` | Registra a revisão humana e reavalia a mesma entrega. |
| `contextlab NOME serve` | Abre o visualizador; `--export` grava a página em um arquivo. |

Todas as opções estão na [referência de comandos](docs/COMANDOS.md).

## Documentação

| Guia | Conteúdo |
|---|---|
| [Primeiro projeto](docs/PRIMEIRO_PROJETO.md) | Passo a passo com o câmbio. |
| [OrçaAPI](projects/orcamentos/README.md) | Segundo projeto didático: API com FastAPI e SQLite, dependências locais e teste HTTP. |
| [Referência de comandos](docs/COMANDOS.md) | Todos os comandos e opções. |
| [Arquivos de saída](docs/SAIDAS.md) | O que cada arquivo de um lote registra. |
| [Uso por manifesto](docs/USO_POR_MANIFESTO.md) | Protocolo completo, congelamento e relatórios. |
| [Novos projetos](docs/NOVOS_PROJETOS.md) | Como preparar outro projeto Python. |
| [Avaliação e métricas](docs/AVALIACAO.md) | Execução, aprovação, cobertura focal e defeitos. |
| [Adaptadores](docs/ADAPTERS.md) | Integração com o Codex e isolamento da sessão. |
| [Verificações](docs/VERIFICACAO.md) | Registro histórico das verificações do instrumento. |

## Organização do repositório

| Local | Conteúdo |
|---|---|
| `src/contextlab/` | Código da ferramenta. |
| `tests/` | Testes automatizados; `tests/fixtures/` tem projetos e manifestos de teste. |
| `docs/` | Guias de uso e verificação. |
| `site/` | Dockerfile e nginx do site de documentação. |
| `projects/cambio/` | Projeto didático: CLI de câmbio. |
| `projects/orcamentos/` | Projeto didático: OrçaAPI. |
| `projects/*/runs/` | Lotes executados localmente, fora do Git. |

## Experimento do TCC

O experimento principal compara L, R e A com o Codex em quatro projetos Python
públicos, com três funções por projeto e três repetições: **108 tentativas de
geração**.

| Projeto | Tipo | Funções |
|---|---|---|
| Fava 1.30.16 | Aplicação web | `calculate_budget`, `group_entries_by_account`, `find_insert_position` |
| bump-my-version 1.8.1 | Aplicação de linha de comando | `VersionConfig.parse`, `serialize`, `SCMConfig.get_version_from_tag` |
| python-dotenv 1.2.4 | Biblioteca | `parse_value`, `parse_variables`, `resolve_variables` |
| python-stdnum 2.2 | Biblioteca | `br.cpf.validate`, `isbn.validate`, `es.nif.validate` |

O manifesto, os testes de referência, os defeitos controlados e os resultados
do experimento serão publicados neste repositório depois da coleta. O código
dos quatro projetos não é copiado: o manifesto aponta as revisões usadas. Os
projetos didáticos ficam fora da amostra e não servem como evidência do
experimento.

## Site de documentação

A documentação do visualizador também é publicada como site estático em
[contextlab.lspr.dev](https://contextlab.lspr.dev). Ele é gerado a partir das
mesmas páginas do `serve`, sem registros de execução:

```bash
python -m contextlab.viewer.site site-dist   # gera site-dist/index.html
docker compose up --build                    # serve o site com nginx, porta 80 do serviço "site"
```

`site/Dockerfile` gera a página e a entrega por nginx; `docker-compose.yml` é o
arquivo usado na implantação.

## Desenvolvimento

```bash
source .venv/bin/activate
python -m pytest -q -p no:cacheprovider
```

## Licença

[MIT](LICENSE).
