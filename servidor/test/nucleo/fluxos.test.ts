// Fluxos completos com objetos em memória e enviador simulado: neutralidade
// da recuperação, teto global, falhas parciais entre objetos, repetição de
// pedidos/validações, envio incerto e ausência de dados sensíveis nos logs.

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  INTERVALO_REENVIO_MS,
  PRAZO_ENVIANDO_MS,
  PRAZO_RESERVA_MS,
  TETO_GLOBAL_DIA,
  VALIDADE_CODIGO_MS,
} from "../../src/config";
import {
  executarEnvio,
  normalizarEmail,
  pedirDesafio,
  prefixoIp,
  validarDesafio,
  type EntradaPedido,
} from "../../src/fluxos";
import { chavePublicaDe, verificarAutorizacao } from "../../src/nucleo/autorizacao";
import { hmacHex } from "../../src/nucleo/cripto";
import { CHAVE_ASSINATURA, CHAVE_HMAC, KID, Mundo, capturarRegistros } from "./apoio";

const EMAIL = "Pessoa@Exemplo.com";
const SEGREDO = "S".repeat(43);
const CONTEXTO = "e".repeat(64);
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
  for (const proibido of [EMAIL, EMAIL.toLowerCase(), SEGREDO, ...codigosVistos]) {
    expect(juntos).not.toContain(proibido);
  }
  codigosVistos.length = 0;
});

function entrada(extra: Partial<EntradaPedido> = {}): EntradaPedido {
  return {
    finalidade: "cadastro", email: EMAIL, contexto: CONTEXTO, segredo: SEGREDO, chave: "pedido-0000000001",
    semEnvio: false, ip: "203.0.113.7", ...extra,
  };
}

function validar(desafioId: string, codigo: string, chave = "valida-000000001", email = EMAIL) {
  return validarDesafio(mundo.deps(), { desafioId, email, segredo: SEGREDO, chave, codigo, ip: "203.0.113.7" });
}

function ultimoCodigo(): string {
  const c = mundo.enviador.ultimoCodigo(EMAIL);
  if (c) codigosVistos.push(c);
  return c as string;
}

function linhaDesafio(id: string) {
  const banco = mundo.bancosDestino.get(hmacHex(CHAVE_HMAC, "email", normalizarEmail(EMAIL)))!;
  return banco.um<Record<string, unknown>>("SELECT * FROM desafios WHERE id = ?", id)!;
}

describe("cadastro e alteração", () => {
  it("cadastro completo: 201, um e-mail com a chave da Resend, autorização verificável", async () => {
    const r = await pedirDesafio(mundo.deps(), entrada());
    expect(r.status).toBe(201);
    const id = r.corpo.desafio_id as string;
    expect(mundo.enviador.enviadas).toHaveLength(1);
    expect(mundo.enviador.enviadas[0].chave).toBe(`sino/cadastro/${id}`);
    expect(mundo.enviador.enviadas[0].mensagem.para).toBe(EMAIL);

    const v = await validar(id, ultimoCodigo());
    expect(v.status).toBe(200);
    const conteudo = verificarAutorizacao(v.corpo.autorizacao as string, { [KID]: chavePublicaDe(CHAVE_ASSINATURA) });
    expect(conteudo).toMatchObject({ fin: "cadastro", ctx: CONTEXTO, kid: KID });
    expect(linhaDesafio(id).estado_envio).toBe("enviado");
  });

  it("resposta perdida do pedido: repetir com a mesma chave devolve o mesmo desafio sem novo e-mail", async () => {
    const r1 = await pedirDesafio(mundo.deps(), entrada());
    const r2 = await pedirDesafio(mundo.deps(), entrada());
    expect(r2.status).toBe(201);
    expect(r2.corpo.desafio_id).toBe(r1.corpo.desafio_id);
    expect(mundo.enviador.enviadas).toHaveLength(1);
    expect((await pedirDesafio(mundo.deps(), entrada({ contexto: "f".repeat(64) }))).status).toBe(409);
  });

  it("resposta perdida da validação: mesma chave devolve a mesma autorização; nova chave é recusada", async () => {
    const id = (await pedirDesafio(mundo.deps(), entrada())).corpo.desafio_id as string;
    const codigo = ultimoCodigo();
    const v1 = await validar(id, codigo, "valida-mesma-0001");
    const v2 = await validar(id, codigo, "valida-mesma-0001");
    expect(v2.corpo.autorizacao).toBe(v1.corpo.autorizacao);
    expect((await validar(id, codigo, "valida-outra-0002")).status).toBe(410);
    expect((await validar(id, "000000", "valida-mesma-0001")).status).toBe(409);
  });

  it("falha definitiva do provedor: 502 e o desafio deixa de valer", async () => {
    mundo.enviador.programar({ tipo: "falha" });
    const r = await pedirDesafio(mundo.deps(), entrada());
    expect(r.status).toBe(502);
    expect(r.corpo.erro).toBe("falha_envio");
    expect(r.corpo.desafio_id).toBeUndefined();
    const banco = [...mundo.bancosDestino.values()][0];
    const linha = banco.um<{ id: string; motivo_invalidacao: string }>("SELECT id, motivo_invalidacao FROM desafios")!;
    expect(linha.motivo_invalidacao).toBe("falha_envio");
    expect((await validar(linha.id, ultimoCodigo())).status).toBe(410);
  });

  it("resultado incerto ou exceção do enviador: 201 e o código continua validável", async () => {
    mundo.enviador.programar({ tipo: "incerto" });
    const r = await pedirDesafio(mundo.deps(), entrada());
    expect(r.status).toBe(201);
    expect((await validar(r.corpo.desafio_id as string, ultimoCodigo())).status).toBe(200);

    const outro = new Mundo();
    mundo = outro;
    mundo.enviador.programar(new Error("quebrou"));
    const r2 = await pedirDesafio(mundo.deps(), entrada());
    expect(r2.status).toBe(201);
    expect(linhaDesafio(r2.corpo.desafio_id as string).estado_envio).toBe("incerto");
  });
});

