# Executar o ContextLab em outro projeto Python

Este guia acompanha um piloto desde a escolha da função até a revisão dos testes
e o relatório final. A configuração usa **Codex com `gpt-6-luna` e avaliação
Docker**, sem Claude.

Já é possível fazer pilotos com funções de projetos maiores. Cada backend ainda
precisa ter suas dependências e seus alvos preparados para o avaliador. O
ContextLab não instala automaticamente as dependências do projeto, não inicia
banco/API e não herda a configuração de pytest dele.

Os nomes, caminhos e regras de negócio abaixo são exemplos. Adapte-os ao
repositório escolhido antes de executar os comandos.

## Manifesto e contrato de execução

O JSON de configuração é chamado de **manifesto do experimento**. Ele funciona
como um contrato de execução: declara projeto, funções, modelo, contexto
permitido, limites e avaliação. O campo `schema_version` identifica a versão do
formato validado pelo ContextLab.

O arquivo `*.lock.json` é a versão congelada desse contrato, com a matriz de
execução e hashes para detectar alterações. Ele é produzido por `freeze`; não
deve ser editado manualmente.

O [demo.json](../examples/demo.json) usa saídas autorais fixas, sem geração por
modelo. Para um piloto real somente com Codex, use como base o
[codex-pilot.json](../examples/codex-pilot.json).

## 1. Clonar o projeto e fixar a versão

Substitua `URL_DO_REPOSITORIO` pela URL real:

```bash
git clone URL_DO_REPOSITORIO /Users/lsprdev/Code/backend-experimento
git -C /Users/lsprdev/Code/backend-experimento rev-parse HEAD
```

Anote o commit. Prepare os arquivos necessários antes de congelar o experimento
e mantenha essa versão durante a execução. O lock registra os arquivos
selecionados; não representa automaticamente todo o histórico Git do projeto.

## 2. Escolher a função

Comece por uma regra de negócio com entradas e resultados claros, como cálculo
de preço, validação ou transformação de dados. Para a primeira tentativa,
escolha uma função que execute sem banco, Redis, chamadas HTTP ou inicialização
do servidor. O avaliador atual executa testes sem rede e não inicia esses serviços.

Suponha esta função no backend:

```python
# src/backend/precos.py — assinatura ilustrativa
def calcular_total(preco: float, quantidade: int) -> float:
    ...
```

Neste exemplo, a regra é: **compras com 10 unidades ou mais recebem 10% de
desconto**. A implementação real deve existir no projeto; o trecho acima apenas
ilustra a assinatura.

Identifique estes dados:

| Informação | Exemplo |
|---|---|
| Arquivo relativo à raiz do projeto | `src/backend/precos.py` |
| Nome da função | `calcular_total` |
| Importação Python | `backend.precos:calcular_total` |
| Diretório que contém os pacotes importáveis | `src` |

Se o pacote estiver diretamente na raiz do repositório, a raiz de importação
pode ser `.` em vez de `src`. A instrumentação não admite funções alvo aninhadas
em outras funções nem definições com o corpo na mesma linha do `def`.

## 3. Separar os testes de referência

São testes revisados pelo pesquisador para confirmar o comportamento esperado.
Podem ser testes existentes ou um arquivo específico, dentro do projeto:

```python
# reference/test_precos.py
from backend.precos import calcular_total


def test_compra_sem_desconto():
    assert calcular_total(10.0, 9) == 90.0


def test_desconto_na_fronteira():
    assert calcular_total(10.0, 10) == 90.0
```

Esses valores só fazem sentido para a regra hipotética acima. No projeto real,
as expectativas precisam vir dos requisitos dele.

**Os testes de referência ficam disponíveis ao avaliador, mas fora do contexto
oferecido ao Codex.** Eles também não são coletados junto com a suíte gerada.
Todo alvo exige ao menos uma referência no manifesto.

## 4. Definir um defeito controlado

Além de verificar se os testes passam no código correto, podemos verificar se
percebem uma alteração incorreta. Exemplo de trecho a substituir:

```python
# Original
quantidade >= 10

# Defeito
quantidade > 10
```

