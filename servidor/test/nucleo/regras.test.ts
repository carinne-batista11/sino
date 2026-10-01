// Regras de um destino: ERS 5.32, repetição, reserva global obrigatória,
// envio incerto, resultados tardios e retenção (SQLite do Node, mesmos
// comandos do Durable Object).

import { describe, expect, it } from "vitest";
import {
  HORA_MS,
  INTERVALO_REENVIO_MS,
  PRAZO_ENVIANDO_MS,
  PRAZO_RESERVA_MS,
  RETENCAO_DESAFIO_MS,
  VALIDADE_CODIGO_MS,
  type Finalidade,
} from "../../src/config";
import { gerarCodigo } from "../../src/nucleo/cripto";
import type { RegrasDestino, ResultadoSolicitar } from "../../src/nucleo/desafios";
import { AleatorioDeTeste, CONTEXTO, INICIO, chaveHashDe, novoDestino, segredoHashDe } from "./apoio";

type Criado = Extract<ResultadoSolicitar, { tipo: "criado" }>;

function pedir(regras: RegrasDestino, agora: number, n = 1, finalidade: Finalidade = "cadastro", semEnvio = false) {
  return regras.solicitar({
    finalidade, contexto: CONTEXTO, segredoHash: segredoHashDe(n), chaveHash: chaveHashDe(n), semEnvio, agora,
  });
}

function pedirCriado(regras: RegrasDestino, agora: number, n = 1, finalidade: Finalidade = "cadastro"): Criado {
  const r = pedir(regras, agora, n, finalidade);
  expect(r.tipo).toBe("criado");
  return r as Criado;
}

/** Pedido com reserva registrada e envio iniciado (validável). */
function pronto(regras: RegrasDestino, agora: number, n = 1, finalidade: Finalidade = "cadastro"): Criado {
  const r = pedirCriado(regras, agora, n, finalidade);
  expect(regras.registrarReserva(r.desafioId, `reserva-${n}`, agora)).toBe(true);
  expect(regras.iniciarEnvio(r.desafioId, agora)).toBe(true);
  return r;
}

function validar(regras: RegrasDestino, r: { desafioId: string }, codigo: string, agora: number, k = "v1", s = 1) {
  return regras.validar({ desafioId: r.desafioId, segredoHash: segredoHashDe(s), chaveHash: k, codigo, agora });
}

const errado = (codigo: string) => (codigo === "000000" ? "000001" : "000000");

function linha(banco: { um: <T>(sql: string, ...p: (string | number)[]) => T | null }, id: string) {
  return banco.um<Record<string, unknown>>("SELECT * FROM desafios WHERE id = ?", id)!;
}

describe("código (5.32)", () => {
  it("tem 6 dígitos com zeros à esquerda e distribuição por rejeição", () => {
    const zeros = { bytes: (n: number) => new Uint8Array(n) };
    expect(gerarCodigo(zeros)).toBe("000000");
    const a = new AleatorioDeTeste("x");
    for (let i = 0; i < 200; i++) expect(gerarCodigo(a)).toMatch(/^\d{6}$/);
  });

  it("não fica guardado em texto no banco", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    const texto = JSON.stringify(banco.todos("SELECT * FROM desafios"));
    expect(texto).not.toContain(r.codigo!);
  });

  it("vale até 10 minutos após a geração, sem extensão", () => {
    const { regras } = novoDestino();
    const r = pronto(regras, INICIO);
    expect(validar(regras, r, r.codigo!, INICIO + VALIDADE_CODIGO_MS - 1).tipo).toBe("autorizado");

    const { regras: outras } = novoDestino(new AleatorioDeTeste("b"));
    const r2 = pronto(outras, INICIO);
    expect(validar(outras, r2, r2.codigo!, INICIO + VALIDADE_CODIGO_MS).tipo).toBe("encerrado");
  });

  it("aceita no máximo 5 tentativas e depois deixa de valer", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    for (let i = 1; i <= 5; i++) {
      const v = validar(regras, r, errado(r.codigo!), INICIO + i, `k${i}`);
      expect(v).toEqual({ tipo: "codigo_invalido", tentativasRestantes: 5 - i });
    }
    expect(linha(banco, r.desafioId)).toMatchObject({ tentativas: 5, motivo_invalidacao: "tentativas" });
    expect(validar(regras, r, r.codigo!, INICIO + 10, "k6").tipo).toBe("encerrado");
  });

  it("libera reenvio só após 60 s; o novo código invalida o anterior", () => {
    const { regras, banco } = novoDestino();
    const r1 = pronto(regras, INICIO);
    expect(pedir(regras, INICIO + INTERVALO_REENVIO_MS - 1, 2)).toEqual({
      tipo: "aguarde", reenvioEm: INICIO + INTERVALO_REENVIO_MS,
    });
    const r2 = pronto(regras, INICIO + INTERVALO_REENVIO_MS, 2);
    expect(linha(banco, r1.desafioId)).toMatchObject({ motivo_invalidacao: "substituido" });
    expect(validar(regras, r1, r1.codigo!, INICIO + 61_000).tipo).toBe("encerrado");
    expect(validar(regras, r2, r2.codigo!, INICIO + 61_000, "v2", 2).tipo).toBe("autorizado");
  });

  it("intervalo de 60 s vale entre finalidades do mesmo destino", () => {
    const { regras } = novoDestino();
    pronto(regras, INICIO, 1, "cadastro");
    expect(pedir(regras, INICIO + 1000, 2, "recuperacao_senha").tipo).toBe("aguarde");
  });
});

