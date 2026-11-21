# Verificação do ContextLab

> Registro histórico do período em que o ContextLab ficava dentro do repositório
> do TCC. Caminhos como `contextlab/`, `.build/` e `docs/historico/` referem-se
> àquela organização; os comandos atuais estão no [README](../README.md).

Esta verificação cobre o instrumento e um piloto de integração com Codex;
não compara a qualidade de agentes nem testa a hipótese principal.
Atualizada em 15 de novembro de 2026. Cada seção identifica a data da verificação.
Os resultados de 01/10 permanecem históricos e não foram incorporados à matriz principal.

## Visualizador: novo visual e documentação embutida — 16/11/2026

A página do `serve` foi redesenhada como produto de análise de dados, inspirada
em ferramentas de avaliação de LLMs: faixa de indicadores, comparação lado a
lado das estratégias com o melhor valor destacado, tabela compacta, fonte do
sistema, paleta neutra e cor reservada a L, R, A e à situação. Textos
explicativos viraram dicas. Tem tema claro e escuro e estimativa de custo por
tarifas de API.
Ganhou a seção Documentação, com oito diagramas Mermaid, a referência do
`contextlab.json` e de todos os comandos, e o manifesto congelado do lote com
os caminhos locais omitidos.

- **185 testes passaram** na suíte completa; treze são do visualizador.
- A biblioteca Mermaid 11.4.1 (licença MIT) foi incluída em `viewer/vendor/`,
  com origem e SHA-256 registrados. No modo servidor ela é entregue pelo
  próprio visualizador; na exportação é embutida na página.
- Os oito diagramas foram renderizados em Chromium sem interface, pelo servidor
  local com a política de segurança de conteúdo ativa e pelo arquivo exportado,
  nos temas claro e escuro.
- O servidor continua recusando qualquer outro caminho além da página, dos
  dados e da biblioteca.

## Visualizador web somente leitura — 15/11/2026

Os comandos `contextlab NOME serve` e `contextlab serve RESULTADOS` abrem uma
página local com as tentativas, seus resultados, tokens, tempos, contexto,
consultas e testes gerados; `--export` grava a mesma página em um arquivo.
O visualizador não escreve nos diretórios de resultados nem reavalia entregas.

- **181 testes passaram** na suíte completa; oito são do visualizador.
- Os testes conferem que a leitura não altera nenhum arquivo do lote, que o
  código gerado não escapa do bloco de dados da página, que o servidor recusa
  outros caminhos, escrita e nomes de host externos, e que registros novos
  aparecem sem reiniciar.
- A página foi aberta em Chromium sem interface com os lotes reais de câmbio e
  OrçaAPI: tabela, filtros, visão por função e abas de detalhe.
- O subpacote `viewer/` não entra no hash de implementação. A inclusão do
  comando alterou `cli.py`, `project_cli.py` e `projects.py`, que entram.
- Não houve novas gerações.

## Limites informados no enunciado — 15/11/2026

O enunciado comum passou a informar o limite de caracteres e o de consultas da
sessão e a avisar que ultrapassá-los a encerra sem entrega. O texto é idêntico
em L, R e A e vem dos limites do manifesto. O encerramento ao esgotar um limite
não mudou. A mudança altera o hash da implementação: lotes anteriores continuam
consultáveis, e sua revisão exige a implementação da época.

- **173 testes passaram** na suíte completa do ContextLab.
- O teste novo confere a presença do aviso, sua posição antes do material
  inicial e sua ausência quando nenhum limite é fornecido.
- O manifesto `native-pilot.json` foi removido das fixtures por duplicar
  `codex-pilot.json`; nenhum teste o utilizava.
- Não houve novas gerações.

## Remoção de doctests da visão de geração — 02/11/2026

