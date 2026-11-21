# Referência de comandos do ContextLab

Use este documento para consultar a sintaxe e as opções. Para acompanhar uma
execução explicada do início ao fim, siga [Primeiro projeto](PRIMEIRO_PROJETO.md).
As duas interfaces abaixo usam o mesmo instrumento:

- **Por projeto:** `contextlab cambio run`. Localiza a configuração pelo nome e
  organiza os resultados automaticamente. Atende demonstrações e pilotos.
- **Por manifesto:** `contextlab run ARQUIVO.lock.json --out PASTA`. Você informa
  os caminhos e executa as etapas separadamente. Também atende a coleta principal.

## Índice

- [Preparar o terminal](#preparar-o-terminal)
- [Entender a sintaxe](#entender-a-sintaxe)
- [Conceitos e configuração](#conceitos-e-configuração)
- [Comandos por projeto](#comandos-por-projeto)
- [Execução local e Docker](#execução-local-e-docker)
- [Comandos por manifesto](#comandos-por-manifesto)
- [Sequências de uso](#sequências-de-uso)
- [Resultados e problemas comuns](#resultados-e-problemas-comuns)

## Preparar o terminal

Com a instalação do [README](../README.md) concluída, ative o ambiente a partir
da raiz do repositório em cada novo terminal:

```bash
source .venv/bin/activate
```

`contextlab` e `python -m contextlab` iniciam a mesma ferramenta. Os comandos
por nome funcionam na raiz do repositório e em suas subpastas: procuram
`projects/` na pasta atual e nas pastas acima. Os caminhos nos comandos por
manifesto são relativos ao diretório atual, salvo quando absolutos.

## Entender a sintaxe

```bash
contextlab cambio run --trusted-local --max-runs 1
```

| Parte | Significado |
|---|---|
| `contextlab` | Programa a executar. |
| `cambio` | Nome da aplicação cadastrada. |
| `run` | Ação: iniciar uma execução. |
| `--trusted-local` | Opção sem valor: autorizar a demonstração local nesta chamada. |
| `--max-runs 1` | Opção com valor: processar no máximo uma tentativa nesta chamada. |

Cada comando aceita suas próprias opções. Não escreva `true` depois de opções
como `--trusted-local` ou `--json`. Opções como `--repetitions` exigem um valor.
Para nomes com espaços, use aspas, por exemplo `--reviewer "Seu nome"`.
Uma barra `\` no fim da linha apenas continua o mesmo comando na linha seguinte.

Todos os comandos aceitam `-h` ou `--help`; a ajuda não executa o experimento:

```bash
contextlab --help
contextlab create --help
contextlab cambio --help
contextlab cambio run --help
contextlab cambio review --help
```

Neste guia, substitua `NOME`, `LOTE`, `ID`, `MODELO` e caminhos em maiúsculas por
valores reais. `LOTE` é a pasta de uma execução, como `20261101-202259-a01d3f`.
`ID` é uma tentativa dentro dela, como `20261101-202259-a01d3f/01`.
Copie os identificadores da tabela de `runs`; `/01` não faz parte do nome do lote.

## Conceitos e configuração

| Termo | Significado no ContextLab |
|---|---|
| Projeto | Aplicação a estudar, como `cambio`. |
| Alvo | Função ou método para o qual serão produzidos testes. |
| Estratégia | L: arquivo focal e tipos necessários; R: L mais dependências diretas locais; A: exploração dos materiais permitidos. |
| Tentativa | Uma combinação de projeto, alvo, agente, estratégia e repetição. Pode conter vários testes. |
| Lote | Plano congelado e registros de um comando `run`. |
| `demo` / `fixture` | Modo de demonstração / adaptador que carrega testes previamente escritos. Não chama IA; serve para aprendizado e verificação do instrumento. |
| `pilot` | Ensaio com o agente real antes da coleta principal. |
| `main` | Coleta principal do TCC: quatro projetos, três alvos por projeto, Codex, L/R/A e três repetições, totalizando 108 tentativas. |
| Revisão | Inspeção dos testes pelo responsável, registrada antes de aprovar a suíte. |
| Lock | Arquivo que preserva configuração, ordem, fontes e identificação do ambiente de uma execução. |

O nome `cambio` aponta para
[projects/cambio/contextlab.json](../../projects/cambio/contextlab.json).
O JSON é o manifesto do projeto. Os campos mais usados são:

| Campo | O que configura |
|---|---|
| `phase`, `conditions`, `repetitions` | Modo, estratégias e número de repetições. |
| `agents` | Adaptador, modelo e configuração de geração; em demo, pasta das entregas fixas. |
| `evaluation` | Avaliação `local` ou `docker` e imagem a usar quando for Docker. |
| `projects[].root` | Raiz do código, relativa ao JSON; no cadastro por nome é `.`. |
| `targets[].path` / `symbol` / `import` | Arquivo da função, seu nome e o caminho de importação. |
| `targets[].test_kind` | `unit` por padrão; `http` muda o contrato para o exercício FastAPI/SQLite e exige revisão adicional. HTTP é permitido apenas fora de `main`. |
| `reference_tests` | Testes reservados para validar o projeto. |
| `defects` | Alterações controladas a avaliar; vazio no primeiro tutorial. |
| `include` / `evaluation_include` | Arquivos candidatos ao contexto / arquivos necessários à avaliação. |
| `source_roots`, `limits`, `seed` | Raízes de importação, limites da execução e semente da ordem do plano. |

`targets` pertence a cada item de `projects`; referências e defeitos pertencem
a cada alvo. A CLI lê a função no código: ela não precisa ser copiada para o JSON.
Campos avançados, dependências e defeitos são explicados em
[Preparar outros projetos](NOVOS_PROJETOS.md). Alterar o JSON configura lotes
futuros; não altera os locks ou resultados anteriores.

## Comandos por projeto

### create: cadastrar uma aplicação

```bash
contextlab create NOME
```

A pasta `projects/NOME/` e o código Python precisam existir. Use nomes como
`cambio` ou `meu-projeto`, começando por letra minúscula e sem espaços; nomes de
comandos são reservados. O cadastro encontra funções sem executá-las e pergunta
qual selecionar, quais referências usar, modo, estratégias e repetições.
Ele grava `contextlab.json` e recusa sobrescrever um cadastro existente.

| Opção específica de `create` | Uso |
|---|---|
| `--target ARQUIVO:SIMBOLO` | Selecionar diretamente; exemplo: `src/cambio/conversao.py:converter_para_brl`. Métodos usam `Classe.metodo`. |
| `--reference CAMINHO` | Teste reservado, relativo ao projeto. Pode repetir a opção para vários arquivos ou casos pytest, como `tests/test_calculo.py::test_zero`. |
| `--fixture-dir PASTA` | Pasta das entregas demo, relativa ao projeto; padrão `tutorial`. |

No modo demo, a entrega `PASTA/NOME__ID_DO_ALVO.py` já precisa existir. `create`
cadastra um alvo; ele não cria a aplicação nem escreve testes. Para cadastrar
mais alvos ou ajustar as listas de arquivos, edite o JSON e confira com `plan`
e `context`. O projeto `cambio` deste repositório já está cadastrado.

### configure: ajustar o cadastro

```bash
contextlab cambio configure
contextlab cambio configure --conditions L R A --repetitions 3
```

A configuração é **por projeto e persistente**: `contextlab cambio configure`
edita `projects/cambio/contextlab.json`; `contextlab orcamentos configure`
edita `projects/orcamentos/contextlab.json`. Ela vale para todos os alvos e
novos lotes daquele projeto até ser alterada novamente. Não é uma preferência
global do ContextLab nem precisa ser refeita a cada execução.
O modelo escolhido no chat ou nas preferências pessoais do Codex também não
altera esse JSON: o adaptador passa o modelo do manifesto explicitamente.

Um cadastro entregue pronto no repositório já pode ser usado por `run`, mesmo
sem passar pelo assistente `configure`. Foi assim no OrçaAPI: seu JSON inicial
foi criado com as opções do piloto, incluindo `gpt-6-luna`. A configuração não
foi herdada automaticamente do câmbio.

Para trocar somente o modelo de um projeto, mantendo suas demais opções:

```bash
contextlab orcamentos configure --model IDENTIFICADOR_DO_MODELO
contextlab orcamentos plan
```

Um novo `run` usa esse JSON e congela uma cópia no lote. `run --resume LOTE`
e `review` usam a configuração congelada daquele lote, incluindo o modelo
original. Para comparar modelos, crie outro lote; não edite seus locks.
Mudar o modelo não exige outra imagem Docker: ela contém as dependências da
aplicação e do avaliador. `setup` pode conferir e reutilizar a mesma imagem.

Sem opções, abre perguntas no terminal. Com opções, altera os valores informados
e mantém os demais, solicitando dados que faltarem, como o modelo ao mudar para
piloto. As mudanças são validadas antes de substituir o JSON.

Estas opções são aceitas por **`create` e `configure`**:

| Opção | Valores e comportamento |
|---|---|
| `--mode demo` ou `--mode pilot` | Demonstração com fixture ou piloto Codex. O assistente sugere `demo` no cadastro; `main` usa o fluxo por manifesto. |
| `--conditions L R A` | Uma ou mais estratégias distintas, separadas por espaços. No cadastro interativo, a pergunta usa vírgulas e sugere `L`. |
| `--repetitions NUMERO` | Inteiro positivo; o cadastro interativo sugere `1`. |
| `--model MODELO` | Identificador explícito do modelo do Codex para `pilot`; solicitado se faltar. |
| `--auth-file CAMINHO` | Caminho do arquivo privado de autenticação do piloto. Prefira caminho absoluto; relativo é resolvido a partir do JSON. Não coloque o conteúdo da credencial no projeto. |
| `--image IMAGEM` | Imagem Docker do avaliador. O cadastro usa `contextlab-evaluator:local` quando omitida. A opção não constrói a imagem. |

`configure` escolhe avaliação local para demo e Docker para pilot, indicando
`setup` como próximo passo do piloto. Ele não constrói imagens nem inicia
contêineres. Ao voltar de
pilot para demo, espera as entregas em `tutorial/`. Sem terminal interativo,
forneça os valores necessários pelas opções; a CLI informa quando falta algum.

### setup: preparar a imagem do avaliador

```bash
contextlab cambio setup
```

Verifica se o Docker está disponível e procura a imagem definida em
`evaluation.image`. Se ela existe, reutiliza sem reconstruir. Se a imagem base
`contextlab-evaluator:local` está ausente, constrói usando o Dockerfile do
ContextLab. A construção pode baixar dependências e mostra o progresso do Docker.
Ela não chama o agente, executa testes, altera o JSON ou cria runs.

| Opção | Uso |
|---|---|
| `--dockerfile CAMINHO` | Receita personalizada relativa à pasta do projeto. Usada somente se a imagem configurada estiver ausente. O contexto de construção é a pasta do projeto. |

Para dependências próprias, prepare um Dockerfile com versões fixadas e escolha
uma tag específica; exemplo para uma aplicação `NOME`:

```bash
contextlab NOME configure --image contextlab-nome:v1
contextlab NOME setup --dockerfile Dockerfile.evaluator
```

A receita deve instalar Python, pytest 8.4.2, coverage 7.10.7 e as dependências
necessárias. O ContextLab não infere nem instala dependências automaticamente.
Use `.dockerignore` no projeto para excluir ambientes, resultados e arquivos
privados da construção. A imagem base já tem um contexto reduzido ao Dockerfile.
Sem receita explícita, `setup` não constrói uma imagem personalizada ausente.

O comando funciona também antes de mudar de demo para pilot, mas mantém o modo
atual. Docker desligado produz uma mensagem para iniciar o serviço; `setup`
não abre o Docker Desktop. Para mudar uma receita, escolha uma nova tag com
`configure --image` e execute `setup --dockerfile`; imagens existentes são
preservadas. Uma reconstrução não garante o mesmo hash de uma imagem antiga.
Uma referência por digest ausente precisa ser restaurada, não reconstruída com
outro conteúdo. A preparação da imagem não substitui a validação dos testes de
referência realizada por `run`.

### plan: consultar o que será executado

```bash
contextlab cambio plan
contextlab cambio plan --json
```

Lê a configuração atual e mostra função, agente, estratégia, repetição e ordem.
Não inicia geração nem executa testes. `--json` troca a tabela por dados JSON.
O plano de um lote antigo permanece no `run.json` daquele lote.

### context: inspecionar o material disponível

```bash
contextlab cambio context --condition L
contextlab cambio context --condition R --target converter_para_brl
```

| Opção | Uso |
|---|---|
| `--condition L`, `R` ou `A` | Estratégia a inspecionar; padrão `L`. |
| `--target ID_DO_ALVO` | ID declarado no JSON; necessário quando houver mais de um alvo. |

L e R mostram o texto preparado; A mostra a lista de arquivos disponíveis para
exploração. O comando não chama o agente nem executa a função. Inspecionar uma
estratégia não a adiciona ao plano: isso é feito por `configure --conditions`.
Em `converter_para_brl`, R é igual a L porque não há dependência direta local
fora do arquivo focal. A CLI informa essa igualdade.

### run: executar ou continuar um lote

```bash
contextlab cambio run --trusted-local
contextlab cambio run --trusted-local --max-runs 1
contextlab cambio run --resume LOTE --trusted-local --max-runs 1
```

Os exemplos acima são para demo local. Em pilot, use `contextlab cambio run`
com Docker disponível e a configuração do agente validada.

| Opção | Uso |
|---|---|
| `--trusted-local` | Autorizar os testes autorais de uma demonstração local nesta chamada. |
| `--max-runs NUMERO` | Processar no máximo esse número positivo de tentativas ainda não registradas. Sem a opção, processa as restantes. Não é o número de funções `test_*`. |
| `--resume LOTE` | Usar o lock e os registros desse lote. Sem a opção, cria um lote novo. |

Um lote novo valida referências e defeitos, congela configuração e fontes,
processa as tentativas e exporta relatórios. Em piloto, também verifica o
adaptador antes da geração. Resultados ficam em `projects/NOME/runs/LOTE/`.
`--max-runs` limita as tentativas processadas, sem reduzir o plano ou a validação.

Por exemplo, um alvo × L/R/A × três repetições produz nove tentativas.
`--max-runs 1` processa uma delas e deixa oito sem iniciar. A entrega dessa
tentativa pode conter vários testes. Com somente L e uma repetição, o plano já
tem uma tentativa; nesse caso, `--max-runs 1` é redundante. Para continuar um
lote parcial, use `--resume LOTE`, sem iniciar um novo `run` independente.

A retomada conserva o plano antigo, mesmo que o JSON editável tenha mudado.
Ela pula tentativas que já possuem registro, inclusive falhas e interrupções;
não pede outra entrega para substituir uma tentativa malsucedida. Retomada e
revisão exigem as fontes e o ambiente compatíveis com o lock.

### runs: consultar as tentativas registradas

```bash
contextlab cambio runs
contextlab cambio runs --json
```

Mostra tentativas de todos os lotes, incluindo as planejadas ainda não iniciadas.
`--json` retorna os registros das tentativas com mais campos. A consulta não
executa testes nem reescreve relatórios. A tabela também avisa quando um lote
falhou na preparação e ainda não tem tentativas; esse aviso não integra a lista
JSON de tentativas. **`run` executa; `runs` consulta.**

### show: abrir uma tentativa

```bash
contextlab cambio show ID
contextlab cambio show ID --code
contextlab cambio show ID --json
```

Use o ID completo da tabela, com `/01`, `/02` etc. Mostra primeiro as contagens
(por exemplo, “28 passaram · 1 falhou”), depois uma tabela por caso e os detalhes
das falhas. Reúne preparação, execução e finalização do mesmo caso; testes
parametrizados permanecem em linhas separadas. Ignorados, marcados `xfail`,
erros e resultados incompletos ficam separados dos casos que passaram.
Sem evidência disponível, não inventa contagens ou resultados.

`--code` acrescenta o código entregue após a avaliação. `--json` retorna somente
o JSON da avaliação mais recente; as duas opções são alternativas. A avaliação
inicial é usada quando não existe revisão. Não executa testes nem modifica
registros, e pode consultar lotes antigos sem restaurar seu ambiente.
Uma tentativa ainda não iniciada não tem registro para abrir.
Veja o [guia dos arquivos de saída](SAIDAS.md) para relacionar a tela às evidências.

### serve: explorar as execuções no navegador

```bash
contextlab cambio serve
contextlab cambio serve --batch LOTE
contextlab cambio serve --export cambio.html
contextlab serve RESULTADOS
```

Abre uma página local com as tentativas registradas. A primeira forma reúne
todos os lotes de `projects/NOME/runs/`; `--batch` restringe a um lote. A última
forma pertence ao fluxo por manifesto e recebe o diretório de resultados que
contém `run.json`, como o da coleta principal.

A página mostra, por estratégia, aprovações, tokens de entrada e saída,
caracteres entregues, consultas e tempo de geração. A tabela pode ser filtrada
por execução, modelo, projeto, função, estratégia, repetição e situação, e
ordenada por qualquer coluna. A visão **Por função** coloca L, R e A lado a lado
para o mesmo alvo e a mesma repetição. Ao abrir uma tentativa, as abas mostram
o resumo, os casos de teste com as mensagens de falha, o teste gerado, o
contexto entregue, as consultas feitas pelo agente e o enunciado.

| Opção | Efeito |
|---|---|
| `--port N` | Porta local; o padrão é 8765. |
| `--no-open` | Não abre o navegador; o endereço aparece no terminal. |
| `--prices TARIFAS.json` | Estima o custo de cada tentativa a partir de tarifas de API. No fluxo por projeto, `projects/NOME/precos.json` é usado automaticamente quando existe. |
| `--export ARQUIVO.html` | Grava uma página única, com os dados embutidos, em vez de iniciar o servidor. Não sobrescreve um arquivo existente. |

Tem duas seções, alternadas no topo. **Execuções** traz uma faixa de indicadores
com o valor de cada estratégia, a comparação lado a lado de L, R e A (o melhor
valor de cada medida fica destacado), os filtros e a tabela das tentativas.
Definições e avisos ficam em dicas, ao passar o mouse sobre o ícone ⓘ.
**Documentação** explica o funcionamento do instrumento com diagramas: o fluxo
de uma tentativa, a preparação do contexto, a sessão do Codex, o contêiner de
avaliação, a revisão e os defeitos. Ela também descreve cada campo do
`contextlab.json`, mostra o manifesto congelado do lote aberto e lista todos os
comandos com suas opções. A seção **Passo a passo** traz uma animação em que um
terminal digita cada comando, de `create` a `serve`, e logo abaixo mostra o que
acontece por dentro, com dados reais do piloto do OrçaAPI. Ela pode ser pausada
ou aberta direto em um comando; com a opção de reduzir movimento do sistema,
avança só pelos botões. Na seção **Preparação do contexto**, outra animação
acompanha o alvo `calcular_orcamento` desde o `contextlab.json` e a árvore de
sintaxe até os pacotes L e R e a exploração de A, terminando com a comparação
das três estratégias no piloto. Um botão alterna entre tema claro e escuro.

Os diagramas usam a biblioteca Mermaid, incluída no pacote em
`src/contextlab/viewer/vendor/`. O visualizador não acessa a internet.

O arquivo de tarifas informa valores por milhão de tokens, com fonte e data:

```json
{
  "moeda": "USD",
  "fonte": "https://developers.openai.com/api/docs/models/gpt-6.1-sol",
  "consulta": "2026-11-15",
  "modelos": {
    "gpt-6.1-sol": {"entrada": 2.00, "entrada_cache": 0.10, "escrita_cache": 2.50, "saida": 10.00}
  }
}
```

A estimativa separa a entrada sem cache, a leitura e a escrita de cache, que são
partes da entrada, e a saída, que já inclui os tokens de raciocínio. A página
mostra o custo por tentativa, a média e o total por estratégia e o custo por
suíte aprovada (custo das gerações observáveis dividido pelas aprovações).
**É um cenário de preço de API, não a despesa efetiva**: com login por
assinatura não há cobrança por tentativa. Sem tarifa para o modelo ou sem
contagem de tokens, o custo fica ausente, nunca zero.

O visualizador é **somente leitura**: não reavalia entregas, não registra
revisões e não grava nada nos diretórios de resultados. A revisão continua pelo
comando `review`. O servidor atende apenas `127.0.0.1` e relê os registros a
cada acesso; recarregue a página para ver tentativas novas. `Ctrl+C` encerra.

A página exportada pode ser enviada a outra pessoa e aberta sem instalação. Por
embutir a biblioteca de diagramas, o arquivo tem cerca de 3 MB. Ela
contém os enunciados, os contextos e os testes gerados das tentativas
incluídas; confira esse conteúdo antes de compartilhar.

O código do visualizador fica em `src/contextlab/viewer/`, fora do conjunto de
arquivos conferido pelo congelamento. Alterar a apresentação não invalida
pilotos nem protocolos congelados.

### review: registrar a inspeção dos testes

```bash
contextlab cambio review ID --trusted-local
```

Para um lote piloto Docker, omita `--trusted-local`. O comando mostra o resumo,
a entrega e o JSON completo da avaliação, pergunta seu nome e três verificações. Responda `yes` ou `no`
após ler os testes; passar na execução não implica aprovação automática.

| Opção | O que informa; se omitida, é perguntado no terminal |
|---|---|
| `--reviewer "Seu nome"` | Responsável pela inspeção. |
| `--behavioral-assertions yes` ou `no` | As asserções verificam resultados ou exceções esperados? |
| `--no-target-mock yes` ou `no` | A função alvo foi usada de verdade, sem ser substituída por uma resposta simulada? |
| `--no-production-changes yes` ou `no` | A implementação foi preservada durante a execução? |
| `--http-requests yes` ou `no` | Somente alvos `http`: o teste fez requisições ao alvo, com regras e SQLite reais, sem chamar diretamente o handler? |

As opções adicionais abaixo não são perguntadas interativamente:

| Opção | Uso |
|---|---|
| `--trusted-local` | Autoriza a reavaliação de uma entrega demo local. |
| `--defect-attribution ID_DO_DEFEITO=yes` ou `no` | Registra se a falha observada é atribuível ao defeito. Pode repetir para defeitos distintos já avaliados. |

O ContextLab registra o responsável e as respostas, reavalia a mesma entrega e
atualiza a situação e os relatórios. Aprovação exige as três verificações e os
critérios automáticos atendidos. Alvos `http` exigem também a confirmação de
`http_requests`; a instrumentação, sozinha, não comprova uso de HTTP.
Revisão não altera o teste nem chama o modelo.
Se houver defeitos com atribuição pendente, inspecione as falhas e registre a
atribuição em nova revisão. O tutorial de câmbio não tem defeitos configurados.
Os critérios completos estão em [Avaliação e métricas](AVALIACAO.md).

## Execução local e Docker

O ContextLab roda no ambiente virtual. `setup` prepara a imagem. Na avaliação Docker, ele inicia e remove
os contêineres que executam os testes; o serviço Docker e a imagem precisam
estar disponíveis. O usuário continua usando `contextlab NOME run`.

`--trusted-local` permite a exceção de demonstração com testes autorais conhecidos,
configurada com `phase: demo` e `evaluation.backend: local`. A opção não muda
o JSON, não fica ativada nas chamadas seguintes e não transforma um piloto em
execução local. Sem ela, a avaliação local é recusada. O `venv` separa bibliotecas;
não substitui as restrições do avaliador Docker.

| Interface | Comandos que aceitam `--trusted-local` |
|---|---|
| Por nome | `contextlab NOME run`, `contextlab NOME review ID` |
| Por manifesto | `contextlab validate`, `contextlab run`, `contextlab review` |

Consultar `plan`, `context`, `runs` ou `show` não requer essa autorização.
A revisão pede autorização local porque executa novamente os testes.

## Comandos por manifesto

Use esta interface para controlar caminhos e etapas, ou reunir os quatro
projetos da coleta principal. Não coloque o nome do projeto após `contextlab`.
O [guia por manifesto](USO_POR_MANIFESTO.md) detalha o protocolo e a preparação.

Na tabela, as opções mostradas na **sintaxe obrigatória** são necessárias.
Todos os comandos também aceitam `-h` / `--help`.

| Sintaxe obrigatória | O que faz | Opções adicionais |
|---|---|---|
| `contextlab plan MANIFESTO` | Mostra o plano em JSON, sem geração. | Nenhuma. |
| `contextlab doctor MANIFESTO` | Verifica executáveis e capacidades dos adaptadores, sem pedir geração ao modelo. | Nenhuma. |
| `contextlab prepare MANIFESTO --project PROJETO --target ALVO --condition L --out PASTA` | Salva `context.json` e `initial.txt` em uma pasta nova. | `--condition` também aceita `R` e `A`. |
| `contextlab validate MANIFESTO --out PASTA` | Executa referências e testemunhos dos defeitos, salvando a validação. | `--trusted-local`. |
| `contextlab freeze MANIFESTO --out ARQUIVO.lock.json` | Congela configuração, fontes, ambiente e ordem. Não gera testes. | `--evidence EVIDENCIAS.json`; exigida com evidências válidas para `main`. |
| `contextlab run ARQUIVO.lock.json --out PASTA` | Executa o plano congelado. | `--trusted-local`, `--max-runs NUMERO`, `--resume`. |
| `contextlab review PASTA_DA_TENTATIVA --reviewer "Seu nome" --behavioral-assertions yes --no-target-mock yes --no-production-changes yes` | Registra a inspeção e reavalia a entrega. Os valores devem refletir a conferência; também aceitam `no`. | `--http-requests yes` ou `no` para alvos HTTP; `--trusted-local`; `--defect-attribution ID_DO_DEFEITO=yes` ou `no`, repetível. |
| `contextlab report PASTA_DA_EXECUCAO` | Exporta `results.csv`, `report.json` e `report.md`; não reexecuta os testes. | Nenhuma. |

`--project` e `--target` em `prepare` são os IDs definidos no manifesto, não
caminhos ou símbolos. `MANIFESTO` é um JSON editável; `ARQUIVO.lock.json` é a
configuração congelada. `--out` indica onde gravar arquivos, relativo ao terminal.
Use destinos novos para novas validações e locks, preservando os anteriores.
`freeze` não substitui a validação das referências; em `main`, exige também as
evidências de piloto e revisão descritas no guia por manifesto.

**A retomada tem sintaxe diferente nas duas interfaces:**

```bash
contextlab cambio run --resume LOTE --trusted-local
contextlab run ARQUIVO.lock.json --out PASTA_EXISTENTE --resume --trusted-local
```

Na primeira, `--resume` recebe o nome do lote. Na segunda, é um interruptor sem
valor; o lock e `--out` identificam a execução. No fluxo por manifesto, execute
`report` após `run` ou `review` para atualizar os relatórios. Na interface por
nome, essa exportação já ocorre automaticamente.

## Sequências de uso

### Aprender com câmbio, sem IA

Na raiz, com o ambiente ativado e o cadastro inicial em modo demo:

```bash
contextlab cambio plan
contextlab cambio context --condition L
contextlab cambio run --trusted-local
contextlab cambio runs
```

Depois, copie um ID e leia a entrega antes de revisar:

```bash
contextlab cambio show ID
contextlab cambio review ID --trusted-local
contextlab cambio runs
```

Para mudar o plano dos próximos lotes:

```bash
contextlab cambio configure --conditions L R A --repetitions 1
contextlab cambio plan
```

### Preparar um piloto real

Com modelo e autenticação definidos conforme [Adaptadores](ADAPTERS.md), ajuste
os marcadores abaixo. Estes comandos mudam a configuração do projeto:

```bash
contextlab cambio configure --mode pilot --conditions L R A --repetitions 1 \
  --model MODELO --auth-file CAMINHO_ABSOLUTO_DO_LOGIN
contextlab cambio plan
```

Se a autenticação configurada usar `CODEX_API_KEY`, não é necessário informar
`--auth-file`. Com Docker ligado, prepare a imagem e inicie uma tentativa:

```bash
contextlab cambio setup
contextlab cambio run --max-runs 1
contextlab cambio runs
```

O último `run` chama o Codex e pode consumir o orçamento da conta. Configurar e
consultar o plano não chama o modelo. Essa imagem atende a função de conversão;
outros alvos podem exigir imagens com dependências adicionais. Se o diagnóstico
do adaptador ou a validação falhar, consulte os registros antes de prosseguir.
Preparação de um piloto não equivale à validação da coleta principal.

### Executar uma demonstração pelo manifesto

Estes exemplos partem da raiz. Use nomes de saída novos se já houver registros:

```bash
contextlab plan projects/cambio/contextlab.json
contextlab validate projects/cambio/contextlab.json --out projects/cambio/runs/manual-validacao --trusted-local
contextlab freeze projects/cambio/contextlab.json --out projects/cambio/runs/manual.lock.json
contextlab run projects/cambio/runs/manual.lock.json --out projects/cambio/runs/manual-resultados --trusted-local --max-runs 1
contextlab report projects/cambio/runs/manual-resultados
```

Esta sequência exige `cambio` configurado como demo. Se você seguiu a seção do
piloto, volte com `contextlab cambio configure --mode demo` antes de usá-la.
O fluxo manual salva nos caminhos informados e não monta a estrutura de lote
da interface por nome. Portanto, navegue pelos arquivos e use `report`; seus
resultados não aparecem automaticamente em `contextlab cambio runs`.

## Resultados e problemas comuns

O JSON editável está em `projects/NOME/contextlab.json`. Cada lote criado pela
interface por nome conserva seus arquivos em `projects/NOME/runs/LOTE/`:

| Arquivo ou pasta | Conteúdo |
|---|---|
| `batch.json` | Situação da preparação e do processamento do lote. |
| `protocol.lock.json` | Configuração congelada. |
| `validation/` | Resultados da validação de referências e defeitos. |
| `results/run.json` | Plano e configuração usados na execução. |
| `results/PASTA_DA_TENTATIVA/` | Contexto, entrega, avaliação e revisões dessa tentativa. |
| `results/report.md`, `report.json`, `results.csv` | Relatórios do lote. |

Os resultados são locais e ignorados pelo Git. No modo demo, `test_generated.py`
é o nome do arquivo preservado mesmo quando o conteúdo veio de uma fixture.
O [guia dos arquivos de saída](SAIDAS.md) explica também os arquivos dentro de
cada tentativa, as cópias da entrega, os logs, a instrumentação e as revisões.

| Situação | Como interpretar ou prosseguir |
|---|---|
| `contextlab: command not found` | Ative o ambiente; confira a instalação do README. |
| Falta configurar um valor | Execute em terminal interativo ou forneça as opções indicadas por `--help`. |
| Projeto já cadastrado | Use `configure`; `create` não sobrescreve o JSON. |
| Imagem do avaliador ausente | Use `contextlab NOME setup`; imagens personalizadas também precisam de uma receita explícita. |
| R igual a L | Nenhuma dependência direta local externa acrescentou material ao contexto. |
| Avaliação local recusada | Confira `phase: demo`, backend local e `--trusted-local`. Piloto usa Docker. |
| Lote com falha de preparação | Leia `validation/`; referências ou defeitos podem não ter passado. Pode ainda não existir lock para retomar. |
| Não iniciada | A tentativa pertence ao plano, mas ainda não possui registro; `--max-runs` pode ter limitado a execução. |
| Aguardando revisão | A avaliação ainda exige inspeção; use `show` e depois `review`. |
| Falha de infraestrutura | Confira diagnóstico/logs. Não conte como reprovação do teste; a retomada não regenera tentativas já registradas. |
| Fontes, entrega ou ambiente alterados | Preserve os registros. Restaure o ambiente original para revisar/retomar, ou valide a mudança e crie um novo lote. Não edite o lock para contornar a conferência. |

`run` encerrar sem erro de comando não significa que todas as suítes foram
aprovadas: consulte a situação em `runs` ou no relatório. Câmbio é um exercício
fora da amostra; o protocolo principal continua em 108 gerações.
