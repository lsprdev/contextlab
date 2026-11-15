# Uso por manifesto e detalhes do protocolo

Este guia detalha o fluxo por manifesto e o protocolo. A sintaxe de todos os comandos e opções está na [referência de comandos](COMANDOS.md). Para começar pelo projeto de câmbio, use o [README do ContextLab](../README.md). Os exemplos de Loja e Agenda são fixtures internas; seus registros históricos permanecem preservados.

**ContextLab é o instrumento experimental do TCC sobre seleção de contexto na
geração de testes unitários.** Ele prepara o material acessível ao agente,
executa uma trajetória de geração, recebe um arquivo de teste e avalia esse
arquivo separadamente. Os resultados ficam registrados para comparar
executabilidade, aprovação, cobertura da unidade alvo, detecção de defeitos e
esforço de geração.

Uma trajetória corresponde a **projeto × função × agente × condição ×
repetição**. O número de funções `test_*` produzidas é um resultado da geração,
não o número de trajetórias. Na matriz principal do TCC, somente o Codex
trabalha sobre as mesmas doze funções em L/R/A: 4 projetos × 3 funções ×
1 agente × 3 condições × 3 repetições = **108 trajetórias**. São 9 por função,
27 por projeto e 36 por estratégia, com modelo e configuração fixados. Outros
agentes ficam para trabalhos futuros.

Os projetos de aprendizado estão em `projects/cambio/` e `projects/orcamentos/`.
Loja e Agenda são fixtures internas. Executar demonstrações não executa o
experimento do TCC. O [OrçaAPI](../../projects/orcamentos/README.md) tem um alvo
unitário e outro HTTP. O campo opcional `targets[].test_kind` aceita `unit`
(padrão) e `http` (exercício FastAPI/SQLite, somente fora de `main`). `create`
cadastra alvos unitários; configure o tipo HTTP explicitamente no JSON.

Os quatro projetos da coleta principal já foram escolhidos: **Fava, wger,
python-dotenv e python-stdnum**, com três funções selecionadas por projeto.
A instalação, os testes de referência e a integração desses alvos com o
ContextLab ainda precisam ser validados. O modelo e os limites da coleta
principal também precisam ser definidos, validados e congelados. O
[acompanhamento do TCC](../../docs/STATUS.md) detalha essas pendências.

## Instalação

Requisitos: Python 3.11 ou posterior em macOS ou Linux (WSL no Windows) para executar o ContextLab. A imagem de avaliação usa Python 3.12. Os comandos abaixo partem da pasta
`contextlab/`, na raiz deste repositório.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m contextlab --help
```

O avaliador Docker e os adaptadores nativos precisam de seus respectivos
executáveis; a demonstração com fixtures pode ser executada apenas com Python.

`contextlab` e `python -m contextlab` são duas formas de iniciar a mesma CLI.
Use `contextlab <comando> --help` para consultar os argumentos disponíveis.

## Primeiro teste: seis trajetórias sem credenciais

O manifesto [tests/fixtures/demo.json](../tests/fixtures/demo.json) usa testes autorais fixos,
denominados *fixtures*, como saída do gerador. Isso permite conferir o fluxo
completo sem consumir chamadas a modelos. Os exemplos são:

| Projeto | Alvo | Dependência externa | Defeito demonstrado |
| --- | --- | --- | --- |
| Loja | `calcular_frete` | `Cliente` e `tarifa` | Excluir peso igual a 5 do desconto VIP |
| Agenda | `calcular_preco` | `Reserva` e `tarifa_hora` | Excluir duração igual a 120 minutos do desconto |

### 1. Conferir a matriz

```bash
python -m contextlab plan tests/fixtures/demo.json
```

O plano contém **6 trajetórias**: 2 projetos × 1 alvo × 1 adaptador `fixture` ×
3 condições × 1 repetição. A semente fixa a ordem embaralhada do plano; ela não
torna um modelo remoto determinístico.

### 2. Inspecionar um pacote de contexto

```bash
contextlab prepare tests/fixtures/demo.json \
  --project loja --target frete --condition R --out runs/contexto
