// Entrada do Worker do serviço de códigos do Sino.

import { REMETENTE_PADRAO } from "./config";
import type { Enviador } from "./envio/enviador";
import { EnviadorResend } from "./envio/resend";
import { EnviadorRestrito } from "./envio/restrito";
import type { Dependencias, PortaDestino, PortaIp, PortaTetoGlobal, Segredos } from "./fluxos";
import { criarApp } from "./http";
import { chaveDeHex } from "./nucleo/cripto";
import { lerDestinatarios } from "./nucleo/destinatarios";
import { registrarEvento } from "./nucleo/registro";
import type { Env } from "./objetos";

export { DestinoDO, LimiteIpDO, TetoGlobalDO } from "./objetos";
export type { Env } from "./objetos";

const RE_KID = /^[A-Za-z0-9_.-]{1,64}$/;

/**
 * `exigirResend` = false só na entrada de desenvolvimento (src/dev.ts), que não
 * usa a Resend. A lista de destinatários é exigida nas duas entradas.
 */
export function segredosDoAmbiente(env: Env, exigirResend = true): Segredos | null {
  const chaveHmac = chaveDeHex(env.CHAVE_HMAC);
  const chaveAssinatura = chaveDeHex(env.CHAVE_ASSINATURA);
  const kid = env.KID_ASSINATURA ?? "";
  if (!chaveHmac || !chaveAssinatura || !RE_KID.test(kid) || (exigirResend && !env.RESEND_API_KEY)) return null;
  const destinatarios = lerDestinatarios(env.DESTINATARIOS_PERMITIDOS, chaveHmac);
  if (!destinatarios) {
    registrarEvento("lista de destinatários ausente, vazia ou inválida");
    return null;
  }
  return { chaveHmac, chaveAssinatura, kid, destinatarios };
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
    // Camada B da restrição: o enviador real só é chamado para a lista.
    enviador: new EnviadorRestrito(
      substituir.enviador ??
        new EnviadorResend({ apiKey: env.RESEND_API_KEY ?? "", remetente: env.REMETENTE ?? REMETENTE_PADRAO }),
      segredos,
    ),
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
