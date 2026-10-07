# Contrato do serviço de códigos do Sino (Etapa 8)

Versão do contrato: **v1.1** (v1 da Etapa 8 + restrição de destinatários da E3,
ERS v7.0 5.49; o serviço ainda não foi publicado). A v1.1 só acrescenta: a
lista de destinatários, a resposta `403 destinatario_nao_permitido` (cadastro e
alteração), o estado de envio `bloqueado` e o segredo `DESTINATARIOS_PERMITIDOS`.
A autorização assinada não muda (`"v":1`). Um cliente da v1 trata o 403 como
resposta fora do contrato (falha genérica), sem risco.

O serviço centralizado gera, envia e valida os códigos de e-mail usados no
cadastro, na alteração de e-mail e na recuperação de senha (ERS v6.0, 5.31,
5.32 e 5.35). Usuários, senhas e dados financeiros continuam somente no
aplicativo; o serviço não conhece contas. Ele atesta apenas que quem fez a
solicitação comprovou acesso ao endereço de e-mail, por meio de uma
**autorização assinada** que o aplicativo confere localmente.

Implementação de referência: `servidor/` (Cloudflare Workers + Durable Objects
com SQLite; envio pela Resend).

## Regras fixas (ERS 5.32)

| Regra | Valor |
|---|---|
| Código | numérico, 6 dígitos (com zeros à esquerda) |
| Validade | 10 minutos a partir da geração; nunca estendida |
| Tentativas | no máximo 5 por código; esgotadas, o código deixa de valer |
| Reenvio | permitido após 60 segundos; o novo código invalida o anterior da mesma finalidade |
| Uso | a primeira validação correta encerra a validação do código |

## Limites contra abuso (aprovados para a v1)

| Escopo | Limite |
|---|---|
| Destino (todas as finalidades) | 60 s entre pedidos, 5 pedidos por hora, 10 por dia |
| IP (IPv4 inteiro, inclusive quando vem em IPv6 como `::ffff:a.b.c.d`; IPv6 por prefixo /64) | 10 pedidos por hora, 30 por dia, 30 validações por hora |
| Global | 80 envios por dia (UTC) |

Janelas fixas: hora cheia e dia UTC. Cada objeto conta de forma atômica; entre
objetos, uma vaga reservada nunca é devolvida (contagem a mais, nunca a menos).

## Restrição de destinatários (v1.1)

O serviço só envia códigos aos endereços da lista do ambiente (uso restrito,
ERS v7.0 5.49). Não existe modo sem restrição, nem no desenvolvimento.

* **Lista:** segredo `DESTINATARIOS_PERMITIDOS`, numa linha:
  `v1:<verificação>,<resumo>,<resumo>,…` (uma quebra de linha final é aceita).
  * `resumo` = HMAC-SHA256 pela `CHAVE_HMAC`, em hexadecimal minúsculo, do
    texto `"email" + "\x1f" + e-mail normalizado` (o mesmo resumo que identifica
    o objeto do destinatário); de 1 a **50**, sem repetição;
  * `verificação` = o mesmo HMAC do texto `"verificacao-lista"`. Ela **só
    detecta** uma lista gerada com outra `CHAVE_HMAC`; não prova a integridade
    do restante do conteúdo;
  * ausente, vazia ou fora desse formato (inclusive com resumo repetido): o
    serviço responde `503 servico_indisponivel` em todas as rotas;
  * trocar a `CHAVE_HMAC` exige gerar a lista de novo com a chave nova;
  * gerada pela ferramenta local `servidor/ferramentas/destinatarios.py`, que
    não mostra e-mails, chave nem resumos.
* **Comparação:** pela forma normalizada do formato de e-mail abaixo (espaços
  comuns nas bordas e minúsculas ASCII). Nenhuma outra limpeza é aplicada.
* **Onde a lista é conferida:**
  1. **no pedido**, depois do limite por IP (que é consumido) e antes do teto e
     do objeto do destinatário, também nas repetições com a mesma
     `Idempotency-Key`:
     * cadastro e alteração fora da lista: `403 destinatario_nao_permitido`;
       nada é gravado e os limites do destinatário e o teto não são consumidos;
     * recuperação fora da lista: o desafio é criado **sem envio**, com a mesma
       resposta, os mesmos limites e o mesmo comportamento na validação de um
       pedido `sem_envio` (a resposta não revela se o endereço está na lista);
       a impressão do pedido continua só com o que o cliente enviou;
  2. **antes de enviar** (camada A, no início do envio, inclusive o envio em
     segundo plano da recuperação): fora da lista, o desafio fica `bloqueado`,
     invalidado, sem reserva global;
  3. **imediatamente antes do provedor** (camada B, que envolve o enviador):
     fora da lista, nada é chamado nem repetido e o desafio fica `bloqueado`
     (a vaga do teto já reservada não é devolvida). Bloqueio pela lista nunca é
     tratado como falha nem como resultado incerto do provedor;
  4. **em toda validação** (revogação): ver a validação abaixo.