A regra `doctest-1` omite comandos, continuações e saídas esperadas dos
doctests nas docstrings e nos documentos permitidos. A transformação acontece
antes de montar os contextos L/R ou disponibilizar os arquivos para A.
Descrições e numeração de linhas são preservadas; quebras são normalizadas
para LF. O manifesto registra hashes de origem e de conteúdo preparado,
tamanhos e transformações. Os arquivos fornecidos ao avaliador permanecem
originais. Não houve novas gerações ou alterações na metodologia.

- **171 testes passaram** na suíte completa do ContextLab.
- As regressões verificam ausência dos exemplos no contexto inicial e nas
  ferramentas `read_file` e `search` de L/R/A, incluindo tipos de assinatura
  e dependências recuperadas.
- Foram conferidos docstrings de módulo, classe, função interna e método
  assíncrono; continuações, tracebacks, texto Unicode, literais raw,
  concatenação de strings, newlines escapadas e documentos Markdown.
- A verificação confere preservação do código fora das docstrings, das linhas,
  dos arquivos originais e da cópia de avaliação. Não há importação do projeto
  nem execução dos exemplos. Formatação inválida interrompe a preparação.
- Os 696 arquivos de runs anteriores permaneceram idênticos por SHA-256.
  Nas nove combinações de alvo/estratégia do câmbio e do OrçaAPI conferidas,
  sem doctests, o texto e os arquivos dos contextos permaneceram idênticos aos
  registros dos pilotos. O novo manifesto acrescenta a auditoria da preparação.
- O reconhecimento automático cobre doctests; a revisão de outros formatos
  de exemplos continua fazendo parte da curadoria, conforme o protocolo.

A implementação anterior, de hash
`6bfdda3568c1497df27fce30f6f0bbaf655d10d7e17392d07091e9b20051624a`,
foi preservada em `.build/contextlab-antes-docstrings/src/contextlab/`.
Ela corresponde aos dois lotes OrçaAPI. Seus locks não devem ser atualizados
para a implementação nova. Para revisar uma entrega antiga, use essa cópia
com o ambiente e a imagem originais. Exemplo a partir da raiz do repositório:

```bash
PYTHONPATH=.build/contextlab-antes-docstrings/src \
  contextlab/.venv/bin/python -m contextlab orcamentos review 20261102-181902-a473e6/01
```

Esse comando continua pedindo a inspeção humana; não foi executado nesta etapa.
O inventário anterior dos 696 arquivos de runs fica em
`.build/contextlab-antes-docstrings/preservacao.json`. A nova implementação
exigirá validação e piloto próprios antes da coleta principal. A conferência
dos registros e contextos está em `verificacao.json` nesse mesmo diretório.

## Segundo piloto OrçaAPI, com GPT-6.1 Sol — 02/11/2026

O lote `20261102-181902-a473e6`
repetiu as seis combinações com `gpt-6.1-sol`, mantendo os demais parâmetros
explícitos, fontes, instrumento, ambiente e contextos iniciais. Foram 26, 31,
33, 20, 17 e 52 casos passando, na ordem do plano; as seis suítes aguardam
revisão. O diagnóstico do adaptador passou para o novo modelo. Os 253 arquivos
anteriores foram preservados, sem reparo de entregas nem edição de locks.
Somente o cadastro do OrçaAPI passou a usar Sol; o câmbio continua em Luna.

## Inspeção do piloto OrçaAPI em L/R/A — 02/11/2026

O autor concluiu as seis gerações do lote `20261102-174143-7c4081`.
A inspeção técnica conferiu todas as
entregas e repetiu a avaliação, sem registrar decisões humanas: HTTP/L falhou
na sintaxe; cálculo/R repetiu sete casos passando e um falhando; cálculo/A,
HTTP/R, cálculo/L e HTTP/A repetiram, respectivamente, 7, 4, 4 e 4 casos
passando e seguem pendentes de revisão. Os 104 arquivos originais permaneceram
idênticos. Não houve nova geração, reparo de testes ou alteração do instrumento.

## OrçaAPI: extensão didática de HTTP — 02/11/2026

