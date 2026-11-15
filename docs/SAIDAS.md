# Como entender os arquivos de uma execução

Cada lote guarda o que foi preparado, o que o agente recebeu e entregou, como
os testes foram executados e qual foi a conclusão. Isso permite investigar
uma falha e conferir a origem dos números usados no TCC. O número de arquivos
vem dessas etapas e da existência de formatos para leitura humana e automática.

Há redundância deliberada: o resultado do avaliador também aparece no registro
da tentativa, e os relatórios resumem esses registros. Você precisa compreender
essas relações, mas pode começar pela CLI e abrir os detalhes quando necessário.

## Comece por estas consultas

```bash
contextlab cambio runs
contextlab cambio show 20261101-221724-9f63ba/01
contextlab cambio show 20261101-221724-9f63ba/01 --code
contextlab cambio show 20261101-221724-9f63ba/01 --json
```

- `runs`: uma linha por tentativa, para localizar o ID e a situação.
- `show`: contagens, tabela por caso e detalhes das falhas na versão original.
- `show --code`: acrescenta o código entregue após os resultados.
- `show --json`: mostra somente a avaliação técnica, para consulta ou processamento.

São consultas: não chamam o agente, não executam testes e não reescrevem saídas.
O `show` usa a avaliação da revisão mais recente quando existir; caso contrário,
usa a avaliação inicial. O comando `review` tem outra finalidade: registra a
inspeção humana e reexecuta a mesma entrega.

## Lote, tentativa, suíte e caso

Um **lote** reúne um plano de execução congelado. Seu nome, como
`20261101-221724-9f63ba`, combina data/hora UTC de criação e um identificador.
Uma **tentativa** combina projeto, função, agente, estratégia e repetição.
O `/01` da CLI identifica sua ordem no plano.

O arquivo entregue contém uma **suíte**, isto é, um conjunto de testes.
Cada combinação de parâmetros de um teste pode produzir um **caso** separado.
Uma geração pode, portanto, resultar em muitos casos. Os 29 casos do piloto
de câmbio vieram de uma única geração; não são 29 gerações do protocolo.

A pasta `cambio__converter_para_brl__codex__L__1` explicita essa combinação:
projeto `cambio`, alvo `converter_para_brl`, agente `codex`, estratégia L,
repetição 1. O identificador longo ajuda a distinguir tentativas dentro do lote.

## O caminho da informação

```text
contextlab.json → validação das referências → protocolo congelado
    → contexto e instrução → agente → resposta e código entregue
    → execução dos testes → avaliação → registro da tentativa → relatórios
```

`projects/cambio/contextlab.json` é a configuração editável para futuros lotes.
As saídas abaixo ficam em `projects/cambio/runs/LOTE/` e registram o que aconteceu.

## 1. Preparação e controle do lote

| Arquivo ou pasta | Para que serve e quando consultar |
|---|---|
| `batch.json` | Situação geral: validação, interrupção ou fim do processamento. Encerrar o lote não significa aprovar suas suítes. |
| `protocol.lock.json` | Preserva configuração, plano, ordem, versões do ambiente e hashes das fontes e do ContextLab. Um hash é uma assinatura calculada dos bytes, usada para detectar mudanças. Consulte para explicar em quais condições o lote foi feito. |
| `results.execution.lock` | Coordena o acesso de processos para impedir duas execuções simultâneas sobre os mesmos resultados. Pode permanecer vazio após o término; sua existência não indica que um processo continua rodando. Não contém métricas. |
| `validation/validation.json` | Consolida a verificação de todos os alvos antes da geração, com identificação do instrumento e do ambiente. |
| `validation/PROJETO__ALVO/validation.json` | Resultado da validação daquele alvo: testes de referência e, quando configurados, testemunhas dos defeitos. |
| `validation/PROJETO__ALVO/reference/` | Relatório e logs da execução dos testes de referência, com a mesma estrutura de `original/` explicada adiante. Esses casos são do pesquisador e não entram nas contagens da suíte gerada. |

Os dois arquivos com `lock` têm funções diferentes: `protocol.lock.json`
descreve as condições congeladas; `results.execution.lock` controla concorrência.
O primeiro **não é uma cópia completa do código ou da imagem Docker**. Reproduzir
o experimento exige preservar também as versões das fontes, dependências e imagem.

## 2. Plano e relatórios do lote

Estes arquivos ficam diretamente em `results/`, acima das pastas das tentativas.

