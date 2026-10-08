// Entrada do AMBIENTE REMOTO DE TESTES do serviço de códigos
// (wrangler.teste.jsonc; Worker sino-servico-codigos-teste, ERS v7.0, E4).
// Igual à de produção (src/index.ts), exceto por:
//   * envio desabilitado por construção: EnviadorDescarte (sem rede, sem
//     registro), envolvido pela camada B da lista; este arquivo não importa o
//     adaptador da Resend nem a caixa local, e RESEND_API_KEY não é lida;
//   * autenticação: toda requisição exige `Authorization: Bearer <TOKEN_TESTE>`
//     (src/acesso_teste.ts); sem ele, 404 antes de qualquer objeto.
// Validade, tentativas, limites, lista de destinatários e retenção são os da
// produção. O código gerado é descartado: o caminho do código correto só é
// coberto pelos testes locais.

import { comToken } from "./acesso_teste";
import { montarDependencias, segredosBasicos } from "./ambiente";
import { EnviadorDescarte } from "./envio/descarte";
import { criarApp } from "./http";
import type { Env } from "./objetos";

export { DestinoDO, LimiteIpDO, TetoGlobalDO } from "./objetos";

export interface EnvTeste extends Env {
  /** Segredo do ambiente de teste: 32 bytes em base64url (43 caracteres). */
  TOKEN_TESTE?: string;
}

export default {
  async fetch(requisicao: Request, env: EnvTeste, ctx: ExecutionContext): Promise<Response> {
    return comToken(requisicao, env.TOKEN_TESTE, () =>
      criarApp(
        montarDependencias(env, (tarefa) => ctx.waitUntil(tarefa), new EnviadorDescarte(), segredosBasicos(env)),
      ),
    );
  },
} satisfies ExportedHandler<EnvTeste>;
