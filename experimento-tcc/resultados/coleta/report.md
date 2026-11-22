# Relatório ContextLab

Fase: `main`. Taxas variam de 0 a 1; `—` significa ausente ou não aplicável.

## Coleta e aprovação

| Projeto | Agente | Condição | Planejadas | Observáveis | Aprovadas / conhecidas | Taxa principal | Pendentes / infra geração | Revisões pendentes |
|---|---|---|---:|---:|---:|---:|---:|---:|
| bump_my_version | codex | A | 9 | 9 | 6 / 9 | 0.667 | 0 / 0 | 0 |
| bump_my_version | codex | L | 9 | 9 | 6 / 9 | 0.667 | 0 / 0 | 0 |
| bump_my_version | codex | R | 9 | 9 | 5 / 9 | 0.556 | 0 / 0 | 0 |
| fava | codex | A | 9 | 9 | 9 / 9 | 1.000 | 0 / 0 | 0 |
| fava | codex | L | 9 | 9 | 6 / 9 | 0.667 | 0 / 0 | 0 |
| fava | codex | R | 9 | 9 | 4 / 9 | 0.444 | 0 / 0 | 0 |
| python_dotenv | codex | A | 9 | 9 | 8 / 9 | 0.889 | 0 / 0 | 0 |
| python_dotenv | codex | L | 9 | 9 | 9 / 9 | 1.000 | 0 / 0 | 0 |
| python_dotenv | codex | R | 9 | 9 | 9 / 9 | 1.000 | 0 / 0 | 0 |
| python_stdnum | codex | A | 9 | 9 | 7 / 9 | 0.778 | 0 / 0 | 0 |
| python_stdnum | codex | L | 9 | 9 | 9 / 9 | 1.000 | 0 / 0 | 0 |
| python_stdnum | codex | R | 9 | 9 | 7 / 9 | 0.778 | 0 / 0 | 0 |

A taxa principal usa gerações observáveis; falhas de infraestrutura de geração são informadas separadamente. Trajetórias ainda não executadas e aprovações sem desfecho mantêm a taxa principal ausente. A taxa entre decisões conhecidas (`approval_rate_known`) tem denominador próprio no JSON. Revisão pendente não equivale a reprovação.

## Qualidade condicionada à aprovação

| Projeto | Agente | Condição | Linhas (n suítes) | Ramificações (n suítes) | Detecção (n suítes) |
|---|---|---|---:|---:|---:|
| bump_my_version | codex | A | 1.000 (6) | 1.000 (3) | 1.000 (6) |
| bump_my_version | codex | L | 1.000 (6) | 1.000 (3) | 1.000 (6) |
| bump_my_version | codex | R | 1.000 (5) | 1.000 (3) | 1.000 (5) |
| fava | codex | A | 1.000 (9) | 1.000 (9) | 1.000 (9) |
| fava | codex | L | 1.000 (6) | 1.000 (6) | 1.000 (6) |
| fava | codex | R | 1.000 (4) | 1.000 (4) | 1.000 (4) |
| python_dotenv | codex | A | 1.000 (8) | 1.000 (8) | 1.000 (8) |
| python_dotenv | codex | L | 1.000 (9) | 1.000 (9) | 1.000 (9) |
| python_dotenv | codex | R | 1.000 (9) | 1.000 (9) | 1.000 (9) |
| python_stdnum | codex | A | 1.000 (7) | 1.000 (7) | 1.000 (7) |
| python_stdnum | codex | L | 1.000 (9) | 1.000 (9) | 1.000 (9) |
| python_stdnum | codex | R | 1.000 (7) | 1.000 (7) | 1.000 (7) |

Cobertura bruta de suítes reprovadas não entra nesta tabela. Funções sem ramificações não recebem zero. Detecção depende da revisão e da medição completa do inventário elegível. Por defeito, saídas inválidas e suítes reprovadas contam zero; infraestrutura de avaliação é excluída e contada à parte. Timeout e atribuição pendente não são convertidos em detecção nem em zero conhecido.

## Comparações pareadas por função

| Agente | Contraste | Métrica | Funções comparáveis / previstas | Diferença média |
|---|---|---|---:|---:|
| codex | L-A | approval_rate | 12 / 12 | 0.000 |
| codex | L-A | line_rate_approved | 10 / 12 | 0.000 |
| codex | L-A | generation_seconds_mean | 12 / 12 | -4.349 |
| codex | R-A | approval_rate | 12 / 12 | -0.139 |
| codex | R-A | line_rate_approved | 10 / 12 | 0.000 |
| codex | R-A | generation_seconds_mean | 12 / 12 | -6.579 |
| codex | R-L | approval_rate | 12 / 12 | -0.139 |
| codex | R-L | line_rate_approved | 9 / 12 | 0.000 |
| codex | R-L | generation_seconds_mean | 12 / 12 | -2.230 |

Cada diferença é calculada na mesma função; a síntese dá peso igual às funções comparáveis. Diferença positiva significa valor maior na condição à esquerda, não necessariamente melhor. A qualidade condicionada à aprovação usa somente funções com medidas comparáveis nos dois braços. As repetições não são tratadas como sujeitos independentes. Resultados detalhados por projeto, função e defeito estão no JSON.

## Recursos e rastreabilidade

`results.csv` contém uma linha por trajetória planejada, inclusive pendentes e falhas. Campos ausentes permanecem vazios; tokens indisponíveis não viram zero. Tempo de preparo, geração e avaliação são registrados separadamente. Caracteres entregues e chamadas de ferramentas vêm da auditoria efetiva; as médias de recursos informam n e completude. `report.json` preserva denominadores, inventário configurado/validado, completude e diferenças por função. Custos de assinatura não são convertidos em preços fictícios por chamada.
