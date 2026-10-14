import { describe, expect, it } from "vitest";
import { sha256 } from "@noble/hashes/sha2.js";
import { utf8ToBytes } from "@noble/hashes/utils.js";
import {
  assinarAutorizacao,
  importarChaveAssinatura,
  pkcs8DaSemente,
} from "../../src/nucleo/autorizacao";
import {
  assinarAutorizacaoReferencia,
  chavePublicaDe,
  verificarAutorizacao,
} from "../../src/nucleo/autorizacao_referencia";
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
const chave = () => importarChaveAssinatura(CHAVE_ASSINATURA);

describe("autorização assinada", () => {
  it("é conferida com a chave pública e traz só os campos do contrato, na ordem fixa", async () => {
    const token = await assinarAutorizacao(DADOS, KID, await chave());
    const conteudo = verificarAutorizacao(token, PUBLICAS);
    expect(conteudo).toEqual({
      v: 1, kid: KID, jti: "jti-123", fin: "recuperacao_senha", ctx: "a".repeat(64),
      iat: Math.floor(DADOS.validadoEm / 1000), exp: Math.floor(DADOS.expiraEm / 1000),
    });
    const json = new TextDecoder().decode(deBase64Url(token.split(".")[0]));
    expect(json.startsWith('{"v":1,"kid":')).toBe(true);
    expect(json).not.toMatch(/@|senha_hash|email/i);
  });

  it("é determinística: os mesmos dados geram exatamente os mesmos bytes", async () => {
    const k = await chave();
    expect(await assinarAutorizacao(DADOS, KID, k)).toBe(await assinarAutorizacao(DADOS, KID, k));
    // Inclusive com chaves importadas separadamente (a importação é por requisição).
    expect(await assinarAutorizacao(DADOS, KID, await chave())).toBe(await assinarAutorizacao(DADOS, KID, k));
  });

  it("recusa conteúdo alterado, kid desconhecido e chave errada", async () => {
    const token = await assinarAutorizacao(DADOS, KID, await chave());
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

describe("Ed25519 nativo (WebCrypto) × referência em JavaScript (@noble/curves)", () => {
  // Sementes e conteúdos fictícios, derivados de um rótulo fixo.
  const semente = (i: number) => sha256(utf8ToBytes(`sino-teste-ficticio|semente|${i}`));
  const dados = (i: number): DadosAutorizacao => ({
    jti: paraBase64Url(sha256(utf8ToBytes(`jti|${i}`)).slice(0, 16)),
    finalidade: (["cadastro", "alteracao_email", "recuperacao_senha"] as const)[i % 3],
    contexto: Array.from(sha256(utf8ToBytes(`ctx|${i}`)), (b) => b.toString(16).padStart(2, "0")).join(""),
    validadoEm: Date.UTC(2026, 9, 1) + i * 1_001,
    expiraEm: Date.UTC(2026, 9, 1) + 600_000 + i * 997,
  });

  it("gera autorizações idênticas byte a byte para 200 sementes e conteúdos fictícios", async () => {
    for (let i = 0; i < 200; i++) {
      const s = semente(i);
      const nativa = await assinarAutorizacao(dados(i), `kid-${i % 4}`, await importarChaveAssinatura(s));
      expect(nativa).toBe(assinarAutorizacaoReferencia(dados(i), `kid-${i % 4}`, s));
      expect(verificarAutorizacao(nativa, { [`kid-${i % 4}`]: chavePublicaDe(s) })).not.toBeNull();
    }
  });

  it("monta o PKCS#8 com 48 bytes: o prefixo RFC 8410 seguido da semente", () => {
    const s = semente(1);
    const envelope = pkcs8DaSemente(s);
    expect(envelope.length).toBe(48);
    expect(Array.from(envelope.slice(0, 16))).toEqual([
      0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x04, 0x22, 0x04, 0x20,
    ]);
    expect(Array.from(envelope.slice(16))).toEqual(Array.from(s));
  });

  it("recusa semente com tamanho diferente de 32 bytes, sem mostrar a semente no erro", async () => {
    for (const n of [0, 16, 31, 33, 64]) {
      const s = new Uint8Array(n).fill(0xab);
      expect(() => pkcs8DaSemente(s)).toThrowError(/^semente Ed25519 com tamanho inválido$/);
      await expect(importarChaveAssinatura(s)).rejects.toThrowError(/^semente Ed25519 com tamanho inválido$/);
    }
  });

  it("importa uma chave não exportável, só para assinar", async () => {
    const k = await importarChaveAssinatura(semente(2));
    expect(k.type).toBe("private");
    expect(k.extractable).toBe(false);
    expect(k.usages).toEqual(["sign"]);
    expect((k.algorithm as { name: string }).name).toBe("Ed25519");
    await expect(crypto.subtle.exportKey("pkcs8", k)).rejects.toThrow();
    await expect(crypto.subtle.exportKey("jwk", k)).rejects.toThrow();
  });
});