O registro de preparação descreve os dois alvos, a
imagem própria, a diferença observada entre L/R, a revisão HTTP adicional e
os limites do exercício. Foram aprovadas as verificações de infraestrutura:
158 testes do instrumento e 44 da aplicação, além das referências e de duas
entregas autorais no avaliador Docker. As entregas permanecem sem revisão;
não houve geração do agente nem execução da coleta principal nesta etapa.
As runs anteriores do câmbio foram preservadas.
Após o uso manual, cupom vazio passou a significar ausência de cupom. As
referências atualizadas (29 casos de cálculo e 14 de HTTP) passaram no Docker;
os registros estão em `.build/orcaapi/cupom-vazio/`. As entregas autorais
foram verificadas na preparação inicial, antes dessa correção.

## Exercício real de câmbio em L/R/A — 01/11/2026 (Brasília)

- Lote `20261102-020722-a321cd` (identificação em UTC), com uma repetição por
  estratégia, Codex CLI `0.164.0`, modelo `gpt-6-luna` e avaliação Docker.
  O código do instrumento corresponde ao commit `ce1ee0f`; somente configuração
  de estratégias e documentação foram alteradas nesta etapa.
- Referências validadas; três gerações e avaliações completas, na ordem R/L/A.
  R: 31/31 casos passando. L: 23/23 passando. A: 31/32 passando, com
  `decimal.InvalidOperation` ao calcular a expectativa com precisão dois.
  A execução de A foi reprovada, e L/R aguardam revisão humana. Não houve
  reparo das entregas, revisão automática ou detecção de defeitos configurada.
- L e R receberam exatamente 1.251 caracteres e não fizeram consultas. A teve
  cinco arquivos disponíveis e fez três consultas: listagem, leitura da
  conversão e leitura de `__init__.py`, totalizando 1.603 caracteres entregues.
  O exercício não demonstra superioridade de estratégia nem inclusão de
  dependência adicional em R, pois os contextos L/R são iguais nesse alvo.
- `setup` preparou a imagem porque a tag local estava ausente. A identificação
  efetiva está no novo lock. A coleta principal ainda exige o congelamento do
  ambiente final, verificação das restrições e as demais evidências do protocolo.
- Todos os 89 arquivos das runs anteriores de câmbio permaneceram idênticos,
  conforme conferência por SHA-256. Os resultados novos continuam ignorados
  pelo Git. A suíte de desenvolvimento não foi repetida, pois não houve mudança
  de código; o exercício real executou as referências e as três entregas.
- Roteiro e interpretação do exercício.
  Por decisão do autor, o próximo projeto didático será uma API, antes da
  preparação dos alvos das bibliotecas da amostra principal.

## Consulta por caso e leitura dos arquivos — 01/11/2026

- O autor executou o piloto `20261101-221724-9f63ba/01`, com Codex e avaliação
  Docker, sobre a conversão de câmbio em L. A avaliação registrou **28 casos
  passando e um falhando**. A asserção de precisão decimal esperava
  `152345677.62`, mas o produto arredondado é `151851850.62`. A suíte permanece
  reprovada, sem revisão humana. Esse exercício não integra as 108 gerações.
- O novo `show` consulta a avaliação preservada e apresenta contagens, uma
  tabela por caso e os detalhes das falhas. `--code` inclui a entrega;
  `--json` retorna somente a avaliação. A revisão mantém acesso ao código e ao
  JSON completo, além do resumo. Não houve mudança dos critérios de aprovação,
  dos dados brutos, das métricas exportadas ou da configuração do projeto.
- **151 testes passaram** com `.venv/bin/python -m pytest -q -p no:cacheprovider`
  em `contextlab/`. As regressões verificam agrupamento das fases, parâmetros,
  falhas de preparação/finalização, ignorados, `xfail`, ausência de resultados,
  erros de coleta, revisão mais recente e consultas sem execução ou gravação.
- O comando foi conferido sobre o piloto real e exibiu os 29 casos e a
  comparação que falhou. Os **89 arquivos existentes em `projects/cambio/runs/`**
  foram comparados por SHA-256 antes e depois e permaneceram idênticos. Não houve
  nova geração ou reavaliação desse piloto.