* **Limites (aceitos e documentados):**
  * a revogação **não é instantânea**: uma autorização já emitida continua
    válida até o `exp` original (o fim da validade do código), porque o
    aplicativo a confere localmente e não consulta o serviço; execuções já em
    andamento usam a configuração com que começaram;
  * a recusa vale para a lista **atual**; o desafio só fica invalidado de
    forma permanente quando uma validação acontece com o endereço fora da lista.
    Remover e incluir de novo, sem validação no meio, não invalida o desafio;
  * um pedido de cadastro ou alteração recusado não grava nada: a mesma
    `Idempotency-Key` pode ser aceita (e enviar) depois da inclusão do endereço;
  * um desafio de recuperação sem envio nunca é reativado por repetição.

## Endpoints

Todas as requisições e respostas usam JSON (`Content-Type: application/json`) e
as respostas trazem `Cache-Control: no-store`. O corpo da requisição tem no
máximo 4 KiB: um `Content-Length` maior é recusado sem leitura, e a leitura é
interrompida assim que o corpo efetivo passa do limite, com ou sem esse
cabeçalho (`413 {erro: "corpo_grande_demais"}`). Os horários são UTC em ISO-8601
com milissegundos; `agora` informa o relógio do serviço para que o aplicativo
calcule prazos relativos.

### `POST /v1/desafios` — pedir um código

Cabeçalho obrigatório: `Idempotency-Key` — 16 a 128 caracteres `[A-Za-z0-9_-]`,
gerado pelo aplicativo para cada ação do usuário.

```json
{
  "finalidade": "cadastro" | "alteracao_email" | "recuperacao_senha",
  "email": "pessoa@exemplo.com",
  "contexto": "<64 hex minúsculos: ver abaixo>",
  "segredo": "<43 caracteres base64url: 32 bytes aleatórios (S)>",
  "sem_envio": false
}
```

* `contexto`: SHA-256, em hexadecimal minúsculo, do texto UTF-8
  `finalidade + "\x1f" + e-mail normalizado + "\x1f" + nonce em hexadecimal
  minúsculo`, com nonce de 32 bytes aleatórios gerado pelo aplicativo para cada
  operação e mantido só em memória. E-mail normalizado: conforme o formato
  abaixo (sem os espaços comuns das bordas e em minúsculas ASCII). O serviço não recalcula o contexto; só o devolve assinado.
* `email`: formato único dos fluxos com código, igual no serviço, no aplicativo
  e na camada de dados local (casos em `servidor/test/conformidade/emails.json`):
  * nas bordas, removem-se **somente** espaços comuns (U+0020); qualquer outro
    espaço ou caractere de controle torna o endereço inválido;
  * depois disso: só ASCII imprimível (U+0021 a U+007E), exatamente um `@`,
    partes local e de domínio não vazias e até 254 caracteres;
  * comparação em minúsculas ASCII (idênticas em JavaScript, Python e no
    `lower()` do SQLite); a mensagem é enviada ao endereço sem os espaços das
    bordas, com as maiúsculas como informadas.
  E-mails antigos fora desse formato não são alterados e continuam entrando no
  aplicativo; só não podem ser usados em novos cadastros, alterações ou
  recuperações. Na recuperação, a recusa por formato acontece antes de
  qualquer consulta à conta e é igual para qualquer endereço.
* `segredo` (S): fica só na memória do aplicativo e precisa acompanhar cada
  validação. O serviço guarda apenas o hash.
* `sem_envio`: só é aceito em `recuperacao_senha`. O aplicativo o envia como
  `true` quando não há conta **verificada** local com esse e-mail. O desafio é
  criado e se comporta igual a um desafio real (limites, intervalo, tentativas),
  mas nenhum e-mail é enviado e ele nunca emite autorização.

Respostas:

