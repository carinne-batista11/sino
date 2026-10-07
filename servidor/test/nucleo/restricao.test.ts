// Restrição de destinatários (ERS v7.0, 5.49; contrato v1.1): configuração,
// pedido, validação (revogação), repetições com a lista alterada, as duas
// camadas antes do enviador, neutralidade da recuperação e registros sem
// dados sensíveis. Alterar mundo.destinatarios entre chamadas simula uma
// nova configuração publicada entre requisições.

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { INTERVALO_REENVIO_MS, LIMITE_DESTINATARIOS, MAX_TENTATIVAS, VALIDADE_CODIGO_MS } from "../../src/config";
import { EnviadorRestrito } from "../../src/envio/restrito";
import { EnviadorSimulado } from "../../src/envio/simulado";
import { executarEnvio, pedirDesafio, prefixoIp, validarDesafio, type EntradaPedido } from "../../src/fluxos";
import { criarApp } from "../../src/http";
import { hmacHex } from "../../src/nucleo/cripto";
import {
  ERRO_ESQUEMA_INCOMPATIVEL,
  EsquemaIncompativelError,
  RegrasDestino,
} from "../../src/nucleo/desafios";
import {
  lerDestinatarios,
  montarDestinatarios,
  resumoDoEmail,
  verificacaoDaLista,
} from "../../src/nucleo/destinatarios";
import { AleatorioDeTeste, BancoNode, CHAVE_HMAC, Mundo, capturarRegistros, resumoDe } from "./apoio";

const PERMITIDO = "pessoa@exemplo.com";
const FORA = "fora@exemplo.com";
const SEGREDO = "S".repeat(43);
const CONTEXTO = "e".repeat(64);
const IP = "203.0.113.20";
const NAO_PERMITIDO = { status: 403, corpo: { erro: "destinatario_nao_permitido" } };

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
  for (const proibido of [PERMITIDO, FORA, resumoDe(PERMITIDO), resumoDe(FORA), SEGREDO, ...codigosVistos]) {
    expect(juntos).not.toContain(proibido);
  }
  codigosVistos.length = 0;
});

function entrada(extra: Partial<EntradaPedido> = {}): EntradaPedido {
  return {
    finalidade: "cadastro", email: PERMITIDO, contexto: CONTEXTO, segredo: SEGREDO, chave: "pedido-0000000001",
    semEnvio: false, ip: IP, ...extra,
  };
}

const pedir = (extra: Partial<EntradaPedido> = {}) => pedirDesafio(mundo.deps(), entrada(extra));

function validar(desafioId: string, codigo: string, chave = "valida-000000001", email = PERMITIDO) {
  return validarDesafio(mundo.deps(), { desafioId, email, segredo: SEGREDO, chave, codigo, ip: IP });
}

function codigoEnviado(email = PERMITIDO): string {
  const c = mundo.enviador.ultimoCodigo(email)!;
  codigosVistos.push(c);
  return c;
}

function linhas(email: string) {
  const banco = mundo.bancosDestino.get(resumoDe(email));
  return banco ? banco.todos<Record<string, unknown>>("SELECT * FROM desafios ORDER BY criado_em") : [];
}

function pedidosDoIp(ip = IP): number {
  const banco = mundo.bancosIp.get(hmacHex(CHAVE_HMAC, "ip", prefixoIp(ip)));
  return banco?.um<{ contagem: number }>(
    "SELECT contagem FROM contadores WHERE nome = 'pedidos' AND duracao = 'hora'",
  )?.contagem ?? 0;
}

function validacoesDoIp(ip = IP): number {
  const banco = mundo.bancosIp.get(hmacHex(CHAVE_HMAC, "ip", prefixoIp(ip)));
  return banco?.um<{ contagem: number }>(
    "SELECT contagem FROM contadores WHERE nome = 'validacoes' AND duracao = 'hora'",
  )?.contagem ?? 0;
}

const enviosNoTeto = () =>
  mundo.bancoTeto.um<{ total: number }>("SELECT COALESCE(SUM(envios), 0) AS total FROM totais_diarios")!.total;

// ------------------------------------------------------------- configuração

