# Relatório ContextLab

Fase: `pilot`. Taxas variam de 0 a 1; `—` significa ausente ou não aplicável.

## Coleta e aprovação

| Projeto | Agente | Condição | Planejadas | Observáveis | Aprovadas / conhecidas | Taxa principal | Pendentes / infra geração | Revisões pendentes |
|---|---|---|---:|---:|---:|---:|---:|---:|
| bump_my_version | codex | A | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| bump_my_version | codex | L | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| bump_my_version | codex | R | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| fava | codex | A | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| fava | codex | L | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| fava | codex | R | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| python_dotenv | codex | A | 1 | 1 | 0 / 1 | 0.000 | 0 / 0 | 0 |
| python_dotenv | codex | L | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| python_dotenv | codex | R | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| python_stdnum | codex | A | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| python_stdnum | codex | L | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |
| python_stdnum | codex | R | 1 | 1 | 1 / 1 | 1.000 | 0 / 0 | 0 |

A taxa principal usa gerações observáveis; falhas de infraestrutura de geração são informadas separadamente. Trajetórias ainda não executadas e aprovações sem desfecho mantêm a taxa principal ausente. A taxa entre decisões conhecidas (`approval_rate_known`) tem denominador próprio no JSON. Revisão pendente não equivale a reprovação.

## Qualidade condicionada à aprovação

| Projeto | Agente | Condição | Linhas (n suítes) | Ramificações (n suítes) | Detecção (n suítes) |
|---|---|---|---:|---:|---:|
| bump_my_version | codex | A | 1.000 (1) | 1.000 (1) | — (0) |
| bump_my_version | codex | L | 1.000 (1) | 1.000 (1) | — (0) |
| bump_my_version | codex | R | 1.000 (1) | 1.000 (1) | — (0) |
| fava | codex | A | 1.000 (1) | 1.000 (1) | — (0) |
| fava | codex | L | 1.000 (1) | 1.000 (1) | — (0) |
| fava | codex | R | 1.000 (1) | 1.000 (1) | — (0) |
| python_dotenv | codex | A | — (0) | — (0) | — (0) |
| python_dotenv | codex | L | 1.000 (1) | 1.000 (1) | — (0) |
| python_dotenv | codex | R | 1.000 (1) | 1.000 (1) | — (0) |
| python_stdnum | codex | A | 1.000 (1) | 1.000 (1) | — (0) |
| python_stdnum | codex | L | 1.000 (1) | 1.000 (1) | — (0) |
| python_stdnum | codex | R | 1.000 (1) | 1.000 (1) | — (0) |

Cobertura bruta de suítes reprovadas não entra nesta tabela. Funções sem ramificações não recebem zero. Detecção depende da revisão e da medição completa do inventário elegível. Por defeito, saídas inválidas e suítes reprovadas contam zero; infraestrutura de avaliação é excluída e contada à parte. Timeout e atribuição pendente não são convertidos em detecção nem em zero conhecido.

## Comparações pareadas por função

| Agente | Contraste | Métrica | Funções comparáveis / previstas | Diferença média |
|---|---|---|---:|---:|
| codex | L-A | approval_rate | 4 / 4 | 0.250 |
| codex | L-A | line_rate_approved | 3 / 4 | 0.000 |
| codex | L-A | generation_seconds_mean | 4 / 4 | -1.382 |
| codex | R-A | approval_rate | 4 / 4 | 0.250 |
| codex | R-A | line_rate_approved | 3 / 4 | 0.000 |
| codex | R-A | generation_seconds_mean | 4 / 4 | 14.718 |
| codex | R-L | approval_rate | 4 / 4 | 0.000 |
| codex | R-L | line_rate_approved | 4 / 4 | 0.000 |
| codex | R-L | generation_seconds_mean | 4 / 4 | 16.100 |

Cada diferença é calculada na mesma função; a síntese dá peso igual às funções comparáveis. Diferença positiva significa valor maior na condição à esquerda, não necessariamente melhor. A qualidade condicionada à aprovação usa somente funções com medidas comparáveis nos dois braços. As repetições não são tratadas como sujeitos independentes. Resultados detalhados por projeto, função e defeito estão no JSON.

## Recursos e rastreabilidade

`results.csv` contém uma linha por trajetória planejada, inclusive pendentes e falhas. Campos ausentes permanecem vazios; tokens indisponíveis não viram zero. Tempo de preparo, geração e avaliação são registrados separadamente. Caracteres entregues e chamadas de ferramentas vêm da auditoria efetiva; as médias de recursos informam n e completude. `report.json` preserva denominadores, inventário configurado/validado, completude e diferenças por função. Custos de assinatura não são convertidos em preços fictícios por chamada.