| Arquivo | Para que serve e quando consultar |
|---|---|
| `run.json` | Cópia do protocolo congelado com dados de início da execução. Permite ligar resultados ao plano, incluindo tentativas ainda não iniciadas. |
| `report.md` | Resumo em Markdown para leitura: aprovação, métricas e agrupamentos do lote. É uma boa entrada para acompanhar o conjunto. |
| `results.csv` | Tabela para planilha ou análise, com uma linha por tentativa planejada. Não há uma linha por caso de teste. |
| `report.json` | Versão estruturada do relatório, com linhas, agrupamentos, denominadores e contrastes. Não substitui os logs e relatórios individuais. |

Os três relatórios são derivados dos registros das tentativas. São formatos
distintos dos mesmos resultados, sem representar novas execuções. `run` e
`review` atualizam os relatórios; `runs` e `show` consultam sem gravar.
O detalhe por caso fica na avaliação, e não no CSV atual.

## 3. O que o agente recebeu e entregou

Os caminhos desta seção são relativos a `results/PASTA_DA_TENTATIVA/`.

| Arquivo ou pasta | Para que serve e quando consultar |
|---|---|
| `context.json` | Material preparado para a estratégia: texto inicial, arquivos disponíveis e dados da preparação. Ajuda a conferir qual contexto estava acessível. Em A, estar disponível não significa ter sido lido. |
| `prompt.txt` | Instrução enviada ao agente, incluindo o alvo, os limites da sessão e o contexto inicial. Abra para entender exatamente o pedido de geração. |
| `agent/native.jsonl` | Eventos emitidos pela CLI do agente, um JSON por linha: histórico técnico da sessão e informações de uso quando disponíveis. O adaptador aplica ocultação das credenciais conhecidas antes de salvar. |
| `agent/stderr.txt` | Diagnósticos emitidos pela CLI do agente. Ajuda a investigar falhas de geração. Pode estar vazio. |
| `agent/tool_audit.json` | Auditoria das ferramentas de contexto: consultas, material entregue e uso dos limites. Ajuda a distinguir o que estava disponível do que foi efetivamente consultado. |
| `response.txt` | Resposta final recebida do gerador, antes da extração do código Python. Não é o histórico inteiro da sessão. |
| `test_generated.py` | Código extraído da resposta e preservado como entrega. É o arquivo principal para ler os testes que o agente escreveu. No modo demo, contém a entrega autoral. |
| `record.json` | Registro central da tentativa: identidade, tempos, geração, hash da entrega e avaliação. Quando há revisão, preserva também a avaliação mais recente e as decisões humanas. A CLI e os relatórios consultam esse registro. |

Uma falha anterior à entrega pode deixar só parte desses arquivos. A demonstração
com fixture não chama uma CLI de agente e pode não ter a pasta `agent/`.

## 4. Como a entrega foi avaliada

Esta parte fica em `results/PASTA_DA_TENTATIVA/evaluation/`.

| Arquivo ou pasta | Para que serve e quando consultar |
|---|---|
| `submission/test_generated.py` | Cópia da entrega usada pelo avaliador. Em Docker, é montada para leitura em `/submission/`. Permite conferir quais bytes foram executados. |
| `original/pytest_report.json` | Relatório produzido durante os testes: casos, fases, resultados, exceções, erros de coleta e cobertura da função. É a evidência detalhada de execução. |
| `original/stdout.log` | Texto que o pytest exibiu, incluindo resumo e comparações que falharam. Costuma ser o caminho mais direto para investigar uma falha. |
| `original/stderr.log` | Saída de diagnóstico do processo de avaliação. Um teste que falha pode ter esse arquivo vazio: a falha costuma aparecer em `stdout.log`. |
| `original/instrumentation/contextlab_pytest_plugin.py` | Cópia do componente do ContextLab que observa a execução e mede a cobertura. Não é um teste escrito pelo agente. |
| `original/instrumentation/pytest.ini` | Configuração mínima do executor usada naquela avaliação. Ajuda a manter a execução controlada. |
| `evaluation.json` | Resultado consolidado: contagens, aprovação, cobertura, defeitos e dados brutos da execução. A mesma avaliação é incorporada ao `record.json` pelo executor. |

**Por que há dois `test_generated.py`?** O primeiro é a entrega recebida; o
segundo é a cópia fornecida à avaliação. Eles devem ter o mesmo conteúdo.
Essa separação permite distinguir geração e avaliação. Não são dois testes
criados independentemente nem duas tentativas.

**Por que existe `original/`?** É a execução sobre a versão original do projeto.
Quando há defeitos controlados, a avaliação também pode executar cópias com uma
alteração aplicada por vez. Não significa “testes originais do projeto”: aqui
são os testes gerados rodando no código original.

