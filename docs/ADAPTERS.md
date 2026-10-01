# Adaptadores nativos e limites de validação

O ContextLab chama **Codex CLI** e **Claude Code CLI** como processos nativos.
Não substitui esses agentes por uma chamada direta a um modelo. O modo
`fixture` é uma demonstração separada e não gera evidência de desempenho de IA.

## Fluxo de uma geração

1. `doctor_agent` verifica o executável, versão, opções obrigatórias e a
   disponibilidade de credenciais, sem iniciar uma conversa com o modelo.
2. `run_agent` cria uma pasta temporária e configurações novas. Não copia o
   projeto completo para o diretório de trabalho do agente.
3. Um servidor MCP local recebe um dicionário de arquivos virtuais permitidos.
   Ele expõe somente `list_files`, `read_file` e `search`. Os caminhos enviados
   pelo modelo são chaves desse dicionário, nunca caminhos abertos no sistema.
4. A sessão começa sem retomada. O pacote inicial L/R já está no prompt; A
   consulta o MCP conforme sua decisão. Todas as respostas das ferramentas e
   releituras consomem o orçamento comum do broker.
5. A resposta final deve ser um objeto `{"test_code": "..."}`. O orquestrador
   recolhe esse texto. O agente não escreve o arquivo de teste, não o executa e
   não recebe retorno da avaliação.
6. O processo termina; somente então pode começar a avaliação separada.

O MCP usa JSON-RPC em stdio. Atingir limite de conteúdo ou de chamadas encerra o
servidor sem uma resposta substituta não contabilizada; o orquestrador observa
essa condição e termina o grupo de processos do agente. O limite de tempo
também encerra o processo e seus filhos em sistemas POSIX. As credenciais não
são enviadas às ferramentas nem registradas em resultados.

## Configuração do manifesto

```json
{"id": "codex", "kind": "codex", "model": "IDENTIFICADOR_EXPLICITO", "binary": "codex"}
```

```json
{"id": "claude", "kind": "claude", "model": "IDENTIFICADOR_EXPLICITO", "binary": "claude"}
```

`binary` é opcional e pode indicar um caminho absoluto para o binário instalado.
Não é um comando shell. `model` deve ser definido antes do piloto e congelado
para a coleta. Não há escolha automática de modelo alternativo no adaptador.

## Autenticação reutilizável

**Codex:** o modo padrão usa `CODEX_API_KEY`, lido somente pelo processo cliente.
Alternativamente, um agente Codex pode declarar `auth_file` com o caminho
absoluto de um `auth.json` já obtido por um login autorizado do próprio usuário.
Somente esse arquivo é copiado para a configuração temporária da sessão.
Histórico, memória, plugins e configurações pessoais não são copiados.
Quando declarado, `auth_file` tem precedência sobre uma `CODEX_API_KEY` presente
no ambiente; um arquivo ausente não provoca fallback silencioso de autenticação.

Se o cliente atualizar as credenciais, o adaptador preserva o arquivo atualizado
no caminho indicado, com permissões restritas, desde que a fonte não tenha
mudado concorrentemente. Não execute duas sessões simultâneas compartilhando
esse arquivo. O harness executa a matriz sequencialmente. Não coloque credenciais
no repositório nem em `runs/`. A chave ou autenticação é reutilizável entre
sessões novas; não é necessário logar novamente a cada geração. Expiração ou
revogação ainda pode exigir renovar o login.

**Claude Code:** esta implementação usa `--bare`, que, segundo a documentação
oficial consultada, **não lê OAuth nem o keychain da assinatura**. Portanto,
requer `ANTHROPIC_API_KEY`; ter apenas uma assinatura Claude não torna esse
adaptador pronto. Isso é uma restrição desta integração, não uma exigência geral
do Claude Code. A chave é reutilizada sem armazená-la no manifesto ou nos logs.
A cobrança e os limites de API devem ser considerados no piloto.

## Restrições aplicadas

| Cliente | Configuração relevante |
|---|---|
| Codex | `exec --json --ephemeral --ignore-user-config --sandbox read-only`; modelo explícito e catálogo restrito; schema de saída; shell, apps, subagentes, memórias, hooks, goals, plugins, skills, web, imagens e navegador desabilitados; instruções de projeto zeradas; somente o servidor MCP ContextLab configurado e obrigatório. |
| Claude Code | `--print --bare --restricted --tools "" --strict-mcp-config --setting-sources "" --no-session-persistence --permission-mode dontAsk`; somente os três MCPs pré-aprovados; modelo explícito; saída stream-json e schema. |

`doctor` recusa uma CLI sem as opções necessárias. Para Codex, confere as flags
e o inventário real de ferramentas com um provedor simulado em localhost, sem
credenciais nem chamadas a modelos. O diagnóstico também envia uma chamada de
shell inexistente e uma leitura de arquivo externo ao pacote, exigindo recusa;
uma leitura autorizada funciona como controle positivo. Configurações
temporárias não substituem nem apagam as configurações pessoais do usuário.
Restrições administrativas do cliente permanecem aplicáveis; se forem
incompatíveis, a execução falha, sem tentar contorná-las.