describe("configuração DESTINATARIOS_PERMITIDOS", () => {
  const resumo = (n: number) => resumoDoEmail(CHAVE_HMAC, `d${n}@exemplo.com`);
  const verificacao = verificacaoDaLista(CHAVE_HMAC);
  const lista = (...resumos: string[]) => [verificacao, ...resumos].join(",");

  it("lista válida: os resumos, com ou sem uma quebra de linha no fim", () => {
    expect(lerDestinatarios(lista(resumo(1), resumo(2)), CHAVE_HMAC)).toEqual(new Set([resumo(1), resumo(2)]));
    expect(lerDestinatarios(`${lista(resumo(1))}\n`, CHAVE_HMAC)).toEqual(new Set([resumo(1)]));
  });

  it(`até ${LIMITE_DESTINATARIOS} resumos únicos`, () => {
    const cinquenta = Array.from({ length: LIMITE_DESTINATARIOS }, (_, i) => resumo(i));
    expect(lerDestinatarios(lista(...cinquenta), CHAVE_HMAC)?.size).toBe(LIMITE_DESTINATARIOS);
    expect(lerDestinatarios(lista(...cinquenta, resumo(99)), CHAVE_HMAC)).toBeNull();
  });

  it.each([
    ["ausente", undefined],
    ["vazia", ""],
    ["só a quebra de linha", "\n"],
    ["só a verificação", verificacao],
    ["verificação seguida de vírgula", `${verificacao},`],
    ["resumo duplicado", lista(resumo(1), resumo(1))],
    ["resumo em maiúsculas", lista(resumo(1).toUpperCase())],
    ["resumo curto", lista(resumo(1).slice(1))],
    ["espaço depois da vírgula", `${verificacao}, ${resumo(1)}`],
    ["item vazio no meio", lista(resumo(1), "", resumo(2))],
    ["duas quebras de linha", `${lista(resumo(1))}\n\n`],
    ["quebra de linha CRLF", `${lista(resumo(1))}\r\n`],
    ["várias linhas", `${verificacao}\n${resumo(1)}`],
    ["sem a verificação", resumo(1)],
    ["outra versão", lista(resumo(1)).replace(/^v1:/, "v2:")],
    ["gerada com outra CHAVE_HMAC", montarDestinatarios(new Uint8Array(32).fill(0x44), ["d1@exemplo.com"])],
    ["e-mail em texto", `${verificacao},d1@exemplo.com`],
  ])("inválida (%s): null", (_nome, texto) => {
    expect(lerDestinatarios(texto, CHAVE_HMAC)).toBeNull();
  });

  it("montarDestinatarios usa a normalização e o resumo do serviço e não repete endereços", () => {
    const texto = montarDestinatarios(CHAVE_HMAC, ["Pessoa@Exemplo.com", "  pessoa@exemplo.com ", "outra@exemplo.com"]);
    expect(lerDestinatarios(texto, CHAVE_HMAC)).toEqual(new Set([resumoDe(PERMITIDO), resumoDe("outra@exemplo.com")]));
    expect(resumoDe(PERMITIDO)).toBe(hmacHex(CHAVE_HMAC, "email", PERMITIDO));
  });

  it("serviço sem lista válida: 503 no pedido e na validação, sem tocar nos objetos", async () => {
    mundo.semSegredos = true;
    expect(await pedir()).toEqual({ status: 503, corpo: { erro: "servico_indisponivel" } });
    expect(await validar("A".repeat(22), "123456")).toEqual({ status: 503, corpo: { erro: "servico_indisponivel" } });
    expect(mundo.destinos.size).toBe(0);
    expect(mundo.ips.size).toBe(0);
  });
});

// -------------------------------------------------- cadastro e alteração