describe("validação única e repetição (ajustes 1 e da rodada de revisão)", () => {
  it("a primeira validação correta encerra o código: nova chave não gera outra autorização", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    const v1 = validar(regras, r, r.codigo!, INICIO + 1000, "k1");
    expect(v1.tipo).toBe("autorizado");
    const antes = linha(banco, r.desafioId);
    expect(validar(regras, r, r.codigo!, INICIO + 2000, "k2").tipo).toBe("encerrado");
    const depois = linha(banco, r.desafioId);
    expect(depois.autorizacao_jti).toBe(antes.autorizacao_jti);
    expect(depois.tentativas).toBe(antes.tentativas);
  });

  it("repetir a mesma operação devolve a mesma autorização até o expira_em original", () => {
    const { regras } = novoDestino();
    const r = pronto(regras, INICIO);
    const v1 = validar(regras, r, r.codigo!, INICIO + 1000, "k1");
    const v2 = validar(regras, r, r.codigo!, INICIO + 5000, "k1");
    expect(v2).toEqual(v1);
    expect(validar(regras, r, r.codigo!, INICIO + VALIDADE_CODIGO_MS, "k1").tipo).toBe("encerrado");
  });

  it("mesma chave com outro código é conflito e não conta tentativa", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    validar(regras, r, errado(r.codigo!), INICIO + 1, "k1");
    expect(validar(regras, r, r.codigo!, INICIO + 2, "k1").tipo).toBe("conflito");
    expect(linha(banco, r.desafioId).tentativas).toBe(1);
  });

  it("repetir uma tentativa errada devolve o mesmo resultado sem contar de novo", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    const a = validar(regras, r, errado(r.codigo!), INICIO + 1, "k1");
    const b = validar(regras, r, errado(r.codigo!), INICIO + 2, "k1");
    expect(b).toEqual(a);
    expect(linha(banco, r.desafioId).tentativas).toBe(1);
  });

  it("conhecer só o id não basta: segredo errado não encontra nem conta tentativa", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    expect(validar(regras, r, r.codigo!, INICIO + 1, "k1", 99).tipo).toBe("nao_encontrado");
    expect(linha(banco, r.desafioId).tentativas).toBe(0);
  });

  it("duas validações corretas com chaves diferentes: só a primeira autoriza", () => {
    const { regras } = novoDestino();
    const r = pronto(regras, INICIO);
    const resultados = ["a", "b", "c"].map((k, i) => validar(regras, r, r.codigo!, INICIO + i, `k-${k}`).tipo);
    expect(resultados).toEqual(["autorizado", "encerrado", "encerrado"]);
  });
});

