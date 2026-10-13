# Serviço de códigos do Sino

Serviço centralizado da Etapa 8 (ERS v6.0): gera, envia e valida os códigos de
e-mail do cadastro, da alteração de e-mail e da recuperação de senha, e assina
a autorização que o aplicativo confere localmente. O contrato está em
[`docs/contrato-servico-codigos.md`](../docs/contrato-servico-codigos.md).

**Estado:** contrato v1.1 (restrição de destinatários da E3, ERS v7.0 5.49),
validado localmente e publicado no repositório com a Sino 6.2. O serviço de
produção **não foi publicado** e nenhum e-mail real foi enviado. Na E4, o
ambiente remoto de testes (T1, sem envio) foi usado e encerrado em 12/10/2026;
o ambiente T2 (primeiro envio real) está preparado no código, sem deploy (ver
abaixo).

## Organização

| Pasta | Conteúdo |
|---|---|
| `src/nucleo/` | Regras (5.32, limites, reserva global, envio incerto, retenção), criptografia e autorização assinada; sem nada da Cloudflare |
| `src/envio/` | Fronteira com o provedor (`Enviador`), adaptador da Resend (com Reply-To), remetente e Reply-To obrigatórios (`enderecos.ts`), textos dos e-mails, enviador simulado para os testes e enviador de descarte do ambiente de teste |
| `src/fluxos.ts`, `src/http.ts` | Orquestração entre os objetos e rotas HTTP do contrato |
| `src/objetos.ts`, `src/ambiente.ts` | Durable Objects com SQLite; segredos e dependências comuns às entradas |
| `src/index.ts`, `src/dev.ts`, `src/teste.ts`, `src/t2.ts` | Entradas do Worker: produção (Resend), desenvolvimento (caixa local), ambiente remoto de testes do T1 (descarte e token, `src/acesso_teste.ts`) e ambiente T2 (produção + token) |
| `test/nucleo/` | Testes das regras com o SQLite do Node (mesmos comandos SQL dos objetos) |
| `test/workers/` | Testes no simulador local dos Durable Objects (concorrência, falhas parciais, alarmes) |
| `ferramentas/` | Ferramentas locais: caixa de mensagens e modo de demonstração (desenvolvimento), `destinatarios.py` (gera a lista de destinatários), `teste_remoto.py` (roteiro do T1), `t2_segredos.py` e `t2_app.py` (segredos e cópia isolada do app do T2) |

## Testes

Requer Node.js 24 (LTS). Os testes não acessam a rede: o `fetch` global é
bloqueado no núcleo e o simulador recusa qualquer requisição de saída.

```bash
npm ci
npm test            # núcleo + simulador local
npm run typecheck
```

O simulador local roda sem login nem conta na Cloudflare.

## Segredos

Nenhum segredo fica no repositório. Para rodar o Worker localmente, copie
`.dev.vars.example` para `.dev.vars` (ignorado pelo Git) e preencha só na sua
máquina. Os valores usados nos testes (`vitest.config.ts`) são fixos e não são
credenciais.

## Lista de destinatários (contrato v1.1)

O serviço só envia códigos aos endereços da lista do ambiente
(`DESTINATARIOS_PERMITIDOS`), em todas as entradas, inclusive a de
desenvolvimento: sem lista válida, responde indisponível (503). A lista guarda
só resumos HMAC (até 50) e é gerada localmente, sem mostrar e-mails, a chave ou
os resumos:

```bash
.venv/bin/python servidor/ferramentas/destinatarios.py gerar --chave <arquivo com CHAVE_HMAC> --saida <arquivo novo>
```

Os e-mails são digitados sem eco (vazio termina). O arquivo de saída (600, nunca
sobrescrito) tem o valor do segredo. Trocar a `CHAVE_HMAC` exige gerar a lista
de novo. A publicação do segredo só acontece com autorização (E4). Regras,
respostas e limites (a revogação não é instantânea) estão no contrato.

## Ambiente remoto de testes (E4, T1; encerrado em 12/10/2026)