- O [guia dos arquivos de saída](SAIDAS.md) documenta cada etapa e distingue
  cópias, logs, relatórios e controle de execução. README, tutorial, referência,
  guia de avaliação e status apontam para essa explicação. Links locais e
  `git diff --check` foram conferidos. O texto LaTeX não foi alterado.

Antes de editar o instrumento, sua implementação foi copiada para
`.build/contextlab-antes-show-casos/src/`. Os hashes da implementação, das
fontes, da configuração e do lock do piloto foram conferidos com essa cópia.
O ambiente Docker não foi revalidado nesta consulta. Para uma futura revisão,
com o ambiente original disponível, o comando a partir da raiz seria:

```bash
PYTHONPATH=.build/contextlab-antes-show-casos/src contextlab/.venv/bin/python -m contextlab cambio review 20261101-221724-9f63ba/01
```

Esse comando executa testes e registra revisão; não foi executado nesta etapa.
A cópia local conserva a compatibilidade durante o desenvolvimento, mas não
substitui o arquivamento formal da versão do instrumento para a coleta. A nova
implementação gera um hash diferente; não se alteram locks antigos para aceitá-la.

## Preparação da imagem pelo ContextLab — 01/11/2026

- `contextlab NOME setup` verifica o serviço Docker, reutiliza a imagem
  configurada quando presente e constrói a imagem base quando ausente. Uma
  imagem personalizada ausente exige `--dockerfile` relativo ao projeto.
  O cadastro/configuração de piloto indica esse próximo passo. O comando
  prepara a imagem sem executar tentativas, chamar agentes ou mudar o JSON.
- **143 testes do instrumento passaram**, incluindo construção simulada,
  reutilização sem substituir imagem, falhas do Docker/build, receita explícita,
  recusa de caminhos inválidos/digest ausente e integração da CLI sem criar runs.
  A suíte foi executada com `.venv/bin/python -m pytest -q -p no:cacheprovider`
  em `contextlab/`. A aplicação de câmbio não foi alterada.
- `contextlab cambio setup` construiu a imagem real em Docker Desktop; uma
  segunda chamada a partir da pasta `projects/cambio/` reutilizou a imagem.
  A construção aproveitou camadas em cache. Nenhum experimento foi iniciado,
  e o projeto permaneceu configurado como demo local.
