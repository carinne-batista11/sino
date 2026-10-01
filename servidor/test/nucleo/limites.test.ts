// Limites aprovados: destino (60 s, 5/h, 10/dia, todas as finalidades),
// IP (10 pedidos/h, 30/dia, 30 validações/h) e teto global (80/dia UTC).

import { describe, expect, it } from "vitest";
import {
  DIA_MS,
  HORA_MS,
  INTERVALO_REENVIO_MS,
  RETENCAO_TOTAIS_GLOBAIS_DIAS,
  TETO_GLOBAL_DIA,
} from "../../src/config";
import { RegrasIp } from "../../src/nucleo/contadores";
import { RegrasTetoGlobal } from "../../src/nucleo/teto_global";
import { AleatorioDeTeste, BancoNode, CONTEXTO, INICIO, novoDestino } from "./apoio";

const FINALIDADES = ["cadastro", "alteracao_email", "recuperacao_senha"] as const;

describe("limites por destino", () => {
  it("5 pedidos por hora, somando todas as finalidades", () => {
    const { regras } = novoDestino();
    const tipos: string[] = [];
    for (let i = 0; i < 6; i++) {
      tipos.push(
        regras.solicitar({
          finalidade: FINALIDADES[i % 3], contexto: CONTEXTO, segredoHash: `s${i}`, chaveHash: `k${i}`,
          semEnvio: false, agora: INICIO + i * INTERVALO_REENVIO_MS,
        }).tipo,
      );
    }
    expect(tipos).toEqual(["criado", "criado", "criado", "criado", "criado", "limite"]);
  });

  it("10 pedidos por dia UTC", () => {
    const { regras } = novoDestino();
    const inicioDoDia = Date.UTC(2026, 9, 1);
    const tipos: string[] = [];
    for (let i = 0; i < 11; i++) {
      // Dois pedidos por hora: nunca bate no limite por hora.
      const agora = inicioDoDia + Math.floor(i / 2) * HORA_MS + (i % 2) * INTERVALO_REENVIO_MS;
      tipos.push(
        regras.solicitar({
          finalidade: "cadastro", contexto: CONTEXTO, segredoHash: `s${i}`, chaveHash: `k${i}`, semEnvio: false, agora,
        }).tipo,
      );
    }
    expect(tipos.filter((t) => t === "criado")).toHaveLength(10);
    expect(tipos[10]).toBe("limite");
    // No dia seguinte, volta a aceitar.
    const amanha = regras.solicitar({
      finalidade: "cadastro", contexto: CONTEXTO, segredoHash: "s-x", chaveHash: "k-x", semEnvio: false,
      agora: inicioDoDia + DIA_MS,
    });
    expect(amanha.tipo).toBe("criado");
  });

  it("pedidos sem envio contam igual aos pedidos reais", () => {
    const { regras } = novoDestino();
    for (let i = 0; i < 5; i++) {
      regras.solicitar({
        finalidade: "recuperacao_senha", contexto: CONTEXTO, segredoHash: `s${i}`, chaveHash: `k${i}`,
        semEnvio: i % 2 === 0, agora: INICIO + i * INTERVALO_REENVIO_MS,
      });
    }
    const sexto = regras.solicitar({
      finalidade: "recuperacao_senha", contexto: CONTEXTO, segredoHash: "s5", chaveHash: "k5", semEnvio: true,
      agora: INICIO + 5 * INTERVALO_REENVIO_MS,
    });
    expect(sexto.tipo).toBe("limite");
  });
});

describe("limites por IP", () => {
  function novoIp() {
    const banco = new BancoNode();
    const regras = new RegrasIp(banco);
    regras.garantirEsquema();
    return { banco, regras };
  }

  it("10 pedidos por hora e 30 por dia", () => {
    const { regras } = novoIp();
    const inicioDoDia = Date.UTC(2026, 9, 1);
    const porHora = Array.from({ length: 11 }, (_, i) => regras.reservarPedido(inicioDoDia + i));
    expect(porHora.filter(Boolean)).toHaveLength(10);
    expect(porHora[10]).toBe(false);
    for (let h = 1; h <= 3; h++) {
      for (let i = 0; i < 10; i++) regras.reservarPedido(inicioDoDia + h * HORA_MS + i);
    }
    // 10 + 10 + 10 = 30 no dia; a quarta hora já não aceita.
    expect(regras.reservarPedido(inicioDoDia + 3 * HORA_MS + 100)).toBe(false);
    expect(regras.reservarPedido(inicioDoDia + DIA_MS)).toBe(true);
  });

  it("30 validações por hora, separadas dos pedidos", () => {
    const { regras } = novoIp();
    const v = Array.from({ length: 31 }, (_, i) => regras.reservarValidacao(INICIO + i));
    expect(v.filter(Boolean)).toHaveLength(30);
    expect(v[30]).toBe(false);
    expect(regras.reservarPedido(INICIO + 100)).toBe(true);
    expect(regras.reservarValidacao(INICIO + HORA_MS)).toBe(true);
  });

  it("contadores somem nos prazos de retenção (2 h e 48 h)", () => {
    const { regras, banco } = novoIp();
    regras.reservarPedido(INICIO);
    regras.limpar(INICIO + 2 * HORA_MS);
    expect(banco.todos("SELECT duracao FROM contadores")).toEqual([{ duracao: "dia" }]);
    regras.limpar(INICIO + 48 * HORA_MS);
    expect(banco.todos("SELECT * FROM contadores")).toHaveLength(0);
    expect(regras.proximaLimpeza()).toBeNull();
  });
});

describe("teto global", () => {
  function novoTeto() {
    const banco = new BancoNode();
    const regras = new RegrasTetoGlobal(banco, new AleatorioDeTeste("teto"));
    regras.garantirEsquema();
    return { banco, regras };
  }

  it("reserva 80 envios por dia UTC e recusa o restante", () => {
    const { regras } = novoTeto();
    const reservas = Array.from({ length: TETO_GLOBAL_DIA + 5 }, (_, i) => regras.reservar(INICIO + i));
    expect(reservas.filter((r) => r !== null)).toHaveLength(TETO_GLOBAL_DIA);
    expect(new Set(reservas.filter(Boolean)).size).toBe(TETO_GLOBAL_DIA);
    expect(regras.esgotado(INICIO)).toBe(true);
    expect(regras.esgotado(Date.UTC(2026, 9, 2))).toBe(false);
    expect(regras.reservar(Date.UTC(2026, 9, 2))).not.toBeNull();
  });

  it("guarda os totais diários por 35 dias", () => {
    const { regras, banco } = novoTeto();
    regras.reservar(Date.UTC(2026, 9, 1, 10));
    regras.limpar(Date.UTC(2026, 9, 1 + RETENCAO_TOTAIS_GLOBAIS_DIAS, 23));
    expect(banco.todos("SELECT dia FROM totais_diarios")).toHaveLength(1);
    expect(regras.proximaLimpeza()).toBe(Date.UTC(2026, 9, 2 + RETENCAO_TOTAIS_GLOBAIS_DIAS));
    regras.limpar(Date.UTC(2026, 9, 2 + RETENCAO_TOTAIS_GLOBAIS_DIAS));
    expect(banco.todos("SELECT dia FROM totais_diarios")).toHaveLength(0);
  });
});
