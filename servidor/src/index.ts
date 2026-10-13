// Entrada do Worker do serviço de códigos do Sino.

import { montarDependencias, segredosBasicos } from "./ambiente";
import { enderecosDeEnvio } from "./envio/enderecos";
import type { Enviador } from "./envio/enviador";
import { EnviadorResend } from "./envio/resend";
import { registrarEvento } from "./nucleo/registro";
import type { Dependencias, Segredos } from "./fluxos";
import { criarApp } from "./http";
import type { Env } from "./objetos";

export { DestinoDO, LimiteIpDO, TetoGlobalDO } from "./objetos";
export type { Env } from "./objetos";

/**
 * `exigirResend` = false só na entrada de desenvolvimento (src/dev.ts), que não
 * usa a Resend. A lista de destinatários é exigida nas duas entradas. Com a
 * Resend, REMETENTE e RESPONDER_PARA também são obrigatórios e válidos (sem
 * valor de reserva); senão o serviço responde indisponível, sem chamar a Resend.
 */
export function segredosDoAmbiente(env: Env, exigirResend = true): Segredos | null {
  if (exigirResend) {
    if (!env.RESEND_API_KEY) return null;
    if (!enderecosDeEnvio(env.REMETENTE, env.RESPONDER_PARA)) {
      registrarEvento("remetente ou endereço de resposta ausente ou inválido");
      return null;
    }
  }
  return segredosBasicos(env);
}

/** Envio desativado (endereços inválidos): nunca chama a rede. */
const SEM_ENVIO: Enviador = { enviar: async () => ({ tipo: "falha" }) };

function enviadorResend(env: Env): Enviador {
  const enderecos = enderecosDeEnvio(env.REMETENTE, env.RESPONDER_PARA);
  if (!enderecos || !env.RESEND_API_KEY) return SEM_ENVIO;
  return new EnviadorResend({ apiKey: env.RESEND_API_KEY, ...enderecos });
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
    substituir.enviador ?? enviadorResend(env),
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
