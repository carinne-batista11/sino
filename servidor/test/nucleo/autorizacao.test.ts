import { describe, expect, it } from "vitest";
import { utf8ToBytes } from "@noble/hashes/utils.js";
import {
  assinarAutorizacao,
  chavePublicaDe,
  verificarAutorizacao,
} from "../../src/nucleo/autorizacao";
import { deBase64Url, paraBase64Url } from "../../src/nucleo/cripto";
import type { DadosAutorizacao } from "../../src/nucleo/desafios";
import { CHAVE_ASSINATURA, KID } from "./apoio";

const DADOS: DadosAutorizacao = {
  jti: "jti-123",
  finalidade: "recuperacao_senha",
  contexto: "a".repeat(64),
  validadoEm: Date.UTC(2026, 9, 1, 12, 3, 0, 999),
  expiraEm: Date.UTC(2026, 9, 1, 12, 10, 0, 500),
};
const PUBLICAS = { [KID]: chavePublicaDe(CHAVE_ASSINATURA) };

describe("autorização assinada", () => {
  it("é conferida com a chave pública e traz só os campos do contrato, na ordem fixa", () => {
    const token = assinarAutorizacao(DADOS, KID, CHAVE_ASSINATURA);
    const conteudo = verificarAutorizacao(token, PUBLICAS);
    expect(conteudo).toEqual({
      v: 1, kid: KID, jti: "jti-123", fin: "recuperacao_senha", ctx: "a".repeat(64),
      iat: Math.floor(DADOS.validadoEm / 1000), exp: Math.floor(DADOS.expiraEm / 1000),
    });
    const json = new TextDecoder().decode(deBase64Url(token.split(".")[0]));
    expect(json.startsWith('{"v":1,"kid":')).toBe(true);
    expect(json).not.toMatch(/@|senha_hash|email/i);
  });

  it("é determinística: os mesmos dados geram exatamente os mesmos bytes", () => {
    expect(assinarAutorizacao(DADOS, KID, CHAVE_ASSINATURA)).toBe(assinarAutorizacao(DADOS, KID, CHAVE_ASSINATURA));
  });

  it("recusa conteúdo alterado, kid desconhecido e chave errada", () => {
    const token = assinarAutorizacao(DADOS, KID, CHAVE_ASSINATURA);
    const [, assinatura] = token.split(".");
    const alterado = paraBase64Url(
      utf8ToBytes(JSON.stringify({ v: 1, kid: KID, jti: "outro", fin: "cadastro", ctx: "a".repeat(64), iat: 1, exp: 2 })),
    );
    expect(verificarAutorizacao(`${alterado}.${assinatura}`, PUBLICAS)).toBeNull();
    expect(verificarAutorizacao(token, { "outro-kid": PUBLICAS[KID] })).toBeNull();
    expect(verificarAutorizacao(token, { [KID]: chavePublicaDe(new Uint8Array(32).fill(7)) })).toBeNull();
    expect(verificarAutorizacao("lixo", PUBLICAS)).toBeNull();
  });
});
