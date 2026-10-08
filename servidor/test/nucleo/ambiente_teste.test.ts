// Ambiente remoto de testes (src/teste.ts, ERS v7.0, E4): token obrigatório
// antes de qualquer objeto e envio descartado sem rede. As regras dos códigos
// são as mesmas da produção; aqui se confere só o que muda nesta entrada.

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { autorizada, comToken, tokenDeTeste } from "../../src/acesso_teste";
import { EnviadorDescarte } from "../../src/envio/descarte";
import type { Enviador, Mensagem } from "../../src/envio/enviador";
import { EnviadorRestrito } from "../../src/envio/restrito";
import { criarApp } from "../../src/http";
import { Mundo, capturarRegistros, resumoDe } from "./apoio";

const TOKEN = "T0kenDeTeste_sem-valor-real-0123456789abcde"; // 43 caracteres, só para os testes
const PERMITIDO = "pessoa@exemplo.com";
const FORA = "fora@exemplo.com";
const SEGREDO = "S".repeat(43);
const CONTEXTO = "e".repeat(64);
const URL_BASE = "https://servico.teste";

let mundo: Mundo;
let registros: ReturnType<typeof capturarRegistros>;
const codigosVistos: string[] = [];

beforeEach(() => {
  mundo = new Mundo();
  registros = capturarRegistros();
});

afterEach(() => {
  registros.restaurar();
  const juntos = registros.linhas.join("\n");
  for (const proibido of [TOKEN, PERMITIDO, FORA, resumoDe(PERMITIDO), resumoDe(FORA), SEGREDO, ...codigosVistos]) {
    expect(juntos).not.toContain(proibido);
  }
  codigosVistos.length = 0;
});

/** Descarte observado: conta as chamadas sem guardar o conteúdo. */
class DescarteContado implements Enviador {
  chamadas = 0;
  private readonly real = new EnviadorDescarte();
  enviar(m: Mensagem, chave: string) {
    this.chamadas++;
    return this.real.enviar(m, chave);
  }
}

function appDeTeste(descarte: Enviador = new EnviadorDescarte()) {
  const deps = mundo.deps();
  return criarApp({ ...deps, enviador: new EnviadorRestrito(descarte, deps.segredos) });
}

