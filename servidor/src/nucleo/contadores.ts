// Contadores em janelas fixas (hora cheia e dia UTC) guardados no SQLite do
// próprio objeto. Cada objeto atualiza os seus contadores dentro da transação
// da operação, então a contagem é atômica dentro do objeto.

import {
  DIA_MS,
  HORA_MS,
  LIMITE_IP_PEDIDOS_DIA,
  LIMITE_IP_PEDIDOS_HORA,
  LIMITE_IP_VALIDACOES_HORA,
  RETENCAO_CONTADOR_DIA_MS,
  RETENCAO_CONTADOR_HORA_MS,
} from "../config";
import type { BancoSql } from "./banco";

export type Duracao = "hora" | "dia";

const DURACAO_MS: Record<Duracao, number> = { hora: HORA_MS, dia: DIA_MS };
const RETENCAO_MS: Record<Duracao, number> = {
  hora: RETENCAO_CONTADOR_HORA_MS,
  dia: RETENCAO_CONTADOR_DIA_MS,
};

export function inicioDaJanela(agora: number, duracao: Duracao): number {
  return agora - (agora % DURACAO_MS[duracao]);
}

export class Contadores {
  constructor(private readonly banco: BancoSql) {}

  garantirEsquema(): void {
    this.banco.executar(`
      CREATE TABLE IF NOT EXISTS contadores (
        nome TEXT NOT NULL,
        duracao TEXT NOT NULL CHECK (duracao IN ('hora', 'dia')),
        inicio INTEGER NOT NULL,
        contagem INTEGER NOT NULL CHECK (contagem >= 0),
        PRIMARY KEY (nome, duracao, inicio)
      )`);
  }

  valor(nome: string, duracao: Duracao, agora: number): number {
    const linha = this.banco.um<{ contagem: number }>(
      "SELECT contagem FROM contadores WHERE nome = ? AND duracao = ? AND inicio = ?",
      nome, duracao, inicioDaJanela(agora, duracao),
    );
    return linha?.contagem ?? 0;
  }

  incrementar(nome: string, duracao: Duracao, agora: number): void {
    this.banco.executar(
      `INSERT INTO contadores (nome, duracao, inicio, contagem) VALUES (?, ?, ?, 1)
       ON CONFLICT (nome, duracao, inicio) DO UPDATE SET contagem = contagem + 1`,
      nome, duracao, inicioDaJanela(agora, duracao),
    );
  }

  /** Apaga janelas cujo início ficou além do prazo de retenção. */
  limpar(agora: number): void {
    for (const duracao of ["hora", "dia"] as const) {
      this.banco.executar(
        "DELETE FROM contadores WHERE duracao = ? AND inicio <= ?",
        duracao, agora - RETENCAO_MS[duracao],
      );
    }
  }

  /** Momento da próxima limpeza necessária, ou null se não houver contadores. */
  proximaLimpeza(): number | null {
    const linha = this.banco.um<{ quando: number | null }>(
      `SELECT MIN(inicio + CASE duracao WHEN 'hora' THEN ? ELSE ? END) AS quando FROM contadores`,
      RETENCAO_CONTADOR_HORA_MS, RETENCAO_CONTADOR_DIA_MS,
    );
    return linha?.quando ?? null;
  }
}

/** Limites por IP (um objeto por IP ou prefixo IPv6 /64). */
export class RegrasIp {
  private readonly contadores: Contadores;

  constructor(private readonly banco: BancoSql) {
    this.contadores = new Contadores(banco);
  }

  garantirEsquema(): void {
    this.contadores.garantirEsquema();
  }

  reservarPedido(agora: number): boolean {
    return this.banco.transacao(() => {
      this.contadores.limpar(agora);
      if (
        this.contadores.valor("pedidos", "hora", agora) >= LIMITE_IP_PEDIDOS_HORA ||
        this.contadores.valor("pedidos", "dia", agora) >= LIMITE_IP_PEDIDOS_DIA
      ) {
        return false;
      }
      this.contadores.incrementar("pedidos", "hora", agora);
      this.contadores.incrementar("pedidos", "dia", agora);
      return true;
    });
  }

  reservarValidacao(agora: number): boolean {
    return this.banco.transacao(() => {
      this.contadores.limpar(agora);
      if (this.contadores.valor("validacoes", "hora", agora) >= LIMITE_IP_VALIDACOES_HORA) return false;
      this.contadores.incrementar("validacoes", "hora", agora);
      return true;
    });
  }

  limpar(agora: number): void {
    this.banco.transacao(() => this.contadores.limpar(agora));
  }

  proximaLimpeza(): number | null {
    return this.contadores.proximaLimpeza();
  }
}