O teste `test_desconto_na_fronteira` será o **testemunho**: precisa passar no
original e falhar na versão alterada por causa da mudança de comportamento.
Um erro de sintaxe ou importação introduzido pela alteração não serve como
detecção de defeito comportamental.

O ContextLab aplica a alteração numa cópia temporária. O trecho original precisa
aparecer **exatamente uma vez** no arquivo. Os defeitos são definidos antes da
geração e mantidos iguais entre as condições.

Para um primeiro piloto apenas de geração e execução, é possível usar
`"defects": []`. Nesse caso, não haverá medição de detecção de defeitos.

## 5. Criar o manifesto

Na pasta `contextlab/`, crie o diretório de manifestos locais:

```bash
mkdir -p experiments
```

Salve o exemplo adaptado em `experiments/backend-pilot.json`:

```json
{
  "schema_version": 1,
  "phase": "pilot",
  "seed": 42,
  "conditions": ["L", "R", "A"],
  "repetitions": 1,
  "limits": {
    "context_chars": 30000,
    "tool_calls": 20,
    "generation_seconds": 120,
    "evaluation_seconds": 20
  },
  "agents": [
    {
      "id": "codex",
      "kind": "codex",
      "model": "gpt-6-luna",
      "auth_file": "~/.codex-work/auth.json"
    }
  ],
  "evaluation": {
    "backend": "docker",
    "image": "contextlab-evaluator:local"
  },
  "projects": [
    {
      "id": "backend",
      "root": "/Users/lsprdev/Code/backend-experimento",
      "source_roots": ["src"],
      "include": [
        "src/backend/**/*.py"
      ],
      "evaluation_include": [
        "src/backend/**/*.py",
        "reference/test_precos.py"
      ],
      "targets": [
        {
          "id": "total",
          "path": "src/backend/precos.py",
          "symbol": "calcular_total",
          "import": "backend.precos:calcular_total",
          "reference_tests": [
            "reference/test_precos.py"
          ],
          "defects": [
            {
              "id": "limite-desconto",
              "path": "src/backend/precos.py",
              "old": "quantidade >= 10",
              "new": "quantidade > 10",
              "witness": "reference/test_precos.py::test_desconto_na_fronteira"
            }
          ]
        }
      ]
    }
  ]
}
```

A distinção mais importante é:

| Campo | Finalidade |
|---|---|
| `include` | Material permitido para montar o contexto do agente |
| `evaluation_include` | Arquivos copiados para executar a avaliação, incluindo código, referências e dados necessários |
| `source_roots` | Raízes de importação relativas ao projeto |
| `targets` | Funções selecionadas, suas referências e seus defeitos |
| `auth_file` | Caminho para um login existente; nunca o conteúdo da credencial |

O exemplo usa o caminho de autenticação do ambiente em que o piloto inicial foi
executado. Ajuste-o se seu login estiver em outro diretório, como `~/.codex/`.
Detalhes estão em [ADAPTERS.md](ADAPTERS.md).

`root` pode ser absoluto. Quando relativo, ele é resolvido a partir da pasta do
manifesto. Os caminhos de produção, referências, padrões e raízes de importação
são relativos à raiz do projeto.

Para disponibilizar documentação, acrescente caminhos explícitos, como
`"docs/regras-precos.md"`, em `include`, após revisar seu conteúdo. Não inclua
testes, credenciais nem saídas esperadas reservadas nesse material.

As condições são:

| Condição | Contexto |
|---|---|
| **L** | Arquivo da função e tipos da assinatura recuperáveis estaticamente |
| **R** | L mais dependências diretas recuperadas pelo analisador |
| **A** | O agente consulta os arquivos permitidos pelo MCP |

`context_chars` limita **caracteres de material entregue**, incluindo releituras;
não é um limite de tokens totais da geração. `tool_calls` limita consultas por
trajetória. `generation_seconds` limita o tempo da geração, e
`evaluation_seconds`, cada execução do avaliador. Esses valores são um ponto de
partida para o piloto, não limites já justificados para qualquer backend.

`seed` fixa o embaralhamento da matriz; não torna o modelo remoto determinístico.

## 6. Preparar o ambiente de execução

Os comandos seguintes partem da pasta `contextlab/`, dentro do repositório do
TCC. Se ainda não houver um ambiente instalado e ativo:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

