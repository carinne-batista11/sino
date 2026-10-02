// Entrada de DESENVOLVIMENTO do serviço de códigos (wrangler.dev.jsonc).
// Igual à de produção (src/index.ts), exceto pelo enviador: as mensagens vão
// para o receptor local (ferramentas/caixa_dev.py) em vez da Resend, e a
// RESEND_API_KEY não é exigida. Nunca é publicada: wrangler.jsonc aponta para
// src/index.ts, que não importa este arquivo.
//
// Variáveis (só na configuração de desenvolvimento):
//   CAIXA_DEV_URL       http://127.0.0.1:<porta> do receptor (outro valor -> indisponível);
//   CAIXA_DEV_ATRASO_MS atraso artificial antes de cada entrega, 0..15000 (padrão 0).
// Validade, tentativas, limites e regras dos códigos são os mesmos da produção.

import { atrasoDaCaixa, EnviadorCaixaLocal, urlDaCaixaLocal } from "./envio/caixa_local";
import { criarApp } from "./http";
import { dependenciasDoAmbiente, segredosDoAmbiente } from "./index";
import { registrarEvento } from "./nucleo/registro";
import type { Env } from "./objetos";

export { DestinoDO, LimiteIpDO, TetoGlobalDO } from "./objetos";

export interface EnvDev extends Env {
  CAIXA_DEV_URL?: string;
  CAIXA_DEV_ATRASO_MS?: string;
}

export default {
  async fetch(requisicao: Request, env: EnvDev, ctx: ExecutionContext): Promise<Response> {
    const url = urlDaCaixaLocal(env.CAIXA_DEV_URL);
    const atrasoMs = atrasoDaCaixa(env.CAIXA_DEV_ATRASO_MS);
    const segredos = url !== null && atrasoMs !== null ? segredosDoAmbiente(env, false) : null;
    if (!segredos) registrarEvento("serviço de desenvolvimento sem configuração completa; respondendo indisponível");
    const deps = dependenciasDoAmbiente(env, (tarefa) => ctx.waitUntil(tarefa), {
      segredos,
      enviador: new EnviadorCaixaLocal({ url: url ?? "", atrasoMs: atrasoMs ?? 0 }),
    });
    return criarApp(deps).fetch(requisicao);
  },
} satisfies ExportedHandler<EnvDev>;
