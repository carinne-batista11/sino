// Garantias verificadas no simulador local dos Durable Objects (workerd):
// atomicidade dentro de cada objeto sob concorrência, limites entre objetos,
// falhas parciais, alarmes de envio abandonado e de retenção, e a entrada
// publicada do Worker sem rede externa.

import { createExecutionContext, env, runDurableObjectAlarm, runInDurableObject } from "cloudflare:test";
import { exports } from "cloudflare:workers";
import { describe, expect, it } from "vitest";
import { HORA_MS, TETO_GLOBAL_DIA } from "../../src/config";
import { EnviadorSimulado } from "../../src/envio/simulado";
import worker_dev from "../../src/dev";
import { pedirDesafio, validarDesafio, type Dependencias, type EntradaPedido, type PortaDestino } from "../../src/fluxos";
import { dependenciasDoAmbiente, segredosDoAmbiente } from "../../src/index";
import { resumoDoEmail } from "../../src/nucleo/destinatarios";
import type { PedidoDesafio, RegrasDestino, ResultadoSolicitar } from "../../src/nucleo/desafios";

const CTX = "c".repeat(64);
const SEGREDO = "Q".repeat(43);
let contador = 0;
const unico = (prefixo: string) => `${prefixo}-${Date.now()}-${contador++}-${crypto.randomUUID()}`;

const destinoStub = (nome = unico("destino")) => env.DESTINO.get(env.DESTINO.idFromName(nome));
const tetoStub = (nome = unico("teto")) => env.TETO_GLOBAL.get(env.TETO_GLOBAL.idFromName(nome));
const ipStub = (nome = unico("ip")) => env.LIMITE_IP.get(env.LIMITE_IP.idFromName(nome));

function pedido(n: number, agora: number, extra: Partial<PedidoDesafio> = {}): PedidoDesafio {
  return {
    finalidade: "cadastro", contexto: CTX, segredoHash: `s${n}`, chaveHash: `k${n}`, semEnvio: false, permitido: true, agora,
    ...extra,
  };
}

type Criado = Extract<ResultadoSolicitar, { tipo: "criado" }>;

async function pronto(stub: ReturnType<typeof destinoStub>, agora: number): Promise<Criado> {
  const r = (await stub.solicitar(pedido(1, agora))) as Criado;
  expect(r.tipo).toBe("criado");
  expect(await stub.registrarReserva(r.desafioId, "reserva-1", agora)).toBe(true);
  expect(await stub.iniciarEnvio(r.desafioId, agora)).toBe(true);
  return r;
}

function linhas(stub: DurableObjectStub, sql: string) {
  return runInDurableObject(stub, (_instancia, estado) => estado.storage.sql.exec(sql).toArray());
}

/**
 * Dependências reais (Durable Objects do simulador) com enviador simulado. A
 * lista do ambiente de teste é ampliada com p0..p99 (acima do limite de 50 da
 * configuração, só para o teste de concorrência).
 */
function depsReais(enviador = new EnviadorSimulado()) {
  const tarefas: Promise<unknown>[] = [];
  const base = segredosDoAmbiente(env)!;
  const destinatarios = new Set(base.destinatarios);
  for (let i = 0; i < 100; i++) destinatarios.add(resumoDoEmail(base.chaveHmac, `p${i}@exemplo.com`));
  const deps = dependenciasDoAmbiente(env, (t) => void tarefas.push(t), {
    enviador, segredos: { ...base, destinatarios },
  });
  const nomeTeto = unico("teto");
  deps.tetoGlobal = () => tetoStub(nomeTeto) as never;
  return { deps, enviador, tarefas, teto: () => tetoStub(nomeTeto) };
}

function entrada(email: string, ip: string, extra: Partial<EntradaPedido> = {}): EntradaPedido {
  return {
    finalidade: "cadastro", email, contexto: CTX, segredo: SEGREDO, chave: `pedido-${crypto.randomUUID()}`,
    semEnvio: false, ip, ...extra,
  };
}