```

Inspecione os arquivos produzidos antes da execução. Em R, o material deve
conter o arquivo focal, o tipo `Cliente` e a função `tarifa`. Troque R por L ou A
e use outra pasta de saída para comparar o que fica disponível em cada caso.

### 3. Validar as referências e os defeitos

```bash
contextlab validate tests/fixtures/demo.json --out runs/validation --trusted-local
```

A validação executa os testes reservados no projeto original. Para cada defeito,
confirma que seu teste testemunha passa no original e falha por asserção ou por
exceção durante sua execução na versão alterada. Um defeito que apenas produz erro de sintaxe ou de importação
não atende esse critério. O inventário validado será o mesmo para todas as
condições de um alvo.

`--trusted-local` autoriza a execução na máquina atual. Use-o nesta demonstração
porque os testes são autorais e podem ser inspecionados. Para saídas de agentes,
configure o backend Docker descrito adiante.

### 4. Congelar e executar

```bash
contextlab freeze tests/fixtures/demo.json --out runs/demo.lock.json
contextlab run runs/demo.lock.json --out runs/demo --trusted-local
contextlab report runs/demo
```

O arquivo de congelamento (*lock*) registra configuração, plano e hashes dos
arquivos e da implementação. Se algo mudar, gere um novo lock com outro nome
após validar a alteração. Não edite um lock para fazer uma execução prosseguir.

### 5. Revisar um teste antes de aprovar métricas de qualidade

Abra a saída preservada e os registros de avaliação de uma trajetória. Para
aprovar o exemplo local de frete, depois dessa inspeção:

```bash
contextlab review runs/demo/loja__frete__fixture__L__1 \
  --reviewer Gabriel \
  --behavioral-assertions yes \
  --no-target-mock yes \
  --no-production-changes yes \
  --trusted-local
contextlab report runs/demo
```

As respostas acima significam que você verificou que as asserções avaliam
comportamento, a unidade alvo não foi substituída por mock e a produção não foi
alterada. Não aprove automaticamente os três itens para testes ainda não
inspecionados. Uma execução que passa pode ficar como `pending_review`; isso é
um estado de trabalho, não uma aprovação implícita.

A revisão confere o protocolo congelado, o código do ContextLab, as versões de
Python e dependências, a imagem Docker, as fontes e a submissão antes de
reavaliar. Se algum desses itens mudar, ela é recusada: mantenha o ambiente
original para revisar uma coleta existente. As avaliações anteriores continuam
preservadas no histórico de revisões.

A detecção de cada defeito também exige examinar a falha obtida e atribuí-la à
alteração de comportamento. Até essa atribuição ser registrada, o resultado
permanece pendente. Depois de inspecionar a falha do defeito `vip-limite`, uma
segunda revisão pode registrar a atribuição:

```bash
contextlab review runs/demo/loja__frete__fixture__L__1 \
  --reviewer Gabriel \
  --behavioral-assertions yes \
  --no-target-mock yes \
  --no-production-changes yes \
  --defect-attribution vip-limite=yes \
  --trusted-local