describe("falhas parciais entre objetos", () => {
  it("teto recusa e a invalidação falha: o desafio nunca autoriza", async () => {
    // O estado do teto ainda não está esgotado, mas a reserva é recusada (corrida).
    for (let i = 0; i < TETO_GLOBAL_DIA; i++) mundo.teto.reservar(mundo.relogio.agora);
    const deps = mundo.deps();
    deps.tetoGlobal = () => ({
      esgotado: async () => false,
      reservar: async (agora: number) => mundo.teto.reservar(agora),
    });
    mundo.falhas.programar("marcarSemReserva");
    const codigo = mundo.aleatorio.proximoCodigo();
    codigosVistos.push(codigo);
    const r = await pedirDesafio(deps, entrada());
    expect(r.status).toBe(503);
    const id = r.corpo.desafio_id as string | undefined;
    expect(id).toBeUndefined();
    expect(mundo.enviador.enviadas).toHaveLength(0);
    // O desafio ficou pendente de reserva (a invalidação falhou) e não autoriza.
    const banco = [...mundo.bancosDestino.values()][0];
    const linha = banco.um<{ id: string; estado_envio: string; invalidado_em: number | null }>(
      "SELECT id, estado_envio, invalidado_em FROM desafios",
    )!;
    expect(linha).toMatchObject({ estado_envio: "pendente_reserva", invalidado_em: null });
    const v = await validar(linha.id, codigo);
    expect(v).toEqual({ status: 422, corpo: { erro: "codigo_invalido", tentativas_restantes: 4 } });
  });

  it("reserva obtida mas não gravada no destino: nenhum envio e nenhuma autorização", async () => {
    mundo.falhas.programar("registrarReserva");
    const codigo = mundo.aleatorio.proximoCodigo();
    codigosVistos.push(codigo);
    const r = await pedirDesafio(mundo.deps(), entrada());
    expect(r.status).toBe(502);
    expect(mundo.enviador.enviadas).toHaveLength(0);
    const banco = [...mundo.bancosDestino.values()][0];
    const linha = banco.um<{ id: string; estado_envio: string }>("SELECT id, estado_envio FROM desafios")!;
    expect(linha.estado_envio).toBe("pendente_reserva");
    expect((await validar(linha.id, codigo)).status).toBe(422);
  });

  it("falha ao registrar o resultado: o envio fica 'enviando' e vira 'incerto' pelo prazo", async () => {
    mundo.falhas.programar("registrarResultado");
    const r = await pedirDesafio(mundo.deps(), entrada());
    expect(r.status).toBe(201);
    const id = r.corpo.desafio_id as string;
    expect(linhaDesafio(id).estado_envio).toBe("enviando");
    mundo.relogio.avancar(PRAZO_ENVIANDO_MS);
    expect((await validar(id, ultimoCodigo())).status).toBe(200);
    expect(linhaDesafio(id).estado_envio).toBe("incerto");
  });

  it("envio antigo concluído fora de ordem não afeta o desafio mais novo", async () => {
    // O envio do primeiro pedido fica parado na reserva global até liberarmos.
    let liberar = () => {};
    const portao = new Promise<void>((r) => (liberar = r));
    const depsLentas = mundo.deps();
    depsLentas.tetoGlobal = () => ({
      esgotado: async (a: number) => mundo.teto.esgotado(a),
      reservar: async (a: number) => {
        await portao;
        return mundo.teto.reservar(a);
      },
    });
    const r1 = await pedirDesafio(depsLentas, entrada({ finalidade: "recuperacao_senha" }));
    expect(r1.status).toBe(202);
    const pendente = mundo.segundoPlano.splice(0);
    mundo.relogio.avancar(INTERVALO_REENVIO_MS);
    const r2 = await pedirDesafio(mundo.deps(), entrada({ finalidade: "recuperacao_senha", chave: "pedido-0000000002" }));
    await mundo.concluirSegundoPlano();
    const codigoNovo = ultimoCodigo();
    liberar();
    await Promise.all(pendente); // o antigo tenta registrar a reserva: já foi substituído
    expect(mundo.enviador.enviadas).toHaveLength(1);
    // O antigo ficou parado além do prazo de reserva: foi encerrado como abandonado.
    expect(linhaDesafio(r1.corpo.desafio_id as string).motivo_invalidacao).toBe("reserva_abandonada");
    expect((await validar(r2.corpo.desafio_id as string, codigoNovo)).status).toBe(200);
  });

  it("executarEnvio nunca chama o enviador sem reserva registrada", async () => {
    const deps = mundo.deps();
    const destino = deps.destino("qualquer");
    expect(await executarEnvio(deps, destino, "inexistente", "cadastro", EMAIL, "123456")).toBe("nao_iniciado");
    expect(mundo.enviador.enviadas).toHaveLength(0);
  });
});