| Status | Corpo | Quando |
|---|---|---|
| 201 | `{desafio_id, expira_em, reenvio_permitido_em, agora}` | cadastro/alteração: envio aceito, em andamento ou com resultado incerto (o código pode ter sido entregue) |
| 202 | `{desafio_id, expira_em, reenvio_permitido_em, agora}` | recuperação: **sempre** a mesma resposta, com ou sem envio; o envio ocorre depois da resposta |
| 202 | `{estado: "em_processamento", desafio_id, expira_em, reenvio_permitido_em, agora}` + `Retry-After: 2` | cadastro/alteração: repetição enquanto a requisição original ainda reserva a vaga de envio |
| 400 | `{erro: "requisicao_invalida"}` | corpo ou cabeçalho fora do formato |
| 403 | `{erro: "destinatario_nao_permitido"}` | v1.1, só cadastro/alteração: destinatário fora da lista (pedido ou repetição), ou envio barrado pela lista na mesma requisição |
| 410 | `{erro: "desafio_encerrado"}` | repetição de um pedido cujo desafio expirou ou foi invalidado (ver abaixo) |
| 413 | `{erro: "corpo_grande_demais"}` | corpo acima de 4 KiB |
| 409 | `{erro: "conflito_idempotencia"}` | mesma `Idempotency-Key` com outro conteúdo |
| 429 | `{erro: "aguarde", reenvio_permitido_em, agora}` | menos de 60 s desde o último pedido para o destino |
| 429 | `{erro: "limite_excedido"}` | limite por destino ou por IP |
| 502 | `{erro: "falha_envio", reenvio_permitido_em, agora}` | cadastro/alteração: o envio falhou de forma definitiva ou não chegou a começar |
| 503 | `{erro: "servico_indisponivel"}` | teto global atingido ou serviço sem configuração; vale igualmente para pedidos com e sem envio |

Repetição: a mesma `Idempotency-Key` com o mesmo conteúdo devolve o mesmo
desafio, **sem criar outro e sem novo envio**.

* Cadastro/alteração:
  * reserva da vaga ainda em andamento (até 60 s após o pedido) →
    `202 em_processamento` com `Retry-After`. O aplicativo repete **a mesma
    requisição, com a mesma `Idempotency-Key`**, depois do intervalo, até
    receber 201, 502, 503 ou 410. Não deve gerar uma chave nova: isso pediria
    outro código (sujeito ao intervalo de 60 s) e invalidaria o primeiro;
  * envio aceito, em andamento ou incerto → 201;
  * falha de envio, ou reserva abandonada (sem avanço em 60 s) → 502;
  * teto global atingido para esse desafio → 503;
  * destinatário fora da lista atual → 403, mesmo que o pedido original tenha
    sido aceito (nenhum envio novo);
  * desafio expirado, substituído, com tentativas esgotadas ou de outra forma
    invalidado (inclusive bloqueado pela lista, se o endereço voltou à lista) →
    410. Um desafio já validado continua respondendo 201 até o `expira_em`.
* Recuperação: 202 enquanto o desafio estiver ativo e 410 depois de expirado,
  substituído ou com tentativas esgotadas — igual com e sem envio. Falhas de
  envio, teto atingido e reserva abandonada **não** encerram o desafio para
  quem pediu (o desafio sem envio nunca passa por elas): ele segue até expirar
  ou esgotar as tentativas, sem nunca autorizar.

### `POST /v1/desafios/{desafio_id}/validacao` — validar o código

Cabeçalho obrigatório: `Idempotency-Key` (mesmo formato), nova para cada
tentativa do usuário.

```json
{ "email": "pessoa@exemplo.com", "segredo": "<S>", "codigo": "123456" }
```

| Status | Corpo | Quando |
|---|---|---|
| 200 | `{autorizacao, expira_em, agora}` | código correto |
| 400 | `{erro: "requisicao_invalida"}` | formato inválido (não conta tentativa) |
| 403 | `{erro: "destinatario_nao_permitido"}` | v1.1, só cadastro/alteração: destinatário fora da lista atual (não conta tentativa; invalida o desafio) |
| 404 | `{erro: "desafio_nao_encontrado"}` | desafio inexistente ou `segredo` que não confere (não conta tentativa) |
| 409 | `{erro: "conflito_idempotencia"}` | mesma `Idempotency-Key` com outro código |
| 410 | `{erro: "desafio_encerrado"}` | expirado, invalidado, tentativas esgotadas ou já validado por outra tentativa |
| 422 | `{erro: "codigo_invalido", tentativas_restantes}` | código errado (conta tentativa) |
| 429 | `{erro: "limite_excedido"}` | limite de validações por IP |
| 503 | `{erro: "servico_indisponivel"}` | serviço sem configuração |