describe("linhas sem usuário / sem reserva nunca autorizam (ajuste 2)", () => {
  it("pedido sem envio não autoriza mesmo com o código coincidente, e conta tentativas", () => {
    const aleatorio = new AleatorioDeTeste("fantasma");
    const { regras, banco } = novoDestino(aleatorio);
    const codigo = aleatorio.proximoCodigo();
    const r = pedir(regras, INICIO, 1, "recuperacao_senha", true) as Criado;
    expect(r.tipo).toBe("criado");
    expect(r.codigo).toBeNull();
    expect(validar(regras, r, codigo, INICIO + 1, "k1")).toEqual({ tipo: "codigo_invalido", tentativasRestantes: 4 });
    expect(linha(banco, r.desafioId)).toMatchObject({ autorizacao_jti: null, estado_envio: "sem_envio" });
    for (let i = 2; i <= 5; i++) validar(regras, r, codigo, INICIO + i, `k${i}`);
    expect(validar(regras, r, codigo, INICIO + 9, "k9").tipo).toBe("encerrado");
  });

  it("desafio sem reserva global registrada trata o código certo como errado", () => {
    const { regras, banco } = novoDestino();
    const r = pedirCriado(regras, INICIO);
    expect(validar(regras, r, r.codigo!, INICIO + 1)).toEqual({ tipo: "codigo_invalido", tentativasRestantes: 4 });
    expect(linha(banco, r.desafioId).autorizacao_jti).toBeNull();
  });

  it("reserva registrada sem envio iniciado também não autoriza", () => {
    const { regras } = novoDestino();
    const r = pedirCriado(regras, INICIO);
    regras.registrarReserva(r.desafioId, "reserva", INICIO);
    expect(validar(regras, r, r.codigo!, INICIO + 1).tipo).toBe("codigo_invalido");
  });

  it("teto atingido: sem_reserva invalida o desafio", () => {
    const { regras, banco } = novoDestino();
    const r = pedirCriado(regras, INICIO);
    expect(regras.marcarSemReserva(r.desafioId, INICIO)).toBe(true);
    expect(linha(banco, r.desafioId)).toMatchObject({ estado_envio: "sem_reserva", motivo_invalidacao: "sem_reserva" });
    expect(validar(regras, r, r.codigo!, INICIO + 1).tipo).toBe("encerrado");
  });

  it("o banco recusa autorização em linha sem reserva ou sem envio", () => {
    const { regras, banco } = novoDestino();
    const semEnvio = pedir(regras, INICIO, 1, "recuperacao_senha", true) as Criado;
    expect(() =>
      banco.executar("UPDATE desafios SET autorizacao_jti = 'x' WHERE id = ?", semEnvio.desafioId),
    ).toThrow(/CHECK/);
    expect(() =>
      banco.executar("UPDATE desafios SET estado_envio = 'enviando' WHERE id = ?", semEnvio.desafioId),
    ).toThrow(/CHECK/);
  });
});

describe("linhas expiradas e índice de um ativo por finalidade (ajuste 3)", () => {
  it("novo pedido encerra a linha expirada como 'expirado'", () => {
    const { regras, banco } = novoDestino();
    const r1 = pronto(regras, INICIO);
    pronto(regras, INICIO + VALIDADE_CODIGO_MS + 1, 2);
    expect(linha(banco, r1.desafioId)).toMatchObject({ motivo_invalidacao: "expirado" });
  });

  it("novo pedido encerra também um desafio já validado; a repetição dele passa a ser recusada", () => {
    const { regras, banco } = novoDestino();
    const r1 = pronto(regras, INICIO);
    validar(regras, r1, r1.codigo!, INICIO + 1000, "k1");
    pronto(regras, INICIO + INTERVALO_REENVIO_MS, 2);
    expect(linha(banco, r1.desafioId)).toMatchObject({ motivo_invalidacao: "substituido" });
    expect(validar(regras, r1, r1.codigo!, INICIO + 61_000, "k1").tipo).toBe("encerrado");
  });

  it("o índice impede duas linhas ativas na mesma finalidade", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    expect(() =>
      banco.executar(
        `INSERT INTO desafios (id, finalidade, contexto, segredo_hash, pedido_chave_hash, pedido_impressao,
           codigo_hash, codigo_salt, criado_em, expira_em, estado_envio)
         SELECT 'outro', finalidade, contexto, segredo_hash, 'outra-chave', pedido_impressao,
           codigo_hash, codigo_salt, criado_em, expira_em, 'pendente_reserva' FROM desafios WHERE id = ?`,
        r.desafioId,
      ),
    ).toThrow(/UNIQUE/);
  });

  it("finalidades diferentes convivem ativas", () => {
    const { regras } = novoDestino();
    const c = pronto(regras, INICIO, 1, "cadastro");
    const rec = pronto(regras, INICIO + INTERVALO_REENVIO_MS, 2, "recuperacao_senha");
    expect(validar(regras, c, c.codigo!, INICIO + 61_000, "a").tipo).toBe("autorizado");
    expect(validar(regras, rec, rec.codigo!, INICIO + 61_000, "b", 2).tipo).toBe("autorizado");
  });
});

