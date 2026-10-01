// Teto global de envios por dia UTC (cota gratuita da Resend: 100/dia).
// Um único objeto conta os envios; uma vaga reservada nunca é devolvida.

import { DIA_MS, RETENCAO_TOTAIS_GLOBAIS_DIAS, TETO_GLOBAL_DIA } from "../config";
import type { BancoSql } from "./banco";
import { identificadorAleatorio, type Aleatorio } from "./cripto";

export function diaUtc(agora: number): string {
  return new Date(agora).toISOString().slice(0, 10);
}

export class RegrasTetoGlobal {
  constructor(
    private readonly banco: BancoSql,
    private readonly aleatorio: Aleatorio,
  ) {}

  garantirEsquema(): void {
    this.banco.executar(`
      CREATE TABLE IF NOT EXISTS totais_diarios (
        dia TEXT PRIMARY KEY,
        envios INTEGER NOT NULL CHECK (envios >= 0)
      )`);
  }

  private envios(dia: string): number {
    return this.banco.um<{ envios: number }>("SELECT envios FROM totais_diarios WHERE dia = ?", dia)?.envios ?? 0;
  }

  /** O teto do dia já foi atingido? Só leitura. */
  esgotado(agora: number): boolean {
    return this.envios(diaUtc(agora)) >= TETO_GLOBAL_DIA;
  }

  /** Reserva uma vaga de envio; devolve o id da reserva, ou null se o teto foi atingido. */
  reservar(agora: number): string | null {
    return this.banco.transacao(() => {
      this.limparSemTransacao(agora);
      const dia = diaUtc(agora);
      if (this.envios(dia) >= TETO_GLOBAL_DIA) return null;
      this.banco.executar(
        `INSERT INTO totais_diarios (dia, envios) VALUES (?, 1)
         ON CONFLICT (dia) DO UPDATE SET envios = envios + 1`,
        dia,
      );
      return `${dia}.${identificadorAleatorio(this.aleatorio)}`;
    });
  }

  limpar(agora: number): void {
    this.banco.transacao(() => this.limparSemTransacao(agora));
  }

  /** Momento em que o dia mais antigo guardado sai da retenção, ou null. */
  proximaLimpeza(): number | null {
    const linha = this.banco.um<{ dia: string | null }>("SELECT MIN(dia) AS dia FROM totais_diarios");
    if (!linha?.dia) return null;
    return Date.parse(`${linha.dia}T00:00:00Z`) + (RETENCAO_TOTAIS_GLOBAIS_DIAS + 1) * DIA_MS;
  }

  private limparSemTransacao(agora: number): void {
    const limite = diaUtc(agora - RETENCAO_TOTAIS_GLOBAIS_DIAS * DIA_MS);
    this.banco.executar("DELETE FROM totais_diarios WHERE dia < ?", limite);
  }
}
