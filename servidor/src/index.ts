// Entrada do Worker do serviço de códigos do Sino.

import { REMETENTE_PADRAO } from "./config";
import type { Enviador } from "./envio/enviador";
import { EnviadorResend } from "./envio/resend";
import type { Dependencias, PortaDestino, PortaIp, PortaTetoGlobal, Segredos } from "./fluxos";
import { criarApp } from "./http";
import { chaveDeHex } from "./nucleo/cripto";
import { registrarEvento } from "./nucleo/registro";
import type { Env } from "./objetos";

export { DestinoDO, LimiteIpDO, TetoGlobalDO } from "./objetos";
export type { Env } from "./objetos";

const RE_KID = /^[A-Za-z0-9_.-]{1,64}$/;

/** `exigirResend` = false só na entrada de desenvolvimento (src/dev.ts), que não usa a Resend. */
export function segredosDoAmbiente(env: Env, exigirResend = true): Segredos | null {
  const chaveHmac = chaveDeHex(env.CHAVE_HMAC);
  const chaveAssinatura = chaveDeHex(env.CHAVE_ASSINATURA);
  const kid = env.KID_ASSINATURA ?? "";
  if (!chaveHmac || !chaveAssinatura || !RE_KID.test(kid) || (exigirResend && !env.RESEND_API_KEY)) return null;
  return { chaveHmac, chaveAssinatura, kid };
}

export function dependenciasDoAmbiente(
  env: Env,
  emSegundoPlano: (tarefa: Promise<unknown>) => void,
  substituir: { enviador?: Enviador; relogio?: () => number; segredos?: Segredos | null } = {},
): Dependencias {
  const segredos = substituir.segredos !== undefined ? substituir.segredos : segredosDoAmbiente(env);
  if (!segredos) registrarEvento("serviço sem configuração completa; respondendo indisponível");
  return {
    segredos,
    destino: (emailHash) => env.DESTINO.get(env.DESTINO.idFromName(emailHash)) as unknown as PortaDestino,
    ip: (ipHash) => env.LIMITE_IP.get(env.LIMITE_IP.idFromName(ipHash)) as unknown as PortaIp,
    tetoGlobal: () => env.TETO_GLOBAL.get(env.TETO_GLOBAL.idFromName("global")) as unknown as PortaTetoGlobal,
    enviador:
      substituir.enviador ??
      new EnviadorResend({ apiKey: env.RESEND_API_KEY ?? "", remetente: env.REMETENTE ?? REMETENTE_PADRAO }),
    relogio: substituir.relogio ?? (() => Date.now()),
    emSegundoPlano,
  };
}

export default {
  async fetch(requisicao: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const deps = dependenciasDoAmbiente(env, (tarefa) => ctx.waitUntil(tarefa));
    return criarApp(deps).fetch(requisicao);
  },
} satisfies ExportedHandler<Env>;
