# Verificação do ContextLab

Esta verificação cobre o instrumento e um piloto de integração com Codex;
não compara a qualidade de agentes nem testa a hipótese principal.
Atualizada em 1º de novembro de 2026. Cada seção identifica a data da verificação.
Os resultados de 01/10 permanecem históricos e não foram incorporados à matriz principal.

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
