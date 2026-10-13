// Endereços do envio real (E4, T2): remetente (From) e endereço de resposta
// (Reply-To) vêm da configuração do ambiente e são obrigatórios na entrada de
// produção. Não há valor de reserva: ausentes ou inválidos, o serviço responde
// indisponível e a Resend nunca é chamada.
//
//   REMETENTE      "Nome <email>" ou só "email";
//   RESPONDER_PARA só "email".
// O e-mail segue a regra de src/email.ts, sem espaços nas bordas e sem
// < > " , ;; o nome não aceita caracteres de controle nem < > " (evita
// cabeçalhos malformados ou com mais de um endereço).

import { aparar, emailValido } from "../email";

export interface EnderecosEnvio {
  remetente: string;
  responderPara: string;
}

const TAMANHO_MAXIMO_NOME = 64;
const RE_COM_NOME = /^([^<>"\x00-\x1f\x7f]+) <([^<>]+)>$/;
// Nos cabeçalhos de envio, além da regra de src/email.ts, nada que separe
// endereços ou delimite nomes.
const RE_SEPARADORES = /[<>",;]/;

function emailExato(texto: string): boolean {
  return emailValido(texto) && aparar(texto) === texto && !RE_SEPARADORES.test(texto);
}

export function remetenteValido(texto: unknown): texto is string {
  if (typeof texto !== "string") return false;
  const comNome = RE_COM_NOME.exec(texto);
  if (!comNome) return emailExato(texto);
  const nome = comNome[1];
  return nome.trim() === nome && nome.length <= TAMANHO_MAXIMO_NOME && emailExato(comNome[2]);
}

/** Os dois endereços validados, ou null se algum faltar ou for inválido. */
export function enderecosDeEnvio(remetente: unknown, responderPara: unknown): EnderecosEnvio | null {
  if (!remetenteValido(remetente) || typeof responderPara !== "string" || !emailExato(responderPara)) return null;
  return { remetente, responderPara };
}
