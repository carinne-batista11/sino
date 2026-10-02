// Enviador de desenvolvimento (caixa local) e isolamento da entrada de
// produção: src/index.ts e wrangler.jsonc não podem alcançar nada dele.

import { readFileSync } from "node:fs";
import { afterEach, describe, expect, it } from "vitest";
import { atrasoDaCaixa, EnviadorCaixaLocal, urlDaCaixaLocal } from "../../src/envio/caixa_local";
import { montarMensagem } from "../../src/envio/mensagens";
import { capturarRegistros } from "./apoio";

const URL_CAIXA = "http://127.0.0.1:8025/mensagens";
const PARA = "pessoa.teste@exemplo.com";
const CODIGO = "042137";
const MENSAGEM = montarMensagem("cadastro", PARA, CODIGO);
const CHAVE = "sino/cadastro/desafio-1";

function caixa(responder: () => Response | Promise<Response>, esperas: number[] = [], atrasoMs = 0) {
  const chamadas: { url: string; corpo: string }[] = [];
  const enviador = new EnviadorCaixaLocal({
    url: URL_CAIXA,
    atrasoMs,
    esperar: async (ms) => void esperas.push(ms),
    fetch: (async (url: RequestInfo | URL, init?: RequestInit) => {
      chamadas.push({ url: String(url), corpo: String(init?.body) });
      return responder();
    }) as typeof fetch,
  });
  return { enviador, chamadas };
}

let registros: ReturnType<typeof capturarRegistros>;
afterEach(() => {
  for (const linha of registros?.linhas ?? []) {
    expect(linha).not.toContain(CODIGO);
    expect(linha).not.toContain(PARA);
  }
  registros?.restaurar();
});

describe("configuração", () => {
  it("aceita só http://127.0.0.1:<porta>", () => {
    expect(urlDaCaixaLocal("http://127.0.0.1:8025")).toBe(URL_CAIXA);
    for (const invalida of [
      undefined, "", "http://localhost:8025", "https://127.0.0.1:8025", "http://127.0.0.1",
      "http://127.0.0.1:0", "http://127.0.0.1:70000", "http://127.0.0.1:8025/", "http://0.0.0.0:8025",
      "http://127.0.0.1.exemplo.com:8025", "http://[::1]:8025", "http://10.0.0.1:8025",
    ]) {
      expect(urlDaCaixaLocal(invalida), String(invalida)).toBeNull();
    }
  });

  it("atraso de 0 a 15 s; inválido -> null", () => {
    expect(atrasoDaCaixa(undefined)).toBe(0);
    expect(atrasoDaCaixa("")).toBe(0);
    expect(atrasoDaCaixa("8000")).toBe(8000);
    expect(atrasoDaCaixa("15000")).toBe(15000);
    for (const invalido of ["15001", "-1", "1.5", "abc", "99999"]) expect(atrasoDaCaixa(invalido)).toBeNull();
  });
});

describe("EnviadorCaixaLocal", () => {
  it("entrega a mensagem com a chave e devolve aceito no 2xx", async () => {
    registros = capturarRegistros();
    const { enviador, chamadas } = caixa(() => new Response(null, { status: 200 }));
    expect(await enviador.enviar(MENSAGEM, CHAVE)).toEqual({ tipo: "aceito" });
    expect(chamadas).toHaveLength(1);
    expect(chamadas[0].url).toBe(URL_CAIXA);
    expect(JSON.parse(chamadas[0].corpo)).toEqual({ ...MENSAGEM, chave: CHAVE });
    expect(registros.linhas).toEqual([]);
  });

  it("resposta de erro do receptor -> falha (não aparenta sucesso)", async () => {
    for (const status of [400, 404, 409, 500, 503, 302]) {
      registros = capturarRegistros();
      const { enviador } = caixa(() => new Response(null, { status }));
      expect(await enviador.enviar(MENSAGEM, CHAVE)).toEqual({ tipo: "falha" });
      expect(registros.linhas.join("\n")).toContain(`(${status})`);
      registros.restaurar();
    }
  });

  it("receptor fora do ar -> falha; tempo esgotado -> incerto", async () => {
    registros = capturarRegistros();
    const recusado = caixa(() => Promise.reject(new TypeError("connection refused")));
    expect(await recusado.enviador.enviar(MENSAGEM, CHAVE)).toEqual({ tipo: "falha" });
    const lento = caixa(() => Promise.reject(new DOMException("timeout", "TimeoutError")));
    expect(await lento.enviador.enviar(MENSAGEM, CHAVE)).toEqual({ tipo: "incerto" });
    expect(registros.linhas).toEqual([
      "sino: falha em envio caixa local (TypeError)",
      "sino: falha em envio caixa local (TimeoutError)",
    ]);
  });

  it("atraso artificial antes da entrega, só quando configurado", async () => {
    registros = capturarRegistros();
    const esperas: number[] = [];
    await caixa(() => new Response(null, { status: 200 }), esperas, 0).enviador.enviar(MENSAGEM, CHAVE);
    expect(esperas).toEqual([]);
    await caixa(() => new Response(null, { status: 200 }), esperas, 8000).enviador.enviar(MENSAGEM, CHAVE);
    expect(esperas).toEqual([8000]);
  });
});

describe("isolamento da produção", () => {
  const ler = (caminho: string) => readFileSync(new URL(caminho, import.meta.url), "utf8");

  it("src/index.ts não importa a entrada nem o enviador de desenvolvimento", () => {
    const index = ler("../../src/index.ts");
    expect(index).not.toMatch(/caixa_local|\.\/dev\b|CAIXA_DEV/);
    expect(index).toContain('from "./envio/resend"');
  });

  it("wrangler.jsonc aponta para src/index.ts e não tem variáveis de desenvolvimento", () => {
    const producao = ler("../../wrangler.jsonc");
    expect(producao).toMatch(/"main":\s*"src\/index\.ts"/);
    expect(producao).not.toMatch(/CAIXA_DEV|dev\.ts|127\.0\.0\.1/);
  });

  it("wrangler.dev.jsonc usa src/dev.ts e escuta só em 127.0.0.1", () => {
    const dev = ler("../../wrangler.dev.jsonc");
    expect(dev).toMatch(/"main":\s*"src\/dev\.ts"/);
    expect(dev).toMatch(/"ip":\s*"127\.0\.0\.1"/);
    expect(dev).not.toMatch(/RESEND_API_KEY|CHAVE_HMAC"\s*:|CHAVE_ASSINATURA"\s*:/);
  });
});