**Por que o JSON repete o mesmo teste?** O pytest registra preparação (`setup`),
execução (`call`) e finalização (`teardown`). Essas entradas pertencem ao mesmo
caso. O `show` reúne as fases em uma linha; um erro de finalização impede que
o caso apareça como tendo passado, mesmo que sua asserção tenha passado.

As contagens internas `active_count` e `passed_count` referem-se à fase de
chamada dos testes ativos. A tabela do `show` considera o desfecho completo do
caso. Por isso, havendo erro de preparação/finalização, consulte também a coluna
de erros, em vez de interpretar apenas `passed_count` como aprovação integral.
Casos ignorados, marcados `xfail` ou incompletos são apresentados separadamente;
sem evidência por caso, o resultado aparece como indisponível, nunca como zero.

## 5. Pastas que podem aparecer depois

- `reviews/review-001.json`, `review-002.json` etc.: nome do revisor, decisões e
  avaliação de cada revisão. A revisão não autoriza corrigir a entrega.
- `reviews/001/`, `reviews/002/` etc.: execução da revisão, com `submission/`,
  `original/` e `evaluation.json`. A avaliação inicial permanece em `evaluation/`.
- `defects/ID/`: resultados de defeitos controlados quando configurados. Na
  avaliação de uma suíte aprovada, `validation/` verifica a testemunha e
  `generated/` registra como a suíte se comportou na versão alterada.
- `validation/PROJETO__ALVO/ID/`: na preparação do lote, guarda
  `witness_original/` e `witness_mutated/`, as execuções da testemunha antes e
  depois de aplicar o defeito. A validação dentro de `defects/ID/validation/`
  usa esses mesmos nomes.

O piloto de câmbio discutido aqui não tem defeitos configurados nem revisão.
Não se pode deduzir detecção de defeitos a partir dos seus 28 casos passando.

## Exemplo real: como explicar o resultado do piloto

Na tentativa `20261101-221724-9f63ba/01`, houve 29 casos: 28 passaram e um falhou.
O caso de precisão decimal esperava `152345677.62`; o cálculo correto é
`123456789.12 × 1.23 = 151851850.6176`, arredondado para `151851850.62`.
A falha veio da expectativa escrita no teste. Essa conclusão exige conferir
a conta; o `show` apresenta a comparação, sem atribuir automaticamente culpa
ao teste ou à implementação.

No estudo, registre a **reprovação da suíte** e preserve o detalhamento de
**28 casos passando e um falhando**. A proporção de casos que passaram descreve
essa entrega; não mede sozinha a qualidade dos testes nem aumenta o número de
gerações. A aprovação continua exigindo os critérios automáticos e a revisão
humana. Cobertura principal de uma suíte reprovada permanece não aplicável.
Este piloto autoral fica fora da amostra principal de 108 gerações.

Para explicar a arquitetura ao orientador:

> O ContextLab preserva as condições do experimento, o material fornecido ao
> agente, a entrega produzida e as evidências de sua avaliação. Os relatórios
> resumem esses registros, permitindo relacionar cada resultado à geração que
> o produziu e investigar suas falhas.

## Roteiro para estudar sem se perder

1. Leia `prompt.txt` e use `show --code`: relacione o pedido aos testes entregues.
2. Use `show` e consulte `original/stdout.log`: entenda o resultado e a falha.
3. Examine `context.json` e `agent/tool_audit.json`: confira o acesso ao contexto.
4. Leia `record.json` e `evaluation.json`: localize as mesmas informações em dados estruturados.
5. Compare `protocol.lock.json`, `run.json` e os relatórios: ligue a tentativa ao plano.
6. Estude `pytest_report.json` e `instrumentation/`: entenda como as medições são produzidas.

JSON representa campos e listas; JSONL guarda um objeto JSON por linha; CSV é
uma tabela; Markdown (`.md`) é texto formatado; `.txt` e `.log` são registros
textuais; `.py` contém código Python; `.ini` contém configuração do pytest.

Preserve o lote inteiro para manter a ligação entre essas evidências. Ele é
ignorado pelo Git, portanto um push do projeto não arquiva os resultados.
Para uma coleta formal, é necessário arquivar também os lotes e suas versões
de ambiente. Alterar `contextlab.json` só configura execuções futuras; não
edite os locks, as entregas ou os registros antigos para corrigir um resultado.
Consultar resultados antigos com `show` não exige o ambiente original. Revisar
ou retomar envolve execução e exige a implementação e o ambiente compatíveis
com o lock. As cópias locais guardadas durante o desenvolvimento estão descritas
em [Verificação](VERIFICACAO.md).
