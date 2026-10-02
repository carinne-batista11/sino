// Enviador de DESENVOLVIMENTO: entrega a mensagem a um receptor local
// (ferramentas/caixa_dev.py), que a grava em arquivo na pasta da validação.
// Só é usado pela entrada src/dev.ts (wrangler.dev.jsonc); a entrada de
// produção (src/index.ts) não o importa.
//
// Resultado, no mesmo modelo do adaptador da Resend:
//   2xx do receptor     -> "aceito" (o receptor só responde 2xx depois de gravar);
//   outra resposta      -> "falha" (o receptor não gravou);
//   tempo esgotado      -> "incerto" (a mensagem pode ter sido gravada);
//   outra falha de rede -> "falha" (receptor fora do ar: nada foi entregue).
// Nunca registra código, e-mail, assunto ou corpo.

import { registrarEvento, registrarFalha } from "../nucleo/registro";
import type { Enviador, Mensagem, ResultadoEnviador } from "./enviador";

export const CAIXA_TEMPO_LIMITE_MS = 5_000;
export const CAIXA_ATRASO_MAXIMO_MS = 15_000;

const RE_URL_CAIXA = /^http:\/\/127\.0\.0\.1:([0-9]{1,5})$/;

/** Endereço do receptor: só `http://127.0.0.1:<porta>`; qualquer outro -> null. */
export function urlDaCaixaLocal(texto: string | undefined): string | null {
  const porta = RE_URL_CAIXA.exec(texto ?? "")?.[1];
  if (!porta || Number(porta) < 1 || Number(porta) > 65_535) return null;
  return `${texto}/mensagens`;
}

/** Atraso artificial antes de cada entrega (ms): vazio = 0; inválido -> null. */
export function atrasoDaCaixa(texto: string | undefined): number | null {
  if (texto === undefined || texto === "") return 0;
  if (!/^[0-9]{1,5}$/.test(texto)) return null;
  const ms = Number(texto);
  return ms <= CAIXA_ATRASO_MAXIMO_MS ? ms : null;
}

export interface OpcoesCaixaLocal {
  url: string;
  atrasoMs: number;
  fetch?: typeof fetch;
  /** Espera do atraso artificial; injetável para os testes não dormirem. */
  esperar?: (ms: number) => Promise<void>;
  tempoLimiteMs?: number;
}

const esperarDeVerdade = (ms: number) => new Promise<void>((resolver) => setTimeout(resolver, ms));

export class EnviadorCaixaLocal implements Enviador {
  private readonly fetch: typeof fetch;
  private readonly esperar: (ms: number) => Promise<void>;

  constructor(private readonly opcoes: OpcoesCaixaLocal) {
    this.fetch = opcoes.fetch ?? ((...a) => fetch(...a));
    this.esperar = opcoes.esperar ?? esperarDeVerdade;
  }

  async enviar(mensagem: Mensagem, chaveIdempotencia: string): Promise<ResultadoEnviador> {
    if (this.opcoes.atrasoMs > 0) await this.esperar(this.opcoes.atrasoMs);
    let resposta: Response;
    try {
      resposta = await this.fetch(this.opcoes.url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...mensagem, chave: chaveIdempotencia }),
        redirect: "manual",
        signal: AbortSignal.timeout(this.opcoes.tempoLimiteMs ?? CAIXA_TEMPO_LIMITE_MS),
      });
    } catch (erro) {
      registrarFalha("envio caixa local", erro);
      const tempoEsgotado = erro instanceof Error && (erro.name === "TimeoutError" || erro.name === "AbortError");
      return { tipo: tempoEsgotado ? "incerto" : "falha" };
    }
    await resposta.body?.cancel();
    if (resposta.status >= 200 && resposta.status < 300) return { tipo: "aceito" };
    registrarEvento(`caixa local recusou o envio (${resposta.status})`);
    return { tipo: "falha" };
  }
}