Regras de repetição:

* **Repetir a mesma operação** (mesmo `desafio_id`, mesmo `segredo`, mesma
  `Idempotency-Key` e mesmo código) devolve o mesmo resultado: a mesma
  autorização, byte a byte, até o `expira_em` original; ou o mesmo
  `codigo_invalido`, sem contar outra tentativa.
* **Nova tentativa** (outra `Idempotency-Key`) depois de uma validação correta
  é recusada com 410: o código não emite uma segunda autorização.
* Conhecer apenas o `desafio_id` não permite obter a autorização: é preciso o
  `segredo` original e a `Idempotency-Key` da validação.
* Um desafio só pode autorizar se tiver reserva global registrada e envio em
  andamento, concluído ou incerto. Desafios sem reserva ou `sem_envio` tratam o
  código como errado, mesmo que ele coincida.
* Na recuperação, um desafio invalidado por falha de envio, teto atingido,
  reserva abandonada ou pela lista de destinatários responde como o desafio sem
  envio: `422 codigo_invalido` (contando tentativas) até esgotá-las ou expirar,
  nunca autorização.
* **Lista de destinatários (v1.1)**, conferida em toda validação, depois do
  `segredo` (sem ele, a resposta continua `404`):
  * cadastro e alteração fora da lista: `403`, para qualquer código e também na
    repetição de uma validação que já tinha autorizado; a tentativa não conta e
    o desafio é invalidado (motivo `destinatario_nao_permitido`), de modo que
    incluir o endereço de novo não o reativa (depois disso, `410`);
  * recuperação fora da lista: como o desafio sem envio — `422` contando a
    tentativa, mesmo com o código certo; a repetição de um `422` devolve o mesmo
    resultado; a repetição de uma validação que já tinha autorizado recebe
    `410`, nunca a autorização. Se o código tinha sido enviado, o desafio
    recebe uma marca neutra (motivo `destinatario_nao_permitido`, com o
    instante de invalidação igual ao `expira_em`) que impede a reativação sem
    mudar nada que quem pediu possa observar: ele segue parecendo ativo até
    expirar ou esgotar as tentativas, a retenção é a mesma e um novo pedido o
    substitui como a qualquer outro (`410` depois disso).

## Autorização assinada

Formato: `<payload>.<assinatura>`, ambos em base64url sem preenchimento.

* `payload`: JSON em UTF-8 com as chaves nesta ordem:
  `{"v":1,"kid":…,"jti":…,"fin":…,"ctx":…,"iat":…,"exp":…}`.
  * `fin`: finalidade; `ctx`: o `contexto` enviado no pedido;
  * `iat`: segundos UTC da validação; `exp`: segundos UTC do `expira_em` original
    do desafio (arredondado para baixo);
  * `jti`: identificador único, para o registro local de uso único: 16 bytes
    aleatórios em base64url canônico (22 caracteres; o último é `A`, `Q`, `g`
    ou `w`, porque os 4 bits de sobra são zero).
* `assinatura`: Ed25519 sobre os bytes de `"sino-autorizacao-v1." + payload`.
  O Ed25519 é determinístico: a repetição devolve exatamente a mesma autorização.

O aplicativo guarda somente as **chaves públicas** (por `kid`) e confere:
assinatura, `fin`, `ctx` (recalculado com o nonce local), prazo e se o `jti` já
foi usado. A autorização não contém e-mail, nome, senha nem dados do aplicativo.

## Envio e estados

`estado_envio` de um desafio: `pendente_reserva` → `reservado` → `enviando` →
`enviado` | `incerto` | `falhou`; ou `sem_reserva` (teto global atingido),
`sem_envio` (pedido sem envio, ou recuperação fora da lista) ou `bloqueado`
(v1.1: envio barrado pela lista; invalidado, nunca autoriza). Um desafio
`sem_envio` nunca passa a enviar.

* Sem reserva global registrada, o desafio nunca autoriza, mesmo que a
  invalidação posterior falhe.
* Um desafio que não chega a `enviando` em 60 s após o pedido é encerrado como
  `reserva_abandonada` (alarme e verificação em toda operação). Registrar a
  reserva e iniciar o envio conferem, na mesma transação, que o desafio está
  ativo e dentro desse prazo: uma execução atrasada, mesmo com relógio
  defasado, não retoma o fluxo nem envia o código.