O Docker precisa estar em execução. A imagem base tem Python, pytest e coverage.
Se a função usa somente a biblioteca padrão, ela pode ser suficiente:

```bash
docker build -f Dockerfile.evaluator -t contextlab-evaluator:local .
```

Se o backend depende de outros pacotes, instale essas dependências numa imagem
própria. Por exemplo, crie no backend um `requirements-contextlab.txt` com as
dependências necessárias e versões fixadas, preservando pytest 8.4.2 e coverage
7.10.7. Um `Dockerfile.contextlab` no mesmo diretório pode conter:

```dockerfile
FROM contextlab-evaluator:local

COPY requirements-contextlab.txt /tmp/requirements-contextlab.txt
RUN python -m pip install --no-cache-dir \
    -r /tmp/requirements-contextlab.txt
```

Construa a imagem:

```bash
docker build \
  -f /Users/lsprdev/Code/backend-experimento/Dockerfile.contextlab \
  -t backend-evaluator:pilot \
  /Users/lsprdev/Code/backend-experimento
```

Nesse caso, altere `evaluation.image` para `"backend-evaluator:pilot"`. Bibliotecas
que dependam de pacotes do sistema também precisam ser preparadas nessa imagem.
O código avaliado será fornecido pelo snapshot do ContextLab.

**Limite atual:** o avaliador usa sua própria configuração de pytest e desativa
o carregamento automático de plugins. Projetos dependentes de `pytest-django`,
`pytest-asyncio` ou fixtures complexas podem exigir adaptação do avaliador;
instalar as bibliotecas sozinho não garante compatibilidade. Os testes gerados
também não recebem os `conftest.py` reservados das referências.

## 7. Conferir o diagnóstico, a matriz e os contextos

```bash
contextlab doctor experiments/backend-pilot.json
contextlab plan experiments/backend-pilot.json
```

O manifesto de exemplo planeja **3 gerações**: uma função × um agente × três
condições × uma repetição. O diagnóstico precisa indicar que o Codex está pronto.

Prepare os contextos para inspecioná-los:

```bash
for condicao in L R A; do
  contextlab prepare experiments/backend-pilot.json \
    --project backend \
    --target total \
    --condition "$condicao" \
    --out "runs/backend-contexto-$condicao"
done
```

Abra `context.json` e `initial.txt` em cada pasta. Confira os arquivos
disponíveis, as dependências não resolvidas (`unresolved`) e os trechos omitidos
(`omitted`). Em A, o material inicial fica vazio porque o agente fará as consultas.

Em projetos maiores, essa etapa é essencial: o analisador não resolve todas as
dependências dinâmicas. O arquivo focal inteiro e os demais componentes
obrigatórios de L precisam caber no orçamento; o programa não os corta
silenciosamente. Se precisar ajustar seleção ou limites, faça isso antes de
congelar e mantenha os limites comuns às condições.

## 8. Validar as referências e os defeitos

```bash
contextlab validate experiments/backend-pilot.json \
  --out runs/backend-validacao-01
```

Confira `runs/backend-validacao-01/validation.json`. A validação precisa confirmar:

- As referências passam no código original e executam a função escolhida.
- O testemunho passa no original e falha pelo defeito introduzido, se houver.
- O ambiente consegue importar e executar o código.

Se houver falha de importação, dependência ou configuração, resolva a preparação
antes de gastar gerações. Depois de corrigir, use outra pasta de validação, como
`runs/backend-validacao-02`, preservando os registros anteriores.

## 9. Congelar e executar o piloto

```bash
contextlab freeze experiments/backend-pilot.json \
  --out runs/backend-piloto-01.lock.json

contextlab run runs/backend-piloto-01.lock.json \
  --out runs/backend-piloto-01 \
  --max-runs 1
```

Inspecione a primeira entrega e a avaliação. A primeira condição depende da
ordem sorteada, que pode ser consultada com `plan`. Depois, complete as restantes:

```bash
contextlab run runs/backend-piloto-01.lock.json \
  --out runs/backend-piloto-01 \
  --resume
```

A retomada preserva as trajetórias já registradas, inclusive as que falharam.
Não gera uma nova tentativa para substituir um resultado desfavorável.