Usado de 08 a 12/10/2026 e excluído pela autora (ver propostas, "T1 —
encerramento"). Fica registrado como referência:

`wrangler.teste.jsonc` descreve um Worker **separado**
(`sino-servico-codigos-teste`, só em `workers.dev`, sem URLs de prévia e com os
registros do Worker desligados), com a entrada `src/teste.ts`:

- **sem envio real por construção:** as mensagens são descartadas
  (`EnviadorDescarte`: sem rede e sem registro); a entrada não importa o
  adaptador da Resend nem a caixa local, e não lê `RESEND_API_KEY`;
- **token obrigatório:** toda requisição precisa de
  `Authorization: Bearer <TOKEN_TESTE>`; sem ele, a resposta é a mesma 404 de
  uma rota inexistente, antes de ler o corpo e de tocar nos objetos;
- regras, limites, lista de destinatários e retenção iguais aos da produção.

Como o código é descartado, o ambiente remoto **não** testa a validação com o
código correto (esse caminho fica com os testes locais). Segredos exclusivos,
só com destinatários fictícios (`.invalid`), numa pasta nova fora do
repositório:

```bash
python3 ferramentas/teste_remoto.py preparar --pasta <pasta nova> --url <URL do Worker de teste>
python3 ferramentas/teste_remoto.py basico --config <pasta>/teste_remoto.json   # e, em outras horas UTC: limite-destino, ip
```

Cada comando do roteiro roda numa hora UTC diferente; o roteiro recusa os
horários que passariam dos limites do contrato (que ele não altera).

Todo comando do Wrangler deste ambiente leva `-c wrangler.teste.jsonc` (sem
ele, a configuração seria a de produção). Deploy, segredos remotos e remoção
só com autorização (plano e comandos em `docs/ERS_v7.0_propostas.md`, "E4").

## Ambiente T2 (E4; primeiro envio real; preparado no código, sem deploy)

**Objetivo:** um Worker **temporário** (`sino-servico-codigos-t2`, no máximo 7
dias depois do deploy, excluído ao encerrar) para o primeiro envio real de
e-mail pela Resend, só para os endereços autorizados pela autora. Nada foi
publicado: não houve deploy, chave da Resend nem envio.

**Diferenças em relação à produção** (`src/index.ts`, `wrangler.jsonc`, nunca
publicada): a entrada `src/t2.ts` é a de produção — Resend, `REMETENTE` e
`RESPONDER_PARA` obrigatórios, lista de destinatários, limites, idempotência e
retenção — envolvida por um **token exclusivo** (`TOKEN_ACESSO`): toda
requisição precisa de `Authorization: Bearer <token>`; sem ele, com outro valor
ou com o segredo ausente, a resposta é a mesma 404 de uma rota inexistente,
antes de ler o corpo e de tocar nos objetos. O token nunca é registrado. É uma
barreira adicional: a lista de destinatários continua valendo.

**Configuração** (`wrangler.t2.jsonc`, só valores não secretos):

- remetente `Sino <nao-responda@envios.appsino.com.br>` e Reply-To
  `sino.lembrete.contas@gmail.com` (aprovados pela autora); KID `t2-1`;
- só `workers.dev`, sem rotas nem domínio personalizado, **Preview URLs
  desligadas**;
- **Workers Logs, registros de invocação, Traces e Issues desligados**
  (amostragem 0, sem persistência), como descreve a Política de Privacidade;
- três Durable Objects **do próprio Worker** (sem `script_name`; migração `v1`):
  nenhum armazenamento do T1 ou da produção é reaproveitado;
- segredos (`CHAVE_HMAC`, `CHAVE_ASSINATURA`, `DESTINATARIOS_PERMITIDOS`,
  `TOKEN_ACESSO`, `RESEND_API_KEY`) só no deploy, por `--secrets-file`, a
  partir de um arquivo fora do Git.

Todo comando do Wrangler deste ambiente leva `-c wrangler.t2.jsonc` (sem ele,
a configuração seria a de produção).

### Ferramentas (Linux; `.venv` do projeto)

`ferramentas/t2_segredos.py` prepara os segredos **novos e exclusivos** do T2:

```bash
.venv/bin/python servidor/ferramentas/t2_segredos.py preparar --pasta <pasta nova, caminho absoluto> --url https://sino-servico-codigos-t2.<subdomínio>.workers.dev
.venv/bin/python servidor/ferramentas/t2_segredos.py chave-resend --pasta <pasta>   # num terminal interativo
.venv/bin/python servidor/ferramentas/t2_segredos.py descartar --pasta <pasta>      # só preparação incompleta
```

- a pasta precisa ser nova ou vazia, com caminho absoluto, fora do projeto e
  de qualquer repositório Git; fica com permissão **700**;
- os e-mails autorizados são digitados sem eco; viram a lista de resumos HMAC
  (até 50), nunca mostrada;
- grava, em arquivos **600** que nunca são sobrescritos, `segredos.json`
  (para `--secrets-file`) e `app_t2.json` (URL, chave pública `t2-1` e token,
  só para `t2_app.py`); `.t2_segredos_estado` fica `incompleto` durante a
  gravação e `concluido` no fim; uma falha no meio apaga só o que esta execução
  criou;
- `chave-resend` só aceita a chave **digitada num terminal interativo**
  (entrada redirecionada ou por pipe é recusada) e a acrescenta por troca
  atômica; nunca a mostra;
- `descartar` recupera uma preparação interrompida: apaga só os arquivos da
  ferramenta e recusa pastas concluídas ou com outros arquivos.

`ferramentas/t2_app.py` abre uma **cópia isolada** do Sino contra o T2:

```bash
.venv/bin/python servidor/ferramentas/t2_app.py preparar --destino <pasta nova, caminho absoluto> --revisao <SHA completo publicado>
.venv/bin/python servidor/ferramentas/t2_app.py abrir    --destino <pasta> --segredos <pasta dos segredos>
.venv/bin/python servidor/ferramentas/t2_app.py remover  --destino <pasta>   # mostra o que apagaria; --confirmar apaga
```

- `preparar` exige o **SHA completo** de um commit já publicado em
  `origin/main` (a referência local; atualize-a antes), sem links simbólicos
  nem submódulos, com o cliente com token, `src/t2.ts` e `wrangler.t2.jsonc`;
  extrai a revisão com `git archive` e confere que `db.py`, banco e backups da
  cópia ficam dentro dela (o banco real nunca é usado nem aberto); a marca
  `.sino_t2_copia` fica `incompleta` até o fim e `concluida` depois;
- `abrir` (ação explícita) confere a cópia, a configuração e o interpretador
  (Flet, httpx e cryptography com `-E -s`) e abre o app com um **ambiente
  fechado**: só as variáveis do sistema necessárias para a janela (listadas,
  com o motivo, em `VARIAVEIS_DO_SISTEMA`) e `SINO_SERVICO_URL`,
  `SINO_SERVICO_CHAVES` e `SINO_SERVICO_TOKEN`, nunca na linha de comando;
  enquanto o app roda, a cópia fica travada;
- `remover` recusa uma cópia em uso (trava, processo com a cópia como
  diretório de trabalho ou nos argumentos, arquivos temporários do SQLite);
  sem `--confirmar`, só mostra as contagens; com `--confirmar`, apaga pelo
  descritor de cada pasta, sem seguir links nem atravessar montagens, e para
  se uma pasta for trocada; a pasta só é removida se tiver sido criada pela
  ferramenta.

**Limitações:** as conferências evitam acidentes; outro processo do mesmo
usuário ainda pode ler as pastas 700 e alterar a cópia. A verificação de
processos usa `/proc` (Linux). A revisão "publicada" é a da referência local.
Apagar arquivos não garante a eliminação física em SSDs, instantâneos ou
armazenamento com cópia na escrita; o que invalida a chave é **revogá-la na
Resend**. O procedimento completo (do commit ao encerramento) está em
`docs/ERS_v7.0_propostas.md`, "E4 — T2: preparação técnica".

## Modo de demonstração (desenvolvimento)

Para apresentar o cadastro, a recuperação de senha e a alteração de e-mail
sem enviar e-mails: o serviço roda localmente (`wrangler.dev.jsonc`, entrada
`src/dev.ts`) e entrega as mensagens a uma caixa neste computador
(`ferramentas/caixa_dev.py`). A integração com a Resend (`src/index.ts`,
`wrangler.jsonc`) não muda e não é usada.

**Início** (na raiz do projeto, com o `.venv` e o Node.js 24 instalados):

```bash
.venv/bin/python servidor/ferramentas/demonstracao.py ~/sino-demonstracao --node-bin <pasta do npx>
```

- A pasta (aqui `~/sino-demonstracao`) precisa ficar **fora do projeto**. Ela
  guarda a cópia do código (`app/`, extraída do commit atual com `git archive`),
  o banco da demonstração, as mensagens (`caixa_dev/`), as chaves
  (`segredos_dev.env`, `app_dev.env`, permissão 600), o estado do serviço e
  os logs. Se ela estiver dentro de um repositório Git, precisa estar ignorada
  (por exemplo, em `.git/info/exclude`); senão o comando se recusa a usá-la.
- O banco nasce **vazio**, criado pelo inicializador normal do Sino ao abrir o
  app. O banco real (`database/sino.db`) nunca é copiado.
- Nas execuções seguintes, a mesma pasta é reutilizada com os cadastros da
  demonstração. Se ela for de outra revisão (ou o banco for de uma versão mais
  nova), o comando para sem alterar nada; use `--revisao` ou outra pasta.
- Alterações não commitadas em `backend/` ou `database/` não entram na cópia
  (o comando avisa).
- O serviço, a caixa e o inspetor escutam só em `127.0.0.1` (portas 8787, 8025
  e 9229, que precisam estar livres).
- A janela se chama **"Sino — Demonstração"** e as telas com código mostram
  **"Modo de demonstração — códigos recebidos neste computador"**. O app só
  entra nesse modo com `SINO_MODO_DEMONSTRACAO=1` **e** o serviço em
  `http://127.0.0.1:<porta>`.
- Cada mensagem nova é aberta no editor padrão (`xdg-open`). Se não abrir, a
  mensagem continua em `caixa_dev/` e o terminal mostra o caminho do arquivo
  (o terminal nunca mostra o código).

**Encerramento:** feche a janela do app (ou use Ctrl+C no terminal). O comando
encerra o serviço e a caixa que ele mesmo iniciou e informa se as portas
ficaram livres.

**Limitações:**

- A conta fica com o e-mail **verificado no banco da demonstração**, mas o
  código foi lido neste computador: isso **não comprova** acesso ao endereço
  informado.
- Qualquer pessoa com acesso a este computador pode ler os códigos.
- Não serve para usuários reais nem para produção.
- As regras dos códigos são as normais (validade de 10 minutos, 5 tentativas,
  reenvio após 60 segundos e limites por endereço e por conexão).
- Como na produção, o serviço local só aceita os endereços da lista, que na
  demonstração são só três **fictícios**: `pessoa1@demonstracao.invalid`,
  `pessoa2@demonstracao.invalid` e `pessoa3@demonstracao.invalid` (domínio
  reservado, que nunca recebe e-mail). Eles aparecem no terminal e em
  `destinatarios_ficticios.txt`, na pasta da demonstração. Outro endereço
  recebe "O envio de códigos está restrito nesta fase do Sino." no cadastro e
  na alteração; na recuperação, a resposta é a de sempre e nada é enviado.
- Pastas de demonstração de versões anteriores (sem a lista) não são
  reaproveitadas: o comando para sem alterar nada; use uma pasta nova.

## Licença

O serviço faz parte do Sino e segue o [`LICENSE`](../LICENSE) da raiz do
repositório: licença MIT com a condição "Commons Clause" v1.0 (código-fonte
disponível, não open source; o direito de vender não é concedido). As
dependências seguem as próprias licenças.