* Um envio em `enviando` há mais de 60 s vira `incerto` (alarme do objeto e
  conversão em toda leitura). `incerto` continua validável.
* Resultados tardios só alteram o próprio desafio, e apenas enquanto ele estiver
  ativo e em `enviando`/`incerto`.
* Cada desafio usa a chave de idempotência da Resend `sino/<finalidade>/<id>`;
  repetições com o mesmo conteúdo ocorrem somente dentro da mesma execução, e a
  chave nunca é trocada para forçar um envio.

### Classificação das respostas da Resend

Conforme <https://resend.com/docs/api-reference/errors> e
<https://resend.com/docs/dashboard/emails/idempotency-keys>:

| Resposta | Ação | Pode ter sido aceita? |
|---|---|---|
| 2xx | concluir | sim (aceito) |
| falha de rede ou tempo esgotado | repetir | sim |
| 409 `concurrent_idempotent_requests`, 409 `resource_locked` | repetir | sim |
| 429 `rate_limit_exceeded` | repetir | não |
| 500 `application_error`, 503 `service_unavailable` | repetir | sim |
| 429 `daily_quota_exceeded` / `monthly_quota_exceeded` | parar | não |
| 409 `invalid_idempotent_request` ou 409 desconhecido | parar (sem trocar a chave) | sim |
| outros 5xx | parar | sim |
| 4xx de validação ou permissão | parar | não |

No máximo 3 tentativas, com esperas de 0,5 s e 1 s. O resultado é **incerto**
se qualquer tentativa pode ter sido aceita — uma recusa posterior não apaga
essa incerteza — e **falha** somente quando nenhuma pode ter sido aceita.

## Retenção

| Dado | Prazo |
|---|---|
| Desafios encerrados (e tentativas de validação) | 24 h após o encerramento (a invalidação ou a expiração, o que vier primeiro) |
| Contadores por hora | 2 h |
| Contadores diários por destino e por IP | 48 h |
| Totais globais diários | 35 dias |

O serviço não grava o e-mail em texto (somente HMAC com chave do serviço), não
grava o código (somente HMAC com salt) e não registra códigos, e-mails,
segredos ou corpos de mensagem em logs.

## Configuração (segredos do serviço)

| Nome | Conteúdo |
|---|---|
| `CHAVE_HMAC` | 64 hex (32 bytes) — hashes de e-mail, IP, código e tentativas |
| `CHAVE_ASSINATURA` | 64 hex (semente Ed25519 de 32 bytes) |
| `KID_ASSINATURA` | identificador da chave de assinatura |
| `RESEND_API_KEY` | chave da API da Resend |
| `REMETENTE` | `Sino <endereço>`; na fase de teste, `Sino <onboarding@resend.dev>` |
| `DESTINATARIOS_PERMITIDOS` | v1.1: lista de resumos dos destinatários permitidos (ver "Restrição de destinatários") |

Sem `CHAVE_HMAC`, `CHAVE_ASSINATURA`, `KID_ASSINATURA` ou `DESTINATARIOS_PERMITIDOS`
válidos, o serviço responde `503 servico_indisponivel`. Nenhum segredo fica no aplicativo nem no repositório.

## Comportamento esperado do cliente

Referência: `backend/servico_codigos.py` (cliente do aplicativo) e
`backend/autorizacao_servico.py` (verificação da autorização).

* Corpo JSON compacto (sem espaços), com as chaves na ordem deste contrato. Na
  recuperação, `sem_envio` vai sempre no corpo (`true` ou `false`), para que os
  pedidos com e sem envio tenham o mesmo formato.
* `403 destinatario_nao_permitido` (v1.1) só é aceito no cadastro e na
  alteração, com exatamente esse corpo: é uma resposta definitiva (sem
  repetição). Na validação, o desafio da operação é encerrado. O app mostra
  "O envio de códigos está restrito nesta fase do Sino.". Um 403 na
  recuperação, ou com outro corpo, é resposta fora do contrato.
* Cada ação do usuário usa uma `Idempotency-Key` nova (18 bytes aleatórios em
  base64url). Falha de rede, tempo esgotado, `503` na validação e `202
  em_processamento` são repetidos com a **mesma** chave e o mesmo corpo.