describe("repetição do pedido", () => {
  it("mesma chave e mesmo conteúdo devolve o mesmo desafio, sem novo código", () => {
    const { regras } = novoDestino();
    const r = pronto(regras, INICIO);
    expect(pedir(regras, INICIO + 5000)).toEqual({
      tipo: "repeticao", desafioId: r.desafioId, expiraEm: r.expiraEm, reenvioEm: r.reenvioEm, estadoEnvio: "enviando",
      encerrado: false, motivoInvalidacao: null,
    });
  });

  it("repetição de desafio substituído ou expirado indica encerrado", () => {
    const { regras } = novoDestino();
    pronto(regras, INICIO);
    pronto(regras, INICIO + INTERVALO_REENVIO_MS, 2);
    expect(pedir(regras, INICIO + 61_000)).toMatchObject({ tipo: "repeticao", encerrado: true, motivoInvalidacao: "substituido" });
    expect(pedir(regras, INICIO + VALIDADE_CODIGO_MS + INTERVALO_REENVIO_MS, 2)).toMatchObject({
      tipo: "repeticao", encerrado: true,
    });
  });

  it("repetição de desafio validado segue ativa até o expira_em", () => {
    const { regras } = novoDestino();
    const r = pronto(regras, INICIO);
    validar(regras, r, r.codigo!, INICIO + 1000, "k1");
    expect(pedir(regras, INICIO + 2000)).toMatchObject({ tipo: "repeticao", encerrado: false });
  });

  it("mesma chave com outro conteúdo é conflito", () => {
    const { regras } = novoDestino();
    pronto(regras, INICIO);
    const r = regras.solicitar({
      finalidade: "cadastro", contexto: "d".repeat(64), segredoHash: segredoHashDe(1), chaveHash: chaveHashDe(1),
      semEnvio: false, agora: INICIO + 1,
    });
    expect(r.tipo).toBe("conflito");
  });
});

describe("envio em andamento, incerto e resultados tardios (ajuste 2 da reserva)", () => {
  it("'enviando' vira 'incerto' após 60 s, inclusive por conversão na leitura, e continua validável", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    expect(validar(regras, r, errado(r.codigo!), INICIO + PRAZO_ENVIANDO_MS - 1, "k0").tipo).toBe("codigo_invalido");
    expect(linha(banco, r.desafioId).estado_envio).toBe("enviando");
    expect(validar(regras, r, r.codigo!, INICIO + PRAZO_ENVIANDO_MS, "k1").tipo).toBe("autorizado");
    expect(linha(banco, r.desafioId).estado_envio).toBe("incerto");
  });

  it("processarPrazos converte o envio abandonado e indica o próximo prazo", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    expect(regras.proximoPrazo()).toBe(INICIO + PRAZO_ENVIANDO_MS);
    regras.processarPrazos(INICIO + PRAZO_ENVIANDO_MS);
    expect(linha(banco, r.desafioId).estado_envio).toBe("incerto");
  });

  it("sucesso tardio depois de 'incerto' vira 'enviado'", () => {
    const { regras } = novoDestino();
    const r = pronto(regras, INICIO);
    regras.processarPrazos(INICIO + PRAZO_ENVIANDO_MS);
    expect(regras.registrarResultado(r.desafioId, "enviado", INICIO + 70_000)).toBe("enviado");
  });

  it("falha tardia depois de 'incerto' invalida o desafio", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    regras.processarPrazos(INICIO + PRAZO_ENVIANDO_MS);
    expect(regras.registrarResultado(r.desafioId, "falhou", INICIO + 70_000)).toBe("falhou");
    expect(linha(banco, r.desafioId).motivo_invalidacao).toBe("falha_envio");
    expect(validar(regras, r, r.codigo!, INICIO + 71_000).tipo).toBe("encerrado");
  });

  it("resultado tardio não altera desafio já validado", () => {
    const { regras } = novoDestino();
    const r = pronto(regras, INICIO);
    const v = validar(regras, r, r.codigo!, INICIO + 1000, "k1");
    expect(regras.registrarResultado(r.desafioId, "falhou", INICIO + 2000)).toBe("enviando");
    expect(validar(regras, r, r.codigo!, INICIO + 3000, "k1")).toEqual(v);
  });

  it("falha antiga não invalida o desafio mais novo", () => {
    const { regras, banco } = novoDestino();
    const antigo = pronto(regras, INICIO);
    const novo = pronto(regras, INICIO + INTERVALO_REENVIO_MS, 2);
    // O antigo já foi substituído (e convertido em incerto pelo prazo): nada muda nele nem no novo.
    expect(regras.registrarResultado(antigo.desafioId, "falhou", INICIO + 61_000)).toBe("incerto");
    expect(linha(banco, novo.desafioId).invalidado_em).toBeNull();
    expect(validar(regras, novo, novo.codigo!, INICIO + 62_000, "k", 2).tipo).toBe("autorizado");
  });

  it("reserva e envio não começam para desafio substituído", () => {
    const { regras } = novoDestino();
    const antigo = pedirCriado(regras, INICIO);
    pedirCriado(regras, INICIO + INTERVALO_REENVIO_MS, 2);
    expect(regras.registrarReserva(antigo.desafioId, "r", INICIO + 61_000)).toBe(false);
    expect(regras.iniciarEnvio(antigo.desafioId, INICIO + 61_000)).toBe(false);
  });
});

