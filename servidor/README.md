# Serviço de códigos do Sino

Serviço centralizado da Etapa 8 (ERS v6.0): gera, envia e valida os códigos de
e-mail do cadastro, da alteração de e-mail e da recuperação de senha, e assina
a autorização que o aplicativo confere localmente. O contrato está em
[`docs/contrato-servico-codigos.md`](../docs/contrato-servico-codigos.md).

**Estado:** contrato v1.1 (restrição de destinatários da E3, ERS v7.0 5.49),
validado localmente e publicado no repositório com a Sino 6.2. **Produção
restrita publicada e validada em 15/10/2026** (`sino-servico-codigos` em
`https://sino-servico-codigos.appsino.workers.dev`, só para os dois
destinatários autorizados da autora; ver "Produção restrita"). Na E4, o ambiente remoto de
testes (T1, sem envio) foi usado e encerrado em 12/10/2026; o ambiente T2
(primeiro envio real) foi usado em 13 e 14/10/2026 para testes restritos e
**encerrado e desmontado em 14/10/2026**: oito e-mails reais, todos Delivered,
só para um único destinatário autorizado (ver abaixo). **E4 encerrada
formalmente pela autora em 15/10/2026** (produção restrita; P43 não atendida,
com risco aceito só para ela; M8 aberta; Sino não liberado ao público; ver
`docs/ERS_v7.0_propostas.md`, "Encerramento formal da E4").

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
| `ferramentas/` | Ferramentas locais: caixa de mensagens e modo de demonstração (desenvolvimento), `destinatarios.py` (gera a lista de destinatários), `teste_remoto.py` (roteiro do T1), `t2_segredos.py` e `t2_app.py` (segredos e cópia isolada do app do T2), `producao_segredos.py` (segredos da produção restrita) |

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
credenciais. Os segredos da produção são outros e nunca passam por `.dev.vars`
(ver "Produção restrita").

## Produção restrita (E4/M8; decisões 5 e 6 de 15/10/2026; publicada em 15/10/2026)

**Situação (15/10/2026):** publicada pela autora em
`https://sino-servico-codigos.appsino.workers.dev` (Workers Free, Resend Free,
dois destinatários autorizados), com o aplicativo configurado para ela
(`backend/servico_codigos.py`, commit `db00f44`). Validada: teste fora da lista
(403, sem envio), cadastro definitivo, CT138 e expiração no próprio serviço.
CPU (P43): critério original não atendido, risco aceito só para a produção
restrita. Encerramento operacional concluído em 15/10/2026: cópia de
recuperação criptografada conferida (com cópia externa), arquivos da pasta de
segredos apagados um a um, `npx wrangler logout` e registros locais do
Wrangler removidos. Registro completo em `docs/ERS_v7.0_propostas.md`,
"Implantação e validação da produção restrita (15/10/2026)" e "Encerramento
operacional e decisão 9 (15/10/2026)".

Configuração em `wrangler.jsonc` (fixada por `test/nucleo/ambiente_producao.test.ts`):
Worker `sino-servico-codigos`, entrada `src/index.ts`, só
`https://sino-servico-codigos.<subdomínio>.workers.dev` (subdomínio neutro da
conta, decisão 1; pretendido `appsino`, sujeito à disponibilidade), sem rotas
nem Preview URLs. Variáveis só públicas: `KID_ASSINATURA` `prod-1` (exclusivo
da produção), `REMETENTE` e `RESPONDER_PARA`. Edite-as no arquivo, nunca no
painel: o deploy substitui as variáveis pelas do arquivo.

**Observabilidade (decisão 6, alternativa A):** Workers Logs, registros de
invocação, Traces e Issues desligados, como no T2 (a Política de Privacidade
descreve Logs e Traces desligados). O acompanhamento usa só as métricas
agregadas dos painéis (Cloudflare: requisições, erros, CPU e duração, Durable
Objects; Resend: cota e situação dos envios). `wrangler tail` só em incidente
autorizado pela autora, na tela, sem gravar em arquivo. O próprio código
registra só contexto e tipo do erro (`src/nucleo/registro.ts`).

**Segredos (decisão 5):** `CHAVE_HMAC`, `CHAVE_ASSINATURA`,
`DESTINATARIOS_PERMITIDOS` e `RESEND_API_KEY` ficam nos Workers Secrets,
enviados no próprio deploy com `--secrets-file` (sem intervalo sem segredos).
São novos, nunca os do desenvolvimento, do T1 ou do T2. A chave da Resend é
exclusiva da produção (só envio, restrita a `envios.appsino.com.br`). A
autora guarda no gerenciador de senhas uma cópia de recuperação da
`CHAVE_HMAC` (sem ela, a lista de destinatários não pode ser atualizada sem
trocar a chave) e da semente Ed25519 (`CHAVE_ASSINATURA`). A lista e a chave
da Resend não são guardadas: a lista é regenerada a partir da `CHAVE_HMAC` e
a chave da Resend é revogada e recriada se perdida. Arquivos `.env` e
`.env.*` são ignorados pelo Git em qualquer pasta.