describe("concorrência dentro de um objeto", () => {
  it("25 pedidos simultâneos ao mesmo destino: um criado, os demais aguardam 60 s", async () => {
    const stub = destinoStub();
    const agora = Date.now();
    const rs = await Promise.all(Array.from({ length: 25 }, (_, i) => stub.solicitar(pedido(i, agora))));
    expect(rs.filter((r) => r.tipo === "criado")).toHaveLength(1);
    expect(rs.filter((r) => r.tipo === "aguarde")).toHaveLength(24);
    expect(await linhas(stub, "SELECT id FROM desafios")).toHaveLength(1);
  });

  it("10 repetições simultâneas do mesmo pedido: um desafio só", async () => {
    const stub = destinoStub();
    const agora = Date.now();
    const rs = await Promise.all(Array.from({ length: 10 }, () => stub.solicitar(pedido(7, agora))));
    const ids = new Set(rs.map((r) => ("desafioId" in r ? r.desafioId : null)));
    expect(ids.size).toBe(1);
    expect(rs.filter((r) => r.tipo === "criado")).toHaveLength(1);
    expect(rs.filter((r) => r.tipo === "repeticao")).toHaveLength(9);
  });

  it("10 validações corretas simultâneas: uma única autorização", async () => {
    const stub = destinoStub();
    const agora = Date.now();
    const r = await pronto(stub, agora);
    const vs = await Promise.all(
      Array.from({ length: 10 }, (_, i) =>
        stub.validar({ desafioId: r.desafioId, segredoHash: "s1", chaveHash: `v${i}`, codigo: r.codigo!, permitido: true, agora: agora + 1 }),
      ),
    );
    expect(vs.filter((v) => v.tipo === "autorizado")).toHaveLength(1);
    expect(vs.filter((v) => v.tipo === "encerrado")).toHaveLength(9);
  });

  it("10 tentativas erradas simultâneas: no máximo 5 contam", async () => {
    const stub = destinoStub();
    const agora = Date.now();
    const r = await pronto(stub, agora);
    const errado = r.codigo === "000000" ? "000001" : "000000";
    const vs = await Promise.all(
      Array.from({ length: 10 }, (_, i) =>
        stub.validar({ desafioId: r.desafioId, segredoHash: "s1", chaveHash: `e${i}`, codigo: errado, permitido: true, agora: agora + 1 }),
      ),
    );
    expect(vs.filter((v) => v.tipo === "codigo_invalido")).toHaveLength(5);
    expect(vs.filter((v) => v.tipo === "encerrado")).toHaveLength(5);
    expect(await linhas(stub, "SELECT tentativas, motivo_invalidacao FROM desafios")).toEqual([
      { tentativas: 5, motivo_invalidacao: "tentativas" },
    ]);
  });

  it("teto global: 100 reservas simultâneas, exatamente 80 aceitas", async () => {
    const stub = tetoStub();
    const agora = Date.now();
    const rs = await Promise.all(Array.from({ length: 100 }, () => stub.reservar(agora)));
    expect(rs.filter((r) => r !== null)).toHaveLength(TETO_GLOBAL_DIA);
    expect(await stub.esgotado(agora)).toBe(true);
  });

  it("IP: 15 pedidos simultâneos, exatamente 10 aceitos", async () => {
    const stub = ipStub();
    const agora = Date.now();
    const rs = await Promise.all(Array.from({ length: 15 }, () => stub.reservarPedido(agora)));
    expect(rs.filter(Boolean)).toHaveLength(10);
  });
});

describe("limites entre objetos", () => {
  it("100 fluxos simultâneos (e-mails e IPs distintos): nunca passa de 80 envios", async () => {
    const { deps, enviador, teto } = depsReais();
    const rs = await Promise.all(
      Array.from({ length: 100 }, (_, i) => pedirDesafio(deps, entrada(`p${i}@exemplo.com`, `198.51.100.${i}`))),
    );
    const enviados = rs.filter((r) => r.status === 201).length;
    expect(enviados).toBeLessThanOrEqual(TETO_GLOBAL_DIA);
    expect(enviados).toBe(enviador.enviadas.length);
    expect(rs.every((r) => r.status === 201 || r.status === 503)).toBe(true);
    const total = await linhas(teto(), "SELECT envios FROM totais_diarios");
    expect(total).toEqual([{ envios: TETO_GLOBAL_DIA }]);
  }, 60_000); // 100 fluxos criam 200 objetos novos no simulador
});