describe("retenção", () => {
  it("apaga desafios encerrados 24 h após o encerramento, com as tentativas", () => {
    const { regras, banco } = novoDestino();
    const r = pronto(regras, INICIO);
    validar(regras, r, errado(r.codigo!), INICIO + 1, "k1");
    regras.processarPrazos(INICIO + VALIDADE_CODIGO_MS + RETENCAO_DESAFIO_MS - 1);
    expect(banco.todos("SELECT id FROM desafios")).toHaveLength(1);
    regras.processarPrazos(INICIO + VALIDADE_CODIGO_MS + RETENCAO_DESAFIO_MS);
    expect(banco.todos("SELECT id FROM desafios")).toHaveLength(0);
    expect(banco.todos("SELECT * FROM validacoes")).toHaveLength(0);
  });

  it("desafio invalidado conta a retenção a partir da invalidação", () => {
    const { regras, banco } = novoDestino();
    const r1 = pronto(regras, INICIO);
    pronto(regras, INICIO + INTERVALO_REENVIO_MS, 2);
    regras.processarPrazos(INICIO + INTERVALO_REENVIO_MS + RETENCAO_DESAFIO_MS);
    expect(banco.um("SELECT id FROM desafios WHERE id = ?", r1.desafioId)).toBeNull();
  });

  it("contadores do destino: hora some após 2 h, dia após 48 h", () => {
    const { regras, banco } = novoDestino();
    pronto(regras, INICIO);
    regras.processarPrazos(INICIO + 2 * HORA_MS);
    expect(banco.todos("SELECT duracao FROM contadores ORDER BY duracao")).toEqual([{ duracao: "dia" }]);
    regras.processarPrazos(INICIO + 48 * HORA_MS);
    expect(banco.todos("SELECT * FROM contadores")).toHaveLength(0);
  });
});