describe.each(["cadastro", "alteracao_email"] as const)("%s com a lista", (finalidade) => {
  it("fora da lista: 403 sem gravar nada; só o limite do IP é consumido", async () => {
    expect(await pedir({ finalidade, email: FORA })).toEqual(NAO_PERMITIDO);
    expect(mundo.destinos.has(resumoDe(FORA))).toBe(false);
    expect(mundo.enviador.enviadas).toHaveLength(0);
    expect(enviosNoTeto()).toBe(0);
    expect(pedidosDoIp()).toBe(1);
  });

  it("variações de maiúsculas e espaços comuns nas bordas do endereço permitido são aceitas", async () => {
    const r = await pedir({ finalidade, email: "  PESSOA@Exemplo.COM " });
    expect(r.status).toBe(201);
    expect(mundo.enviador.enviadas).toHaveLength(1);
    codigoEnviado("PESSOA@Exemplo.COM");
  });

  it("caso 1 — permitido no pedido e na repetição: o mesmo desafio, um único envio", async () => {
    const r1 = await pedir({ finalidade });
    const r2 = await pedir({ finalidade });
    expect(r1.status).toBe(201);
    expect(r2).toEqual(r1);
    expect(mundo.enviador.enviadas).toHaveLength(1);
    expect(pedidosDoIp()).toBe(2);
    expect(enviosNoTeto()).toBe(1);
    expect((await validar(r1.corpo.desafio_id as string, codigoEnviado())).status).toBe(200);
  });

  it("caso 2 — permitido no pedido, removido antes da repetição: 403, desafio inalterado, sem envio", async () => {
    const r1 = await pedir({ finalidade });
    const antes = linhas(PERMITIDO);
    mundo.remover(PERMITIDO);
    expect(await pedir({ finalidade })).toEqual(NAO_PERMITIDO);
    expect(linhas(PERMITIDO)).toEqual(antes);
    expect(mundo.enviador.enviadas).toHaveLength(1);
    expect(pedidosDoIp()).toBe(2);
    // A validação nova também é recusada (caso 5).
    expect(await validar(r1.corpo.desafio_id as string, codigoEnviado())).toEqual(NAO_PERMITIDO);
  });

  it("caso 3 — recusado no pedido, incluído antes da repetição: a mesma chave vira um pedido novo", async () => {
    expect(await pedir({ finalidade, email: FORA })).toEqual(NAO_PERMITIDO);
    mundo.permitir(FORA);
    const r = await pedir({ finalidade, email: FORA });
    expect(r.status).toBe(201);
    expect(mundo.enviador.enviadas).toHaveLength(1);
    expect(linhas(FORA)).toHaveLength(1);
    expect(pedidosDoIp()).toBe(2);
    expect(enviosNoTeto()).toBe(1);
    codigoEnviado(FORA);
  });

  it("caso 5 — código enviado antes da remoção: 403 na validação, sem contar tentativa; incluir de novo não reativa", async () => {
    const r = await pedir({ finalidade });
    const id = r.corpo.desafio_id as string;
    const codigo = codigoEnviado();
    mundo.remover(PERMITIDO);
    expect(await validar(id, codigo)).toEqual(NAO_PERMITIDO);
    expect(await validar(id, "000000", "valida-000000002")).toEqual(NAO_PERMITIDO);
    expect(validacoesDoIp()).toBe(2);
    const [linha] = linhas(PERMITIDO);
    expect(linha).toMatchObject({ tentativas: 0, motivo_invalidacao: "destinatario_nao_permitido", validado_em: null });
    mundo.permitir(PERMITIDO);
    expect((await validar(id, codigo, "valida-000000003")).status).toBe(410);
    // Repetir o pedido original agora encontra o desafio encerrado.
    expect((await pedir({ finalidade })).status).toBe(410);
    expect(mundo.enviador.enviadas).toHaveLength(1);
  });

  it("validação repetida (mesma chave) de uma autorização já emitida: 403 depois da remoção", async () => {
    const r = await pedir({ finalidade });
    const id = r.corpo.desafio_id as string;
    const codigo = codigoEnviado();
    expect((await validar(id, codigo)).status).toBe(200);
    mundo.remover(PERMITIDO);
    expect(await validar(id, codigo)).toEqual(NAO_PERMITIDO);
  });

  it("segredo que não confere: 404 mesmo fora da lista (nada é revelado sem o segredo)", async () => {
    const r = await pedir({ finalidade });
    mundo.remover(PERMITIDO);
    const v = await validarDesafio(mundo.deps(), {
      desafioId: r.corpo.desafio_id as string, email: PERMITIDO, segredo: "T".repeat(43), chave: "valida-000000001",
      codigo: "000000", ip: IP,
    });
    expect(v).toEqual({ status: 404, corpo: { erro: "desafio_nao_encontrado" } });
    expect(linhas(PERMITIDO)[0].invalidado_em).toBeNull();
  });

  it("limitação registrada: remover e incluir de novo sem validação no meio não invalida o desafio", async () => {
    const r = await pedir({ finalidade });
    mundo.remover(PERMITIDO);
    mundo.permitir(PERMITIDO);
    expect((await validar(r.corpo.desafio_id as string, codigoEnviado())).status).toBe(200);
  });
});

