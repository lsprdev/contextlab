# Experimento do TCC

Material da avaliação experimental do TCC *Seleção de contexto na geração de
testes unitários por agentes de programação: uma avaliação experimental*
(Gabriel Lopes Pereira, IFC Campus Araquari, 2026): 4 projetos Python × 3
funções × L/R/A × 3 repetições = **108 gerações** com o Codex.

A coleta usou o ContextLab na tag [`v0.1.0`](https://github.com/lsprdev/contextlab/tree/v0.1.0).
Os resultados também estão em [contextlab.lspr.dev](https://contextlab.lspr.dev),
na página **Experimento**.

## Configuração congelada

| Item | Valor |
|---|---|
| Modelo | `gpt-6.2-sol`, esforço de raciocínio `medium` |
| Cliente | `codex-cli 0.170.0` |
| Avaliador | imagem `sha256:5fae9b0d2ee1…` (`avaliador/`), Python 3.12.11, pytest 8.4.2, coverage 7.10.7 |
| Limites | 30.000 caracteres de contexto, 20 consultas, 300 s de geração, 60 s de avaliação |
| Semente | 20261121 |
| Lock | `manifesto/principal.lock.json`, `lock_hash 49dd66a5…` |

## Projetos e revisões

O código dos projetos não é copiado. O manifesto aponta as revisões:

| Projeto | Versão | Revisão |
|---|---|---|
| [Fava](https://github.com/beancount/fava) | 1.30.16 | `d8d426f9cbf08ace852a4a319adb4b9dda853b69` |
| [bump-my-version](https://github.com/callowayproject/bump-my-version) | 1.8.1 | `22dbc5c88dba0ce5552078b48278d96467264b6d` |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.2.4 | `a565c2cc41599c48eabc6b7b7f5b826d43c5a6d7` |
| [python-stdnum](https://github.com/arthurdejong/python-stdnum) | 2.2 | `52d316200c347b4f3d2b61a77ce746f3d28a3815` |

## Conteúdo

| Pasta | Conteúdo |
|---|---|
| `manifesto/` | `gerar_manifesto.py` (fonte dos manifestos), `principal.json`, `piloto.json`, a evidência de congelamento e os dois locks. |
| `avaliador/` | Dockerfile e versões exatas das dependências da imagem de avaliação. |
| `referencias/` | Testes de referência dos 12 alvos (`test_ref_*.py`) e dos 4 alvos do piloto (`piloto/`). Em cada projeto, ficam em `tcc_referencia/`. |
| `defeitos/` | `candidatos.json`: os 20 defeitos controlados (trecho original e alterado). A testemunha de cada um está no manifesto. |
| `verificacoes/` | Scripts de conferência do ambiente, dos defeitos e de triagem da revisão. |
| `precos.json` | Tarifas de API do `gpt-6.2-sol` usadas no cenário de custo (consulta de 22/11/2026). |
| `resultados/coleta/` | `report.md`, `report.json`, `results.csv` e, em `tentativas/`, o `record.json` de cada uma das 108 tentativas e o teste entregue nas 105 que produziram arquivo. |
| `resultados/piloto/` | O mesmo para as 12 gerações do piloto. |

Os registros brutos das sessões (`agent/native.jsonl`), os contextos entregues
(que contêm código dos projetos) e as cópias de avaliação não foram publicados.
Os locks preservam os caminhos da máquina onde a coleta rodou, porque
alterá-los invalidaria o `lock_hash`.

## Resultados em resumo

| | L | R | A |
|---|---|---|---|
| Suítes aprovadas | 30/36 (83%) | 25/36 (69%) | 30/36 (83%) |
| Cobertura focal e detecção (aprovadas) | 100% | 100% | 100% |
| Tokens de entrada por tentativa | 23,8 mil | 23,7 mil | 77,0 mil¹ |
| Custo estimado por suíte aprovada (API) | US$ 0,044 | US$ 0,054 | US$ 0,060¹ |

¹ Três tentativas de A atingiram o limite de contexto sem contagem de tokens.
A média de tokens descreve as 33 tentativas com medição, e o custo por suíte
aprovada é um limite inferior.

## Reproduzir

1. Clone os quatro projetos nas revisões acima em `projetos/` e copie
   `referencias/<projeto>/` para `projetos/<projeto>/tcc_referencia/`.
2. Construa a imagem em `avaliador/` e atualize o ID em `gerar_manifesto.py`.
3. Gere os manifestos e valide:
   ```bash
   cd manifesto
   python3 gerar_manifesto.py
   contextlab validate principal.json --out ../validacao/NOVA
   ```
4. Rode um piloto (`piloto.json`), congele com a sua evidência e execute
   `contextlab run`. As respostas do modelo não são determinísticas: uma nova
   coleta não reproduz as mesmas entregas, mas o mesmo protocolo.