function requisicao(caminho: string, corpo: unknown, extra: Record<string, string> = {}, chave = "pedido-0000000001") {
  return new Request(`${URL_BASE}${caminho}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": chave,
      "CF-Connecting-IP": "203.0.113.30",
      Authorization: `Bearer ${TOKEN}`,
      ...extra,
    },
    body: JSON.stringify(corpo),
  });
}

function cabecalhosDe(h: Headers): [string, string][] {
  const lista: [string, string][] = [];
  h.forEach((valor, nome) => void lista.push([nome, valor]));
  return lista;
}

const cadastro = (email = PERMITIDO, extra: Record<string, string> = {}) =>
  requisicao("/v1/desafios", { finalidade: "cadastro", email, contexto: CONTEXTO, segredo: SEGREDO }, extra);

describe("token do ambiente de teste", () => {
  it("só aceita 32 bytes em base64url", () => {
    expect(tokenDeTeste(TOKEN)).toBe(TOKEN);
    for (const ruim of [undefined, "", "curto", `${TOKEN}x`, TOKEN.slice(1), `${TOKEN.slice(1)}=`, `${TOKEN.slice(1)}+`]) {
      expect(tokenDeTeste(ruim)).toBeNull();
    }
  });

  it("exige exatamente `Bearer <token>`", () => {
    const com = (valor?: string) =>
      new Request(URL_BASE, valor === undefined ? {} : { headers: { Authorization: valor } });
    expect(autorizada(com(`Bearer ${TOKEN}`), TOKEN)).toBe(true);
    for (const ruim of [
      // (Espaços nas bordas do valor são removidos pelo próprio Headers, como no HTTP.)
      undefined, "", TOKEN, `bearer ${TOKEN}`, `Bearer  ${TOKEN}`, `Bearer ${TOKEN}x`,
      `Bearer ${TOKEN.slice(0, -1)}A`, `Basic ${TOKEN}`,
    ]) {
      expect(autorizada(com(ruim), TOKEN)).toBe(false);
    }
    // Segredo ausente ou malformado: nada é aceito, nem um cabeçalho vazio.
    expect(autorizada(com("Bearer "), null)).toBe(false);
    expect(autorizada(com("Bearer null"), null)).toBe(false);
  });

  it("sem o token certo: 404 igual ao de rota inexistente, sem criar o app", async () => {
    let criado = 0;
    const criar = () => {
      criado++;
      return appDeTeste();
    };
    const semToken = await comToken(cadastro(PERMITIDO, { Authorization: "" }), TOKEN, criar);
    const errado = await comToken(cadastro(PERMITIDO, { Authorization: `Bearer ${"A".repeat(43)}` }), TOKEN, criar);
    const semSegredo = await comToken(cadastro(), undefined, criar);
    const malformado = await comToken(cadastro(PERMITIDO, { Authorization: "Bearer curto" }), "curto", criar);
    expect(criado).toBe(0);
    expect(mundo.ips.size).toBe(0);
    expect(mundo.destinos.size).toBe(0);

    const rotaInexistente = await appDeTeste().fetch(new Request(`${URL_BASE}/x`));
    const esperado = {
      status: rotaInexistente.status,
      corpo: await rotaInexistente.text(),
      cabecalhos: cabecalhosDe(rotaInexistente.headers),
    };
    for (const r of [semToken, errado, semSegredo, malformado]) {
      expect({ status: r.status, corpo: await r.text(), cabecalhos: cabecalhosDe(r.headers) }).toEqual(esperado);
    }
    expect(esperado.status).toBe(404);
  });
});

describe("envio descartado", () => {
  it("cadastro na lista: 201, desafio enviado, nenhuma rede; código correto só localmente", async () => {
    const descarte = new DescarteContado();
    const codigo = mundo.aleatorio.proximoCodigo();
    codigosVistos.push(codigo);
    const r = await comToken(cadastro(), TOKEN, () => appDeTeste(descarte));
    await mundo.concluirSegundoPlano();
    expect(r.status).toBe(201);
    const { desafio_id } = (await r.json()) as { desafio_id: string };
    expect(descarte.chamadas).toBe(1);
    expect(mundo.enviador.enviadas).toHaveLength(0); // o simulado do Mundo não é usado
    const linha = mundo.bancosDestino.get(resumoDe(PERMITIDO))!.um<{ estado_envio: string }>(
      "SELECT estado_envio FROM desafios",
    );
    expect(linha?.estado_envio).toBe("enviado");

    const validar = (cod: string, chave: string) =>
      comToken(
        requisicao(`/v1/desafios/${desafio_id}/validacao`, { email: PERMITIDO, segredo: SEGREDO, codigo: cod }, {}, chave),
        TOKEN,
        () => appDeTeste(descarte),
      );
    const errado = await validar(codigo === "000000" ? "111111" : "000000", "valida-000000001");
    expect(errado.status).toBe(422);
    expect(await errado.json()).toEqual({ erro: "codigo_invalido", tentativas_restantes: 4 });
    // Só aqui, com a aleatoriedade controlada, o código é conhecido; no
    // ambiente remoto ele é descartado e este caminho não pode ser testado.
    const certo = await validar(codigo, "valida-000000002");
    expect(certo.status).toBe(200);
  });

  it("fora da lista: 403 e o descarte nem é chamado", async () => {
    const descarte = new DescarteContado();
    const r = await comToken(cadastro(FORA), TOKEN, () => appDeTeste(descarte));
    await mundo.concluirSegundoPlano();
    expect(r.status).toBe(403);
    expect(descarte.chamadas).toBe(0);
  });

  it("o descarte não usa a rede nem registra nada", async () => {
    const linhasAntes = registros.linhas.length;
    const r = await new EnviadorDescarte().enviar({ para: PERMITIDO, assunto: "a", texto: "123456" }, "chave");
    expect(r).toEqual({ tipo: "aceito" });
    expect(registros.linhas.length).toBe(linhasAntes);
  });
});

describe("pacote da entrada de teste", () => {
  it("não alcança a Resend, a caixa local nem as outras entradas", async () => {
    const { readFileSync } = await import("node:fs");
    const { dirname, join, normalize } = await import("node:path");
    const raiz = join(__dirname, "../../src");
    const vistos = new Set<string>();
    const visitar = (arquivo: string) => {
      if (vistos.has(arquivo)) return;
      vistos.add(arquivo);
      const fonte = readFileSync(join(raiz, arquivo), "utf-8");
      for (const m of fonte.matchAll(/from\s+"(\.[^"]+)"/g)) {
        visitar(normalize(join(dirname(arquivo), `${m[1]}.ts`)));
      }
    };
    visitar("teste.ts");
    expect(vistos).toContain("envio/descarte.ts");
    expect(vistos).toContain("acesso_teste.ts");
    for (const proibido of ["envio/resend.ts", "envio/caixa_local.ts", "envio/simulado.ts", "index.ts", "dev.ts"]) {
      expect(vistos).not.toContain(proibido);
    }
  });
});

describe("configuração do ambiente de teste (wrangler.teste.jsonc)", () => {
  it("Worker separado, entrada de teste, só workers.dev e registros desligados", async () => {
    const { readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const ler = (nome: string) =>
      JSON.parse(
        readFileSync(join(__dirname, "../..", nome), "utf-8")
          .split("\n")
          .filter((linha) => !linha.trim().startsWith("//"))
          .join("\n"),
      );
    const teste = ler("wrangler.teste.jsonc");
    const producao = ler("wrangler.jsonc");
    expect(teste.name).toBe("sino-servico-codigos-teste");
    expect(teste.name).not.toBe(producao.name);
    expect(teste.main).toBe("src/teste.ts");
    expect(teste.workers_dev).toBe(true);
    expect(teste.preview_urls).toBe(false);
    expect(teste.route ?? teste.routes ?? null).toBeNull();
    expect(teste.send_metrics).toBe(false);
    expect(teste.observability).toEqual({
      enabled: false,
      head_sampling_rate: 0,
      logs: { enabled: false, invocation_logs: false, head_sampling_rate: 0, persist: false },
      traces: { enabled: false, head_sampling_rate: 0, persist: false },
    });
    // Sem account_id, sem remetente e sem nada da Resend; só o KID nas variáveis.
    expect(teste.account_id).toBeUndefined();
    expect(teste.vars).toEqual({ KID_ASSINATURA: "teste-1" });
    // Mesmos objetos e migração da produção.
    expect(teste.durable_objects).toEqual(producao.durable_objects);
    expect(teste.migrations).toEqual(producao.migrations);
  });
});