// ------------------------------------------------------------- recuperação

/** O que um cliente observa numa resposta neutra (sem valores sorteados). */
function forma(r: { status: number; corpo: Record<string, unknown>; cabecalhos?: Record<string, string> }) {
  const c = r.corpo;
  const instante = (v: unknown) => Date.parse(v as string);
  return {
    status: r.status,
    chaves: Object.keys(c).sort(),
    cabecalhos: r.cabecalhos ?? null,
    erro: c.erro ?? null,
    idValido: c.desafio_id === undefined ? null : /^[A-Za-z0-9_-]{22}$/.test(c.desafio_id as string),
    validadeMs: c.expira_em === undefined ? null : instante(c.expira_em) - instante(c.agora),
    reenvioMs: c.reenvio_permitido_em === undefined ? null : instante(c.reenvio_permitido_em) - instante(c.agora),
    tentativas: c.tentativas_restantes ?? null,
  };
}

describe("recuperação com a lista (neutralidade)", () => {
  const rec = (email: string, extra: Partial<EntradaPedido> = {}) =>
    pedir({ finalidade: "recuperacao_senha", email, ip: email === FORA ? "198.51.100.2" : "198.51.100.1", ...extra });

  it("dentro e fora da lista: mesma resposta, mesmos limites; fora, nada é enviado nem reservado", async () => {
    const dentro = await rec(PERMITIDO);
    const fora = await rec(FORA);
    expect(forma(fora)).toEqual(forma(dentro));
    expect(dentro.status).toBe(202);
    await mundo.concluirSegundoPlano();
    expect(mundo.enviador.enviadas.map((e) => e.mensagem.para)).toEqual([PERMITIDO]);
    codigoEnviado();
    expect(linhas(FORA)).toMatchObject([{ estado_envio: "sem_envio", reserva_global: null }]);
    expect(enviosNoTeto()).toBe(1);
    // Repetição com a mesma chave e novo pedido antes de 60 s: iguais nos dois.
    expect(forma(await rec(FORA))).toEqual(forma(await rec(PERMITIDO)));
    const novoFora = await rec(FORA, { chave: "pedido-0000000002" });
    const novoDentro = await rec(PERMITIDO, { chave: "pedido-0000000002" });
    expect(novoFora.corpo.erro).toBe("aguarde");
    expect(forma(novoFora)).toEqual(forma(novoDentro));
    expect(pedidosDoIp("198.51.100.2")).toBe(pedidosDoIp("198.51.100.1"));
    expect(linhas(FORA)).toHaveLength(linhas(PERMITIDO).length);
  });

  it("fora da lista: validações com qualquer código iguais às de um desafio sem envio, nunca autoriza", async () => {
    mundo.relogio.avancar(1);
    const codigoFora = mundo.aleatorio.proximoCodigo();
    const fora = await rec(FORA);
    const semEnvio = await rec("outra@exemplo.com", { semEnvio: true, ip: "198.51.100.3" });
    const respostas = async (id: string, email: string, codigo: string) => {
      const lista = [];
      for (let i = 1; i <= MAX_TENTATIVAS + 1; i++) {
        lista.push(forma(await validar(id, codigo, `valida-${String(i).padStart(10, "0")}`, email)));
      }
      return lista;
    };
    const rf = await respostas(fora.corpo.desafio_id as string, FORA, codigoFora);
    const rs = await respostas(semEnvio.corpo.desafio_id as string, "outra@exemplo.com", "000000");
    expect(rf).toEqual(rs);
    expect(rf.map((r) => r.status)).toEqual([422, 422, 422, 422, 422, 410]);
    expect(mundo.enviador.enviadas).toHaveLength(0);
  });

  it("caso 4 — sem envio, depois incluído: a repetição não reativa; um novo pedido depois de 60 s envia", async () => {
    const codigoAntigo = mundo.aleatorio.proximoCodigo();
    const r1 = await rec(FORA);
    mundo.permitir(FORA);
    const repeticao = await rec(FORA);
    expect(repeticao).toEqual(r1);
    await mundo.concluirSegundoPlano();
    expect(mundo.enviador.enviadas).toHaveLength(0);
    expect(linhas(FORA)).toMatchObject([{ estado_envio: "sem_envio" }]);
    expect((await validar(r1.corpo.desafio_id as string, codigoAntigo, "valida-000000001", FORA)).status).toBe(422);

    mundo.relogio.avancar(INTERVALO_REENVIO_MS);
    const novo = await rec(FORA, { chave: "pedido-0000000002" });
    expect(novo.status).toBe(202);
    await mundo.concluirSegundoPlano();
    expect(mundo.enviador.enviadas).toHaveLength(1);
    const codigo = codigoEnviado(FORA);
    expect(linhas(FORA).map((l) => l.motivo_invalidacao)).toEqual(["substituido", null]);
    expect((await validar(novo.corpo.desafio_id as string, codigo, "valida-000000002", FORA)).status).toBe(200);
  });

  it("caso 4 — sem envio pedido pelo cliente continua sem envio mesmo dentro da lista", async () => {
    const r1 = await rec(PERMITIDO, { semEnvio: true });
    expect(await rec(PERMITIDO, { semEnvio: true })).toEqual(r1);
    await mundo.concluirSegundoPlano();
    expect(mundo.enviador.enviadas).toHaveLength(0);
  });

  it("caso 2 — enviado, removido antes da repetição: 202 sem novo envio", async () => {
    const r1 = await rec(PERMITIDO);
    await mundo.concluirSegundoPlano();
    codigoEnviado();
    mundo.remover(PERMITIDO);
    expect(await rec(PERMITIDO)).toEqual(r1);
    await mundo.concluirSegundoPlano();
    expect(mundo.enviador.enviadas).toHaveLength(1);
  });

  it("caso 5 — código enviado antes da remoção: 422 com o código certo, tentativa contada, nunca autoriza", async () => {
    const r = await rec(PERMITIDO);
    await mundo.concluirSegundoPlano();
    const id = r.corpo.desafio_id as string;
    const codigo = codigoEnviado();
    mundo.remover(PERMITIDO);
    expect(await validar(id, codigo)).toEqual({ status: 422, corpo: { erro: "codigo_invalido", tentativas_restantes: 4 } });
    expect(linhas(PERMITIDO)[0]).toMatchObject({ tentativas: 1, motivo_invalidacao: "destinatario_nao_permitido" });
    // Mesma validação repetida: o mesmo resultado; incluir de novo não reativa.
    expect(await validar(id, codigo)).toEqual({ status: 422, corpo: { erro: "codigo_invalido", tentativas_restantes: 4 } });
    mundo.permitir(PERMITIDO);
    expect((await validar(id, codigo, "valida-000000002")).status).toBe(422);
    // O pedido original continua "ativo" para quem pediu (neutralidade).
    expect((await rec(PERMITIDO)).status).toBe(202);
  });

  it("marca invisível: fora da lista desde o pedido, a validação não altera o desafio sem envio", async () => {
    const r = await rec(FORA);
    await validar(r.corpo.desafio_id as string, "000000", "valida-000000001", FORA);
    expect(linhas(FORA)[0]).toMatchObject({ estado_envio: "sem_envio", invalidado_em: null, tentativas: 1 });
  });

  it("removido depois do envio: retenção e substituição iguais às de um desafio dentro da lista", async () => {
    // A: removido depois do envio. B: continua na lista. Mesmas operações nos dois.
    const B = "outra@exemplo.com";
    const recB = (extra: Partial<EntradaPedido> = {}) => rec(B, { ip: "198.51.100.9", ...extra });
    const a1 = await rec(PERMITIDO);
    const b1 = await recB();
    await mundo.concluirSegundoPlano();
    codigoEnviado();
    codigoEnviado(B);
    mundo.remover(PERMITIDO);
    expect(forma(await validar(a1.corpo.desafio_id as string, "000000", "valida-000000001")))
      .toEqual(forma(await validar(b1.corpo.desafio_id as string, "000000", "valida-000000001", B)));
    const [linhaA] = linhas(PERMITIDO);
    expect(linhaA.motivo_invalidacao).toBe("destinatario_nao_permitido");
    expect(linhaA.invalidado_em).toBe(linhaA.expira_em); // retenção igual à de um desafio não invalidado
    expect(linhas(B)[0].invalidado_em).toBeNull();

    // Novo pedido depois de 60 s: o antigo vira "substituido" nos dois e responde 410 igual.
    mundo.relogio.avancar(INTERVALO_REENVIO_MS);
    expect(forma(await rec(PERMITIDO, { chave: "pedido-0000000002" })))
      .toEqual(forma(await recB({ chave: "pedido-0000000002" })));
    await mundo.concluirSegundoPlano();
    expect(linhas(PERMITIDO)[0]).toMatchObject({ motivo_invalidacao: "substituido" });
    expect(linhas(PERMITIDO)[0].invalidado_em).toBe(linhas(B)[0].invalidado_em);
    expect(forma(await validar(a1.corpo.desafio_id as string, "000000", "valida-000000002")))
      .toEqual(forma(await validar(b1.corpo.desafio_id as string, "000000", "valida-000000002", B)));
    expect((await validar(a1.corpo.desafio_id as string, "000000", "valida-000000003")).status).toBe(410);
  });

  it("autorização já emitida: a repetição da mesma validação depois da remoção recebe 410, não a autorização", async () => {
    const r = await rec(PERMITIDO);
    await mundo.concluirSegundoPlano();
    const id = r.corpo.desafio_id as string;
    const codigo = codigoEnviado();
    expect((await validar(id, codigo)).status).toBe(200);
    mundo.remover(PERMITIDO);
    expect(await validar(id, codigo)).toEqual({ status: 410, corpo: { erro: "desafio_encerrado" } });
  });

  it("depois de expirar: 410 igual dentro e fora da lista", async () => {
    const dentro = await rec(PERMITIDO);
    const fora = await rec(FORA);
    await mundo.concluirSegundoPlano();
    codigoEnviado();
    mundo.relogio.avancar(VALIDADE_CODIGO_MS);
    expect(forma(await rec(FORA))).toEqual(forma(await rec(PERMITIDO)));
    expect(forma(await validar(fora.corpo.desafio_id as string, "000000", "valida-1111111111", FORA)))
      .toEqual(forma(await validar(dentro.corpo.desafio_id as string, "000000", "valida-1111111111")));
  });
});