describe("recuperação neutra", () => {
  it("com e sem envio: mesma resposta, mesmos campos, mesmas tentativas", async () => {
    const real = await pedirDesafio(mundo.deps(), entrada({ finalidade: "recuperacao_senha" }));
    const outro = new Mundo();
    const semEnvio = await pedirDesafio(outro.deps(), entrada({ finalidade: "recuperacao_senha", semEnvio: true }));
    expect(semEnvio.status).toBe(real.status);
    expect(real.status).toBe(202);
    expect(Object.keys(semEnvio.corpo).sort()).toEqual(Object.keys(real.corpo).sort());
    await mundo.concluirSegundoPlano();
    await outro.concluirSegundoPlano();
    expect(mundo.enviador.enviadas).toHaveLength(1);
    expect(outro.enviador.enviadas).toHaveLength(0);

    const vReal = await validar(real.corpo.desafio_id as string, "999999");
    mundo = outro;
    const vSem = await validar(semEnvio.corpo.desafio_id as string, "999999");
    expect(vSem).toEqual(vReal);
    ultimoCodigo();
  });

  it("intervalo de reenvio igual com e sem envio", async () => {
    await pedirDesafio(mundo.deps(), entrada({ finalidade: "recuperacao_senha", semEnvio: true }));
    const r = await pedirDesafio(mundo.deps(), entrada({ finalidade: "recuperacao_senha", chave: "pedido-0000000002" }));
    expect(r.status).toBe(429);
    expect(r.corpo.erro).toBe("aguarde");
  });

  it("teto global esgotado: 503 igual para pedidos com e sem envio", async () => {
    for (let i = 0; i < TETO_GLOBAL_DIA; i++) mundo.teto.reservar(mundo.relogio.agora);
    const real = await pedirDesafio(mundo.deps(), entrada({ finalidade: "recuperacao_senha" }));
    const semEnvio = await pedirDesafio(
      mundo.deps(), entrada({ finalidade: "recuperacao_senha", semEnvio: true, email: "outra@exemplo.com" }),
    );
    expect(real).toEqual({ status: 503, corpo: { erro: "servico_indisponivel" } });
    expect(semEnvio).toEqual(real);
    expect((await pedirDesafio(mundo.deps(), entrada({ email: "x@exemplo.com" }))).status).toBe(503);
  });

  it("corrida no teto durante a recuperação: a resposta continua 202 e não há envio", async () => {
    for (let i = 0; i < TETO_GLOBAL_DIA; i++) mundo.teto.reservar(mundo.relogio.agora);
    const deps = mundo.deps();
    deps.tetoGlobal = () => ({ esgotado: async () => false, reservar: async (a: number) => mundo.teto.reservar(a) });
    const r = await pedirDesafio(deps, entrada({ finalidade: "recuperacao_senha" }));
    expect(r.status).toBe(202);
    await mundo.concluirSegundoPlano();
    expect(mundo.enviador.enviadas).toHaveLength(0);
    expect(linhaDesafio(r.corpo.desafio_id as string).estado_envio).toBe("sem_reserva");
  });
});