describe("reservas abandonadas (prazo de 60 s)", () => {
  it("pendente_reserva é encerrada como abandonada no prazo, com a data do abandono", () => {
    const { regras, banco } = novoDestino();
    const r = pedirCriado(regras, INICIO);
    expect(regras.proximoPrazo()).toBe(INICIO + PRAZO_RESERVA_MS);
    regras.processarPrazos(INICIO + PRAZO_RESERVA_MS - 1);
    expect(linha(banco, r.desafioId).invalidado_em).toBeNull();
    regras.processarPrazos(INICIO + 5 * PRAZO_RESERVA_MS);
    expect(linha(banco, r.desafioId)).toMatchObject({
      motivo_invalidacao: "reserva_abandonada", invalidado_em: INICIO + PRAZO_RESERVA_MS,
    });
  });

  it("execução atrasada não reserva depois do prazo, nem com relógio defasado", () => {
    const { regras } = novoDestino();
    const r = pedirCriado(regras, INICIO);
    // Pelo prazo, mesmo sem encerramento prévio:
    expect(regras.registrarReserva(r.desafioId, "r", INICIO + PRAZO_RESERVA_MS)).toBe(false);

    const { regras: outras } = novoDestino(new AleatorioDeTeste("b"));
    const r2 = pedirCriado(outras, INICIO);
    outras.processarPrazos(INICIO + PRAZO_RESERVA_MS); // alarme encerra
    // A execução atrasada ainda acha que é INICIO + 1 s: o estado encerrado a impede.
    expect(outras.registrarReserva(r2.desafioId, "r", INICIO + 1000)).toBe(false);
  });

  it("execução atrasada não inicia o envio de uma reserva abandonada", () => {
    const { regras, banco } = novoDestino();
    const r = pedirCriado(regras, INICIO);
    expect(regras.registrarReserva(r.desafioId, "r", INICIO + 1000)).toBe(true);
    expect(regras.iniciarEnvio(r.desafioId, INICIO + PRAZO_RESERVA_MS)).toBe(false);
    expect(linha(banco, r.desafioId)).toMatchObject({ estado_envio: "reservado", motivo_invalidacao: "reserva_abandonada" });
    expect(regras.iniciarEnvio(r.desafioId, INICIO + 2000)).toBe(false); // relógio defasado
    expect(validar(regras, r, r.codigo!, INICIO + 3000).tipo).toBe("encerrado");
  });

  it("retenção conta do abandono mesmo quando o encerramento é registrado depois de expirar", () => {
    const { regras, banco } = novoDestino();
    pedirCriado(regras, INICIO);
    regras.processarPrazos(INICIO + PRAZO_RESERVA_MS + RETENCAO_DESAFIO_MS);
    expect(banco.todos("SELECT id FROM desafios")).toHaveLength(0);
  });
});

describe("neutralidade da recuperação com invalidação por envio", () => {
  function recuperacaoComFalha(motivo: "falhou" | "sem_reserva") {
    const ctx = novoDestino();
    const r = pedirCriado(ctx.regras, INICIO, 1, "recuperacao_senha");
    if (motivo === "sem_reserva") {
      ctx.regras.marcarSemReserva(r.desafioId, INICIO);
    } else {
      ctx.regras.registrarReserva(r.desafioId, "r", INICIO);
      ctx.regras.iniciarEnvio(r.desafioId, INICIO);
      ctx.regras.registrarResultado(r.desafioId, "falhou", INICIO + 1);
    }
    return { ...ctx, r };
  }

  it.each(["falhou", "sem_reserva"] as const)(
    "desafio real com %s se comporta como o pedido sem envio na repetição e na validação",
    (motivo) => {
      const { regras, r } = recuperacaoComFalha(motivo);
      const semEnvio = novoDestino(new AleatorioDeTeste("sem"));
      const s = pedir(semEnvio.regras, INICIO, 1, "recuperacao_senha", true) as Criado;

      expect(pedir(regras, INICIO + 2, 1, "recuperacao_senha")).toMatchObject({ encerrado: false });
      expect(pedir(semEnvio.regras, INICIO + 2, 1, "recuperacao_senha", true)).toMatchObject({ encerrado: false });

      for (let i = 1; i <= 5; i++) {
        const real = validar(regras, r, r.codigo!, INICIO + 10 + i, `k${i}`);
        const neutro = validar(semEnvio.regras, s, r.codigo!, INICIO + 10 + i, `k${i}`);
        expect(real).toEqual(neutro);
        expect(real.tipo).toBe("codigo_invalido");
      }
      expect(validar(regras, r, r.codigo!, INICIO + 20, "k9").tipo).toBe("encerrado");
      expect(validar(semEnvio.regras, s, r.codigo!, INICIO + 20, "k9").tipo).toBe("encerrado");
    },
  );

  it("no cadastro, a falha de envio encerra o desafio normalmente", () => {
    const { regras } = novoDestino();
    const r = pronto(regras, INICIO);
    regras.registrarResultado(r.desafioId, "falhou", INICIO + 1);
    expect(validar(regras, r, r.codigo!, INICIO + 2).tipo).toBe("encerrado");
    expect(pedir(regras, INICIO + 3)).toMatchObject({ encerrado: true, motivoInvalidacao: "falha_envio" });
  });
});
