// Lista de destinatários permitidos (ERS v7.0, 5.49; contrato v1.1). O
// segredo DESTINATARIOS_PERMITIDOS de cada ambiente traz só resumos HMAC,
// nunca e-mails em texto, numa única linha:
//
//   v1:<verificação>,<resumo>,<resumo>,...
//
//   * verificação: hmacHex(CHAVE_HMAC, "verificacao-lista"). Só detecta uma
//     lista gerada com outra CHAVE_HMAC; não prova a integridade do restante
//     do conteúdo;
//   * resumo: hmacHex(CHAVE_HMAC, "email", e-mail normalizado), o mesmo
//     resumo que identifica o objeto do destinatário;
//   * de 1 a LIMITE_DESTINATARIOS resumos, 64 hex minúsculos, sem repetição;
//   * aceita-se uma única quebra de linha no fim.
//
// Ausente, vazia ou fora desse formato: lista inválida (null). Não existe
// forma de liberar todos os destinatários.

import { LIMITE_DESTINATARIOS } from "../config";
import { normalizarEmail } from "../email";
import { hmacHex, iguaisTempoConstante } from "./cripto";

export const VERSAO_LISTA = "v1";
const RE_RESUMO = /^[0-9a-f]{64}$/;

export type Destinatarios = ReadonlySet<string>;

/** Resumo de um e-mail válido, igual ao nome do objeto do destinatário. */
export function resumoDoEmail(chaveHmac: Uint8Array, email: string): string {
  return hmacHex(chaveHmac, "email", normalizarEmail(email));
}

export function verificacaoDaLista(chaveHmac: Uint8Array): string {
  return `${VERSAO_LISTA}:${hmacHex(chaveHmac, "verificacao-lista")}`;
}

/** Conjunto de resumos permitidos, ou null se a configuração for inválida. */
export function lerDestinatarios(texto: string | undefined, chaveHmac: Uint8Array): Destinatarios | null {
  if (!texto) return null;
  const linha = texto.endsWith("\n") ? texto.slice(0, -1) : texto;
  const [verificacao, ...resumos] = linha.split(",");
  if (!iguaisTempoConstante(verificacao, verificacaoDaLista(chaveHmac))) return null;
  if (resumos.length === 0 || resumos.length > LIMITE_DESTINATARIOS) return null;
  if (!resumos.every((r) => RE_RESUMO.test(r))) return null;
  const conjunto = new Set(resumos);
  return conjunto.size === resumos.length ? conjunto : null;
}

/** Texto da configuração para uma lista de e-mails (testes e ferramentas). */
export function montarDestinatarios(chaveHmac: Uint8Array, emails: string[]): string {
  const resumos = [...new Set(emails.map((e) => resumoDoEmail(chaveHmac, e)))];
  return [verificacaoDaLista(chaveHmac), ...resumos].join(",");
}
