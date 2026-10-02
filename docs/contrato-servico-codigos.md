# Contrato do serviço de códigos do Sino (Etapa 8)

Versão do contrato: **v1** (rascunho do primeiro bloco local; o serviço ainda não foi publicado).

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
  * desafio expirado, substituído, com tentativas esgotadas ou de outra forma
    invalidado → 410. Um desafio já validado continua respondendo 201 até o
    `expira_em`.
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
* Na recuperação, um desafio invalidado por falha de envio, teto atingido ou
  reserva abandonada responde como o desafio sem envio: `422 codigo_invalido`
  (contando tentativas) até esgotá-las ou expirar, nunca autorização.

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
`enviado` | `incerto` | `falhou`; ou `sem_reserva` (teto global atingido) ou
`sem_envio`.

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

Sem `CHAVE_HMAC`, `CHAVE_ASSINATURA` ou `KID_ASSINATURA` válidos, o serviço responde
`503 servico_indisponivel`. Nenhum segredo fica no aplicativo nem no repositório.

## Comportamento esperado do cliente

Referência: `backend/servico_codigos.py` (cliente do aplicativo) e
`backend/autorizacao_servico.py` (verificação da autorização).

* Corpo JSON compacto (sem espaços), com as chaves na ordem deste contrato. Na
  recuperação, `sem_envio` vai sempre no corpo (`true` ou `false`), para que os
  pedidos com e sem envio tenham o mesmo formato.
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

`servidor/test/conformidade/autorizacao.json` (vetores de assinatura) e
`servidor/test/conformidade/transcricoes.json` (requisições e respostas reais)
são gerados pelos testes do servidor com relógio e aleatoriedade fixos, e
reproduzidos byte a byte pelos testes do cliente Python. Uma mudança no
contrato exige regenerá-los (`SINO_ATUALIZAR_CONFORMIDADE=1`) e conferir as
duas suítes.
