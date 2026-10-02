# Serviço de códigos do Sino

Serviço centralizado da Etapa 8 (ERS v6.0): gera, envia e valida os códigos de
e-mail do cadastro, da alteração de e-mail e da recuperação de senha, e assina
a autorização que o aplicativo confere localmente. O contrato está em
[`docs/contrato-servico-codigos.md`](../docs/contrato-servico-codigos.md).

**Estado:** primeiro bloco local. O serviço **não foi publicado**, não há conta
na Cloudflare nem na Resend, e nenhum e-mail real é enviado.

## Organização

| Pasta | Conteúdo |
|---|---|
| `src/nucleo/` | Regras (5.32, limites, reserva global, envio incerto, retenção), criptografia e autorização assinada; sem nada da Cloudflare |
| `src/envio/` | Fronteira com o provedor (`Enviador`), adaptador da Resend, textos dos e-mails e enviador simulado para os testes |
| `src/fluxos.ts`, `src/http.ts` | Orquestração entre os objetos e rotas HTTP do contrato |
| `src/objetos.ts`, `src/index.ts` | Durable Objects com SQLite e entrada do Worker |
| `test/nucleo/` | Testes das regras com o SQLite do Node (mesmos comandos SQL dos objetos) |
| `test/workers/` | Testes no simulador local dos Durable Objects (concorrência, falhas parciais, alarmes) |

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
