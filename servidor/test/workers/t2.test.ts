// Entrada do ambiente T2 (src/t2.ts, E4): token exclusivo antes de qualquer
// efeito; com o token, o fluxo da produção (Resend, lista, limites,
// idempotência). No simulador, a rede externa responde 599: um envio pela
// Resend fica "incerto" (201), sem sair do computador.

import { createExecutionContext, env, waitOnExecutionContext } from "cloudflare:test";
import { exports } from "cloudflare:workers";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import worker_t2, { type EnvT2 } from "../../src/t2";

// Só para os testes; não vale fora do simulador.
const TOKEN = "TokenDoSimuladorT2_sem-valor-real-012345678";
const CTX = "c".repeat(64);
const SEGREDO = "Q".repeat(43);
const envT2: EnvT2 = { ...env, TOKEN_ACESSO: TOKEN };

function req(
  caminho: string, corpo: unknown, chave: string, ip: string,
  autorizacao: string | null = `Bearer ${TOKEN}`, extra: RequestInit = {},
): Request {
  return new Request(`https://servico.teste${caminho}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": chave,
      "CF-Connecting-IP": ip,
      ...(autorizacao === null ? {} : { Authorization: autorizacao }),
    },
    body: JSON.stringify(corpo),
    ...extra,
  });
}
const cadastro = (email: string, chave: string, ip: string, autorizacao?: string | null) =>
  req("/v1/desafios", { finalidade: "cadastro", email, contexto: CTX, segredo: SEGREDO }, chave, ip, autorizacao);

async function chamar(r: Request, ambiente: EnvT2 = envT2): Promise<Response> {
  const ctx = createExecutionContext();
  const resposta = await worker_t2.fetch(r, ambiente, ctx);
  await waitOnExecutionContext(ctx);
  return resposta;
}

/** Ambiente que conta os acessos aos Durable Objects. */
function ambienteVigiado(base: EnvT2) {
  const acessos: string[] = [];
  const ambiente = new Proxy(base, {
    get(alvo, nome, receptor) {
      if (nome === "DESTINO" || nome === "LIMITE_IP" || nome === "TETO_GLOBAL") acessos.push(String(nome));
      return Reflect.get(alvo, nome, receptor);
    },
  });
  return { ambiente, acessos };
}

/** Requisição cujo corpo registra se foi lido. */
function comCorpoVigiado(autorizacao: string | null) {
  let lido = false;
  // Fila de tamanho 0: `pull` só acontece quando alguém lê o corpo (com o
  // padrão 1, o próprio fluxo chamaria `pull` logo na criação).
  const corpo = new ReadableStream<Uint8Array>({
    pull(controlador) {
      lido = true;
      controlador.enqueue(new TextEncoder().encode(
        JSON.stringify({ finalidade: "cadastro", email: "ninguem@exemplo.com", contexto: CTX, segredo: SEGREDO }),
      ));
      controlador.close();
    },
  }, { highWaterMark: 0 });
  const r = req("/v1/desafios", null, "pedido-t2-corpo-0001", "192.0.2.60", autorizacao, {
    body: corpo, duplex: "half",
  } as RequestInit);
  return { r, lido: () => lido };
}

let registros: string[] = [];
const originais = { error: console.error, warn: console.warn, log: console.log };
beforeEach(() => {
  registros = [];
  console.error = (...a: unknown[]) => void registros.push(a.map(String).join(" "));
  console.warn = (...a: unknown[]) => void registros.push(a.map(String).join(" "));
  console.log = (...a: unknown[]) => void registros.push(a.map(String).join(" "));
});
afterEach(() => {
  const juntos = registros.join("\n");
  for (const proibido of [TOKEN, SEGREDO, "x@exemplo.com", "ninguem@exemplo.com", "fora@exemplo.com", "re_teste_nao_e_credencial"]) {
    expect(juntos).not.toContain(proibido);
  }
  Object.assign(console, originais);
});

describe("entrada do ambiente T2 (src/t2.ts)", () => {
  it("sem token, com token errado, segredo ausente ou malformado: 404 igual ao de rota inexistente", async () => {
    const ip = "192.0.2.50";
    const casos: [Request, EnvT2][] = [
      [cadastro("x@exemplo.com", "pedido-t2-000000001", ip, null), envT2],
      [cadastro("x@exemplo.com", "pedido-t2-000000002", ip, "Bearer errado"), envT2],
      [cadastro("x@exemplo.com", "pedido-t2-000000003", ip, `Bearer ${"A".repeat(43)}`), envT2],
      [cadastro("x@exemplo.com", "pedido-t2-000000004", ip, `bearer ${TOKEN}`), envT2],
      [cadastro("x@exemplo.com", "pedido-t2-000000005", ip), { ...envT2, TOKEN_ACESSO: undefined }],
      [cadastro("x@exemplo.com", "pedido-t2-000000006", ip, "Bearer curto"), { ...envT2, TOKEN_ACESSO: "curto" }],
    ];
    // A 404 de rota inexistente da própria produção, para comparação.
    const inexistente = await exports.default.fetch(new Request("https://servico.teste/x"));
    const esperado = { status: inexistente.status, corpo: await inexistente.text(), tipo: inexistente.headers.get("Content-Type") };
    expect(esperado.status).toBe(404);
    for (const [r, ambiente] of casos) {
      const resposta = await chamar(r, ambiente);
      expect({ status: resposta.status, corpo: await resposta.text(), tipo: resposta.headers.get("Content-Type") })
        .toEqual(esperado);
    }
    // Os 404 não consumiram o limite do IP: os 10 pedidos da hora continuam livres.
    for (let i = 0; i < 10; i++) {
      expect((await chamar(cadastro("fora@exemplo.com", `pedido-t2-limite-${i}`, ip))).status).toBe(403);
    }
    expect((await chamar(cadastro("fora@exemplo.com", "pedido-t2-limite-x", ip))).status).toBe(429);
  });

  it("sem o token certo, o corpo não é lido e nenhum Durable Object é acessado", async () => {
    for (const autorizacao of [null, "Bearer errado"]) {
      const { ambiente, acessos } = ambienteVigiado(envT2);
      const { r, lido } = comCorpoVigiado(autorizacao);
      expect((await chamar(r, ambiente)).status).toBe(404);
      expect(lido()).toBe(false);
      expect(acessos).toEqual([]);
    }
    // Com o token certo, o mesmo pedido chega ao serviço (corpo lido, objetos usados).
    const { ambiente, acessos } = ambienteVigiado(envT2);
    const { r, lido } = comCorpoVigiado(`Bearer ${TOKEN}`);
    expect((await chamar(r, ambiente)).status).toBe(201);
    expect(lido()).toBe(true);
    expect(acessos.length).toBeGreaterThan(0);
  });

  it("com token: fluxo da produção; envio pela Resend (incerto no simulador) e idempotência preservada", async () => {
    const ip = "192.0.2.51";
    const primeiro = await chamar(cadastro("x@exemplo.com", "pedido-t2-000000010", ip));
    expect(primeiro.status).toBe(201);
    const corpo = (await primeiro.json()) as { desafio_id: string };
    // Mesma chave e mesmo corpo: mesma resposta, sem novo desafio.
    const repetido = await chamar(cadastro("x@exemplo.com", "pedido-t2-000000010", ip));
    expect(repetido.status).toBe(201);
    expect(((await repetido.json()) as { desafio_id: string }).desafio_id).toBe(corpo.desafio_id);
    // Mesma chave com outro conteúdo: conflito de idempotência.
    const conflito = await chamar(
      req("/v1/desafios", { finalidade: "alteracao_email", email: "x@exemplo.com", contexto: CTX, segredo: SEGREDO },
        "pedido-t2-000000010", ip),
    );
    expect(conflito.status).toBe(409);
  });

  it("com token: destinatário fora da lista continua bloqueado (403) e a recuperação, neutra (202)", async () => {
    const ip = "192.0.2.52";
    const fora = await chamar(cadastro("fora@exemplo.com", "pedido-t2-000000020", ip));
    expect(fora.status).toBe(403);
    expect(await fora.json()).toEqual({ erro: "destinatario_nao_permitido" });
    const recuperacao = await chamar(
      req("/v1/desafios", { finalidade: "recuperacao_senha", email: "fora@exemplo.com", contexto: CTX, segredo: SEGREDO },
        "pedido-t2-000000021", ip),
    );
    expect(recuperacao.status).toBe(202);
  });

  it("com token: endereços de envio ausentes continuam dando 503, sem chamar a Resend", async () => {
    const r = await chamar(cadastro("x@exemplo.com", "pedido-t2-000000030", "192.0.2.53"), { ...envT2, REMETENTE: undefined });
    expect(r.status).toBe(503);
    expect(await r.json()).toEqual({ erro: "servico_indisponivel" });
  });

  it("a produção (src/index.ts) continua sem exigir token", async () => {
    const r = await exports.default.fetch(cadastro("fora@exemplo.com", "pedido-prod-000000001", "192.0.2.54", null));
    expect(r.status).toBe(403);
    expect(await r.json()).toEqual({ erro: "destinatario_nao_permitido" });
  });
});