No Codex CLI 0.159.3, o catálogo de `gpt-6-luna` força `unified_exec` ativo,
Code Mode e subagentes v2 apesar de algumas flags antigas. O adaptador deriva
um catálogo do próprio binário, preservando identidade, instruções e parâmetros
de inferência, mas usa ferramentas diretas (`tool_mode=standard`), sem
`apply_patch`, ferramentas experimentais ou descoberta adiada. Desabilita também
`agents.enabled` e `features.multi_agent_v2.enabled`. O hash do catálogo é
registrado no diagnóstico e na geração; nenhuma troca silenciosa de modelo ocorre.

A flag `unified_exec` sozinha não comprova a presença de shell. A verificação
exige ausência de execução, escrita, imagens, navegação, subagentes e Code Mode
no inventário efetivo. Apenas os três MCPs do ContextLab e os auxiliares nativos
`list_mcp_resources`, `list_mcp_resource_templates` e `read_mcp_resource` são
aceitos. Esses auxiliares não abrem arquivos: o único servidor configurado
anuncia listas vazias de recursos/templates e recusa `resources/read`.

O parser rejeita chamadas nativas de comandos, alteração de arquivos, pesquisa
web, outro MCP e tipos inesperados de eventos. Para Claude, também verifica a
lista anunciada de ferramentas. `StructuredOutput` e `EndConversation` são
controles internos de formatação/encerramento sem acesso ao projeto, e são
aceitos além dos três MCPs. Eventos desconhecidos podem exigir atualizar o
adaptador e repetir o piloto com a nova versão.

**Limitação importante:** rejeitar uma trajetória depois de observar uma chamada
proibida não impede que a chamada tenha ocorrido. A auditoria JSONL não equivale
a isolamento do sistema operacional nem prova que todas as capacidades de uma
CLI futura foram removidas. Em especial, a documentação do Codex não oferece
nesta integração uma allowlist única de todos os seus recursos nativos.
O servidor MCP restringe de fato suas próprias leituras; as restrições do cliente
precisam ser verificadas com a versão instalada e com configurações gerenciadas
do ambiente. Uma configuração que permita capacidades extras **não está apta à
coleta**. `doctor` sempre retorna `isolation_verified: false`; essa verificação
pertence ao piloto e ao congelamento do estudo, não à existência das flags.

## Evidência que fica registrada

- `native.jsonl`: saída estruturada nativa, com valores de credenciais conhecidos
  e padrões comuns de segredo redigidos.
- `stderr.txt`: diagnósticos redigidos; o ambiente completo não é gravado.
- `tool_audit.json`: chamadas mediadas, negativas de acesso, caracteres
  entregues, orçamento inicial e motivo de encerramento por limite.
- Resultado da geração: status, resposta, versão, sessão, tempo e contadores de
  uso informados pelo cliente. Campos ausentes permanecem `null`.

Tokens de entrada, saída e cache têm semânticas que podem diferir por provedor.
Os dados brutos de `usage` são preservados; não se inventa custo nem se converte
caracteres para tokens. O total em dólares só aparece quando informado pelo
cliente. O tempo de `run_agent` inclui seu preflight e preparação; o timeout
`generation_seconds` começa ao iniciar o subprocesso de geração.

## Como esta implementação foi verificada

Os testes automatizados usam um executável falso explicitamente
identificado, mas iniciam o servidor MCP real para conferir o transporte,
contabilização de orçamento, recusa de ferramentas, tempo limite e redação de
segredos. Isso testa o adaptador, não os agentes ou a hipótese do TCC. O
diagnóstico local adicional exercita o Codex CLI real com respostas simuladas.
O estado das execuções reais está em [VERIFICACAO.md](VERIFICACAO.md).

No computador do pesquisador, execute o diagnóstico, configure uma credencial,
fixe versões e rode o piloto antes de atestar o congelamento. Verifique tentativas
de leitura fora do pacote, shell, execução, web, histórico e outras integrações,
além de confirmar que não há retorno do avaliador durante a geração. Não use
uma aprovação manual para superar uma negativa de ferramenta do protocolo.

## Fontes oficiais consultadas

Consulta em 28/09/2026 (UTC). Flags são verificadas novamente localmente pelo
diagnóstico; a data desta consulta não fixa uma versão de CLI.

- [Codex: modo não interativo](https://developers.openai.com/codex/noninteractive):
  `exec`, eventos JSONL, saída com schema, `CODEX_API_KEY` e reutilização de auth.
- [Codex: comandos](https://developers.openai.com/codex/cli/reference):
  `--ephemeral`, `--ignore-user-config`, `features list` e argumentos de execução.
- [Codex: configuração](https://developers.openai.com/codex/config-reference):
  flags de capacidades, permissões, MCP obrigatório e lista de ferramentas MCP.
- [Codex: MCP](https://developers.openai.com/codex/mcp): configuração stdio.
- [Claude Code: CLI](https://code.claude.com/docs/en/cli-reference):
  `--restricted` (documentado a partir de 2.1.248), `--tools`, MCP estrito e flags
  de sessões/saída. Versão mínima não garante todas as outras flags: `doctor`
  exige que a instalação as anuncie.
- [Claude Code: uso programático](https://code.claude.com/docs/en/headless):
  `--bare`, sua autenticação por chave, saída estruturada e ausência de retomada.
- [MCP: transporte stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
  e [ferramentas](https://modelcontextprotocol.io/specification/2025-06-18/server/tools):
  framing JSON-RPC, inicialização, schemas e respostas de ferramentas.
