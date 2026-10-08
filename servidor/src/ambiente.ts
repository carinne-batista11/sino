// Leitura dos segredos e montagem das dependências, comuns às entradas do
// Worker (src/index.ts, src/dev.ts, src/teste.ts). Não importa nenhum
// enviador: cada entrada escolhe o seu, e a entrada de teste não leva o
// adaptador da Resend para o pacote publicado.

import type { Enviador } from "./envio/enviador";
import { EnviadorRestrito } from "./envio/restrito";
import type { Dependencias, PortaDestino, PortaIp, PortaTetoGlobal, Segredos } from "./fluxos";
import { chaveDeHex } from "./nucleo/cripto";
import { lerDestinatarios } from "./nucleo/destinatarios";
import { registrarEvento } from "./nucleo/registro";
import type { Env } from "./objetos";

const RE_KID = /^[A-Za-z0-9_.-]{1,64}$/;

/** Segredos comuns a todas as entradas; a lista de destinatários é sempre exigida. */
export function segredosBasicos(env: Env): Segredos | null {
  const chaveHmac = chaveDeHex(env.CHAVE_HMAC);
  const chaveAssinatura = chaveDeHex(env.CHAVE_ASSINATURA);
  const kid = env.KID_ASSINATURA ?? "";
  if (!chaveHmac || !chaveAssinatura || !RE_KID.test(kid)) return null;
  const destinatarios = lerDestinatarios(env.DESTINATARIOS_PERMITIDOS, chaveHmac);
  if (!destinatarios) {
    registrarEvento("lista de destinatários ausente, vazia ou inválida");
    return null;
  }
  return { chaveHmac, chaveAssinatura, kid, destinatarios };
}

/**
 * `enviador` é o da entrada (Resend, caixa local ou descarte); a camada B da
 * restrição (EnviadorRestrito) o envolve sempre.
 */
export function montarDependencias(
  env: Env,
  emSegundoPlano: (tarefa: Promise<unknown>) => void,
  enviador: Enviador,
  segredos: Segredos | null,
  relogio: () => number = () => Date.now(),
): Dependencias {
  if (!segredos) registrarEvento("serviço sem configuração completa; respondendo indisponível");
  return {
    segredos,
    destino: (emailHash) => env.DESTINO.get(env.DESTINO.idFromName(emailHash)) as unknown as PortaDestino,
    ip: (ipHash) => env.LIMITE_IP.get(env.LIMITE_IP.idFromName(ipHash)) as unknown as PortaIp,
    tetoGlobal: () => env.TETO_GLOBAL.get(env.TETO_GLOBAL.idFromName("global")) as unknown as PortaTetoGlobal,
    // Camada B da restrição: o enviador só é chamado para a lista.
    enviador: new EnviadorRestrito(enviador, segredos),
    relogio,
    emSegundoPlano,
  };
}
