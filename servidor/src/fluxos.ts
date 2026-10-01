// Orquestração dos pedidos e validações entre os objetos (IP, destino e teto
// global) e o enviador. Cada objeto é atômico por si; entre objetos, a ordem
// e as reservas sem devolução garantem que nunca se envia além dos limites e
// que um desafio sem reserva global registrada não autoriza.

import { REPETIR_APOS_S, type Finalidade } from "./config";
import type { Enviador } from "./envio/enviador";
import { montarMensagem } from "./envio/mensagens";
import { assinarAutorizacao } from "./nucleo/autorizacao";
import { hmacHex, sha256Hex } from "./nucleo/cripto";
import type {
  EstadoEnvio,
  PedidoDesafio,
  PedidoValidacao,
  ResultadoEnvio,
  ResultadoSolicitar,
  ResultadoValidar,
} from "./nucleo/desafios";
import { registrarFalha } from "./nucleo/registro";

export interface PortaDestino {
  solicitar(p: PedidoDesafio): Promise<ResultadoSolicitar>;
  registrarReserva(desafioId: string, reservaId: string, agora: number): Promise<boolean>;
  marcarSemReserva(desafioId: string, agora: number): Promise<boolean>;
  iniciarEnvio(desafioId: string, agora: number): Promise<boolean>;
  registrarResultado(desafioId: string, resultado: ResultadoEnvio, agora: number): Promise<EstadoEnvio | null>;
  validar(p: PedidoValidacao): Promise<ResultadoValidar>;
}

export interface PortaIp {
  reservarPedido(agora: number): Promise<boolean>;
  reservarValidacao(agora: number): Promise<boolean>;
}

export interface PortaTetoGlobal {
  esgotado(agora: number): Promise<boolean>;
  reservar(agora: number): Promise<string | null>;
}

export interface Segredos {
  chaveHmac: Uint8Array;
  chaveAssinatura: Uint8Array;
  kid: string;
}

export interface Dependencias {
  segredos: Segredos | null;
  destino(emailHash: string): PortaDestino;
  ip(ipHash: string): PortaIp;
  tetoGlobal(): PortaTetoGlobal;
  enviador: Enviador;
  relogio(): number;
  /** Mantém uma tarefa viva depois da resposta (ctx.waitUntil no Worker). */
  emSegundoPlano(tarefa: Promise<unknown>): void;
}

export interface Resposta {
  status: number;
  corpo: Record<string, unknown>;
  cabecalhos?: Record<string, string>;
}

const iso = (ms: number) => new Date(ms).toISOString();

export function normalizarEmail(email: string): string {
  return email.trim().toLowerCase();
}

