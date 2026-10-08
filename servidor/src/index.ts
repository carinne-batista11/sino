// Entrada do Worker do serviço de códigos do Sino.

import { montarDependencias, segredosBasicos } from "./ambiente";
import { REMETENTE_PADRAO } from "./config";
import type { Enviador } from "./envio/enviador";
import { EnviadorResend } from "./envio/resend";
import type { Dependencias, Segredos } from "./fluxos";
import { criarApp } from "./http";
import type { Env } from "./objetos";

export { DestinoDO, LimiteIpDO, TetoGlobalDO } from "./objetos";
export type { Env } from "./objetos";

/**
 * `exigirResend` = false só na entrada de desenvolvimento (src/dev.ts), que não
 * usa a Resend. A lista de destinatários é exigida nas duas entradas.
 */
export function segredosDoAmbiente(env: Env, exigirResend = true): Segredos | null {
  if (exigirResend && !env.RESEND_API_KEY) return null;
  return segredosBasicos(env);
}

export function dependenciasDoAmbiente(
  env: Env,
  emSegundoPlano: (tarefa: Promise<unknown>) => void,
  substituir: { enviador?: Enviador; relogio?: () => number; segredos?: Segredos | null } = {},
): Dependencias {
  const segredos = substituir.segredos !== undefined ? substituir.segredos : segredosDoAmbiente(env);
  return montarDependencias(
    env,
    emSegundoPlano,
    substituir.enviador ??
      new EnviadorResend({ apiKey: env.RESEND_API_KEY ?? "", remetente: env.REMETENTE ?? REMETENTE_PADRAO }),
    segredos,
    substituir.relogio,
  );
}

export default {
  async fetch(requisicao: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const deps = dependenciasDoAmbiente(env, (tarefa) => ctx.waitUntil(tarefa));
    return criarApp(deps).fetch(requisicao);
  },
} satisfies ExportedHandler<Env>;