Depois do congelamento, mudanças no código selecionado, no ContextLab ou no
ambiente verificado exigem nova validação e outro lock. Alterações no manifesto
fonte também exigem novo congelamento para fazer parte de uma execução: `run`
usa a configuração armazenada no lock. Não edite os testes gerados para melhorar
o resultado da rodada.

## 10. Revisar as suítes e atribuir os defeitos detectados

Cada trajetória terá arquivos como:

```text
runs/backend-piloto-01/
  backend__total__codex__L__1/
    test_generated.py
    record.json
    agent/
      native.jsonl
      tool_audit.json
    evaluation/
      original/
        stdout.log
        stderr.log
```

Confira se a suíte tem verificações comportamentais, não substitui a própria
função alvo e não altera produção. **Depois dessa inspeção**, uma aprovação pode
ser registrada assim, usando a trajetória L como exemplo:

```bash
contextlab review \
  runs/backend-piloto-01/backend__total__codex__L__1 \
  --reviewer "Seu nome" \
  --behavioral-assertions yes \
  --no-target-mock yes \
  --no-production-changes yes
```

Use `no` no item que não atender ao critério. Passar no pytest sozinho não implica
aprovação. Uma suíte que falha na versão original não será aprovada só porque os
três itens de revisão receberam `yes`.

Quando a suíte é aprovada, a revisão também executa os defeitos cadastrados.
Inspecione a falha, se houver, no diretório da trajetória:

```text
reviews/001/defects/limite-desconto/generated/stdout.log
```

Se confirmar que ela revela o defeito, registre a atribuição:

```bash
contextlab review \
  runs/backend-piloto-01/backend__total__codex__L__1 \
  --reviewer "Seu nome" \
  --behavioral-assertions yes \
  --no-target-mock yes \
  --no-production-changes yes \
  --defect-attribution limite-desconto=yes
```

Se a falha não for atribuível ao defeito, use `limite-desconto=no`. Se os testes
continuarem passando na versão alterada, o defeito sobreviveu e não foi detectado.
As novas revisões preservam o histórico; não substituem a entrega original.
Repita a inspeção para as demais trajetórias.

## 11. Gerar o relatório e ampliar gradualmente

```bash
contextlab report runs/backend-piloto-01
```

Esse comando pode ser executado antes das revisões para visualizar pendências
e novamente depois delas para atualizar o relatório.

| Arquivo | Conteúdo |
|---|---|
| `report.md` | Relatório para leitura |
| `results.csv` | Uma linha por trajetória, com tokens, tempos e resultados |
| `report.json` | Resultados detalhados, denominadores e pendências |
| `record.json` de cada trajetória | Geração, uso de tokens, ferramentas e avaliação |
| `test_generated.py` de cada trajetória | Suíte entregue pelo agente |

Os tokens são registrados por geração da suíte inteira, não por cada função
`test_*`. Cobertura principal e detecção dependem da aprovação e das revisões;
campos pendentes não devem ser interpretados como zero.

Os diretórios de execução em `runs/` são ignorados pelo Git. Preserve seus
artefatos separadamente se precisar arquivar ou compartilhar a coleta.

Para ampliar, acrescente funções em `targets` e ajuste `repetitions` antes de uma
nova rodada. Com cinco funções, Codex, L/R/A e três repetições, serão **45
gerações**. Use `plan` para conferir a matriz antes de executar.

Para ensaios com quantidades diferentes da matriz principal, mantenha
`"phase": "pilot"`. A fase `main` exige **4 projetos × 3 funções × 1 agente
Codex × 3 condições (L/R/A) × 3 repetições = 108 trajetórias**, avaliação Docker
e evidências do piloto do Codex nas três condições. O modelo, a versão, os
limites, o ambiente e a implementação devem coincidir com os validados. O
piloto usa alvos externos à matriz principal. Outros agentes ficam para
trabalhos futuros; não são necessários para concluir a coleta atual.

## Documentação relacionada

- [README](../README.md): instalação, comandos e protocolo geral.
- [Adaptadores](ADAPTERS.md): autenticação, capacidades e limites de isolamento.
- [Avaliação](AVALIACAO.md): aprovação, cobertura e detecção de defeitos.
- [Verificação](VERIFICACAO.md): testes e pilotos já executados.