/** Os 8 grupos de um IPv6 (com um IPv4 final convertido em dois grupos), ou null. */
function gruposIpv6(ip: string): number[] | null {
  let texto = ip.trim().toLowerCase();
  const ipv4Final = /(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(texto);
  if (ipv4Final) {
    const b = ipv4Final.slice(1).map(Number);
    if (b.some((x) => x > 255)) return null;
    texto = texto.slice(0, ipv4Final.index) + `${((b[0] << 8) | b[1]).toString(16)}:${((b[2] << 8) | b[3]).toString(16)}`;
  }
  const partes = texto.split("::");
  if (partes.length > 2) return null;
  const esquerda = partes[0] ? partes[0].split(":") : [];
  const direita = partes.length === 2 && partes[1] ? partes[1].split(":") : [];
  const faltam = 8 - esquerda.length - direita.length;
  if (partes.length === 1 ? faltam !== 0 : faltam < 1) return null;
  const grupos = [...esquerda, ...Array(partes.length === 2 ? faltam : 0).fill("0"), ...direita];
  if (!grupos.every((g) => /^[0-9a-f]{1,4}$/.test(g))) return null;
  return grupos.map((g) => parseInt(g, 16));
}

/**
 * Chave de limite por IP: IPv4 inteiro (inclusive quando vem representado em
 * IPv6, ::ffff:a.b.c.d); IPv6 agrupado pelo prefixo /64.
 */
export function prefixoIp(ip: string): string {
  if (!ip.includes(":")) return ip.trim();
  const g = gruposIpv6(ip);
  if (!g) return `invalido:${ip.trim().toLowerCase()}`;
  if (g.slice(0, 5).every((x) => x === 0) && g[5] === 0xffff) {
    return [g[6] >> 8, g[6] & 0xff, g[7] >> 8, g[7] & 0xff].join(".");
  }
  return g.slice(0, 4).map((x) => x.toString(16)).join(":") + "::/64";
}

const INDISPONIVEL: Resposta = { status: 503, corpo: { erro: "servico_indisponivel" } };

export interface EntradaPedido {
  finalidade: Finalidade;
  email: string;
  contexto: string;
  segredo: string;
  chave: string;
  semEnvio: boolean;
  ip: string;
}

export async function pedirDesafio(deps: Dependencias, e: EntradaPedido): Promise<Resposta> {
  const segredos = deps.segredos;
  if (!segredos) return INDISPONIVEL;
  const agora = deps.relogio();
  const emailHash = hmacHex(segredos.chaveHmac, "email", normalizarEmail(e.email));
  const ipHash = hmacHex(segredos.chaveHmac, "ip", prefixoIp(e.ip));

  if (!(await deps.ip(ipHash).reservarPedido(agora))) {
    return { status: 429, corpo: { erro: "limite_excedido" } };
  }
  // O estado do teto vale também para pedidos sem envio (neutralidade).
  const teto = deps.tetoGlobal();
  if (await teto.esgotado(agora)) return INDISPONIVEL;

  const destino = deps.destino(emailHash);
  const r = await destino.solicitar({
    finalidade: e.finalidade,
    contexto: e.contexto,
    segredoHash: sha256Hex(e.segredo),
    chaveHash: sha256Hex(e.chave),
    semEnvio: e.semEnvio,
    agora,
  });

  if (r.tipo === "conflito") return { status: 409, corpo: { erro: "conflito_idempotencia" } };
  if (r.tipo === "limite") return { status: 429, corpo: { erro: "limite_excedido" } };
  if (r.tipo === "aguarde") {
    return { status: 429, corpo: { erro: "aguarde", reenvio_permitido_em: iso(r.reenvioEm), agora: iso(agora) } };
  }

  const corpo = {
    desafio_id: r.desafioId,
    expira_em: iso(r.expiraEm),
    reenvio_permitido_em: iso(r.reenvioEm),
    agora: iso(agora),
  };

  const falhaEnvio: Resposta = {
    status: 502,
    corpo: { erro: "falha_envio", reenvio_permitido_em: corpo.reenvio_permitido_em, agora: corpo.agora },
  };

  if (e.finalidade === "recuperacao_senha") {
    // Neutralidade: a repetição só distingue ativo de encerrado, nunca o motivo
    // (um pedido sem envio nunca falha no envio; um real pode falhar).
    if (r.tipo === "repeticao") return r.encerrado ? ENCERRADO : { status: 202, corpo };
    // Resposta neutra e imediata; o envio (se houver) acontece depois.
    if (r.codigo !== null) {
      deps.emSegundoPlano(executarEnvio(deps, destino, r.desafioId, e.finalidade, e.email.trim(), r.codigo));
    }
    return { status: 202, corpo };
  }

  // Cadastro e alteração.
  if (r.tipo === "repeticao") {
    if (r.encerrado) {
      if (r.motivoInvalidacao === "falha_envio" || r.motivoInvalidacao === "reserva_abandonada") return falhaEnvio;
      if (r.motivoInvalidacao === "sem_reserva") return INDISPONIVEL;
      return ENCERRADO;
    }
    if (r.estadoEnvio === "pendente_reserva" || r.estadoEnvio === "reservado") {
      // A execução original ainda está reservando a vaga: repetir a MESMA
      // requisição (mesma Idempotency-Key) depois de Retry-After.
      return {
        status: 202,
        corpo: { estado: "em_processamento", ...corpo },
        cabecalhos: { "Retry-After": String(REPETIR_APOS_S) },
      };
    }
    return statusDoEnvio(r.estadoEnvio, corpo, falhaEnvio);
  }

  // O envio é aguardado para informar falhas.
  const estado = await executarEnvio(deps, destino, r.desafioId, e.finalidade, e.email.trim(), r.codigo as string);
  return statusDoEnvio(estado, corpo, falhaEnvio);
}

const ENCERRADO: Resposta = { status: 410, corpo: { erro: "desafio_encerrado" } };

function statusDoEnvio(
  estado: EstadoEnvio | "nao_iniciado",
  corpo: Record<string, unknown>,
  falhaEnvio: Resposta,
): Resposta {
  if (estado === "enviando" || estado === "enviado" || estado === "incerto") return { status: 201, corpo };
  if (estado === "sem_reserva") return INDISPONIVEL;
  return falhaEnvio;
}

/**
 * Reserva a vaga global, registra-a no desafio e só então envia. Qualquer
 * falha entre objetos deixa o desafio sem autorização possível ou o envio
 * como "incerto" (convertido pelo alarme); nunca envia sem reserva.
 */
export async function executarEnvio(
  deps: Dependencias,
  destino: PortaDestino,
  desafioId: string,
  finalidade: Finalidade,
  para: string,
  codigo: string,
): Promise<EstadoEnvio | "nao_iniciado"> {
  let reserva: string | null;
  try {
    reserva = await deps.tetoGlobal().reservar(deps.relogio());
  } catch (erro) {
    registrarFalha("reserva global", erro);
    return "nao_iniciado";
  }
  if (reserva === null) {
    try {
      await destino.marcarSemReserva(desafioId, deps.relogio());
    } catch (erro) {
      // O desafio continua sem reserva registrada: não autoriza de qualquer forma.
      registrarFalha("invalidação sem reserva", erro);
    }
    return "sem_reserva";
  }

  try {
    if (!(await destino.registrarReserva(desafioId, reserva, deps.relogio()))) return "nao_iniciado";
    if (!(await destino.iniciarEnvio(desafioId, deps.relogio()))) return "nao_iniciado";
  } catch (erro) {
    registrarFalha("registro da reserva", erro);
    return "nao_iniciado";
  }

  let resultado: ResultadoEnvio;
  try {
    const r = await deps.enviador.enviar(montarMensagem(finalidade, para, codigo), `sino/${finalidade}/${desafioId}`);
    resultado = r.tipo === "aceito" ? "enviado" : r.tipo === "incerto" ? "incerto" : "falhou";
  } catch (erro) {
    registrarFalha("envio", erro);
    resultado = "incerto";
  }

  try {
    return (await destino.registrarResultado(desafioId, resultado, deps.relogio())) ?? resultado;
  } catch (erro) {
    // O alarme do objeto converte o envio abandonado em "incerto".
    registrarFalha("registro do resultado do envio", erro);
    return "enviando";
  }
}

export interface EntradaValidacao {
  desafioId: string;
  email: string;
  segredo: string;
  chave: string;
  codigo: string;
  ip: string;
}

export async function validarDesafio(deps: Dependencias, e: EntradaValidacao): Promise<Resposta> {
  const segredos = deps.segredos;
  if (!segredos) return INDISPONIVEL;
  const agora = deps.relogio();
  const ipHash = hmacHex(segredos.chaveHmac, "ip", prefixoIp(e.ip));
  if (!(await deps.ip(ipHash).reservarValidacao(agora))) {
    return { status: 429, corpo: { erro: "limite_excedido" } };
  }

  const emailHash = hmacHex(segredos.chaveHmac, "email", normalizarEmail(e.email));
  const r = await deps.destino(emailHash).validar({
    desafioId: e.desafioId,
    segredoHash: sha256Hex(e.segredo),
    chaveHash: sha256Hex(e.chave),
    codigo: e.codigo,
    agora,
  });

  switch (r.tipo) {
    case "autorizado":
      return {
        status: 200,
        corpo: {
          autorizacao: assinarAutorizacao(r.dados, segredos.kid, segredos.chaveAssinatura),
          expira_em: iso(r.dados.expiraEm),
          agora: iso(agora),
        },
      };
    case "codigo_invalido":
      return { status: 422, corpo: { erro: "codigo_invalido", tentativas_restantes: r.tentativasRestantes } };
    case "encerrado":
      return { status: 410, corpo: { erro: "desafio_encerrado" } };
    case "conflito":
      return { status: 409, corpo: { erro: "conflito_idempotencia" } };
    case "nao_encontrado":
      return { status: 404, corpo: { erro: "desafio_nao_encontrado" } };
  }
}
