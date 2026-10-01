// Adaptador da Resend (POST /emails). Idempotência conforme a documentação
// oficial: header Idempotency-Key, janela de 24 h, mesma chave + mesmo
// conteúdo devolve o e-mail original sem reenviar.
//
// O corpo é serializado uma única vez e repetido byte a byte, só dentro desta
// execução. A chave nunca é trocada para forçar um envio.
//
// Classificação (https://resend.com/docs/api-reference/errors):
//   repetir  - falha de rede/tempo esgotado; 409 concurrent_idempotent_requests
//              e resource_locked; 429 rate_limit_exceeded; 500 application_error
//              e 503 service_unavailable ("try the request again later");
//   parar    - 429 daily_quota_exceeded/monthly_quota_exceeded (cota esgotada);
//              409 invalid_idempotent_request (conteúdo diferente: não muda a
//              chave); outros 5xx não documentados; 4xx de validação/permissão.
// Resultado: "aceito"; "incerto" se ALGUMA tentativa pode ter sido aceita
// (rede/tempo, 5xx, 409 de idempotência) - uma recusa posterior não apaga essa
// incerteza; "falha" só quando nenhuma tentativa pode ter sido aceita.

import { RESEND_ESPERAS_MS, RESEND_TEMPO_LIMITE_MS, RESEND_TENTATIVAS, RESEND_URL } from "../config";
import { registrarEvento, registrarFalha } from "../nucleo/registro";
import type { Enviador, Mensagem, ResultadoEnviador } from "./enviador";

export interface OpcoesResend {
  apiKey: string;
  remetente: string;
  fetch?: typeof fetch;
  /** Espera entre tentativas; injetável para os testes não dormirem. */
  esperar?: (ms: number) => Promise<void>;
  tentativas?: number;
  tempoLimiteMs?: number;
}

const esperarDeVerdade = (ms: number) => new Promise<void>((resolver) => setTimeout(resolver, ms));

// Só nomes conhecidos vão para o registro; qualquer outro texto do provedor
// é descartado.
const CODIGOS_CONHECIDOS = new Set([
  "concurrent_idempotent_requests",
  "invalid_idempotent_request",
  "resource_locked",
  "rate_limit_exceeded",
  "daily_quota_exceeded",
  "monthly_quota_exceeded",
  "application_error",
  "service_unavailable",
  "validation_error",
  "missing_required_field",
  "invalid_from_address",
  "invalid_api_key",
  "restricted_api_key",
  "missing_api_key",
  "invalid_idempotency_key",
]);

async function codigoDoErro(resposta: Response): Promise<string | null> {
  try {
    const corpo = (await resposta.json()) as { name?: unknown };
    return typeof corpo?.name === "string" && CODIGOS_CONHECIDOS.has(corpo.name) ? corpo.name : null;
  } catch {
    return null;
  }
}

type Decisao = "repetir" | "repetir_incerto" | "parar" | "parar_incerto";

export function classificar(status: number, codigo: string | null): Decisao {
  if (status === 409) {
    if (codigo === "concurrent_idempotent_requests" || codigo === "resource_locked") return "repetir_incerto";
    // invalid_idempotent_request ou 409 desconhecido: a chave já foi usada por
    // outra requisição que pode ter enviado; não repetir nem trocar a chave.
    return "parar_incerto";
  }
  if (status === 429) {
    if (codigo === "daily_quota_exceeded" || codigo === "monthly_quota_exceeded") return "parar";
    return "repetir";
  }
  if (status === 500 || status === 503) return "repetir_incerto";
  if (status >= 500) return "parar_incerto";
  return "parar";
}

export class EnviadorResend implements Enviador {
  private readonly fetch: typeof fetch;
  private readonly esperar: (ms: number) => Promise<void>;
  private readonly tentativas: number;
  private readonly tempoLimiteMs: number;

  constructor(private readonly opcoes: OpcoesResend) {
    this.fetch = opcoes.fetch ?? ((...a) => fetch(...a));
    this.esperar = opcoes.esperar ?? esperarDeVerdade;
    this.tentativas = opcoes.tentativas ?? RESEND_TENTATIVAS;
    this.tempoLimiteMs = opcoes.tempoLimiteMs ?? RESEND_TEMPO_LIMITE_MS;
  }

  async enviar(mensagem: Mensagem, chaveIdempotencia: string): Promise<ResultadoEnviador> {
    const corpo = JSON.stringify({
      from: this.opcoes.remetente,
      to: [mensagem.para],
      subject: mensagem.assunto,
      text: mensagem.texto,
    });
    const cabecalhos = {
      Authorization: `Bearer ${this.opcoes.apiKey}`,
      "Content-Type": "application/json",
      "Idempotency-Key": chaveIdempotencia,
    };

    // Alguma tentativa pode ter sido aceita sem que soubéssemos?
    let incerto = false;
    const resultado = (): ResultadoEnviador => (incerto ? { tipo: "incerto" } : { tipo: "falha" });

    for (let i = 0; i < this.tentativas; i++) {
      if (i > 0) await this.esperar(RESEND_ESPERAS_MS[Math.min(i - 1, RESEND_ESPERAS_MS.length - 1)]);

      let resposta: Response;
      try {
        resposta = await this.fetch(RESEND_URL, {
          method: "POST",
          headers: cabecalhos,
          body: corpo,
          signal: AbortSignal.timeout(this.tempoLimiteMs),
        });
      } catch (erro) {
        // Tempo esgotado ou rede: a requisição pode ter sido aceita.
        registrarFalha("envio Resend", erro);
        incerto = true;
        continue;
      }

      if (resposta.ok) return { tipo: "aceito" };
      const codigo = await codigoDoErro(resposta);

      switch (classificar(resposta.status, codigo)) {
        case "repetir_incerto":
          registrarEvento(`Resend respondeu ${resposta.status}${codigo ? ` (${codigo})` : ""}; repetindo`);
          incerto = true;
          continue;
        case "repetir":
          registrarEvento(`Resend respondeu ${resposta.status}${codigo ? ` (${codigo})` : ""}; repetindo`);
          continue;
        case "parar_incerto":
          registrarEvento(`Resend respondeu ${resposta.status}${codigo ? ` (${codigo})` : ""}; resultado incerto`);
          incerto = true;
          return resultado();
        case "parar":
          registrarEvento(`Resend recusou o envio (${resposta.status}${codigo ? `, ${codigo}` : ""})`);
          return resultado();
      }
    }
    return resultado();
  }
}
