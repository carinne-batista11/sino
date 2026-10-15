// Configuração de produção restrita (wrangler.jsonc; ERS v7.0, E4/M8,
// decisões 1, 5 e 6 de 15/10/2026): só workers.dev, sem URLs de prévia nem
// rotas, registros desligados, KID exclusivo, só variáveis públicas e nenhum
// segredo ou identificador de conta no arquivo.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { enderecosDeEnvio } from "../../src/envio/enderecos";

const RAIZ = join(__dirname, "../..");
const texto = (nome: string) => readFileSync(join(RAIZ, nome), "utf-8");
// Os arquivos usam só comentários em linha própria.
const semComentarios = (nome: string) =>
  texto(nome).split("\n").filter((linha) => !linha.trim().startsWith("//")).join("\n");
const ler = (nome: string) => JSON.parse(semComentarios(nome));

const producao = ler("wrangler.jsonc");
const outros = {
  desenvolvimento: ler("wrangler.dev.jsonc"),
  teste: ler("wrangler.teste.jsonc"),
  t2: ler("wrangler.t2.jsonc"),
};

describe("configuração de produção restrita (wrangler.jsonc)", () => {
  it("Worker de produção, entrada só com a Resend, só workers.dev e sem URLs de prévia", () => {
    expect(producao.name).toBe("sino-servico-codigos");
    expect(producao.main).toBe("src/index.ts");
    expect(producao.workers_dev).toBe(true);
    expect(producao.preview_urls).toBe(false);
    expect(producao.send_metrics).toBe(false);
    expect(producao.compatibility_date).toBe(outros.t2.compatibility_date);
  });

  it("sem account_id, domínio personalizado, rotas, ambientes nem configuração local", () => {
    for (const chave of [
      "account_id", "route", "routes", "custom_domain", "custom_domains", "zone_id", "zone_name",
      "env", "dev", "keep_vars", "secrets",
    ]) {
      expect(producao[chave], chave).toBeUndefined();
    }
  });

  it("decisão 6: Workers Logs, registros de invocação, Traces e Issues desligados, como no T2", () => {
    const desligada = {
      enabled: false,
      head_sampling_rate: 0,
      logs: { enabled: false, invocation_logs: false, head_sampling_rate: 0, persist: false },
      traces: { enabled: false, head_sampling_rate: 0, persist: false },
      issues: { enabled: false },
    };
    expect(producao.observability).toEqual(desligada);
    expect(producao.observability).toEqual(outros.t2.observability);
    expect(producao.logpush ?? null).toBeNull();
    expect(producao.tail_consumers ?? null).toBeNull();
  });

  it("os três objetos do próprio Worker e a migração v1", () => {
    expect(producao.durable_objects.bindings).toEqual([
      { name: "DESTINO", class_name: "DestinoDO" },
      { name: "LIMITE_IP", class_name: "LimiteIpDO" },
      { name: "TETO_GLOBAL", class_name: "TetoGlobalDO" },
    ]);
    expect(producao.migrations).toEqual([
      { tag: "v1", new_sqlite_classes: ["DestinoDO", "LimiteIpDO", "TetoGlobalDO"] },
    ]);
  });

  it("decisão 5: só variáveis públicas, com KID exclusivo da produção", () => {
    expect(producao.vars).toEqual({
      KID_ASSINATURA: "prod-1",
      REMETENTE: "Sino <nao-responda@envios.appsino.com.br>",
      RESPONDER_PARA: "sino.lembrete.contas@gmail.com",
    });
    for (const [nome, config] of Object.entries(outros)) {
      expect(config.vars.KID_ASSINATURA, nome).not.toBe(producao.vars.KID_ASSINATURA);
    }
    // Remetente e Reply-To passam na validação da entrada de produção.
    expect(enderecosDeEnvio(producao.vars.REMETENTE, producao.vars.RESPONDER_PARA)).not.toBeNull();
  });

  it("nenhum segredo nem valor de desenvolvimento no conteúdo efetivo", () => {
    const efetivo = semComentarios("wrangler.jsonc");
    for (const nome of ["CHAVE_HMAC", "CHAVE_ASSINATURA", "DESTINATARIOS_PERMITIDOS", "RESEND_API_KEY", "TOKEN_"]) {
      expect(efetivo, nome).not.toContain(nome);
    }
    for (const proibido of ["re_", "dev-1", "CAIXA_DEV", "127.0.0.1", "onboarding@resend.dev", "script_name"]) {
      expect(efetivo, proibido).not.toContain(proibido);
    }
    // Nenhuma sequência que pareça chave (32 bytes em hexadecimal).
    expect(efetivo).not.toMatch(/[0-9a-fA-F]{64}/);
  });
});