describe("falhas parciais com objetos reais", () => {
  /** Porta de destino que captura o código gerado e pode falhar num método. */
  function destinoInstrumentado(deps: Dependencias, falharEm?: keyof PortaDestino) {
    const capturado: { codigo?: string; desafioId?: string; emailHash?: string } = {};
    const original = deps.destino;
    deps.destino = (emailHash) => {
      const porta = original(emailHash);
      capturado.emailHash = emailHash;
      return new Proxy(porta, {
        get(alvo, prop) {
          if (prop === falharEm) return async () => { throw new Error("falha simulada"); };
          if (prop === "solicitar") {
            return async (p: PedidoDesafio) => {
              const r = await alvo.solicitar(p);
              if (r.tipo === "criado") Object.assign(capturado, { codigo: r.codigo, desafioId: r.desafioId });
              return r;
            };
          }
          return Reflect.get(alvo, prop);
        },
      });
    };
    return capturado;
  }

  it("teto recusa e a invalidação falha: o código certo não autoriza", async () => {
    const { deps, enviador, teto } = depsReais();
    const t = teto();
    const agora = Date.now();
    await Promise.all(Array.from({ length: TETO_GLOBAL_DIA }, () => t.reservar(agora)));
    deps.tetoGlobal = () => ({ esgotado: async () => false, reservar: (a: number) => t.reservar(a) }) as never;
    const capturado = destinoInstrumentado(deps, "marcarSemReserva");

    const r = await pedirDesafio(deps, entrada("teto@exemplo.com", "198.51.100.200"));
    expect(r.status).toBe(503);
    expect(enviador.enviadas).toHaveLength(0);
    const stub = env.DESTINO.get(env.DESTINO.idFromName(capturado.emailHash!));
    expect(await linhas(stub, "SELECT estado_envio, invalidado_em FROM desafios")).toEqual([
      { estado_envio: "pendente_reserva", invalidado_em: null },
    ]);
    const v = await validarDesafio(deps, {
      desafioId: capturado.desafioId!, email: "teto@exemplo.com", segredo: SEGREDO, chave: "valida-0000000001",
      codigo: capturado.codigo!, ip: "198.51.100.200",
    });
    expect(v).toEqual({ status: 422, corpo: { erro: "codigo_invalido", tentativas_restantes: 4 } });
  });

  it("reserva obtida mas não gravada no destino: nenhum envio e nenhuma autorização", async () => {
    const { deps, enviador } = depsReais();
    const capturado = destinoInstrumentado(deps, "registrarReserva");
    const r = await pedirDesafio(deps, entrada("reserva@exemplo.com", "198.51.100.201"));
    expect(r.status).toBe(502);
    expect(enviador.enviadas).toHaveLength(0);
    const v = await validarDesafio(deps, {
      desafioId: capturado.desafioId!, email: "reserva@exemplo.com", segredo: SEGREDO, chave: "valida-0000000002",
      codigo: capturado.codigo!, ip: "198.51.100.201",
    });
    expect(v.status).toBe(422);
  });
});

