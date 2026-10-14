// Implementação de REFERÊNCIA do Ed25519 em JavaScript (@noble/curves), usada
// só pelos testes: chave pública da semente, assinatura de referência e
// verificação. Nenhuma entrada do Worker importa este módulo, então ele não
// entra no pacote publicado. O serviço assina com o Ed25519 nativo
// (autorizacao.ts); o aplicativo verifica com a sua própria biblioteca.

import { ed25519 } from "@noble/curves/ed25519.js";
import { utf8ToBytes } from "@noble/hashes/utils.js";
import { deBase64Url, paraBase64Url } from "./cripto";
import { conteudoDe, PREFIXO_ASSINATURA, type ConteudoAutorizacao } from "./autorizacao";
import type { DadosAutorizacao } from "./desafios";

export function chavePublicaDe(chavePrivada: Uint8Array): Uint8Array {
  return ed25519.getPublicKey(chavePrivada);
}

/** Assinatura de referência: deve ser idêntica à de assinarAutorizacao. */
export function assinarAutorizacaoReferencia(dados: DadosAutorizacao, kid: string, chavePrivada: Uint8Array): string {
  const payload = paraBase64Url(utf8ToBytes(JSON.stringify(conteudoDe(dados, kid))));
  const assinatura = ed25519.sign(utf8ToBytes(PREFIXO_ASSINATURA + payload), chavePrivada);
  return `${payload}.${paraBase64Url(assinatura)}`;
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
