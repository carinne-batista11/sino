// Apoio aos testes do núcleo: SQLite do Node (mesmos comandos SQL do Durable
// Object), relógio e aleatoriedade controláveis e portas em memória com
// injeção de falhas. Sem rede, sem sleep.

import { DatabaseSync } from "node:sqlite";
import { sha256 } from "@noble/hashes/sha2.js";
import { utf8ToBytes } from "@noble/hashes/utils.js";
import type { BancoSql, ValorSql } from "../../src/nucleo/banco";
import { RegrasIp } from "../../src/nucleo/contadores";
import { gerarCodigo, type Aleatorio } from "../../src/nucleo/cripto";
import { RegrasDestino } from "../../src/nucleo/desafios";
import { RegrasTetoGlobal } from "../../src/nucleo/teto_global";
import { EnviadorSimulado } from "../../src/envio/simulado";
import type { Dependencias, PortaDestino, PortaIp, PortaTetoGlobal } from "../../src/fluxos";

export const CHAVE_HMAC = new Uint8Array(32).fill(0x11);
export const CHAVE_ASSINATURA = new Uint8Array(32).fill(0x22);
export const KID = "teste-1";
export const INICIO = Date.UTC(2026, 9, 1, 12, 0, 0); // 2026-10-01 12:00:00 UTC

export class BancoNode implements BancoSql {
  readonly db = new DatabaseSync(":memory:");

  executar(sql: string, ...p: ValorSql[]): void {
    this.db.prepare(sql).run(...p);
  }
  todos<T>(sql: string, ...p: ValorSql[]): T[] {
    return this.db.prepare(sql).all(...p) as T[];
  }
  um<T>(sql: string, ...p: ValorSql[]): T | null {
    return (this.db.prepare(sql).get(...p) as T | undefined) ?? null;
  }
  transacao<T>(fn: () => T): T {
    this.db.exec("BEGIN IMMEDIATE");
    try {
      const r = fn();
      this.db.exec("COMMIT");
      return r;
    } catch (e) {
      this.db.exec("ROLLBACK");
      throw e;
    }
  }
}

/** Aleatoriedade determinística (SHA-256 em contador), clonável. */
export class AleatorioDeTeste implements Aleatorio {
  constructor(private readonly semente = "sino", private contador = 0) {}

  bytes(n: number): Uint8Array {
    const saida = new Uint8Array(n);
    let preenchido = 0;
    while (preenchido < n) {
      const bloco = sha256(utf8ToBytes(`${this.semente}:${this.contador++}`));
      const parte = bloco.subarray(0, Math.min(bloco.length, n - preenchido));
      saida.set(parte, preenchido);
      preenchido += parte.length;
    }
    return saida;
  }

  clonar(): AleatorioDeTeste {
    return new AleatorioDeTeste(this.semente, this.contador);
  }

  /** Código que o próximo `solicitar` vai gerar (id é sorteado antes do código). */
  proximoCodigo(): string {
    const c = this.clonar();
    c.bytes(16);
    return gerarCodigo(c);
  }
}

export class Relogio {
  constructor(public agora = INICIO) {}
  avancar(ms: number): number {
    this.agora += ms;
    return this.agora;
  }
  readonly ler = () => this.agora;
}

export function novoDestino(aleatorio = new AleatorioDeTeste()) {
  const banco = new BancoNode();
  const regras = new RegrasDestino(banco, CHAVE_HMAC, aleatorio);
  regras.garantirEsquema();
  return { banco, regras, aleatorio };
}

export const segredoHashDe = (n: number) => `segredo-hash-${n}`;
export const chaveHashDe = (n: number) => `chave-hash-${n}`;
export const CONTEXTO = "c".repeat(64);

/** Falhas programáveis por nome de método: lança uma vez na próxima chamada. */
export class Falhas {
  private pendentes = new Set<string>();
  programar(...metodos: string[]): void {
    for (const m of metodos) this.pendentes.add(m);
  }
  verificar(metodo: string): void {
    if (this.pendentes.delete(metodo)) throw new Error(`falha simulada em ${metodo}`);
  }
}

function comFalhas<T extends object>(alvo: T, falhas: Falhas): T {
  return new Proxy(alvo, {
    get(obj, prop) {
      const valor = Reflect.get(obj, prop);
      if (typeof valor !== "function") return valor;
      return async (...args: unknown[]) => {
        falhas.verificar(String(prop));
        return valor.apply(obj, args);
      };
    },
  });
}

/** Mundo em memória: um objeto por chave, como os Durable Objects. */
export class Mundo {
  readonly relogio = new Relogio();
  readonly aleatorio = new AleatorioDeTeste();
  readonly enviador = new EnviadorSimulado();
  readonly falhas = new Falhas();
  readonly destinos = new Map<string, RegrasDestino>();
  readonly bancosDestino = new Map<string, BancoNode>();
  readonly ips = new Map<string, RegrasIp>();
  readonly teto: RegrasTetoGlobal;
  readonly segundoPlano: Promise<unknown>[] = [];
  semSegredos = false;

  constructor() {
    const banco = new BancoNode();
    this.teto = new RegrasTetoGlobal(banco, this.aleatorio);
    this.teto.garantirEsquema();
  }

  regrasDestino(emailHash: string): RegrasDestino {
    let r = this.destinos.get(emailHash);
    if (!r) {
      const banco = new BancoNode();
      r = new RegrasDestino(banco, CHAVE_HMAC, this.aleatorio);
      r.garantirEsquema();
      this.destinos.set(emailHash, r);
      this.bancosDestino.set(emailHash, banco);
    }
    return r;
  }

  deps(): Dependencias {
    return {
      segredos: this.semSegredos ? null : { chaveHmac: CHAVE_HMAC, chaveAssinatura: CHAVE_ASSINATURA, kid: KID },
      destino: (h) => comFalhas(this.regrasDestino(h), this.falhas) as unknown as PortaDestino,
      ip: (h) => {
        let r = this.ips.get(h);
        if (!r) {
          r = new RegrasIp(new BancoNode());
          r.garantirEsquema();
          this.ips.set(h, r);
        }
        return comFalhas(r, this.falhas) as unknown as PortaIp;
      },
      tetoGlobal: () => comFalhas(this.teto, this.falhas) as unknown as PortaTetoGlobal,
      enviador: this.enviador,
      relogio: this.relogio.ler,
      emSegundoPlano: (t) => {
        this.segundoPlano.push(t);
      },
    };
  }

  async concluirSegundoPlano(): Promise<void> {
    await Promise.all(this.segundoPlano.splice(0));
  }
}

/** Captura console.error/console.warn para conferir que nada sensível vaza. */
export function capturarRegistros(): { linhas: string[]; restaurar: () => void } {
  const linhas: string[] = [];
  const erro = console.error;
  const aviso = console.warn;
  console.error = (...a: unknown[]) => void linhas.push(a.map(String).join(" "));
  console.warn = (...a: unknown[]) => void linhas.push(a.map(String).join(" "));
  return {
    linhas,
    restaurar: () => {
      console.error = erro;
      console.warn = aviso;
    },
  };
}
