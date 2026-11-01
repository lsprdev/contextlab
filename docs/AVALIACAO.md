# Operação e interpretação do avaliador

`src/contextlab/evaluation.py` recebe uma submissão já encerrada. Ele não chama
modelos, não repara testes e não devolve feedback ao gerador.

1. **Validar o inventário:** `validate_defects` executa os testes reservados
   contra o original. Cada testemunha deve executar o alvo e passar; sua
   execução contra uma alteração por vez deve falhar durante a chamada do
   teste. Erros de coleta, preparação e infraestrutura e timeouts não tornam
   um defeito elegível. O patch textual deve ter exatamente uma ocorrência.
2. **Preservar e executar a entrega:** a sintaxe é verificada sem executar o
   código. Uma cópia da submissão é executada sozinha por pytest. Os arquivos
   declarados como referências/testemunhas, assim como seus `conftest.py`,
   ficam ausentes desse snapshot; eles existem apenas na validação separada.
3. **Revisar a aprovação:** passar no original e executar o alvo produz uma
   candidatura (`pending_review`). A aprovação exige inspeção humana de
   verificações comportamentais, ausência de mock do próprio alvo e ausência
   de alteração da produção. A verificação de hash e o volume somente leitura
   são controles adicionais; não substituem essa inspeção.
4. **Medir qualidade:** somente uma suíte aprovada recebe `coverage_main`.
   Cada defeito validado é aplicado sozinho em outra cópia limpa. Um teste
   que continua passando marca o defeito como `survived`. Uma asserção ou
   exceção na chamada do teste cria `pending_attribution`: é necessário
   examinar a evidência e registrar a atribuição ao defeito para marcar
   `detected`. Timeout nunca conta automaticamente como detecção.

## Estados e denominadores

| Campo | Interpretação |
| --- | --- |
| `received` / `syntax_ok` | Existência e validade sintática da entrega |
| `collected` | Quantidade de itens coletados pelo pytest |
| `active_started` | Algum item ativo chegou à fase de chamada; itens ignorados e `xfail` não contam |
| `reference_passed` | A suíte submetida passou no projeto original e possui ao menos um item ativo |
| `approval` | `approved`, `pending_review`, `rejected` ou `not_applicable` |
| `coverage_raw` | Medição diagnóstica, inclusive de uma suíte reprovada; não substitui a principal |
| `coverage_main` | Cobertura focal exclusiva de suíte aprovada; caso contrário, `null` |
| `defects_eligible` / `defects_measured` | Inventário elegível e quantidade com resultado conclusivo |
| `detection_rate` | Detectados/elegíveis, somente quando a medição está completa; ausência não vira zero |

Falhas têm categorias distintas: sintaxe, coleta/importação, preparação,
asserção, execução, desmontagem, timeout e infraestrutura. Os JSON preservam
os relatórios de cada fase, a exceção e a mensagem, junto dos logs de execução.
O `show` apresenta um resumo por caso, considerando as três fases em conjunto:
uma chamada que passa e falha na finalização aparece como erro. Isso difere de
`passed_count`, que conta chamadas de testes ativos que passaram. Casos marcados
`xfail` ficam separados, mesmo quando passam. Essas contagens explicam a entrega;
não alteram o critério de aprovação nem tornam casos gerações independentes.
Consulte [Arquivos de saída](SAIDAS.md) para localizar cada evidência.
`pytest_report.json` é descartado antes de cada invocação para impedir que um
relatório antigo seja interpretado como evidência de uma execução interrompida.

## Tempo da avaliação

`total_seconds` mede a duração completa de uma invocação de avaliação, incluindo
preparo das cópias, checagens de dependências, execução no original, validação
das testemunhas e execução dos defeitos, até a gravação do resultado. Ele
existe também para entregas ausentes ou sintaticamente inválidas.
`original.seconds` (também exposto em `seconds` por compatibilidade) mede somente
a execução do pytest original; não representa o custo total de avaliação.
Uma nova revisão que reexecuta a avaliação tem sua própria duração: não inclui
tempo humano de inspeção nem deve apagar o histórico das invocações anteriores.

## Cobertura focal

A instrumentação usa as APIs públicas `analysis2`, `branch_stats` e contextos
do coverage.py. O AST delimita o corpo do alvo, excluindo declarações e corpos
de funções/classes aninhadas. Apenas contextos dos testes ativos entram na
medição: importação/coleta e itens `xfail` não fornecem cobertura principal.

Uma função de uma linha, como `def f(): return 1`, é recusada: sua definição e
seu corpo compartilham a linha, impedindo distinguir importação de chamada por
essa medição. Sem saídas de ramificação, `branch_rate` é `null`. Os mapas de
linhas e saídas devem ser inspecionados no piloto para os alvos escolhidos.

## Ambiente e limites operacionais

Docker é o backend padrão, sem fallback automático. Ele usa rede desabilitada,
sistema de arquivos e entradas somente leitura, saída separada, limite de
processos/memória/CPU, capacidades removidas e `no-new-privileges`. Instale as
dependências fixadas do projeto em uma imagem derivada **antes** da avaliação;
não há instalação pela internet durante a execução.

O backend `local` exige autorização explícita `trusted_local`, um ambiente
virtual com `pytest==8.4.2` e `coverage==7.10.7`, e serve somente para os exemplos
autorais inspecionados. Ele não impede que um teste acesse a máquina hospedeira.
O filho recebe ambiente reduzido, sem credenciais herdadas, e o timeout encerra
seu grupo de processos. Uma interrupção pelo operador também encerra o grupo,
aguarda o filho e remove o contêiner Docker quando aplicável, antes de
propagar a interrupção ao orquestrador. Esse controle usa processos POSIX
(macOS/Linux); Windows nativo não é suportado pelo avaliador.
Pacotes instalados somente no diretório de usuário
não fazem parte desse ambiente reduzido.

Os relatórios são evidência experimental para revisão, não atestação resistente
a código adversarial. O piloto deve verificar a imagem Docker real, as
restrições dos adaptadores e o mapeamento de cobertura antes da coleta.

Documentação usada na implementação:

- [coverage.py 7.10.7 — APIs públicas](https://coverage.readthedocs.io/en/7.10.7/api_coverage.html).
- [pytest — hooks e fases de execução](https://docs.pytest.org/en/stable/reference/reference.html#pytest.hookspec.pytest_runtest_makereport).
