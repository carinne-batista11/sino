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
