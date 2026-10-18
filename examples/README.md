# Projetos didáticos

Os pilotos `codex-pilot.json` e `native-pilot.json` usam somente Codex, dois
projetos didáticos, L/R/A e uma repetição: **seis gerações**. Eles não são a
matriz principal de **108 gerações** (quatro projetos, três funções por projeto,
Codex, L/R/A e três repetições). `evidence.template.json` registra apenas a
versão do Codex e mantém as confirmações falsas até a verificação.

Estes projetos permitem testar o funcionamento do ContextLab antes de conectar
agentes e selecionar os projetos do estudo principal. São exemplos autorais,
pequenos e fictícios; não representam uma amostra experimental.

| Projeto | Unidade alvo | Informação fora do arquivo focal | Defeito demonstrado |
| --- | --- | --- | --- |
| `loja` | `loja.frete.calcular_frete` | Tipo `Cliente` e função `tarifa` | Excluir peso igual a cinco do desconto VIP |
| `agenda` | `agenda.preco.calcular_preco` | Tipo `Reserva` e função `tarifa_hora` | Excluir duração igual a duas horas do desconto |

Cada diretório contém três partes:

- O pacote de produção (`loja/` ou `agenda/`) e `docs/regras.md`, elegíveis como contexto.
- `reference/`, com testes reservados ao avaliador. Um teste testemunha passa na
  versão original e falha com o defeito indicado no manifesto.
- As saídas autorais em `../fixtures/`, usadas pelo adaptador `fixture` para
  verificar o fluxo completo sem credenciais ou chamadas a modelos.

O manifesto `demo.json` contém **seis trajetórias**: dois projetos, uma função
por projeto, um adaptador `fixture`, três condições e uma repetição. O mesmo
arquivo de teste autoral é devolvido em L, R e A; seus resultados **não permitem
comparar estratégias de contexto nem agentes reais**. A finalidade é conferir
planejamento, preparação, avaliação e registro.

Os valores de limite em `demo.json` são configurações práticas desta
demonstração. Eles não foram calibrados para a pesquisa e não justificam limites
do experimento principal. A lista de defeitos tem apenas um caso por alvo;
detectar esses casos não equivale a avaliar uma campanha ampla de mutação.

O manifesto mantém produção e documentação na lista `include`, e adiciona
`reference/` somente em `evaluation_include`. Não adicione os testes de
referência nem `fixtures/` ao contexto disponibilizado aos agentes.

## Conferir os projetos diretamente

Com `pytest` instalado, a partir da pasta `contextlab/`:

```bash
cd examples/loja
python -m pytest reference -q
cd ../agenda
python -m pytest reference -q
```

Consulte o [README do ContextLab](../README.md) para executar o manifesto,
inspecionar os pacotes L/R/A e conectar os agentes. O backend local desta
demonstração executa os testes autorais na máquina atual; para testes produzidos
por agentes, use o avaliador isolado descrito nesse README.
