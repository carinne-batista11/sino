// Regras dos desafios de um destino (um objeto por e-mail, em HMAC): ERS 5.32,
// limites por destino, reserva global obrigatória, envio incerto, resultados
// tardios e repetição de pedidos/validações. Cada operação pública roda numa
// única transação síncrona.

import {
  INTERVALO_REENVIO_MS,
  LIMITE_DESTINO_DIA,
  LIMITE_DESTINO_HORA,
  MAX_TENTATIVAS,
  PRAZO_ENVIANDO_MS,
  PRAZO_RESERVA_MS,
  RETENCAO_DESAFIO_MS,
  VALIDADE_CODIGO_MS,
  type Finalidade,
} from "../config";
import type { BancoSql } from "./banco";
import { Contadores } from "./contadores";
import {
  gerarCodigo,
  hmacHex,
  identificadorAleatorio,
  iguaisTempoConstante,
  type Aleatorio,
} from "./cripto";

export type EstadoEnvio =
  | "pendente_reserva"
  | "sem_reserva"
  | "sem_envio"
  | "reservado"
  | "enviando"
  | "enviado"
  | "incerto"
  | "falhou";

export type ResultadoEnvio = "enviado" | "incerto" | "falhou";

export type MotivoInvalidacao =
  | "substituido"
  | "expirado"
  | "tentativas"
  | "falha_envio"
  | "sem_reserva"
  | "reserva_abandonada";

/** Motivos ligados ao envio: um pedido sem envio nunca os recebe. */
export const MOTIVOS_DE_ENVIO: readonly MotivoInvalidacao[] = ["falha_envio", "sem_reserva", "reserva_abandonada"];

/**
 * Na recuperação, o desafio real invalidado por motivo de envio precisa se
 * comportar como o desafio sem envio (que segue ativo até expirar ou esgotar
 * as tentativas); senão a diferença revelaria que a conta existe.
 */
export function encerradoParaQuemPediu(
  finalidade: Finalidade,
  invalidadoEm: number | null,
  motivo: MotivoInvalidacao | null,
  expiraEm: number,
  agora: number,
): boolean {
  if (agora >= expiraEm) return true;
  if (invalidadoEm === null) return false;
  return !(finalidade === "recuperacao_senha" && motivo !== null && MOTIVOS_DE_ENVIO.includes(motivo));
}

export interface PedidoDesafio {
  finalidade: Finalidade;
  contexto: string;
  segredoHash: string;
  chaveHash: string;
  semEnvio: boolean;
  agora: number;
}

export type ResultadoSolicitar =
  | { tipo: "criado"; desafioId: string; codigo: string | null; expiraEm: number; reenvioEm: number }
  | {
      tipo: "repeticao";
      desafioId: string;
      expiraEm: number;
      reenvioEm: number;
      estadoEnvio: EstadoEnvio;
      /** Expirado ou invalidado: a repetição não pode mais levar a um código válido. */
      encerrado: boolean;
      motivoInvalidacao: MotivoInvalidacao | null;
    }
  | { tipo: "aguarde"; reenvioEm: number }
  | { tipo: "limite" }
  | { tipo: "conflito" };

export interface PedidoValidacao {
  desafioId: string;
  segredoHash: string;
  chaveHash: string;
  codigo: string;
  agora: number;
}

export interface DadosAutorizacao {
  jti: string;
  finalidade: Finalidade;
  contexto: string;
  validadoEm: number;
  expiraEm: number;
}

export type ResultadoValidar =
  | { tipo: "autorizado"; dados: DadosAutorizacao }
  | { tipo: "codigo_invalido"; tentativasRestantes: number }
  | { tipo: "encerrado" }
  | { tipo: "nao_encontrado" }
  | { tipo: "conflito" };

interface LinhaDesafio {
  id: string;
  finalidade: Finalidade;
  contexto: string;
  segredo_hash: string;
  pedido_chave_hash: string;
  pedido_impressao: string;
  codigo_hash: string;
  codigo_salt: string;
  criado_em: number;
  expira_em: number;
  tentativas: number;
  estado_envio: EstadoEnvio;
  reserva_global: string | null;
  envio_iniciado_em: number | null;
  validado_em: number | null;
  autorizacao_jti: string | null;
  invalidado_em: number | null;
  motivo_invalidacao: MotivoInvalidacao | null;
}

const ESTADOS_VALIDAVEIS: EstadoEnvio[] = ["enviando", "enviado", "incerto"];