describe("limites e configuração", () => {
  it("limite por IP: 10 pedidos por hora", async () => {
    const status: number[] = [];
    for (let i = 0; i < 11; i++) {
      const r = await pedirDesafio(mundo.deps(), entrada({ email: `p${i}@exemplo.com`, chave: `pedido-${String(i).padStart(10, "0")}` }));
      status.push(r.status);
    }
    expect(status.slice(0, 10).every((s) => s === 201)).toBe(true);
    expect(status[10]).toBe(429);
  });

  it("IPv6 é agrupado por prefixo /64; IPv4 em IPv6 vira o próprio IPv4", () => {
    expect(prefixoIp("2001:db8:abcd:12:1::5")).toBe("2001:db8:abcd:12::/64");
    expect(prefixoIp("2001:0db8:abcd:0012:ffff:0:0:1")).toBe("2001:db8:abcd:12::/64");
    expect(prefixoIp("203.0.113.7")).toBe("203.0.113.7");
    expect(prefixoIp("::ffff:203.0.113.7")).toBe("203.0.113.7");
    expect(prefixoIp("::FFFF:203.0.113.7")).toBe("203.0.113.7");
    expect(prefixoIp("0:0:0:0:0:ffff:cb00:7107")).toBe("203.0.113.7");
    expect(prefixoIp("::ffff:cb00:7107")).toBe("203.0.113.7");
    expect(prefixoIp("::1")).toBe("0:0:0:0::/64");
    expect(prefixoIp("::ffff:999.0.0.1")).toBe("invalido:::ffff:999.0.0.1");
    expect(prefixoIp("1::2::3")).toBe("invalido:1::2::3");
  });

  it("IPv4 e o mesmo IPv4 em IPv6 dividem o mesmo limite", async () => {
    const status: number[] = [];
    for (let i = 0; i < 11; i++) {
      const ip = i % 2 ? "::ffff:203.0.113.9" : "203.0.113.9";
      const r = await pedirDesafio(mundo.deps(), entrada({ ip, email: `q${i}@exemplo.com`, chave: `pedido-q-${String(i).padStart(8, "0")}` }));
      status.push(r.status);
    }
    expect(status[10]).toBe(429);
  });

  it("sem segredos configurados: 503 sem tocar nos objetos", async () => {
    mundo.semSegredos = true;
    expect(await pedirDesafio(mundo.deps(), entrada())).toEqual({ status: 503, corpo: { erro: "servico_indisponivel" } });
    expect(mundo.destinos.size).toBe(0);
  });
});

/** Dependências cuja reserva global só termina quando o portão for liberado. */
function depsComPortao() {
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
  return { deps, liberar };
}

describe("repetição durante a reserva (M1)", () => {
  it("202 em_processamento com Retry-After; repetir a mesma requisição não duplica nada", async () => {
    const { deps, liberar } = depsComPortao();
    const primeira = pedirDesafio(deps, entrada());
    await new Promise((r) => setImmediate(r)); // deixa a primeira chegar à reserva
    const repeticao = await pedirDesafio(deps, entrada());
    expect(repeticao.status).toBe(202);
    expect(repeticao.corpo.estado).toBe("em_processamento");
    expect(repeticao.cabecalhos).toEqual({ "Retry-After": "2" });
    expect(Object.keys(repeticao.corpo).sort()).toEqual(
      ["agora", "desafio_id", "estado", "expira_em", "reenvio_permitido_em"],
    );
    liberar();
    const r1 = await primeira;
    expect(r1.status).toBe(201);
    expect(r1.corpo.desafio_id).toBe(repeticao.corpo.desafio_id);
    const depois = await pedirDesafio(deps, entrada());
    expect(depois.status).toBe(201);
    expect(depois.corpo.desafio_id).toBe(r1.corpo.desafio_id);
    expect(mundo.enviador.enviadas).toHaveLength(1);
    expect(mundo.destinos.size).toBe(1);
    ultimoCodigo();
  });

  it("reserva abandonada: repetição após 60 s responde 502 e a execução atrasada não envia", async () => {
    const { deps, liberar } = depsComPortao();
    const primeira = pedirDesafio(deps, entrada());
    await new Promise((r) => setImmediate(r));
    mundo.relogio.avancar(PRAZO_RESERVA_MS);
    const repeticao = await pedirDesafio(deps, entrada());
    expect(repeticao.status).toBe(502);
    expect(repeticao.corpo.erro).toBe("falha_envio");
    liberar(); // a execução original acorda atrasada
    const r1 = await primeira;
    expect(r1.status).toBe(502);
    expect(mundo.enviador.enviadas).toHaveLength(0);
  });
});