contextlab report runs/demo
```

Use `no` se a falha não puder ser atribuída ao defeito. Para vários defeitos,
repita `--defect-attribution`. O histórico de revisões é preservado.

O adaptador `fixture` entrega os mesmos testes em L, R e A. Portanto, os
resultados dessa demonstração verificam o instrumento e **não permitem concluir
que uma estratégia de contexto é melhor**.

## O que muda entre L, R e A

| Condição | Material disponível | Quem seleciona a informação |
| --- | --- | --- |
| **L — Local** | Arquivo focal completo e declarações de tipos diretamente necessárias à assinatura | Preparador determinístico |
| **R — Recuperado** | L e declarações de dependências diretas da função, resolvidas estaticamente | Preparador determinístico |
| **A — Autônomo** | Código de produção e documentação permitidos na cópia preparada do repositório | Agente, por listagem, leitura e busca |

O recuperador usa a árvore sintática do Python (`ast`) para localizar símbolos,
imports e referências. A expansão termina nas dependências diretas. Ele não
percorre recursivamente as dependências das dependências, não executa imports e
não utiliza embeddings. Referências dinâmicas ou ambíguas ficam registradas
como não resolvidas; o sistema não inventa uma resolução. Se R não acrescentar
material a L, isso também é registrado.

Os pacotes são material de leitura e não precisam formar um projeto Python
executável. Um trecho recuperado representa a declaração selecionada, não uma
cópia completa do arquivo externo.

O agente consulta **arquivos virtuais** por três ferramentas: `list_files`,
`read_file` e `search`. O intermediário (*broker*) responde apenas com o snapshot
permitido para aquela condição. Caminhos fora dele, links simbólicos e nomes de
ferramentas não permitidos são recusados. A busca é literal; ela não executa
expressões de shell.

O limite de caracteres contabiliza o contexto inicial e as respostas JSON
entregues pelas ferramentas, inclusive leituras repetidas e erros. Ele mede o
material fornecido por esse canal, não o total de tokens internos do agente.
Uma resposta que ultrapassaria o saldo não é entregue parcialmente. O arquivo
focal de L precisa caber integralmente; em R, trechos adicionais que não cabem
ficam registrados como omitidos.

O enunciado enviado ao agente informa os limites de caracteres e de consultas
da sessão e avisa que ultrapassá-los a encerra sem entrega. O aviso é o mesmo
em L, R e A e fica registrado em `prompt.txt`.

### Exemplos executáveis na documentação

A preparação comum de L/R/A remove doctests: comandos iniciados por `>>>`,
continuações com `...` e suas saídas esperadas, inclusive tracebacks. A regra
vale para docstrings de módulos, classes, funções e métodos e para a
documentação explicitamente incluída. A descrição do comportamento permanece.

As linhas dos exemplos ficam vazias para manter a numeração de origem. As
quebras de linha são normalizadas para LF. O código fora das docstrings não é
reescrito; os arquivos do projeto e a cópia usada pelo avaliador conservam os
originais. O preparador apenas analisa o texto, sem executar os exemplos ou
importar o projeto. Fontes Python ou doctests que não possam ser analisados
interrompem a preparação com indicação do arquivo.

O `manifest` de cada contexto registra `preparation_version`, `source_sha256`,
`sha256`, `source_chars`, `chars` e `transformations`: versão da regra, hashes
e tamanhos antes/depois, tipos de transformação, intervalos das docstrings e
quantidade de exemplos removidos. Os hashes do lock continuam identificando
as fontes originais. As ferramentas de leitura e busca só acessam a visão
preparada, impedindo que os exemplos removidos reapareçam na exploração de A.

A detecção automática usa a sintaxe de doctest. Blocos de código sem esses
marcadores, exemplos em outros formatos e materiais com respostas continuam
sujeitos à curadoria e inspeção previstas antes do congelamento.

## Separação entre geração e avaliação

O gerador não recebe o ambiente completo de avaliação. Nos adaptadores nativos,
cada trajetória usa uma sessão nova e um diretório temporário vazio; as leituras
de contexto passam pelo servidor MCP do ContextLab. Ferramentas nativas de
shell, execução, edição e navegação ficam desabilitadas conforme a configuração
do adaptador. O agente devolve o teste como saída estruturada, que o
orquestrador preserva em disco.

Depois, o avaliador cria uma cópia do projeto e executa somente a submissão
gerada. Os testes de referência são usados separadamente para validar o
projeto e os defeitos, sem entrar na cobertura atribuída ao agente. Nenhum
erro, resultado de cobertura ou teste de referência retorna ao agente para
reparo. A trajetória termina após uma submissão.

Os testes existentes e os arquivos privados ficam fora da lista de contexto.
A preparação do repositório exclui automaticamente arquivos e conteúdos que
correspondam aos padrões conhecidos, mas também exige inspeção:
documentação pode conter exemplos de testes, resultados esperados e outros
materiais que precisam ser revisados. Declare cada documento elegível pelo
caminho exato; documentos abrangidos apenas por um glob não são admitidos.

## Avaliação isolada com Docker

Construa a imagem usada pelos exemplos:

```bash
docker build -f Dockerfile.evaluator -t contextlab-evaluator:local .
```

No manifesto, configure:

```json
"evaluation": {
  "backend": "docker",
  "image": "contextlab-evaluator:local"
}
```

O avaliador inicia um container sem rede, com produção e submissão montadas para
leitura e saída de resultados em diretório separado. A imagem dos exemplos
contém Python, pytest e coverage. Para outros projetos, prepare uma imagem com
suas dependências fixadas antes de avaliar; o container não instala dependências
durante a execução.

Um container de avaliação é uma execução do avaliador, não uma sessão de login
do agente. Os clientes de IA e suas credenciais ficam no ambiente de geração.
Veja [docs/ADAPTERS.md](ADAPTERS.md) para configuração e limitações dos
adaptadores.

As categorias de falha, o cálculo da cobertura focal e as regras de detecção
estão detalhados em [docs/AVALIACAO.md](AVALIACAO.md).

## Conectar o Codex

O piloto atual usa somente **Codex com `gpt-6-luna`**, em
[tests/fixtures/codex-pilot.json](../tests/fixtures/codex-pilot.json): dois projetos, L/R/A e
uma repetição, totalizando **seis trajetórias**. O campo `auth_file` aponta para
o login local do ChatGPT em `~/.codex-work/auth.json`; ajuste apenas esse caminho
se seu login estiver em outro diretório. O manifesto contém o caminho, nunca o
conteúdo da credencial. Esse modelo identifica o piloto de integração; o modelo
da coleta principal ainda deve ser escolhido, validado e congelado. Claude fica
fora do piloto atual e da matriz principal.

```bash
contextlab doctor tests/fixtures/codex-pilot.json
contextlab freeze tests/fixtures/codex-pilot.json --out runs/codex-pilot.lock.json
contextlab run runs/codex-pilot.lock.json --out runs/codex-pilot --max-runs 1
contextlab report runs/codex-pilot
```

O diagnóstico do Codex usa um servidor simulado em localhost, sem chamadas ao
modelo nem credenciais, para conferir o inventário real de ferramentas e testar
recusas de comandos e leituras externas. O catálogo restrito preserva o modelo,
suas instruções e parâmetros de inferência; remove capacidades nativas que
permitiriam acesso fora do MCP. Sua identidade é registrada por SHA-256.
Após inspecionar a primeira trajetória, `run --resume` continua a matriz.

Para ensaiar a integração com outro modelo, copie `codex-pilot.json`, altere o
campo `model` para o identificador explícito que será validado e repita os
comandos acima com o novo arquivo.

O adaptador da coleta chama o executável nativo `codex`, sem substituí-lo por
uma chamada direta a uma API de modelo. O adaptador `claude` continua disponível
para extensões futuras do instrumento, fora do protocolo principal.

- **Codex:** configure `CODEX_API_KEY` ou o campo `auth_file` apontando para um
  arquivo privado compatível. Não inclua a credencial no repositório.
- Use a verificação `doctor` antes de congelar o piloto; consulte
  `contextlab doctor --help` e [docs/ADAPTERS.md](ADAPTERS.md).

Execute a sequência `doctor`, `freeze`, `run` e `report` após escolher o modelo, configurar as credenciais e
construir a imagem Docker. A execução com agentes pode consumir seu orçamento
do provedor. Para começar com apenas uma trajetória, acrescente `--max-runs 1`
ao comando `run`; depois continue com o mesmo lock e diretório usando `--resume`.
Trajetórias já preservadas não são geradas novamente por esse mecanismo.

O modo `doctor` verifica executáveis e capacidades esperadas sem pedir geração
à IA. Isso não substitui um piloto real. Compatibilidade de versão, autenticação
e bloqueio das ferramentas devem ser conferidos no seu ambiente antes da
coleta; os registros de uma execução, sozinhos, não provam isolamento completo.

Mantenha credenciais fora de `include` e `evaluation_include`. Uma sessão nova
de geração não exige que você faça um novo login manual para cada função.
Configurações e históricos das sessões anteriores não são copiados como
contexto para a próxima trajetória.

## Como configurar outros projetos

O guia [Executar em outro projeto Python](NOVOS_PROJETOS.md) apresenta o
passo a passo completo: escolha da função, manifesto JSON, referências,
defeitos, dependências Docker, geração com Codex, revisão e relatório.

Comece copiando um dos manifestos em `tests/fixtures/`. Caminhos de projeto,
fixtures e credenciais são relativos ao arquivo de configuração, quando não
forem absolutos nos campos em que isso é permitido.

| Campo | Finalidade |
| --- | --- |
| `phase` | `demo`, `pilot` ou `main`; fixtures são admitidas somente em `demo` |
| `agents` | Em `main`, exatamente uma entrada Codex com modelo explícito e fixado |
| `conditions`, `repetitions`, `seed` | Matriz e ordem de execução |
| `limits` | Limites explícitos de caracteres, consultas, geração e avaliação |
| `project.root` | Diretório do projeto |
| `source_roots` | Raízes de importação; por exemplo `["."]` ou `["src"]` |
| `include` | Lista permitida de produção e documentos para contexto |
| `evaluation_include` | Arquivos necessários à execução, incluindo referências reservadas |
| `target.path`, `symbol`, `import` | Arquivo, símbolo estático e importação da unidade alvo |
| `reference_tests` | Testes reservados que validam a versão original |
| `defects` | Alterações fixas e seus testes testemunha |

Cada defeito informa `id`, `path`, `old`, `new` e `witness`. O texto `old` precisa
aparecer exatamente uma vez no arquivo. `witness` aceita o identificador pytest,
por exemplo `reference/test_frete.py::test_limite_vip`. Essa representação torna
o inventário pequeno e auditável; não é um gerador geral de mutantes.

Os números de `tests/fixtures/demo.json` e `tests/fixtures/codex-pilot.json` são valores
práticos para demonstração, **não limites justificados para o TCC**. O piloto
precisa registrar por que os limites escolhidos acomodam as unidades,
restringem o esforço de maneira comparável e cabem no orçamento disponível.

Para a coleta principal, configure os quatro projetos escolhidos, com três alvos
em cada um. Use apenas Codex e mantenha L/R/A com três repetições: **108 gerações**. O plano
sorteia os blocos de função/repetição e as estratégias dentro de cada bloco,
com semente registrada. Os planos de demonstração e piloto mantêm sorteio global.
Prepare suas referências e seu inventário de defeitos, execute a validação,
faça o piloto com o Codex real nas três estratégias e revise os contextos. O congelamento de `main`
exige evidências de piloto e revisão nominal de isolamento, preparação do repositório,
mapeamento focal e calibração do orçamento. Consulte
`contextlab freeze --help` para fornecer essas evidências. O comando recebe
`--evidence caminho/para/evidencias.json`; o arquivo deve identificar
`pilot_run`, `validation_dir`, `reviewer` e `agent_versions`, além das confirmações
`isolation_verified`, `docs_sanitized`, `focal_mapping_verified` e
`budget_calibrated`. O campo `docs_sanitized` confirma a revisão da documentação
permitida e a exclusão de materiais reservados; seu nome técnico foi mantido
para compatibilidade dos manifestos. Registre as confirmações somente depois de verificar os
itens; o comando também confere os artefatos de piloto e validação apontados.
O arquivo [tests/fixtures/evidence.template.json](../tests/fixtures/evidence.template.json)
oferece a estrutura, com confirmações inicialmente falsas. Os caminhos nele
são relativos ao próprio arquivo de evidências. Use outros alvos no piloto;
versão do Codex, modelo, limites, ambiente e implementação finais precisam
coincidir com os verificados. Mudanças exigem nova validação e novos locks;
preserve os registros e locks das execuções anteriores.
Não transforme a
demonstração com fixtures em uma coleta principal renomeando sua fase.

## Como interpretar os registros

A avaliação distingue perguntas diferentes:

1. **Foi entregue um teste?** Ausência de saída e falhas de geração são
   registradas.
2. **O teste pode executar?** Sintaxe, coleta, importação, preparação, início de
   testes ativos e término da execução são observados separadamente.
3. **Passa na versão original?** Asserções que falham no original não se tornam
   detecções de defeitos.
4. **É elegível para avaliar qualidade?** Exige execução da unidade alvo e
   revisão das asserções, mocks e integridade da produção.
5. **Qual foi sua qualidade e esforço?** Cobertura focal, detecção dos defeitos
   elegíveis, tempo e informações de uso que o adaptador conseguir registrar.

Saídas ausentes, falhas, timeouts, pendências de revisão e erros de infraestrutura
não devem desaparecer da análise. Cobertura bruta pode existir mesmo em uma
execução reprovada; a métrica principal de qualidade só é preenchida para
submissões aprovadas. Dados ausentes e pendentes não são convertidos
automaticamente em zero.

Não confunda o tempo de geração com o tempo de avaliação nem interprete tokens
não informados pelo cliente como consumo zero. Este instrumento registra dados
para a análise; ele não decide automaticamente qual estratégia é melhor nem
comprova significância estatística a partir da demonstração.

## Testes da implementação

```bash
python -m pytest -q
```

Os testes automatizados do instrumento e a demonstração autoral verificam a
implementação local. Para os clientes nativos e o backend Docker, faça também
os ensaios correspondentes no ambiente de coleta. Os testes de referência dos
domínios podem ser executados separadamente seguindo
[tests/fixtures/README.md](../tests/fixtures/README.md).

## Organização

| Caminho | Conteúdo |
| --- | --- |
| `src/contextlab/` | CLI, manifesto, preparação, ferramentas, adaptadores e avaliação |
| `tests/fixtures/` | Projetos didáticos, referências, fixtures e manifestos |
| `tests/` | Verificações automatizadas do instrumento |
| `Dockerfile.evaluator` | Imagem base para avaliar os projetos didáticos |
| `docs/ADAPTERS.md` | Configuração e limites dos clientes nativos |
| `runs/` | Diretório sugerido para locks, contextos, submissões e resultados locais |

Os arquivos de protocolo do TCC ficam na raiz do repositório. As saídas da
coleta devem ser preservadas com suas versões e revisões para permitir auditoria;
credenciais não fazem parte desses resultados.