- O `.dockerignore` da imagem base limita o contexto de construção ao Dockerfile.
  A preparação usa a CLI oficial de [construção](https://docs.docker.com/reference/cli/docker/buildx/build/)
  e [inspeção](https://docs.docker.com/reference/cli/docker/image/inspect/).
- A implementação anterior foi preservada localmente em
  `.build/contextlab-antes-setup/src/`. Sua compatibilidade com o lock didático
  `20261101-202259-a01d3f` foi conferida. A versão nova muda o hash do instrumento;
  novos lotes usam novos locks. Os registros anteriores não foram reescritos.
- README, tutorial e referência foram atualizados com `setup` e com a distinção
  entre limite de tentativas e quantidade de testes em uma entrega. Links e
  âncoras locais foram conferidos; `git diff --check` passou. O texto LaTeX não
  mudou, portanto não houve nova compilação.

Para revisar a demonstração antiga, mantenha o ambiente original e, a partir
da raiz, use a cópia preservada da implementação:

```bash
PYTHONPATH=.build/contextlab-antes-setup/src contextlab/.venv/bin/python -m contextlab cambio review 20261101-202259-a01d3f/01 --trusted-local
```

Esse comando reavalia a entrega antiga e pede a revisão; não foi executado
nesta verificação. A cópia em `.build/` é local e não substitui versionamento
ou arquivamento formal da implementação antes da coleta principal.

## Referência de comandos — 01/11/2026

- A [referência de comandos](COMANDOS.md) reúne as interfaces por nome e por
  manifesto, com sintaxe, todas as opções, conceitos, exemplos e problemas comuns.
  README geral, README do instrumento, tutorial, guia por manifesto e status
  apontam para esse documento.
- A cobertura das opções de **16 comandos** foi conferida contra os parsers
  reais. **18 chamadas de ajuda** concluíram; **40 exemplos** tiveram a sintaxe
  analisada pelos parsers, sem executar suas ações. Essa conferência não equivale
  a executar os fluxos de piloto ou coleta apresentados nos exemplos.
- Links e âncoras locais foram conferidos. O lock da demonstração existente
  continua compatível. Esta atualização altera somente documentação; não cria
  runs, chama modelos, muda a configuração do projeto ou reavalia entregas.
- `git diff --check` passou. A suíte Python e a compilação LaTeX não foram
  repetidas, pois não houve alteração em código ou no texto da monografia.

## Interface por projeto e câmbio — 01/11/2026

- **131 testes do ContextLab aprovados** com `.venv/bin/python -m pytest -q -p no:cacheprovider`,
  em `contextlab/`, usando Python 3.12.14, pytest 8.4.2, coverage 7.10.7 e Rich 14.1.0.
  Os novos casos cobrem cadastro sem sobrescrita, configuração, seleção de função,
  recusa de caminhos inválidos, planejamento, execução, listagem somente de leitura,
  revisão e retomada sem regenerar a entrega. Referências reprovadas impedem a geração.
- **32 testes da aplicação aprovados** com
  `contextlab/.venv/bin/python -m pytest -q -p no:cacheprovider projects/cambio/tests`,
  na raiz. Cobrem cálculo, arredondamento, entradas inválidas, respostas HTTP
  simuladas, falhas de consulta e navegação do menu. Não dependem da rede.
- As consultas reais de USD/BRL e EUR/BRL passaram pela função `buscar_cotacao`
  usando a [API Frankfurter v2](https://frankfurter.dev/). Esse resultado verifica
  a integração nesta data; as taxas recebidas não são expectativas dos testes.
  O menu foi também exercitado em terminal interativo com `--demo`, incluindo
  consulta, conversão de 10 USD fictícios para 52 BRL e saída.
- O lote local `projects/cambio/runs/20261101-202259-a01d3f/` validou as referências,
  congelou a configuração e avaliou **três testes autorais**, todos passando.
  A tentativa `20261101-202259-a01d3f/01` continua em **aguardando revisão**.
  O lock corresponde à implementação final desta alteração. Não houve geração
  pelo Codex, avaliação Docker desse projeto ou medição de detecção de defeitos.
- R não adiciona material a L na função `converter_para_brl`, pois não há
  dependências diretas locais externas ao arquivo focal. A inspeção informa isso.
  Repetir a entrega fixa nas três condições não produz evidência comparativa.
- As duas execuções de conferência durante a implementação foram preservadas em
  `.build/cambio-audit/execucao-durante-implementacao-*`. Não são registros da
  coleta. Os registros históricos em `contextlab/runs/` não foram alterados.
- Os 19 arquivos de exemplos internos foram movidos para `tests/fixtures/`, com
  alteração apenas do README. Os dez arquivos do antigo `exemplos/loja/` foram
  preservados integralmente em `docs/historico/exemplos/loja/`, na raiz.
  Reproduzir locks anteriores exige restaurar seus caminhos e ambiente originais.

A interface por nome foi verificada para demonstração local e configuração de
piloto, sem chamada ao modelo. Um piloto real com Codex e Docker ainda precisa
validar a versão final. Fava, wger, python-dotenv e python-stdnum permanecem
selecionados, com preparação técnica pendente. Câmbio não integra as 108 gerações.

## Atualização do protocolo — 18/10/2026

- **119 testes automatizados aprovados**, com `python -m pytest -q -p no:cacheprovider`,
  em ambiente virtual Python com pytest 8.4.2 e coverage 7.10.7.
- Aceitação de quatro projetos, três funções por projeto, somente Codex, L/R/A e
  três repetições: **108 gerações únicas**, 9 por função, 27 por projeto e 36 por estratégia.
- Rejeição das matrizes anteriores, de outros agentes na fase `main`, de modelos
  Codex adicionais, da ausência de estratégias e da avaliação principal local.
- Plano reproduzível por semente, com blocos completos de função/repetição e
  sorteio das estratégias dentro deles.
- Aceitação de evidências simuladas de piloto somente Codex nas três estratégias;
  rejeição de condição ausente, modelo divergente e falhas de infraestrutura.
  Esses testes validam as regras do instrumento, não comprovam um piloto real.
- O piloto genérico em `examples/native-pilot.json` e o modelo de evidências
  agora usam somente Codex. Claude permanece como capacidade para trabalhos futuros.

A alteração da implementação exige nova validação e novos locks antes de uma
nova coleta. O piloto de 01/10 e seus artefatos permanecem preservados; não
constituem evidência suficiente para liberar esta versão da coleta principal.

## Testes anteriores — 01/10/2026

- **105 testes automatizados aprovados** em ambiente virtual Python, com pytest
  8.4.2 e coverage 7.10.7, pelo comando `python -m pytest -q`.
- Preparação de L/R/A, extração por AST, aliases, tipos, dependências diretas,
  limites, sanitização, recusas de caminhos e conteúdo repetido contabilizado.
- Transporte MCP real com executável de cliente simulado: ciclo da sessão,
  autenticação isolada, limites, eventos inesperados e encerramento de processos.
- Coleta, execução, asserções, erros, skip/xfail, revisão obrigatória, cobertura
  focal, defeitos, atribuição, timeout e ausência dos testes reservados na suíte gerada.
- Matriz pareada, congelamento, alteração de fontes, retomada sem regeneração,
  bloqueio de execução concorrente e bloqueio de evidências insuficientes para main.
- Importações locais que ocultam definições do módulo, preservação das demais
  importações globais e registro de dependências não resolvidas.
- Recusa de revisão se houver alteração do protocolo, código do ContextLab,
  Python, dependências, imagem Docker ou vínculo da trajetória com o lock.
- Rejeição de ferramentas extras, descoberta adiada, Code Mode, outros servidores
  MCP e ausência de metadados no diagnóstico do cliente Codex.
- Relatórios com todas as trajetórias planejadas, denominadores, pendências,
  infraestrutura, tokens ausentes e peso igual por função nos contrastes.

## Demonstração de ponta a ponta — 01/10/2026

Foi executado o manifesto `examples/demo.json`, em modo local confiável e
sequencial, com os dois projetos autorais. As seis trajetórias produziram entregas
e avaliações completas. As referências e os dois defeitos de fronteira foram
validados por seus testemunhos.

Na revisão técnica da fixture de frete em L, realizada pelo Codex e identificada
como tal no registro, as asserções observadas verificam
valores e exceções, sem mock do alvo ou alteração da produção. Essa suíte foi
aprovada, cobriu as sete linhas executáveis e quatro saídas de ramificação
medidas no alvo e revelou a alteração `peso <= 5` para `peso < 5`: o valor 22,0
divergiu do esperado 17,6 no limite de 5 kg. A atribuição foi registrada após
inspeção da falha. As outras cinco suítes permaneceram com revisão pendente;
o relatório preservou essa distinção, sem transformá-las em reprovações.

A retomada do mesmo diretório processou zero novas trajetórias. CSV, JSON e
Markdown foram gerados. Esses dados são de testes autorais fixos e não constituem
evidência de superioridade de L, R ou A.

Os artefatos locais desta execução estão em
`runs/demo-2026-10-01-fo4lp9l5/`, diretório ignorado pelo Git. O relatório fica em
`run/report.md`, com os dados em `run/report.json` e `run/results.csv`; as duas
revisões da suíte de frete e seus logs permanecem em `run/loja__frete__fixture__L__1/reviews/`.

## Verificação do avaliador Docker — 01/10/2026

A imagem `contextlab-evaluator:local` foi construída com Python 3.12.11,
pytest 8.4.2 e coverage 7.10.7. As referências e os testemunhos dos dois projetos
também passaram pela validação em contêineres. A fixture de frete executou três
testes com sucesso e cobriu as sete linhas e quatro saídas de ramificação do alvo.
Essa execução separada permaneceu com revisão pendente e não substituiu os
registros congelados da demonstração local. Seus artefatos estão em
`docker-validation/` e `docker-fixture/` no mesmo diretório de execução.

## Piloto real com Codex e GPT-6 Luna — 01/10/2026

O manifesto `examples/codex-pilot.json` foi executado em 1º de outubro de 2026,
com Codex CLI 0.159.3, modelo `gpt-6-luna`, login ChatGPT já existente e avaliação
Docker. Nenhuma chave de API ou novo login foi necessário. Claude não participou.
O catálogo restrito tem SHA-256
`7f2ab56d6c62e2593ac99b93f68ffa76a2d63ea69fefcaf192ce0e87f82fe793`.

As seis gerações e avaliações concluíram sem falhas de infraestrutura ou
violações registradas pelo parser. Os testes recebidos foram preservados sem
correções, repetição de geração ou feedback do avaliador ao modelo.

| Projeto | Condição | Casos passando / coletados | Estado da suíte |
|---|---|---:|---|
| agenda | L | 15 / 16 | Reprovada: esperava erro para duração válida de 60 minutos |
| loja | R | 13 / 14 | Reprovada: esperava 19,2 para frete cujo valor é 17,6 |
| loja | A | 12 / 12 | Passou na referência; revisão humana pendente |
| agenda | R | 15 / 16 | Reprovada: esperava erro para duração válida de 90 minutos |
| loja | L | 9 / 10 | Reprovada: esperava 21,6 em um caso cujo resultado é 28,8 |
| agenda | A | 23 / 23 | Passou na referência; revisão humana pendente |

As duas trajetórias A usaram `list_files` e `read_file` pelo MCP. Referências e
testemunhos dos defeitos dos dois projetos foram validados novamente na imagem
Docker reconstruída. As suítes que passaram ainda não têm aprovação nem métricas
principais de cobertura/detecção: passar na referência não substitui a revisão.
Este piloto com duas funções e uma repetição verifica a integração; não permite
concluir superioridade de uma condição de contexto.

Os arquivos estão em `runs/codex-luna-f68ex7p9/`: `pilot.lock.json`, `validation/`
e `run/`, com entregas, eventos nativos, auditoria das ferramentas, logs do Docker
e relatórios CSV/JSON/Markdown. O diretório é local e ignorado pelo Git.

## Limites da verificação de 01/10/2026

- O Codex CLI 0.159.3 foi configurado com `gpt-6-luna` e reutilização de login
  ChatGPT. O catálogo restrito resolveu o bloqueio causado pelas capacidades
  forçadas do catálogo original; a flag `unified_exec` não é usada isoladamente
  como prova da presença ou ausência de comandos. O diagnóstico local confirmou
  a recusa de execução de shell e de leitura fora do pacote, com uma leitura
  permitida como controle positivo.
- Claude Code fica fora do piloto atual e da coleta principal. Seu
  adaptador continua coberto por testes simulados; não houve geração por Claude.
- Opções de cliente e auditoria posterior não comprovam isolamento. O piloto
  precisa verificar o binário e o modelo finais do Codex, tentativas de acesso
  proibido, configurações e ferramentas permitidas em L/R/A antes de liberar a coleta.
- Os projetos científicos, os limites calibrados, o inventário principal e as
  108 trajetórias do estudo permanecem pendentes. Os valores dos exemplos são
  parâmetros de demonstração.
- A revisão técnica automatizada da fixture demonstra o fluxo do instrumento;
  a coleta principal ainda exige a inspeção humana prevista no protocolo.

Instruções para repetir a verificação: [README](../README.md).
