# Biblioteca de terceiros incluída

| Arquivo | Origem | Versão | Licença |
|---|---|---|---|
| `mermaid.min.js` | <https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js> | 11.4.1 | MIT, Copyright (c) 2014-2022 Knut Sveidqvist |

SHA-256: `a43bc1afd446f9c4cc66ac5dd45d02e8d65e26fc5344ec0ef787f88d6ddb6f9e`

## Logos da animação do passo a passo

Embutidas como SVG em `../tour.html`, sem acesso à internet, só para identificar as ferramentas:

| Logo | Origem | Licença |
|---|---|---|
| Docker, OpenAI | Simple Icons 13.21.0, <https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/> | CC0 1.0 (os ícones); as marcas pertencem aos donos |
| Python | <https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg>, com as cores planas oficiais no lugar dos gradientes | marca da Python Software Foundation |

## Mermaid

Usada somente para desenhar os diagramas da aba Documentação do visualizador.
No modo `serve`, é entregue pelo próprio servidor local; em `--export`, é
embutida na página para que ela abra sem internet. Sem o arquivo, a página
continua funcionando e mostra o texto dos diagramas.