```bash
.venv/bin/python servidor/ferramentas/producao_segredos.py preparar --pasta <pasta nova, caminho absoluto> --url https://sino-servico-codigos.<subdomínio>.workers.dev
.venv/bin/python servidor/ferramentas/producao_segredos.py chave-resend --pasta <pasta>   # num terminal interativo
.venv/bin/python servidor/ferramentas/producao_segredos.py conferir --pasta <pasta>       # sem mostrar valores
.venv/bin/python servidor/ferramentas/producao_segredos.py descartar --pasta <pasta>      # só preparação incompleta
```

- mesmas garantias de `t2_segredos.py` (pasta 700 fora de qualquer repositório
  Git, arquivos 600 nunca sobrescritos, e-mails sem eco, nada sensível no
  terminal, desfazimento de falhas);
- grava `segredos.json` (para `--secrets-file`), `recuperacao.json` (cópia de
  recuperação: `CHAVE_HMAC`, semente, KID e chave pública) e
  `app_producao.json` (só valores públicos: URL e chave pública `prod-1`, para
  a versão do aplicativo);
- `conferir` confere formatos, a lista contra a `CHAVE_HMAC`, a cópia de
  recuperação, a correspondência entre semente e chave pública (uma
  autorização fictícia assinada com a semente e verificada pelo código do
  aplicativo), o KID de `wrangler.jsonc` e a presença da chave da Resend.

Deploy (só com autorização da autora, no terminal dela): na pasta `servidor/`,
`npx wrangler deploy --secrets-file <pasta>/segredos.json`. Depois:
conferência no painel (Logs, Traces, Issues e Preview URLs desligados; três
variáveis; quatro segredos só por nome), cópia de recuperação guardada,
arquivos da pasta apagados um a um e `npx wrangler logout`.

**Rotação:** a chave de assinatura e o `KID_ASSINATURA` mudam sempre no MESMO
deploy (com `--secrets-file`), depois de uma versão do aplicativo que conheça
as duas chaves públicas; autorizações em andamento podem ser recusadas na
troca, mas os códigos pendentes não dependem dessa chave. Trocar a
`CHAVE_HMAC` invalida os códigos pendentes, zera os contadores de limite
(objetos com outro nome) e exige gerar a lista de novo no mesmo deploy.

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

## Ambiente T2 (E4; primeiro envio real; encerrado em 14/10/2026)

**Objetivo:** um Worker **temporário** (`sino-servico-codigos-t2`, no máximo 7
dias depois do deploy; a Cloudflare não o exclui sozinha: a exclusão é
**manual**, no encerramento) para o primeiro envio real de
e-mail pela Resend, só para os endereços autorizados pela autora.

**Situação:** implantado em 13/10/2026; oito e-mails reais, todos Delivered,
para um único destinatário autorizado; **encerrado em 14/10/2026**, antes do
prazo de 20/10/2026. Worker, chave da Resend (`sino-t2-temporario`), cópia
isolada e segredos locais removidos; logout do Wrangler e remoção dos 14
registros locais temporários. O domínio `envios.appsino.com.br` foi mantido.
Não houve implantação definitiva nem validação de produção. Resultados,
ressalvas e evidências em `docs/ERS_v7.0_propostas.md`, "E4 — T2: execução e
testes reais" e "E4 — avaliação dos critérios". A descrição abaixo fica como
referência para um próximo ambiente.

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
a configuração seria a de produção), **inclusive a exclusão do Worker**.

**Autenticação:** o login no Wrangler (`npx wrangler login`) é feito pela
autora, no terminal dela. A sessão expira: depois disso, qualquer comando
autenticado exige renovar a sessão ou fazer novo login, por isso nenhum deles é
executado sem autorização. `npx wrangler logout` faz parte do encerramento.

**Encerramento (resumo; cada etapa com autorização):** registro final das
evidências (painéis da Cloudflare e da Resend, banco da cópia) **antes** de
excluir qualquer coisa; `t2_app.py remover`; exclusão manual do Worker, pelo
painel ou com `npx wrangler delete -c wrangler.t2.jsonc` num terminal
interativo; **revogação da chave na Resend**; remoção controlada da pasta dos
segredos; `npx wrangler logout`; nova conferência do banco real e dos backups.
Executado em 14/10/2026; detalhes em `docs/ERS_v7.0_propostas.md`, "E4 — T2:
execução e testes reais".

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
`docs/ERS_v7.0_propostas.md`, "E4 — T2: preparação técnica"; a situação dos
testes e o encerramento atualizado, em "E4 — T2: execução e testes reais".

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
