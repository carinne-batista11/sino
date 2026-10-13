// Configuração do ambiente T2 (wrangler.t2.jsonc, ERS v7.0, E4): Worker
// separado e temporário, entrada src/t2.ts (produção + token), registros
// desligados, sem segredos no arquivo e sem armazenamento de outro Worker.

import { readFileSync } from "node:fs";
import { dirname, join, normalize } from "node:path";
import { describe, expect, it } from "vitest";
import { enderecosDeEnvio } from "../../src/envio/enderecos";

const RAIZ = join(__dirname, "../..");
const texto = (nome: string) => readFileSync(join(RAIZ, nome), "utf-8");
// Os arquivos usam só comentários em linha própria.
const ler = (nome: string) =>
  JSON.parse(texto(nome).split("\n").filter((linha) => !linha.trim().startsWith("//")).join("\n"));

const t2 = ler("wrangler.t2.jsonc");
const producao = ler("wrangler.jsonc");
const teste = ler("wrangler.teste.jsonc");

describe("configuração do ambiente T2 (wrangler.t2.jsonc)", () => {
  it("Worker próprio, entrada do T2, só workers.dev e sem URLs de prévia", () => {
    expect(t2.name).toBe("sino-servico-codigos-t2");
    expect(new Set([t2.name, producao.name, teste.name]).size).toBe(3);
    expect(t2.main).toBe("src/t2.ts");
    expect(t2.workers_dev).toBe(true);
    expect(t2.preview_urls).toBe(false);
    expect(t2.send_metrics).toBe(false);
    expect(t2.account_id).toBeUndefined();
  });

  it("sem domínio personalizado nem rotas", () => {
    for (const chave of ["route", "routes", "custom_domain", "custom_domains", "zone_id", "zone_name"]) {
      expect(t2[chave], chave).toBeUndefined();
    }
  });

  it("Workers Logs, registros de invocação, Traces e Issues desligados", () => {
    expect(t2.observability).toEqual({
      enabled: false,
      head_sampling_rate: 0,
      logs: { enabled: false, invocation_logs: false, head_sampling_rate: 0, persist: false },
      traces: { enabled: false, head_sampling_rate: 0, persist: false },
      issues: { enabled: false },
    });
  });

  it("os mesmos três objetos e a migração da produção, sem apontar para outro Worker", () => {
    expect(t2.durable_objects).toEqual(producao.durable_objects);
    expect(t2.migrations).toEqual(producao.migrations);
    for (const vinculo of t2.durable_objects.bindings) {
      expect(Object.keys(vinculo).sort()).toEqual(["class_name", "name"]); // sem script_name nem environment
    }
    expect(t2.migrations).toEqual([
      { tag: "v1", new_sqlite_classes: ["DestinoDO", "LimiteIpDO", "TetoGlobalDO"] },
    ]);
    // Conteúdo efetivo (sem comentários): nenhuma referência a outro Worker.
    const efetivo = JSON.stringify(t2);
    for (const outro of ["script_name", "sino-servico-codigos-teste", "\"sino-servico-codigos\""]) {
      expect(efetivo).not.toContain(outro);
    }
  });

  it("só valores não secretos: KID do T2, remetente e Reply-To aprovados", () => {
    expect(t2.vars).toEqual({
      KID_ASSINATURA: "t2-1",
      REMETENTE: "Sino <nao-responda@envios.appsino.com.br>",
      RESPONDER_PARA: "sino.lembrete.contas@gmail.com",
    });
    expect(t2.vars.KID_ASSINATURA).not.toBe(teste.vars.KID_ASSINATURA);
    expect(t2.vars.KID_ASSINATURA).not.toBe(producao.vars.KID_ASSINATURA);
    // Os dois passam na mesma validação da entrada de produção.
    expect(enderecosDeEnvio(t2.vars.REMETENTE, t2.vars.RESPONDER_PARA)).toEqual({
      remetente: "Sino <nao-responda@envios.appsino.com.br>",
      responderPara: "sino.lembrete.contas@gmail.com",
    });
  });

  it("nenhum segredo no arquivo", () => {
    for (const segredo of ["TOKEN_ACESSO", "RESEND_API_KEY", "CHAVE_HMAC", "CHAVE_ASSINATURA", "DESTINATARIOS_PERMITIDOS"]) {
      expect(Object.keys(t2.vars)).not.toContain(segredo);
    }
    const semComentarios = JSON.stringify(t2);
    expect(semComentarios).not.toMatch(/\bre_[A-Za-z0-9_]{8,}/); // chave da Resend
    expect(semComentarios).not.toMatch(/\b[0-9a-f]{64}\b/i); // chaves de 32 bytes em hex
    expect(semComentarios).not.toMatch(/(^|[^A-Za-z0-9_-])[A-Za-z0-9_-]{43}([^A-Za-z0-9_-]|$)/); // token
    expect(semComentarios).not.toMatch(/v1:[0-9a-f]/); // lista de destinatários
  });

  it("a entrada do T2 alcança a Resend e o token, e nada da caixa local, do descarte ou do T1", () => {
    const raiz = join(RAIZ, "src");
    const vistos = new Set<string>();
    const visitar = (arquivo: string) => {
      if (vistos.has(arquivo)) return;
      vistos.add(arquivo);
      for (const m of readFileSync(join(raiz, arquivo), "utf-8").matchAll(/from\s+"(\.[^"]+)"/g)) {
        visitar(normalize(join(dirname(arquivo), `${m[1]}.ts`)));
      }
    };
    visitar(t2.main.replace(/^src\//, ""));
    for (const necessario of ["index.ts", "envio/resend.ts", "envio/enderecos.ts", "acesso_teste.ts", "envio/restrito.ts"]) {
      expect(vistos).toContain(necessario);
    }
    for (const proibido of ["envio/caixa_local.ts", "envio/simulado.ts", "envio/descarte.ts", "dev.ts", "teste.ts"]) {
      expect(vistos).not.toContain(proibido);
    }
  });
});

describe("configurações existentes preservadas", () => {
  it("produção: mesma entrada e sem remetente de reserva; T1: inalterada", () => {
    expect(producao.name).toBe("sino-servico-codigos");
    expect(producao.main).toBe("src/index.ts");
    expect(producao.vars).toEqual({ KID_ASSINATURA: "dev-1" });
    expect(texto("wrangler.jsonc")).not.toContain("onboarding@resend.dev");
    expect(teste.name).toBe("sino-servico-codigos-teste");
    expect(teste.main).toBe("src/teste.ts");
  });
});
