// Durable Objects com SQLite. Cada objeto atende uma operação por vez e cada
// operação roda numa transação síncrona (transactionSync), então as regras
// de um objeto são atômicas. Os alarmes cuidam dos envios abandonados e da
// retenção, inclusive em objetos que não recebem mais pedidos.

import { DurableObject } from "cloudflare:workers";
import type { BancoSql, ValorSql } from "./nucleo/banco";
import { RegrasIp } from "./nucleo/contadores";
import { aleatorioSeguro, chaveDeHex } from "./nucleo/cripto";
import {
  ERRO_ESQUEMA_INCOMPATIVEL,
  EsquemaIncompativelError,
  RegrasDestino,
  type EstadoEnvio,
  type PedidoDesafio,
  type PedidoValidacao,
  type ResultadoEnvio,
  type ResultadoSolicitar,
  type ResultadoValidar,
} from "./nucleo/desafios";
import { registrarEvento } from "./nucleo/registro";
import { RegrasTetoGlobal } from "./nucleo/teto_global";

export interface Env {
  DESTINO: DurableObjectNamespace<DestinoDO>;
  LIMITE_IP: DurableObjectNamespace<LimiteIpDO>;
  TETO_GLOBAL: DurableObjectNamespace<TetoGlobalDO>;
  CHAVE_HMAC?: string;
  CHAVE_ASSINATURA?: string;
  KID_ASSINATURA?: string;
  RESEND_API_KEY?: string;
  REMETENTE?: string;
  /** Lista de destinatários permitidos (ver src/nucleo/destinatarios.ts). */
  DESTINATARIOS_PERMITIDOS?: string;
}

export class ConfiguracaoAusenteError extends Error {
  override name = "ConfiguracaoAusenteError";
}

export function bancoDoObjeto(storage: DurableObjectStorage): BancoSql {
  const sql = storage.sql;
  return {
    executar(consulta: string, ...parametros: ValorSql[]) {
      sql.exec(consulta, ...parametros).toArray();
    },
    todos<T>(consulta: string, ...parametros: ValorSql[]) {
      return sql.exec(consulta, ...parametros).toArray() as T[];
    },
    um<T>(consulta: string, ...parametros: ValorSql[]) {
      return (sql.exec(consulta, ...parametros).toArray()[0] as T | undefined) ?? null;
    },
    transacao<T>(fn: () => T) {
      return storage.transactionSync(fn);
    },
  };
}

/** Agenda o alarme para o próximo prazo (ou remove, se não houver). */
async function agendarAlarme(storage: DurableObjectStorage, proximo: number | null): Promise<void> {
  if (proximo === null) await storage.deleteAlarm();
  else await storage.setAlarm(proximo);
}

export class DestinoDO extends DurableObject<Env> {
  private readonly regras: RegrasDestino | null;
  private readonly esquemaIncompativel: boolean = false;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    const chave = chaveDeHex(env.CHAVE_HMAC);
    let regras = chave ? new RegrasDestino(bancoDoObjeto(ctx.storage), chave, aleatorioSeguro) : null;
    try {
      regras?.garantirEsquema();
    } catch (erro) {
      if (!(erro instanceof EsquemaIncompativelError)) throw erro;
      // Estado local de uma versão anterior: não é alterado nem reaproveitado.
      registrarEvento("estado local do destino de versão anterior; respondendo indisponível");
      regras = null;
      this.esquemaIncompativel = true;
    }
    this.regras = regras;
  }

  private exigirRegras(): RegrasDestino {
    if (this.esquemaIncompativel) throw new Error(ERRO_ESQUEMA_INCOMPATIVEL);
    if (!this.regras) throw new ConfiguracaoAusenteError();
    return this.regras;
  }

  private async aposAlterar<T>(resultado: T): Promise<T> {
    await agendarAlarme(this.ctx.storage, this.exigirRegras().proximoPrazo());
    return resultado;
  }

  async solicitar(p: PedidoDesafio): Promise<ResultadoSolicitar> {
    return this.aposAlterar(this.exigirRegras().solicitar(p));
  }

  async registrarReserva(desafioId: string, reservaId: string, agora: number): Promise<boolean> {
    return this.aposAlterar(this.exigirRegras().registrarReserva(desafioId, reservaId, agora));
  }

  async marcarSemReserva(desafioId: string, agora: number): Promise<boolean> {
    return this.aposAlterar(this.exigirRegras().marcarSemReserva(desafioId, agora));
  }

  async marcarBloqueado(desafioId: string, agora: number): Promise<boolean> {
    return this.aposAlterar(this.exigirRegras().marcarBloqueado(desafioId, agora));
  }

  async iniciarEnvio(desafioId: string, agora: number): Promise<boolean> {
    return this.aposAlterar(this.exigirRegras().iniciarEnvio(desafioId, agora));
  }

  async registrarResultado(desafioId: string, resultado: ResultadoEnvio, agora: number): Promise<EstadoEnvio | null> {
    return this.aposAlterar(this.exigirRegras().registrarResultado(desafioId, resultado, agora));
  }

  async validar(p: PedidoValidacao): Promise<ResultadoValidar> {
    return this.aposAlterar(this.exigirRegras().validar(p));
  }

  override async alarm(): Promise<void> {
    if (!this.regras) return;
    await agendarAlarme(this.ctx.storage, this.regras.processarPrazos(Date.now()));
  }
}

export class LimiteIpDO extends DurableObject<Env> {
  private readonly regras: RegrasIp;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    this.regras = new RegrasIp(bancoDoObjeto(ctx.storage));
    this.regras.garantirEsquema();
  }

  async reservarPedido(agora: number): Promise<boolean> {
    const ok = this.regras.reservarPedido(agora);
    await agendarAlarme(this.ctx.storage, this.regras.proximaLimpeza());
    return ok;
  }

  async reservarValidacao(agora: number): Promise<boolean> {
    const ok = this.regras.reservarValidacao(agora);
    await agendarAlarme(this.ctx.storage, this.regras.proximaLimpeza());
    return ok;
  }

  override async alarm(): Promise<void> {
    this.regras.limpar(Date.now());
    await agendarAlarme(this.ctx.storage, this.regras.proximaLimpeza());
  }
}

export class TetoGlobalDO extends DurableObject<Env> {
  private readonly regras: RegrasTetoGlobal;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
    this.regras = new RegrasTetoGlobal(bancoDoObjeto(ctx.storage), aleatorioSeguro);
    this.regras.garantirEsquema();
  }

  async esgotado(agora: number): Promise<boolean> {
    return this.regras.esgotado(agora);
  }

  async reservar(agora: number): Promise<string | null> {
    const reserva = this.regras.reservar(agora);
    await agendarAlarme(this.ctx.storage, this.regras.proximaLimpeza());
    return reserva;
  }

  override async alarm(): Promise<void> {
    this.regras.limpar(Date.now());
    await agendarAlarme(this.ctx.storage, this.regras.proximaLimpeza());
  }
}
