# Serviço de códigos do Sino

Serviço centralizado da Etapa 8 (ERS v6.0): gera, envia e valida os códigos de
e-mail do cadastro, da alteração de e-mail e da recuperação de senha, e assina
a autorização que o aplicativo confere localmente. O contrato está em
[`docs/contrato-servico-codigos.md`](../docs/contrato-servico-codigos.md).

**Estado:** contrato v1.1 (restrição de destinatários da E3, ERS v7.0 5.49),
validado localmente e publicado no repositório com a Sino 6.2. O serviço **não
foi publicado** (sem deploy) e nenhum e-mail real é enviado. O ambiente remoto
de testes da E4 está preparado localmente, sem deploy (ver abaixo).

## Organização

| Pasta | Conteúdo |
|---|---|
| `src/nucleo/` | Regras (5.32, limites, reserva global, envio incerto, retenção), criptografia e autorização assinada; sem nada da Cloudflare |
| `src/envio/` | Fronteira com o provedor (`Enviador`), adaptador da Resend, textos dos e-mails, enviador simulado para os testes e enviador de descarte do ambiente de teste |
| `src/fluxos.ts`, `src/http.ts` | Orquestração entre os objetos e rotas HTTP do contrato |
| `src/objetos.ts`, `src/ambiente.ts` | Durable Objects com SQLite; segredos e dependências comuns às entradas |
| `src/index.ts`, `src/dev.ts`, `src/teste.ts` | Entradas do Worker: produção (Resend), desenvolvimento (caixa local) e ambiente remoto de testes (descarte e token, `src/acesso_teste.ts`) |
| `test/nucleo/` | Testes das regras com o SQLite do Node (mesmos comandos SQL dos objetos) |
| `test/workers/` | Testes no simulador local dos Durable Objects (concorrência, falhas parciais, alarmes) |
| `ferramentas/` | Ferramentas locais: caixa de mensagens e modo de demonstração (desenvolvimento), `destinatarios.py` (gera a lista de destinatários) e `teste_remoto.py` (roteiro do ambiente remoto de testes) |

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

## Ambiente remoto de testes (E4; preparado, sem deploy)

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