// ------------------------------------------------ camadas antes do enviador

describe("proteção imediatamente antes do envio", () => {
  it("camada A: executarEnvio para destinatário fora da lista bloqueia sem reservar o teto", async () => {
    mundo.permitir(FORA);
    const deps = mundo.deps();
    const destino = deps.destino(resumoDe(FORA));
    const criado = await destino.solicitar({
      finalidade: "recuperacao_senha", contexto: CONTEXTO, segredoHash: "s", chaveHash: "k", semEnvio: false,
      permitido: true, agora: mundo.relogio.agora,
    });
    expect(criado.tipo).toBe("criado");
    mundo.remover(FORA);
    const estado = await executarEnvio(
      deps, destino, (criado as { desafioId: string }).desafioId, "recuperacao_senha", FORA, "123456",
    );
    expect(estado).toBe("bloqueado");
    expect(linhas(FORA)).toMatchObject([
      { estado_envio: "bloqueado", reserva_global: null, motivo_invalidacao: "destinatario_nao_permitido" },
    ]);
    expect(enviosNoTeto()).toBe(0);
    expect(mundo.enviador.enviadas).toHaveLength(0);
  });

  /** Dependências cuja camada B usa uma lista vazia (inconsistência proposital). */
  function depsComCamadaBVazia() {
    const deps = mundo.deps();
    deps.enviador = new EnviadorRestrito(mundo.enviador, { chaveHmac: CHAVE_HMAC, destinatarios: new Set() });
    return deps;
  }

  it("camada B no cadastro: 403, estado 'bloqueado' (não 'falhou'), sem rede e sem repetição", async () => {
    const r = await pedirDesafio(depsComCamadaBVazia(), entrada());
    expect(r).toEqual(NAO_PERMITIDO);
    expect(mundo.enviador.enviadas).toHaveLength(0);
    expect(linhas(PERMITIDO)).toMatchObject([
      { estado_envio: "bloqueado", motivo_invalidacao: "destinatario_nao_permitido" },
    ]);
    // A vaga do teto já tinha sido reservada e não é devolvida.
    expect(enviosNoTeto()).toBe(1);
    // Repetição com a lista coerente: o desafio está encerrado.
    expect((await pedir()).status).toBe(410);
    expect(mundo.enviador.enviadas).toHaveLength(0);
  });

  it("camada B na recuperação em segundo plano: 202 neutro, bloqueado, nunca autoriza", async () => {
    const codigo = mundo.aleatorio.proximoCodigo();
    const r = await pedirDesafio(depsComCamadaBVazia(), entrada({ finalidade: "recuperacao_senha" }));
    expect(r.status).toBe(202);
    await mundo.concluirSegundoPlano();
    expect(mundo.enviador.enviadas).toHaveLength(0);
    expect(linhas(PERMITIDO)).toMatchObject([{ estado_envio: "bloqueado" }]);
    expect((await validar(r.corpo.desafio_id as string, codigo)).status).toBe(422);
  });

  it("EnviadorRestrito: sem configuração não envia; dentro da lista repassa o resultado tal como veio", async () => {
    const real = new EnviadorSimulado();
    const mensagem = { para: "Pessoa@Exemplo.com", assunto: "a", texto: "b" };
    expect(await new EnviadorRestrito(real, null).enviar(mensagem, "k")).toEqual({ tipo: "bloqueado" });
    const restrito = new EnviadorRestrito(real, { chaveHmac: CHAVE_HMAC, destinatarios: new Set([resumoDe(PERMITIDO)]) });
    real.programar({ tipo: "incerto" });
    expect(await restrito.enviar(mensagem, "k")).toEqual({ tipo: "incerto" });
    expect(await restrito.enviar({ ...mensagem, para: FORA }, "k2")).toEqual({ tipo: "bloqueado" });
    expect(real.enviadas.map((e) => e.chave)).toEqual(["k"]);
  });
});

