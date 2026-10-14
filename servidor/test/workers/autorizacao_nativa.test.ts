// Ed25519 nativo no runtime de testes (workerd): validação completa com o
// código certo, conferência da assinatura pela referência e repetição
// idempotente. Só dados fictícios; nenhuma rede externa.

import { env } from "cloudflare:test";
import { describe, expect, it } from "vitest";
import { hexToBytes } from "@noble/hashes/utils.js";
import { EnviadorSimulado } from "../../src/envio/simulado";
import { pedirDesafio, validarDesafio } from "../../src/fluxos";
import { dependenciasDoAmbiente } from "../../src/index";
import { importarChaveAssinatura, pkcs8DaSemente } from "../../src/nucleo/autorizacao";
import { chavePublicaDe, verificarAutorizacao } from "../../src/nucleo/autorizacao_referencia";

const CTX = "d".repeat(64);
const SEGREDO = "R".repeat(43);
const EMAIL = "x@exemplo.com"; // na lista de teste (vitest.config.ts)

describe("autorização com Ed25519 nativo no workerd", () => {
  it("importa a semente por PKCS#8 como chave não exportável, só para assinar", async () => {
    const semente = hexToBytes(env.CHAVE_ASSINATURA!);
    expect(pkcs8DaSemente(semente).length).toBe(48);
    const chave = await importarChaveAssinatura(semente);
    expect(chave.extractable).toBe(false);
    expect(chave.usages).toEqual(["sign"]);
    await expect(crypto.subtle.exportKey("pkcs8", chave)).rejects.toThrow();
  });

  it("validação com o código certo: autorização verificável e repetição idempotente", async () => {
    const enviador = new EnviadorSimulado();
    const tarefas: Promise<unknown>[] = [];
    const deps = dependenciasDoAmbiente(env, (t) => void tarefas.push(t), { enviador });
    const ip = `198.51.100.${10 + Math.floor(Math.random() * 200)}`;

    const r = await pedirDesafio(deps, {
      finalidade: "cadastro", email: EMAIL, contexto: CTX, segredo: SEGREDO,
      chave: `pedido-${crypto.randomUUID()}`, semEnvio: false, ip,
    });
    expect(r.status).toBe(201);
    await Promise.all(tarefas);
    const codigo = enviador.ultimoCodigo(EMAIL)!;
    expect(codigo).toMatch(/^\d{6}$/);

    const chave = `valida-${crypto.randomUUID()}`;
    const entradaValidacao = { desafioId: r.corpo.desafio_id as string, email: EMAIL, segredo: SEGREDO, chave, codigo, ip };
    const v1 = await validarDesafio(deps, entradaValidacao);
    expect(v1.status).toBe(200);
    const publicas = { [env.KID_ASSINATURA!]: chavePublicaDe(hexToBytes(env.CHAVE_ASSINATURA!)) };
    const conteudo = verificarAutorizacao(v1.corpo.autorizacao as string, publicas);
    expect(conteudo).toMatchObject({ v: 1, kid: env.KID_ASSINATURA, fin: "cadastro", ctx: CTX });
    expect(conteudo!.exp).toBe(Math.floor(Date.parse(r.corpo.expira_em as string) / 1000));

    const v2 = await validarDesafio(deps, entradaValidacao);
    expect(v2.status).toBe(200);
    expect(v2.corpo.autorizacao).toBe(v1.corpo.autorizacao);
    expect((await validarDesafio(deps, { ...entradaValidacao, chave: `valida-${crypto.randomUUID()}` })).status).toBe(410);
  });
});