// Momento do encerramento para a retenção: a invalidação ou a expiração, o
// que vier primeiro (uma invalidação registrada depois de expirar não adia).
const ENCERRAMENTO = "MIN(COALESCE(invalidado_em, expira_em), expira_em)";

export class RegrasDestino {
  private readonly contadores: Contadores;

  constructor(
    private readonly banco: BancoSql,
    private readonly chaveHmac: Uint8Array,
    private readonly aleatorio: Aleatorio,
  ) {
    this.contadores = new Contadores(banco);
  }

  garantirEsquema(): void {
    this.contadores.garantirEsquema();
    this.banco.executar(`
      CREATE TABLE IF NOT EXISTS desafios (
        id TEXT PRIMARY KEY,
        finalidade TEXT NOT NULL CHECK (finalidade IN ('cadastro', 'alteracao_email', 'recuperacao_senha')),
        contexto TEXT NOT NULL,
        segredo_hash TEXT NOT NULL,
        pedido_chave_hash TEXT NOT NULL UNIQUE,
        pedido_impressao TEXT NOT NULL,
        codigo_hash TEXT NOT NULL,
        codigo_salt TEXT NOT NULL,
        criado_em INTEGER NOT NULL,
        expira_em INTEGER NOT NULL,
        tentativas INTEGER NOT NULL DEFAULT 0 CHECK (tentativas BETWEEN 0 AND ${MAX_TENTATIVAS}),
        estado_envio TEXT NOT NULL CHECK (estado_envio IN
          ('pendente_reserva', 'sem_reserva', 'sem_envio', 'reservado', 'enviando', 'enviado', 'incerto', 'falhou')),
        reserva_global TEXT,
        envio_iniciado_em INTEGER,
        validado_em INTEGER,
        autorizacao_jti TEXT,
        invalidado_em INTEGER,
        motivo_invalidacao TEXT CHECK (motivo_invalidacao IN
          ('substituido', 'expirado', 'tentativas', 'falha_envio', 'sem_reserva', 'reserva_abandonada')),
        CHECK (estado_envio IN ('pendente_reserva', 'sem_reserva', 'sem_envio') OR reserva_global IS NOT NULL),
        CHECK (autorizacao_jti IS NULL
               OR (reserva_global IS NOT NULL AND estado_envio IN ('enviando', 'enviado', 'incerto'))),
        CHECK ((invalidado_em IS NULL) = (motivo_invalidacao IS NULL))
      )`);
    // Um desafio não invalidado por finalidade: o novo pedido encerra os
    // anteriores (inclusive expirados) antes de inserir.
    this.banco.executar(`
      CREATE UNIQUE INDEX IF NOT EXISTS desafios_um_ativo_por_finalidade
      ON desafios (finalidade) WHERE invalidado_em IS NULL`);
    this.banco.executar(`
      CREATE TABLE IF NOT EXISTS validacoes (
        desafio_id TEXT NOT NULL,
        chave_hash TEXT NOT NULL,
        impressao TEXT NOT NULL,
        resultado TEXT NOT NULL CHECK (resultado IN ('autorizado', 'codigo_invalido')),
        tentativas_restantes INTEGER NOT NULL,
        PRIMARY KEY (desafio_id, chave_hash)
      )`);
  }

  // ------------------------------------------------------------------ pedido

