# Câmbio

Uma aplicação Python de terminal para consultar dólar/euro em reais e converter
valores. Possui menu interativo, tabela de cotações e animação durante a consulta.

## Instalar e abrir

Na raiz deste repositório:

```bash
python3 -m venv contextlab/.venv
source contextlab/.venv/bin/activate
python -m pip install -e ./contextlab -e ./projects/cambio
cambio
```

Escolha `1` para consultar, `2` para converter e `0` para sair. A quantidade aceita
vírgula ou ponto decimal, sem separadores de milhares. Ctrl+C encerra o programa.
A opção `cambio --demo` usa valores fictícios e funciona sem internet; o menu
identifica explicitamente essa simulação.

As taxas vêm da [Frankfurter v2](https://frankfurter.dev/), que fornece taxas
diárias sem chave de API. São consultados os pares USD/BRL e EUR/BRL. A tela
mostra a data informada pelo serviço; não representa cotação a cada segundo nem
preço final de compra em uma instituição financeira. A consulta tem timeout e
mensagens para indisponibilidade ou resposta inválida. A interface usa
[Rich](https://rich.readthedocs.io/en/stable/console.html#status).

## Onde está cada parte

| Arquivo/pasta | Responsabilidade |
|---|---|
| `src/cambio/cli.py` | Menu, leitura de entrada e apresentação. |
| `src/cambio/cotacoes.py` | Consulta e interpretação da resposta HTTP. |
| `src/cambio/conversao.py` | Cálculo de conversão, sem rede. |
| `tests/` | Testes automatizados, com respostas fixas para a consulta HTTP. |
| `tutorial/` | Entrega autoral usada na demonstração do ContextLab, sem IA. |
| `contextlab.json` | Função, estratégias, repetições e avaliação. |
| `runs/` | Lotes locais do ContextLab, ignorados pelo Git. |

`converter_para_brl(valor, cotacao)` recebe dois `Decimal` finitos. O valor deve
ser não negativo e a cotação positiva. Os limites didáticos são 1 trilhão para
a quantidade e 1 milhão para a taxa. O resultado é arredondado para centavos,
com metades para cima, independentemente da precisão decimal do chamador.
A aplicação não inclui tarifas, impostos ou transações reais.

## Testar e estudar

Com o ambiente ativado, na raiz:

```bash
python -m pytest -q -p no:cacheprovider projects/cambio/tests
contextlab cambio plan
contextlab cambio context --condition L
```

Os testes automatizados não dependem da API. O
[guia passo a passo](../../contextlab/docs/PRIMEIRO_PROJETO.md) acompanha a primeira
execução. A configuração inicial usa uma tentativa em L e uma entrega já
escrita; não chama o Codex. O projeto está fora das 108 gerações do TCC.