* Respostas: no máximo 16 KiB; `Content-Type: application/json`; JSON estrito
  (sem chaves duplicadas, sem `NaN`/`Infinity`, chaves exatas por resposta,
  inteiros que não sejam booleanos nem frações); instantes no formato exato
  `AAAA-MM-DDTHH:MM:SS.mmmZ`. Redirecionamentos não são seguidos; proxy,
  `.netrc` e cookies do ambiente são ignorados; HTTP só para o próprio
  computador.
* Compressão: o cliente sempre pede `Accept-Encoding: identity` e recusa,
  antes de ler o corpo, qualquer `Content-Encoding` diferente de `identity`;
  o limite de 16 KiB vale sobre os bytes recebidos.
* Cancelamento: descartar a operação impede novos envios, esperas e
  repetições e o registro de qualquer resposta que chegue depois. Para
  interromper na hora uma chamada em andamento, a tela também cancela a tarefa
  assíncrona, o que fecha a resposta HTTP.
* Prazos: o `expira_em` original (UTC) é guardado e o `exp` assinado precisa
  ser igual a ele (em segundos, arredondado para baixo). O tempo restante usa
  o relógio monotônico, contado de forma conservadora a partir do início da
  requisição (`início + (expira_em − agora) − 2 s`), e nunca é ampliado para o
  mesmo desafio. UTC e monotônico não são comparados entre si.
* Autorização: conferida antes de ser usada (formato, tamanhos, assinatura com
  a chave pública do `kid`, finalidade e contexto da operação, validade). O uso
  único do `jti` é registrado pelo aplicativo na mesma transação local da
  operação (tabela `autorizacoes_usadas`, schema v8), que confere de novo a
  finalidade, o e-mail vinculado e a validade antes e depois de obter o
  bloqueio do banco e imediatamente antes de gravar. Registros com `expira_em`
  menor que o `iat` assinado da autorização sendo consumida são apagados na
  mesma transação; sem uma autorização verificada, nada é apagado.

## Desenvolvimento (fora do contrato de produção)

Para testes manuais e demonstrações sem enviar e-mails, existe uma entrada só
de desenvolvimento (`servidor/src/dev.ts`, configuração
`servidor/wrangler.dev.jsonc`, usada apenas com `wrangler dev`). Ela segue
este contrato em tudo — endpoints, formatos, regras, limites, retenção e
autorização assinada —, com estas diferenças:

* as mensagens não vão para a Resend: são entregues a um receptor local
  (`servidor/ferramentas/caixa_dev.py`) em `http://127.0.0.1:<porta>`, que as
  grava em arquivos fora do projeto; resposta 2xx do receptor conta como envio
  aceito, outra resposta ou receptor fora do ar como falha, tempo esgotado como
  resultado incerto;
* `RESEND_API_KEY` não é exigida; `CHAVE_HMAC` e `CHAVE_ASSINATURA` são
  geradas localmente para cada pasta de teste;
* a lista de destinatários é **exigida** como na produção (sem modo
  irrestrito) e é gerada na mesma pasta só com três endereços fictícios
  (`pessoa1@demonstracao.invalid`, `pessoa2@demonstracao.invalid` e
  `pessoa3@demonstracao.invalid`; domínio reservado, que nunca recebe e-mail),
  listados também em `destinatarios_ficticios.txt`;
* o serviço escuta só em `127.0.0.1`, e a configuração aceita um atraso
  artificial de 0 a 15 s antes de cada entrega, para observar o carregamento
  nas telas.

A entrada de produção (`servidor/src/index.ts`, `servidor/wrangler.jsonc`) não
importa nada disso, e os testes conferem essa separação. Nada impede
tecnicamente um `wrangler deploy -c wrangler.dev.jsonc`: essa configuração
**não deve ser publicada**. O modo de demonstração do aplicativo
(`servidor/ferramentas/demonstracao.py`) usa esta entrada; um e-mail
confirmado por ela não comprova acesso ao endereço.

## Conformidade

`servidor/test/conformidade/autorizacao.json` (vetores de assinatura),
`servidor/test/conformidade/transcricoes.json` (requisições e respostas reais,
inclusive os cenários da v1.1) e `servidor/test/conformidade/destinatarios.json`
(resumos e verificação da lista, com chave de teste) são gerados pelos testes do
servidor com relógio e aleatoriedade fixos, e reproduzidos pelos testes do
cliente Python e da ferramenta local. Uma mudança no
contrato exige regenerá-los (`SINO_ATUALIZAR_CONFORMIDADE=1`) e conferir as
duas suítes.