  solicitar(p: PedidoDesafio): ResultadoSolicitar {
    return this.banco.transacao(() => {
      this.encerrarVencidos(p.agora);
      const impressao = hmacHex(
        this.chaveHmac, "pedido", p.finalidade, p.contexto, p.segredoHash, p.semEnvio ? "1" : "0",
      );

      const anterior = this.banco.um<LinhaDesafio>(
        "SELECT * FROM desafios WHERE pedido_chave_hash = ?", p.chaveHash,
      );
      if (anterior) {
        if (!iguaisTempoConstante(anterior.pedido_impressao, impressao)) return { tipo: "conflito" };
        return {
          tipo: "repeticao",
          desafioId: anterior.id,
          expiraEm: anterior.expira_em,
          reenvioEm: anterior.criado_em + INTERVALO_REENVIO_MS,
          estadoEnvio: anterior.estado_envio,
          encerrado: encerradoParaQuemPediu(
            anterior.finalidade, anterior.invalidado_em, anterior.motivo_invalidacao, anterior.expira_em, p.agora,
          ),
          motivoInvalidacao: anterior.motivo_invalidacao,
        };
      }

      const ultimo = this.banco.um<{ quando: number | null }>("SELECT MAX(criado_em) AS quando FROM desafios");
      if (ultimo?.quando != null && p.agora < ultimo.quando + INTERVALO_REENVIO_MS) {
        return { tipo: "aguarde", reenvioEm: ultimo.quando + INTERVALO_REENVIO_MS };
      }
      if (
        this.contadores.valor("pedidos", "hora", p.agora) >= LIMITE_DESTINO_HORA ||
        this.contadores.valor("pedidos", "dia", p.agora) >= LIMITE_DESTINO_DIA
      ) {
        return { tipo: "limite" };
      }

      // 5.32: o novo código invalida imediatamente o anterior da mesma
      // finalidade; linhas já expiradas são encerradas como 'expirado'.
      this.banco.executar(
        `UPDATE desafios
           SET invalidado_em = ?,
               motivo_invalidacao = CASE WHEN expira_em <= ? THEN 'expirado' ELSE 'substituido' END
         WHERE finalidade = ? AND invalidado_em IS NULL`,
        p.agora, p.agora, p.finalidade,
      );

      const id = identificadorAleatorio(this.aleatorio);
      const codigo = gerarCodigo(this.aleatorio);
      const salt = identificadorAleatorio(this.aleatorio);
      const expiraEm = p.agora + VALIDADE_CODIGO_MS;
      this.banco.executar(
        `INSERT INTO desafios (id, finalidade, contexto, segredo_hash, pedido_chave_hash, pedido_impressao,
                               codigo_hash, codigo_salt, criado_em, expira_em, estado_envio)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        id, p.finalidade, p.contexto, p.segredoHash, p.chaveHash, impressao,
        this.hashCodigo(id, p.finalidade, salt, codigo), salt, p.agora, expiraEm,
        p.semEnvio ? "sem_envio" : "pendente_reserva",
      );
      this.contadores.incrementar("pedidos", "hora", p.agora);
      this.contadores.incrementar("pedidos", "dia", p.agora);

      return {
        tipo: "criado",
        desafioId: id,
        codigo: p.semEnvio ? null : codigo,
        expiraEm,
        reenvioEm: p.agora + INTERVALO_REENVIO_MS,
      };
    });
  }

  // ------------------------------------------------------------------- envio

  /**
   * Grava a reserva global; só depois disso o envio pode começar. Confere na
   * mesma transação que o desafio está ativo e dentro do prazo de reserva:
   * uma execução atrasada (inclusive com relógio defasado) não retoma o fluxo
   * de um desafio já encerrado como abandonado.
   */
  registrarReserva(desafioId: string, reservaId: string, agora: number): boolean {
    return this.banco.transacao(() => {
      this.encerrarVencidos(agora);
      return (
        this.banco.todos(
          `UPDATE desafios SET reserva_global = ?, estado_envio = 'reservado'
            WHERE id = ? AND estado_envio = 'pendente_reserva'
              AND invalidado_em IS NULL AND validado_em IS NULL
              AND expira_em > ? AND criado_em + ? > ?
           RETURNING id`,
          reservaId, desafioId, agora, PRAZO_RESERVA_MS, agora,
        ).length === 1
      );
    });
  }

  /** Teto global atingido: o desafio fica sem reserva e é invalidado. */
  marcarSemReserva(desafioId: string, agora: number): boolean {
    return this.banco.transacao(
      () =>
        this.banco.todos(
          `UPDATE desafios
              SET estado_envio = 'sem_reserva',
                  invalidado_em = COALESCE(invalidado_em, ?),
                  motivo_invalidacao = COALESCE(motivo_invalidacao, 'sem_reserva')
            WHERE id = ? AND estado_envio = 'pendente_reserva'
           RETURNING id`,
          agora, desafioId,
        ).length === 1,
    );
  }

  /** Mesmas garantias de `registrarReserva`: só um desafio ativo e no prazo começa a ser enviado. */
  iniciarEnvio(desafioId: string, agora: number): boolean {
    return this.banco.transacao(() => {
      this.encerrarVencidos(agora);
      return (
        this.banco.todos(
          `UPDATE desafios SET estado_envio = 'enviando', envio_iniciado_em = ?
            WHERE id = ? AND estado_envio = 'reservado'
              AND invalidado_em IS NULL AND validado_em IS NULL
              AND expira_em > ? AND criado_em + ? > ?
           RETURNING id`,
          agora, desafioId, agora, PRAZO_RESERVA_MS, agora,
        ).length === 1
      );
    });
  }

  /**
   * Resultado do envio (inclusive tardio). Só altera o próprio desafio, e só
   * enquanto ele está ativo (não validado, não invalidado, não expirado) e em
   * 'enviando' ou 'incerto'. Devolve o estado de envio resultante.
   */
  registrarResultado(desafioId: string, resultado: ResultadoEnvio, agora: number): EstadoEnvio | null {
    return this.banco.transacao(() => {
      this.encerrarVencidos(agora);
      const ativo = `id = ? AND estado_envio IN ('enviando', 'incerto')
                     AND invalidado_em IS NULL AND validado_em IS NULL AND expira_em > ?`;
      if (resultado === "falhou") {
        this.banco.executar(
          `UPDATE desafios SET estado_envio = 'falhou', invalidado_em = ?, motivo_invalidacao = 'falha_envio'
            WHERE ${ativo}`,
          agora, desafioId, agora,
        );
      } else if (resultado === "enviado") {
        this.banco.executar(`UPDATE desafios SET estado_envio = 'enviado' WHERE ${ativo}`, desafioId, agora);
      } else {
        this.banco.executar(
          `UPDATE desafios SET estado_envio = 'incerto' WHERE ${ativo} AND estado_envio = 'enviando'`,
          desafioId, agora,
        );
      }
      return this.banco.um<{ estado_envio: EstadoEnvio }>(
        "SELECT estado_envio FROM desafios WHERE id = ?", desafioId,
      )?.estado_envio ?? null;
    });
  }

  // --------------------------------------------------------------- validação

  validar(p: PedidoValidacao): ResultadoValidar {
    return this.banco.transacao(() => {
      this.encerrarVencidos(p.agora);
      const linha = this.banco.um<LinhaDesafio>("SELECT * FROM desafios WHERE id = ?", p.desafioId);
      if (!linha || !iguaisTempoConstante(linha.segredo_hash, p.segredoHash)) return { tipo: "nao_encontrado" };

      const impressao = hmacHex(this.chaveHmac, "tentativa", linha.id, p.codigo);
      const repetida = this.banco.um<{ impressao: string; resultado: string; tentativas_restantes: number }>(
        "SELECT impressao, resultado, tentativas_restantes FROM validacoes WHERE desafio_id = ? AND chave_hash = ?",
        linha.id, p.chaveHash,
      );
      if (repetida) {
        if (!iguaisTempoConstante(repetida.impressao, impressao)) return { tipo: "conflito" };
        if (repetida.resultado === "codigo_invalido") {
          return { tipo: "codigo_invalido", tentativasRestantes: repetida.tentativas_restantes };
        }
        // Mesma operação repetida: a mesma autorização, até o expira_em original.
        if (linha.invalidado_em !== null || p.agora >= linha.expira_em || linha.autorizacao_jti === null) {
          return { tipo: "encerrado" };
        }
        return { tipo: "autorizado", dados: this.dadosAutorizacao(linha) };
      }

      // Nova tentativa: a primeira validação correta encerra o código.
      if (
        linha.validado_em !== null ||
        encerradoParaQuemPediu(linha.finalidade, linha.invalidado_em, linha.motivo_invalidacao, linha.expira_em, p.agora) ||
        linha.tentativas >= MAX_TENTATIVAS
      ) {
        return { tipo: "encerrado" };
      }

      const confere = iguaisTempoConstante(
        this.hashCodigo(linha.id, linha.finalidade, linha.codigo_salt, p.codigo), linha.codigo_hash,
      );
      // Sem reserva global registrada, ou desafio sem envio: nunca autoriza,
      // mesmo que o código coincida (é tratado como código errado).
      const elegivel =
        linha.invalidado_em === null &&
        linha.reserva_global !== null &&
        ESTADOS_VALIDAVEIS.includes(linha.estado_envio);

      if (confere && elegivel) {
        const jti = identificadorAleatorio(this.aleatorio);
        const atualizadas = this.banco.todos(
          `UPDATE desafios SET validado_em = ?, autorizacao_jti = ?
            WHERE id = ? AND validado_em IS NULL AND invalidado_em IS NULL AND expira_em > ?
           RETURNING id`,
          p.agora, jti, linha.id, p.agora,
        );
        if (atualizadas.length !== 1) return { tipo: "encerrado" };
        this.banco.executar(
          `INSERT INTO validacoes (desafio_id, chave_hash, impressao, resultado, tentativas_restantes)
           VALUES (?, ?, ?, 'autorizado', ?)`,
          linha.id, p.chaveHash, impressao, MAX_TENTATIVAS - linha.tentativas,
        );
        return {
          tipo: "autorizado",
          dados: this.dadosAutorizacao({ ...linha, validado_em: p.agora, autorizacao_jti: jti }),
        };
      }

      const tentativas = linha.tentativas + 1;
      const esgotou = tentativas >= MAX_TENTATIVAS;
      this.banco.executar(
        `UPDATE desafios SET tentativas = ?,
                invalidado_em = CASE WHEN ? THEN ? ELSE invalidado_em END,
                motivo_invalidacao = CASE WHEN ? THEN 'tentativas' ELSE motivo_invalidacao END
          WHERE id = ?`,
        tentativas, esgotou ? 1 : 0, p.agora, esgotou ? 1 : 0, linha.id,
      );
      const restantes = MAX_TENTATIVAS - tentativas;
      this.banco.executar(
        `INSERT INTO validacoes (desafio_id, chave_hash, impressao, resultado, tentativas_restantes)
         VALUES (?, ?, ?, 'codigo_invalido', ?)`,
        linha.id, p.chaveHash, impressao, restantes,
      );
      return { tipo: "codigo_invalido", tentativasRestantes: restantes };
    });
  }

  // ------------------------------------------------------ prazos e retenção

  /**
   * Converte envios abandonados em 'incerto', encerra reservas abandonadas e
   * apaga o que passou da retenção. Chamado pelo alarme do objeto. Devolve o próximo momento em que
   * há trabalho a fazer (para reagendar o alarme), ou null.
   */
  processarPrazos(agora: number): number | null {
    return this.banco.transacao(() => {
      this.encerrarVencidos(agora);
      const limite = agora - RETENCAO_DESAFIO_MS;
      this.banco.executar(
        `DELETE FROM validacoes WHERE desafio_id IN (SELECT id FROM desafios WHERE ${ENCERRAMENTO} <= ?)`,
        limite,
      );
      this.banco.executar(`DELETE FROM desafios WHERE ${ENCERRAMENTO} <= ?`, limite);
      this.contadores.limpar(agora);
      return this.proximoPrazo();
    });
  }

  proximoPrazo(): number | null {
    const linha = this.banco.um<{ enviando: number | null; reserva: number | null; retencao: number | null }>(
      `SELECT
         (SELECT MIN(envio_iniciado_em) FROM desafios WHERE estado_envio = 'enviando') AS enviando,
         (SELECT MIN(criado_em) FROM desafios
           WHERE estado_envio IN ('pendente_reserva', 'reservado') AND invalidado_em IS NULL) AS reserva,
         (SELECT MIN(${ENCERRAMENTO}) FROM desafios) AS retencao`,
    );
    const candidatos = [
      linha?.enviando != null ? linha.enviando + PRAZO_ENVIANDO_MS : null,
      linha?.reserva != null ? linha.reserva + PRAZO_RESERVA_MS : null,
      linha?.retencao != null ? linha.retencao + RETENCAO_DESAFIO_MS : null,
      this.contadores.proximaLimpeza(),
    ].filter((v): v is number => v !== null);
    return candidatos.length ? Math.min(...candidatos) : null;
  }

  // ----------------------------------------------------------------- apoio

  /**
   * Prazos verificados em toda operação (e pelo alarme): envio em andamento
   * há 60 s vira "incerto"; reserva não concluída em 60 s é encerrada.
   */
  private encerrarVencidos(agora: number): void {
    this.banco.executar(
      "UPDATE desafios SET estado_envio = 'incerto' WHERE estado_envio = 'enviando' AND envio_iniciado_em <= ?",
      agora - PRAZO_ENVIANDO_MS,
    );
    this.banco.executar(
      `UPDATE desafios SET invalidado_em = criado_em + ?, motivo_invalidacao = 'reserva_abandonada'
        WHERE estado_envio IN ('pendente_reserva', 'reservado') AND invalidado_em IS NULL
          AND criado_em <= ?`,
      PRAZO_RESERVA_MS, agora - PRAZO_RESERVA_MS,
    );
  }

  private hashCodigo(id: string, finalidade: string, salt: string, codigo: string): string {
    return hmacHex(this.chaveHmac, "codigo", salt, finalidade, id, codigo);
  }

  private dadosAutorizacao(linha: LinhaDesafio): DadosAutorizacao {
    return {
      jti: linha.autorizacao_jti as string,
      finalidade: linha.finalidade,
      contexto: linha.contexto,
      validadoEm: linha.validado_em as number,
      expiraEm: linha.expira_em,
    };
  }
}
