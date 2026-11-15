# Sua primeira execução: câmbio

O objetivo é acompanhar uma função do início ao fim. Esta experiência é
**didática** e não faz parte das 108 gerações do TCC.

Para consultar todas as opções `--` ou entender nomes como fixture, lote e lock,
abra a [referência de comandos](COMANDOS.md). Este guia acompanha uma sequência;
a referência serve para localizar uma dúvida específica.

## 1. Conheça o programa

Na raiz do repositório, após a instalação descrita no [README](../README.md):

```bash
source contextlab/.venv/bin/activate
cambio --demo
```

Escolha consultar, converter e sair. Aqui `--demo` significa cotações fictícias.
Sem essa opção, a aplicação consulta taxas diárias da Frankfurter. A função
`converter_para_brl` recebe valor e cotação; não faz chamadas HTTP.

## 2. Entenda a configuração já criada

Abra [contextlab.json](../../projects/cambio/contextlab.json). Os campos centrais são:

| Campo | Valor inicial e significado |
|---|---|
| `phase` | `demo`: uma entrega previamente escrita substitui a geração por IA. |
| `conditions` | `["L"]`: somente contexto local. |
| `repetitions` | `1`: uma tentativa. |
| `root` | `.`: a pasta que contém a configuração é a raiz da aplicação. |
| `path` | `src/cambio/conversao.py`: arquivo da função. |
| `symbol` | `converter_para_brl`: função selecionada. |
| `reference_tests` | Testes reservados para validar a implementação antes da execução. |
| `defects` | Lista vazia: esta primeira experiência não mede detecção de defeitos. |

A entrega didática está em
[tutorial/cambio__converter_para_brl.py](../../projects/cambio/tutorial/cambio__converter_para_brl.py).
Ela é diferente dos testes de referência. Nenhum desses dois materiais é
fornecido como contexto ao gerador.

O projeto já está cadastrado. Para cadastrar outra aplicação existente em
`projects/NOME/`, use `contextlab create NOME`: o assistente lista as funções
sem executá-las e pede referência, modo, estratégias e repetições. No modo demo,
é necessário fornecer uma entrega autoral em `tutorial/NOME__ID_DO_ALVO.py`.
O comando não cria a aplicação nem escreve automaticamente seus testes.

## 3. Veja o que está prestes a acontecer

```bash
contextlab cambio plan
contextlab cambio context --condition L
```

O primeiro comando mostra uma linha. O segundo mostra o material de leitura.
Nenhum deles chama IA ou executa os testes.

## 4. Execute e encontre a entrega

Depois de inspecionar a entrega didática:

```bash
contextlab cambio run --trusted-local
contextlab cambio runs
```

O ContextLab executa as referências, salva a configuração congelada e avalia a
entrega. `--trusted-local` autoriza a execução desses testes autorais no ambiente
virtual. Esse modo não isola código gerado por IA; pilotos Codex exigem Docker.

Copie o ID completo exibido na tabela, por exemplo `20261101-120000-abcdef/01`,
e substitua `LOTE/01` abaixo:

```bash
contextlab cambio show LOTE/01
contextlab cambio show LOTE/01 --code
contextlab cambio review LOTE/01 --trusted-local
```

O `show` começa pelas contagens, lista cada caso e mostra as falhas registradas.
Com `--code`, acrescenta a entrega para leitura. Para entender todos os arquivos
preservados e as cópias da entrega, consulte [Arquivos de saída](SAIDAS.md).

A revisão apresenta o teste e a avaliação e pede seu nome e três verificações:
asserções de comportamento, função alvo sem substituição e produção preservada.
Responda `yes` somente após conferir. A revisão reavalia a mesma entrega, sem
pedir outra à IA. Até essa etapa, passar nos testes significa **aguardar revisão**.
A lista de defeitos está vazia, então essa métrica ficará não aplicável.

## 5. Experimente as três estratégias

O [exercício real de câmbio em L/R/A](../../docs/historico/EXERCICIO_CAMBIO_LRA.md) registra
um lote já executado com Codex e Docker, com comandos para ler cada entrega e
as consultas do agente. A sequência abaixo continua sendo a demonstração com
fixture; ela não chama o modelo.

```bash
contextlab cambio configure --mode demo --conditions L R A --repetitions 1
contextlab cambio plan
contextlab cambio context --condition R
contextlab cambio run --trusted-local
contextlab cambio runs
```

Será criado outro lote com três tentativas. Os lotes anteriores permanecem
intactos. Nesta função, R não acrescenta material a L: suas dependências são da
biblioteca padrão. Isso é esperado e informado na inspeção. As entregas demo
são iguais nas três condições; seus resultados não demonstram superioridade de
uma estratégia.

Para processar apenas parte de um lote demo, use `run --max-runs 1 --trusted-local`. Para continuar,
use `run --resume LOTE --trusted-local`; não use um `run` novo esperando que ele
retome o anterior. Na listagem, tentativas não iniciadas continuam visíveis.

## 6. Só depois: piloto com Codex

A troca de modo exige modelo explícito, autenticação e Docker preparados. Não
houve geração real com Codex na criação deste tutorial.

```bash
contextlab cambio configure --mode pilot --conditions L R A --repetitions 1 \
  --model IDENTIFICADOR_DO_MODELO --auth-file CAMINHO_DO_LOGIN
```

Substitua os dois valores por sua configuração validada. Se usar `CODEX_API_KEY`,
omita `--auth-file`. O JSON contém somente o caminho do login, nunca a credencial.
Com Docker ligado, prepare a imagem pelo próprio ContextLab:

```bash
contextlab cambio setup
contextlab cambio plan
contextlab cambio run --max-runs 1
```

A imagem base basta para a função de conversão, que depende da biblioteca
padrão; outros alvos podem exigir imagem com dependências adicionais fixadas.
`setup` reutiliza a imagem se ela já existe; não chama o agente nem mantém um
contêiner ativo. `configure` só salva a configuração e indica o próximo passo.
`--max-runs 1` processa uma tentativa do plano; não limita a quantidade de testes
escritos nessa entrega. Com um alvo, somente L e uma repetição, o plano já tem
uma tentativa, então essa opção é dispensável.
O comando `run` do piloto usa o Codex e pode consumir o orçamento da conta. Ele
verifica o adaptador e as referências antes da geração. Não reduz as restrições
se houver incompatibilidade. Consulte [ADAPTERS.md](ADAPTERS.md).

## Arquivos produzidos

```text
projects/cambio/runs/LOTE/
├── batch.json              Situação da preparação/execução
├── protocol.lock.json      Configuração e fontes congeladas
├── validation/             Execução dos testes de referência
└── results/
    ├── run.json            Plano e configuração preservados
    ├── <tentativa>/        Contexto, entrega e avaliação
    ├── results.csv         Uma linha por tentativa planejada
    ├── report.json         Dados completos do relatório
    └── report.md           Relatório para leitura
```

Use `runs` para navegar sem decorar esses caminhos. Consultar a tabela não
altera os arquivos nem repete execuções. Uma falha de preparação é exibida como
lote sem gerações iniciadas. O JSON editável em `projects/cambio/` configura
execuções futuras; não reescreva arquivos congelados para mudar o passado.
O [guia dos arquivos de saída](SAIDAS.md) detalha cada pasta e propõe uma ordem
de leitura para estudar o funcionamento do instrumento.