describe("repetição de desafio encerrado (M2)", () => {
  it("cadastro substituído ou expirado: 410", async () => {
    await pedirDesafio(mundo.deps(), entrada());
    mundo.relogio.avancar(INTERVALO_REENVIO_MS);
    await pedirDesafio(mundo.deps(), entrada({ chave: "pedido-0000000002" }));
    expect(await pedirDesafio(mundo.deps(), entrada())).toEqual({ status: 410, corpo: { erro: "desafio_encerrado" } });
    mundo.relogio.avancar(VALIDADE_CODIGO_MS);
    expect((await pedirDesafio(mundo.deps(), entrada({ chave: "pedido-0000000002" }))).status).toBe(410);
    ultimoCodigo();
  });

  it("cadastro com falha de envio: a repetição continua 502; sem reserva, 503", async () => {
    mundo.enviador.programar({ tipo: "falha" });
    await pedirDesafio(mundo.deps(), entrada());
    expect((await pedirDesafio(mundo.deps(), entrada())).status).toBe(502);

    mundo = new Mundo();
    for (let i = 0; i < TETO_GLOBAL_DIA; i++) mundo.teto.reservar(mundo.relogio.agora);
    const deps = mundo.deps();
    deps.tetoGlobal = () => ({ esgotado: async () => false, reservar: async (a: number) => mundo.teto.reservar(a) });
    expect((await pedirDesafio(deps, entrada())).status).toBe(503);
    expect((await pedirDesafio(deps, entrada())).status).toBe(503);
  });

  it("recuperação: repetição neutra (falha de envio não aparece; expiração igual para todos)", async () => {
    mundo.enviador.programar({ tipo: "falha" });
    const real = await pedirDesafio(mundo.deps(), entrada({ finalidade: "recuperacao_senha" }));
    await mundo.concluirSegundoPlano();
    const outro = new Mundo();
    const semEnvio = await pedirDesafio(outro.deps(), entrada({ finalidade: "recuperacao_senha", semEnvio: true }));

    const repReal = await pedirDesafio(mundo.deps(), entrada({ finalidade: "recuperacao_senha" }));
    const repSem = await pedirDesafio(outro.deps(), entrada({ finalidade: "recuperacao_senha", semEnvio: true }));
    const semId = (r: typeof repReal) => ({ ...r, corpo: { ...r.corpo, desafio_id: undefined } });
    expect(semId(repReal)).toEqual(semId(repSem));
    expect(repReal.status).toBe(202);
    expect(repReal.corpo.desafio_id).toBe(real.corpo.desafio_id);
    expect(repSem.corpo.desafio_id).toBe(semEnvio.corpo.desafio_id);

    const vReal = await validar(real.corpo.desafio_id as string, "000000");
    const atual = mundo;
    mundo = outro;
    const vSem = await validar(semEnvio.corpo.desafio_id as string, "000000");
    expect(vReal).toEqual(vSem);
    mundo = atual;

    for (const m of [mundo, outro]) m.relogio.avancar(VALIDADE_CODIGO_MS);
    const fimReal = await pedirDesafio(mundo.deps(), entrada({ finalidade: "recuperacao_senha" }));
    const fimSem = await pedirDesafio(outro.deps(), entrada({ finalidade: "recuperacao_senha", semEnvio: true }));
    expect(fimReal).toEqual({ status: 410, corpo: { erro: "desafio_encerrado" } });
    expect(fimSem).toEqual(fimReal);
    ultimoCodigo();
  });
});
