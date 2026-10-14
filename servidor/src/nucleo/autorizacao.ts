// Autorização assinada (Ed25519) entregue ao aplicativo após o código
// correto. O aplicativo guarda só a chave pública e confere assinatura,
// finalidade, contexto, prazo e uso único do jti.
//
// A assinatura usa o Ed25519 nativo do runtime (WebCrypto). O Ed25519 é
// determinístico: a mesma chave e o mesmo conteúdo geram sempre os mesmos
// bytes, iguais aos da implementação de referência em JavaScript
// (autorizacao_referencia.ts, usada só pelos testes e fora do pacote publicado).

import { utf8ToBytes } from "@noble/hashes/utils.js";
import type { Finalidade } from "../config";
import { paraBase64Url } from "./cripto";
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

const ALGORITMO = { name: "Ed25519" } as const;

// PKCS#8 (RFC 8410) de uma chave privada Ed25519: este prefixo fixo de 16 bytes
// seguido da semente de 32 bytes. O runtime não importa a semente crua.
const PREFIXO_PKCS8 = Uint8Array.from([
  0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x04, 0x22, 0x04, 0x20,
]);

/** Envelope PKCS#8 da semente Ed25519 (32 bytes, o formato de CHAVE_ASSINATURA). */
export function pkcs8DaSemente(semente: Uint8Array): Uint8Array<ArrayBuffer> {
  if (semente.length !== 32) throw new Error("semente Ed25519 com tamanho inválido");
  const envelope = new Uint8Array(PREFIXO_PKCS8.length + semente.length);
  envelope.set(PREFIXO_PKCS8);
  envelope.set(semente, PREFIXO_PKCS8.length);
  return envelope;
}

/** Chave de assinatura não exportável, só para assinar. Qualquer erro vira uma Promise rejeitada. */
export async function importarChaveAssinatura(semente: Uint8Array): Promise<CryptoKey> {
  return crypto.subtle.importKey("pkcs8", pkcs8DaSemente(semente), ALGORITMO, false, ["sign"]);
}

export async function assinarAutorizacao(dados: DadosAutorizacao, kid: string, chave: CryptoKey): Promise<string> {
  const payload = paraBase64Url(utf8ToBytes(JSON.stringify(conteudoDe(dados, kid))));
  const assinatura = await crypto.subtle.sign(ALGORITMO, chave, utf8ToBytes(PREFIXO_ASSINATURA + payload));
  return `${payload}.${paraBase64Url(new Uint8Array(assinatura))}`;
}