describe("alarmes", () => {
  it("envio abandonado em 'enviando' vira 'incerto' pelo alarme e o código continua validável", async () => {
    const stub = destinoStub();
    const base = Date.now() - 2 * 60_000;
    // Preparação síncrona dentro do objeto (nenhum alarme intercala), no passado.
    const r = await runInDurableObject(stub, async (instancia, estado) => {
      const regras = (instancia as unknown as { regras: RegrasDestino }).regras;
      const criado = regras.solicitar(pedido(1, base)) as Criado;
      expect(regras.registrarReserva(criado.desafioId, "reserva-1", base + 1)).toBe(true);
      expect(regras.iniciarEnvio(criado.desafioId, base + 2)).toBe(true);
      await estado.storage.setAlarm(Date.now());
      return criado;
    });
    await runDurableObjectAlarm(stub);
    expect(await linhas(stub, "SELECT estado_envio FROM desafios")).toEqual([{ estado_envio: "incerto" }]);
    const v = await stub.validar({
      desafioId: r.desafioId, segredoHash: "s1", chaveHash: "v1", codigo: r.codigo!, permitido: true,
      agora: Date.now(),
    });
    expect(v.tipo).toBe("autorizado");
  });

  it("reserva abandonada: o alarme encerra e a execução atrasada não retoma o fluxo", async () => {
    const stub = destinoStub();
    const base = Date.now() - 2 * 60_000;
    const r = (await stub.solicitar(pedido(1, base))) as Criado;
    await runDurableObjectAlarm(stub);
    expect(await linhas(stub, "SELECT estado_envio, motivo_invalidacao FROM desafios")).toEqual([
      { estado_envio: "pendente_reserva", motivo_invalidacao: "reserva_abandonada" },
    ]);
    // Execução atrasada, com relógio defasado ou atual: nada avança.
    expect(await stub.registrarReserva(r.desafioId, "reserva-tardia", base + 1000)).toBe(false);
    expect(await stub.registrarReserva(r.desafioId, "reserva-tardia", Date.now())).toBe(false);
    expect(await stub.iniciarEnvio(r.desafioId, base + 2000)).toBe(false);
    const v = await stub.validar({
      desafioId: r.desafioId, segredoHash: "s1", chaveHash: "v1", codigo: r.codigo!, permitido: true,
      agora: Date.now(),
    });
    expect(v.tipo).toBe("encerrado");
  });

  it("retenção: o alarme apaga desafios encerrados há mais de 24 h", async () => {
    const stub = destinoStub();
    await stub.solicitar(pedido(1, Date.now() - 25 * HORA_MS));
    await runDurableObjectAlarm(stub);
    await runDurableObjectAlarm(stub);
    expect(await linhas(stub, "SELECT id FROM desafios")).toHaveLength(0);
  });

  it("retenção por IP: o alarme apaga o contador por hora após 2 h e mantém o diário", async () => {
    const stub = ipStub();
    // 3 h atrás: a janela por hora já passou da retenção (2 h); a diária (48 h), não.
    await stub.reservarPedido(Date.now() - 3 * HORA_MS);
    await runDurableObjectAlarm(stub);
    expect(await linhas(stub, "SELECT duracao FROM contadores")).toEqual([{ duracao: "dia" }]);
  });
});

describe("entrada publicada do Worker (sem rede externa)", () => {
  it("recuperação sem envio responde 202 neutro pelo fetch padrão", async () => {
    const resposta = await exports.default.fetch(
      new Request("https://servico.teste/v1/desafios", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": "pedido-publicado-0001",
          "CF-Connecting-IP": "192.0.2.10",
        },
        body: JSON.stringify({
          finalidade: "recuperacao_senha", email: "ninguem@exemplo.com", contexto: CTX, segredo: SEGREDO, sem_envio: true,
        }),
      }),
    );
    expect(resposta.status).toBe(202);
    expect(Object.keys((await resposta.json()) as object).sort()).toEqual([
      "agora", "desafio_id", "expira_em", "reenvio_permitido_em",
    ]);
  });

  it("requisição inválida e rota desconhecida", async () => {
    const invalida = await exports.default.fetch(
      new Request("https://servico.teste/v1/desafios", { method: "POST", body: "{}" }),
    );
    expect(invalida.status).toBe(400);
    expect((await exports.default.fetch(new Request("https://servico.teste/x"))).status).toBe(404);
  });

  it("sem segredos configurados: 503", async () => {
    const deps = dependenciasDoAmbiente({ ...env, CHAVE_HMAC: undefined }, () => {}, { enviador: new EnviadorSimulado() });
    const r = await pedirDesafio(deps, entrada("x@exemplo.com", "192.0.2.11"));
    expect(r).toEqual({ status: 503, corpo: { erro: "servico_indisponivel" } });
  });
});

