# Verificação da implementação 0.1.0

Esta verificação demonstra o instrumento, não compara a qualidade de agentes.

## Executado

- **79 testes automatizados aprovados** em ambiente virtual Python, com pytest
  8.4.2 e coverage 7.10.7, pelo comando `python -m pytest -q`.
- Preparação de L/R/A, extração por AST, aliases, tipos, dependências diretas,
  limites, sanitização, recusas de caminhos e conteúdo repetido contabilizado.
- Transporte MCP real com executável de cliente simulado: ciclo da sessão,
  autenticação isolada, limites, eventos inesperados e encerramento de processos.
- Coleta, execução, asserções, erros, skip/xfail, revisão obrigatória, cobertura
  focal, defeitos, atribuição, timeout e ausência dos testes reservados na suíte gerada.
- Matriz pareada, congelamento, alteração de fontes, retomada sem regeneração,
  bloqueio de execução concorrente e bloqueio de evidências insuficientes para main.
- Relatórios com todas as trajetórias planejadas, denominadores, pendências,
  infraestrutura, tokens ausentes e peso igual por função nos contrastes.

## Demonstração de ponta a ponta

Foi executado o manifesto `examples/demo.json`, em modo local confiável e
sequencial, com os dois projetos autorais. As seis trajetórias produziram entregas
e avaliações completas. As referências e os dois defeitos de fronteira foram
validados por seus testemunhos.

Na revisão técnica da fixture de frete em L, as asserções observadas verificam
valores e exceções, sem mock do alvo ou alteração da produção. Essa suíte foi
aprovada, cobriu as sete linhas executáveis e quatro saídas de ramificação
medidas no alvo e revelou a alteração `peso <= 5` para `peso < 5`: o valor 22,0
divergiu do esperado 17,6 no limite de 5 kg. A atribuição foi registrada após
inspeção da falha. As outras cinco suítes permaneceram com revisão pendente;
o relatório preservou essa distinção, sem transformá-las em reprovações.

A retomada do mesmo diretório processou zero novas trajetórias. CSV, JSON e
Markdown foram gerados. Esses dados são de testes autorais fixos e não constituem
evidência de superioridade de L, R ou A.

## Limites da verificação

- Codex e Claude Code não estavam instalados neste ambiente. Seus comandos,
  transporte e tratamento de eventos foram testados com processos simulados;
  não houve geração real, login ou consumo de modelos.
- Docker não estava instalado. O comando de isolamento e o comportamento sem
  Docker foram testados, mas a imagem não foi construída nem executada aqui.
- Opções de cliente e auditoria posterior não comprovam isolamento. O piloto
  precisa verificar os binários e modelos reais, tentativas de acesso proibido,
  configurações e equivalência de ferramentas antes de liberar a coleta.
- Os projetos científicos, os limites calibrados, o inventário principal e as
  216 trajetórias do estudo permanecem pendentes. Os valores dos exemplos são
  parâmetros de demonstração.

Instruções para repetir a verificação: [README](../README.md).
