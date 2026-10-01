# Verificação da implementação 0.1.0

Esta verificação cobre o instrumento e um piloto de integração com Codex;
não compara a qualidade de agentes nem testa a hipótese principal.
Atualizada em 1º de outubro de 2026.

## Executado

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

## Demonstração de ponta a ponta

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

## Verificação do avaliador Docker

A imagem `contextlab-evaluator:local` foi construída com Python 3.12.11,
pytest 8.4.2 e coverage 7.10.7. As referências e os testemunhos dos dois projetos
também passaram pela validação em contêineres. A fixture de frete executou três
testes com sucesso e cobriu as sete linhas e quatro saídas de ramificação do alvo.
Essa execução separada permaneceu com revisão pendente e não substituiu os
registros congelados da demonstração local. Seus artefatos estão em
`docker-validation/` e `docker-fixture/` no mesmo diretório de execução.

## Piloto real com Codex e GPT-6 Luna

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

## Limites da verificação

- O Codex CLI 0.159.3 foi configurado com `gpt-6-luna` e reutilização de login
  ChatGPT. O catálogo restrito resolveu o bloqueio causado pelas capacidades
  forçadas do catálogo original; a flag `unified_exec` não é usada isoladamente
  como prova da presença ou ausência de comandos. O diagnóstico local confirmou
  a recusa de execução de shell e de leitura fora do pacote, com uma leitura
  permitida como controle positivo.
- Claude Code fica fora do piloto atual por decisão do pesquisador. Seu
  adaptador continua coberto por testes simulados; não houve geração por Claude.
- Opções de cliente e auditoria posterior não comprovam isolamento. O piloto
  precisa verificar os binários e modelos reais, tentativas de acesso proibido,
  configurações e equivalência de ferramentas antes de liberar a coleta.
- Os projetos científicos, os limites calibrados, o inventário principal e as
  216 trajetórias do estudo permanecem pendentes. Os valores dos exemplos são
  parâmetros de demonstração.
- A revisão técnica automatizada da fixture demonstra o fluxo do instrumento;
  a coleta principal ainda exige a inspeção humana prevista no protocolo.

Instruções para repetir a verificação: [README](../README.md).
