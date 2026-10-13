// Entrada do AMBIENTE T2 do serviço de códigos (ERS v7.0, E4): Worker
// temporário e separado para o primeiro envio real pela Resend. Igual à de
// produção (src/index.ts) — Resend, REMETENTE e RESPONDER_PARA obrigatórios,
// lista de destinatários, limites, idempotência e retenção —, mais um token
// exclusivo deste ambiente (mecanismo de src/acesso_teste.ts): toda
// requisição exige `Authorization: Bearer <TOKEN_ACESSO>`; sem ele (ou com o
// segredo ausente ou malformado), a resposta é a mesma 404 de uma rota
// inexistente, antes de ler o corpo e de tocar nos Durable Objects. O token
// nunca é registrado e é revogado com a exclusão do Worker (ou trocando ou
// apagando o segredo). A produção (src/index.ts) continua sem token.

import { comToken } from "./acesso_teste";
import { criarApp } from "./http";
import { dependenciasDoAmbiente } from "./index";
import type { Env } from "./objetos";

export { DestinoDO, LimiteIpDO, TetoGlobalDO } from "./objetos";

export interface EnvT2 extends Env {
  /** Segredo exclusivo do T2: 32 bytes em base64url (43 caracteres). */
  TOKEN_ACESSO?: string;
}

export default {
  async fetch(requisicao: Request, env: EnvT2, ctx: ExecutionContext): Promise<Response> {
    return comToken(requisicao, env.TOKEN_ACESSO, () =>
      criarApp(dependenciasDoAmbiente(env, (tarefa) => ctx.waitUntil(tarefa))),
    );
  },
} satisfies ExportedHandler<EnvT2>;