// ------------------------------------------------------ esquema dos objetos

describe("versão do esquema do destino", () => {
  it("objeto novo recebe a marca; garantirEsquema é idempotente", () => {
    const banco = new BancoNode();
    const regras = new RegrasDestino(banco, CHAVE_HMAC, new AleatorioDeTeste());
    regras.garantirEsquema();
    regras.garantirEsquema();
    expect(banco.todos("SELECT * FROM esquema_destino")).toEqual([{ id: 1, versao: 2 }]);
  });

  it("tabela da versão anterior (sem marca) ou marca de outra versão: recusa sem alterar", () => {
    const antigo = new BancoNode();
    antigo.executar("CREATE TABLE desafios (id TEXT PRIMARY KEY)");
    expect(() => new RegrasDestino(antigo, CHAVE_HMAC, new AleatorioDeTeste()).garantirEsquema())
      .toThrow(EsquemaIncompativelError);
    expect(antigo.todos("SELECT * FROM esquema_destino")).toEqual([]);

    const outra = new BancoNode();
    outra.executar("CREATE TABLE esquema_destino (id INTEGER PRIMARY KEY, versao INTEGER NOT NULL)");
    outra.executar("INSERT INTO esquema_destino VALUES (1, 1)");
    expect(() => new RegrasDestino(outra, CHAVE_HMAC, new AleatorioDeTeste()).garantirEsquema())
      .toThrow(ERRO_ESQUEMA_INCOMPATIVEL);
  });

  it("erro de esquema incompatível vindo de um objeto: 503 servico_indisponivel", async () => {
    const deps = mundo.deps();
    deps.destino = () => ({
      solicitar: async () => {
        throw new Error(ERRO_ESQUEMA_INCOMPATIVEL);
      },
    }) as never;
    const resposta = await criarApp(deps).fetch(
      new Request("https://servico.teste/v1/desafios", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": "pedido-0000000001" },
        body: JSON.stringify({ finalidade: "cadastro", email: PERMITIDO, contexto: CONTEXTO, segredo: SEGREDO }),
      }),
    );
    expect(resposta.status).toBe(503);
    expect(await resposta.json()).toEqual({ erro: "servico_indisponivel" });
  });
});