describe("restrição de destinatários com objetos reais (contrato v1.1)", () => {
  it("estado 'bloqueado' e motivo novo aceitos pelas restrições da tabela; validação fora da lista", async () => {
    const stub = destinoStub();
    const agora = Date.now();
    const r = (await stub.solicitar(pedido(1, agora))) as Criado;
    expect(await stub.marcarBloqueado(r.desafioId, agora)).toBe(true);
    const outro = destinoStub();
    const r2 = await pronto(outro, agora);
    expect(await outro.registrarResultado(r2.desafioId, "bloqueado", agora + 1)).toBe("bloqueado");
    expect(await linhas(stub, "SELECT estado_envio, reserva_global, motivo_invalidacao FROM desafios")).toEqual([
      { estado_envio: "bloqueado", reserva_global: null, motivo_invalidacao: "destinatario_nao_permitido" },
    ]);
    expect(await linhas(outro, "SELECT estado_envio, motivo_invalidacao FROM desafios")).toEqual([
      { estado_envio: "bloqueado", motivo_invalidacao: "destinatario_nao_permitido" },
    ]);
    const terceiro = destinoStub();
    const r3 = await pronto(terceiro, agora);
    const v = await terceiro.validar({
      desafioId: r3.desafioId, segredoHash: "s1", chaveHash: "v1", codigo: r3.codigo!, permitido: false, agora: agora + 1,
    });
    expect(v).toEqual({ tipo: "nao_permitido" });
    expect(await linhas(terceiro, "SELECT tentativas, motivo_invalidacao FROM desafios")).toEqual([
      { tentativas: 0, motivo_invalidacao: "destinatario_nao_permitido" },
    ]);
    expect(await linhas(terceiro, "SELECT versao FROM esquema_destino")).toEqual([{ versao: 2 }]);
  });

  it("recuperação fora da lista: desafio sem envio no objeto real", async () => {
    const stub = destinoStub();
    const r = (await stub.solicitar(pedido(1, Date.now(), { finalidade: "recuperacao_senha", permitido: false }))) as Criado;
    expect(r.codigo).toBeNull();
    expect(await linhas(stub, "SELECT estado_envio FROM desafios")).toEqual([{ estado_envio: "sem_envio" }]);
  });

  it.each([
    ["ausente", undefined],
    ["vazia", ""],
    ["malformada", "v1:abc"],
  ])("lista %s: 503 no pedido e na validação", async (_nome, lista) => {
    const deps = dependenciasDoAmbiente({ ...env, DESTINATARIOS_PERMITIDOS: lista }, () => {}, {
      enviador: new EnviadorSimulado(),
    });
    expect(deps.segredos).toBeNull();
    expect(await pedirDesafio(deps, entrada("x@exemplo.com", "192.0.2.12"))).toEqual({
      status: 503, corpo: { erro: "servico_indisponivel" },
    });
    expect(await validarDesafio(deps, {
      desafioId: "A".repeat(22), email: "x@exemplo.com", segredo: SEGREDO, chave: "valida-0000000009", codigo: "123456",
      ip: "192.0.2.12",
    })).toEqual({ status: 503, corpo: { erro: "servico_indisponivel" } });
  });

  it("entrada publicada: cadastro fora da lista recebe 403 sem envio", async () => {
    const resposta = await exports.default.fetch(
      new Request("https://servico.teste/v1/desafios", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": "pedido-publicado-0002",
          "CF-Connecting-IP": "192.0.2.13",
        },
        body: JSON.stringify({ finalidade: "cadastro", email: "fora@exemplo.com", contexto: CTX, segredo: SEGREDO }),
      }),
    );
    expect(resposta.status).toBe(403);
    expect(await resposta.json()).toEqual({ erro: "destinatario_nao_permitido" });
  });

  it("entrada de desenvolvimento: também exige a lista, sem modo irrestrito", async () => {
    const pedidoDev = (chave: string, email: string) =>
      new Request("https://servico.teste/v1/desafios", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": chave, "CF-Connecting-IP": "192.0.2.14" },
        body: JSON.stringify({ finalidade: "cadastro", email, contexto: CTX, segredo: SEGREDO }),
      });
    const envDev = { ...env, CAIXA_DEV_URL: "http://127.0.0.1:8025" };
    const semLista = await worker_dev.fetch(
      pedidoDev("pedido-dev-000000001", "x@exemplo.com"), { ...envDev, DESTINATARIOS_PERMITIDOS: undefined },
      createExecutionContext(),
    );
    expect(semLista.status).toBe(503);
    const fora = await worker_dev.fetch(pedidoDev("pedido-dev-000000002", "fora@exemplo.com"), envDev, createExecutionContext());
    expect(fora.status).toBe(403);
  });
});
