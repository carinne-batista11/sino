// Contrato HTTP v1: validação estrita, rotas e respostas sem dados sensíveis.

import { beforeEach, describe, expect, it } from "vitest";
import { criarApp, emailValido } from "../../src/http";
import { Mundo } from "./apoio";

const SEGREDO = "A".repeat(43);
let mundo: Mundo;
beforeEach(() => {
  mundo = new Mundo();
});

function pedido(corpo: unknown, cabecalhos: Record<string, string> = {}, rota = "/v1/desafios") {
  return new Request(`https://servico.teste${rota}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": "chave-pedido-00001", ...cabecalhos },
    body: typeof corpo === "string" ? corpo : JSON.stringify(corpo),
  });
}

const CORPO = { finalidade: "cadastro", email: "pessoa@exemplo.com", contexto: "b".repeat(64), segredo: SEGREDO };

describe("POST /v1/desafios", () => {
  it("aceita o formato do contrato e não devolve o e-mail nem o código", async () => {
    const resposta = await criarApp(mundo.deps()).fetch(pedido(CORPO));
    expect(resposta.status).toBe(201);
    expect(resposta.headers.get("Cache-Control")).toBe("no-store");
    const texto = await resposta.text();
    expect(texto).not.toContain("pessoa@exemplo.com");
    expect(texto).not.toContain(mundo.enviador.ultimoCodigo("pessoa@exemplo.com"));
    expect(Object.keys(JSON.parse(texto)).sort()).toEqual(["agora", "desafio_id", "expira_em", "reenvio_permitido_em"]);
  });

  it.each([
    ["sem Idempotency-Key", CORPO, { "Idempotency-Key": "" }],
    ["chave curta", CORPO, { "Idempotency-Key": "curta" }],
    ["finalidade desconhecida", { ...CORPO, finalidade: "login" }, {}],
    ["e-mail com espaço", { ...CORPO, email: "a b@c.d" }, {}],
    ["e-mail sem @", { ...CORPO, email: "pessoa.exemplo.com" }, {}],
    ["contexto curto", { ...CORPO, contexto: "abc" }, {}],
    ["segredo curto", { ...CORPO, segredo: "abc" }, {}],
    ["sem_envio no cadastro", { ...CORPO, sem_envio: true }, {}],
    ["sem_envio não booleano", { ...CORPO, finalidade: "recuperacao_senha", sem_envio: "sim" }, {}],
    ["JSON inválido", "{", {}],
    ["lista em vez de objeto", "[]", {}],
    ["Content-Type errado", CORPO, { "Content-Type": "text/plain" }],
    ["Content-Length não numérico", CORPO, { "Content-Length": "abc" }],
  ])("recusa %s com 400", async (_nome, corpo, cabecalhos) => {
    const resposta = await criarApp(mundo.deps()).fetch(pedido(corpo, cabecalhos as Record<string, string>));
    expect(resposta.status).toBe(400);
    expect(await resposta.json()).toEqual({ erro: "requisicao_invalida" });
    expect(mundo.destinos.size).toBe(0);
  });

  it("aceita sem_envio somente na recuperação", async () => {
    const resposta = await criarApp(mundo.deps()).fetch(
      pedido({ ...CORPO, finalidade: "recuperacao_senha", sem_envio: true }),
    );
    expect(resposta.status).toBe(202);
  });
});

describe("POST /v1/desafios/{id}/validacao", () => {
  it("fluxo completo pela API", async () => {
    const app = criarApp(mundo.deps());
    const { desafio_id } = (await (await app.fetch(pedido(CORPO))).json()) as { desafio_id: string };
    const codigo = mundo.enviador.ultimoCodigo("pessoa@exemplo.com");
    const v = await app.fetch(
      pedido({ email: "PESSOA@exemplo.com", segredo: SEGREDO, codigo }, { "Idempotency-Key": "chave-validacao-001" },
        `/v1/desafios/${desafio_id}/validacao`),
    );
    expect(v.status).toBe(200);
    const corpo = (await v.json()) as Record<string, unknown>;
    expect(Object.keys(corpo).sort()).toEqual(["agora", "autorizacao", "expira_em"]);
  });

  it.each([
    ["código com letras", { email: "pessoa@exemplo.com", segredo: SEGREDO, codigo: "12a456" }, "/v1/desafios/AAAAAAAAAAAAAAAAAAAAAA/validacao"],
    ["código com 5 dígitos", { email: "pessoa@exemplo.com", segredo: SEGREDO, codigo: "12345" }, "/v1/desafios/AAAAAAAAAAAAAAAAAAAAAA/validacao"],
    ["id malformado", { email: "pessoa@exemplo.com", segredo: SEGREDO, codigo: "123456" }, "/v1/desafios/curto/validacao"],
  ])("recusa %s com 400", async (_nome, corpo, rota) => {
    const resposta = await criarApp(mundo.deps()).fetch(pedido(corpo, {}, rota));
    expect(resposta.status).toBe(400);
  });

  it("desafio inexistente: 404 sem detalhes", async () => {
    const resposta = await criarApp(mundo.deps()).fetch(
      pedido({ email: "pessoa@exemplo.com", segredo: SEGREDO, codigo: "123456" }, {},
        "/v1/desafios/AAAAAAAAAAAAAAAAAAAAAA/validacao"),
    );
    expect(resposta.status).toBe(404);
    expect(await resposta.json()).toEqual({ erro: "desafio_nao_encontrado" });
  });
});

describe("rotas", () => {
  it("rota desconhecida 404 e método errado 405", async () => {
    const app = criarApp(mundo.deps());
    expect((await app.fetch(new Request("https://servico.teste/"))).status).toBe(404);
    expect((await app.fetch(new Request("https://servico.teste/v1/desafios"))).status).toBe(405);
  });

  it("erro inesperado vira 500 genérico", async () => {
    const deps = mundo.deps();
    deps.ip = () => {
      throw new Error("pessoa@exemplo.com 123456");
    };
    const resposta = await criarApp(deps).fetch(pedido(CORPO));
    expect(resposta.status).toBe(500);
    expect(await resposta.json()).toEqual({ erro: "erro_interno" });
  });
});

describe("emailValido", () => {
  it("aplica só a checagem de formato do contrato", () => {
    expect(emailValido("a@b")).toBe(true);
    expect(emailValido(" a@b.com ")).toBe(true);
    expect(emailValido("a@@b")).toBe(false);
    expect(emailValido("@b")).toBe(false);
    expect(emailValido(`${"a".repeat(250)}@b.com`)).toBe(false);
    expect(emailValido(42)).toBe(false);
  });
});

describe("limite efetivo do corpo (4 KiB)", () => {
  const grande = JSON.stringify({ ...CORPO, extra: "x".repeat(5000) });

  function emPartes(texto: string, tamanho = 1000): ReadableStream<Uint8Array> {
    const bytes = new TextEncoder().encode(texto);
    let i = 0;
    return new ReadableStream({
      pull(c) {
        if (i >= bytes.length) return c.close();
        c.enqueue(bytes.subarray(i, (i += tamanho)));
      },
    });
  }

  function requisicao(corpo: BodyInit, cabecalhos: Record<string, string> = {}) {
    return new Request("https://servico.teste/v1/desafios", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": "chave-pedido-00001", ...cabecalhos },
      body: corpo,
      duplex: "half",
    } as RequestInit);
  }

  it("recusa antecipada pelo Content-Length", async () => {
    const r = requisicao(grande, { "Content-Length": String(new TextEncoder().encode(grande).length) });
    const resposta = await criarApp(mundo.deps()).fetch(r);
    expect(resposta.status).toBe(413);
    expect(await resposta.json()).toEqual({ erro: "corpo_grande_demais" });
    expect(r.bodyUsed).toBe(false); // recusado sem ler o corpo
  });

  it("sem Content-Length, interrompe a leitura ao passar do limite", async () => {
    const r = requisicao(emPartes(grande));
    expect(r.headers.get("Content-Length")).toBeNull();
    const resposta = await criarApp(mundo.deps()).fetch(r);
    expect(resposta.status).toBe(413);
    expect(mundo.destinos.size).toBe(0);
  });

  it("Content-Length menor que o corpo real não engana o limite", async () => {
    const r = requisicao(emPartes(grande), { "Content-Length": "100" });
    expect((await criarApp(mundo.deps()).fetch(r)).status).toBe(413);
  });

  it("corpo dentro do limite, em partes e sem Content-Length, é aceito", async () => {
    const r = requisicao(emPartes(JSON.stringify(CORPO), 7));
    expect((await criarApp(mundo.deps()).fetch(r)).status).toBe(201);
  });

  it("a repetição em processamento leva o Retry-After pela API", async () => {
    let liberar = () => {};
    const portao = new Promise<void>((r) => (liberar = r));
    const deps = mundo.deps();
    deps.tetoGlobal = () => ({
      esgotado: async (a: number) => mundo.teto.esgotado(a),
      reservar: async (a: number) => {
        await portao;
        return mundo.teto.reservar(a);
      },
    });
    const app = criarApp(deps);
    const primeira = app.fetch(pedido(CORPO));
    await new Promise((r) => setImmediate(r));
    const repeticao = await app.fetch(pedido(CORPO));
    expect(repeticao.status).toBe(202);
    expect(repeticao.headers.get("Retry-After")).toBe("2");
    expect(((await repeticao.json()) as { estado: string }).estado).toBe("em_processamento");
    liberar();
    expect((await primeira).status).toBe(201);
  });
});
