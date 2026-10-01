// Autorização assinada (Ed25519) entregue ao aplicativo após o código
// correto. O aplicativo guarda só a chave pública e confere assinatura,
// finalidade, contexto, prazo e uso único do jti.

import { ed25519 } from "@noble/curves/ed25519.js";
import { utf8ToBytes } from "@noble/hashes/utils.js";
import type { Finalidade } from "../config";
import { deBase64Url, paraBase64Url } from "./cripto";
import type { DadosAutorizacao } from "./desafios";

export const PREFIXO_ASSINATURA = "sino-autorizacao-v1.";

export interface ConteudoAutorizacao {
  v: 1;
  kid: string;
  jti: string;
  fin: Finalidade;
  ctx: string;
  iat: number;
  exp: number;
}

export function conteudoDe(dados: DadosAutorizacao, kid: string): ConteudoAutorizacao {
  // Ordem fixa das chaves: a mesma validação gera sempre os mesmos bytes.
  return {
    v: 1,
    kid,
    jti: dados.jti,
    fin: dados.finalidade,
    ctx: dados.contexto,
    iat: Math.floor(dados.validadoEm / 1000),
    exp: Math.floor(dados.expiraEm / 1000),
  };
}

export function assinarAutorizacao(dados: DadosAutorizacao, kid: string, chavePrivada: Uint8Array): string {
  const payload = paraBase64Url(utf8ToBytes(JSON.stringify(conteudoDe(dados, kid))));
  const assinatura = ed25519.sign(utf8ToBytes(PREFIXO_ASSINATURA + payload), chavePrivada);
  return `${payload}.${paraBase64Url(assinatura)}`;
}

export function chavePublicaDe(chavePrivada: Uint8Array): Uint8Array {
  return ed25519.getPublicKey(chavePrivada);
}

/**
 * Referência do que o aplicativo confere: assinatura com a chave pública do
 * kid. Devolve o conteúdo, ou null se a autorização não for autêntica.
 * (Finalidade, contexto, prazo e jti são conferidos por quem chama.)
 */
export function verificarAutorizacao(
  token: string,
  chavesPublicas: Record<string, Uint8Array>,
): ConteudoAutorizacao | null {
  const partes = token.split(".");
  if (partes.length !== 2) return null;
  const [payload, assinatura] = partes;
  let conteudo: ConteudoAutorizacao;
  try {
    conteudo = JSON.parse(new TextDecoder().decode(deBase64Url(payload)));
  } catch {
    return null;
  }
  const chave = chavesPublicas[conteudo?.kid];
  if (!chave) return null;
  try {
    return ed25519.verify(deBase64Url(assinatura), utf8ToBytes(PREFIXO_ASSINATURA + payload), chave)
      ? conteudo
      : null;
  } catch {
    return null;
  }
}
