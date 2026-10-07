// Rotas HTTP do contrato v1.1 (docs/contrato-servico-codigos.md): validação
// estrita da entrada e respostas JSON sem dados sensíveis.

import { FINALIDADES, type Finalidade } from "./config";
import { emailValido } from "./email";
import { pedirDesafio, validarDesafio, type Dependencias, type Resposta } from "./fluxos";
import { ERRO_ESQUEMA_INCOMPATIVEL } from "./nucleo/desafios";
import { registrarFalha } from "./nucleo/registro";

const RE_CHAVE = /^[A-Za-z0-9_-]{16,128}$/;
const RE_SEGREDO = /^[A-Za-z0-9_-]{43}$/;
const RE_CONTEXTO = /^[0-9a-f]{64}$/;
const RE_CODIGO = /^\d{6}$/;
const RE_DESAFIO = /^[A-Za-z0-9_-]{22}$/;
const RE_ROTA_VALIDACAO = /^\/v1\/desafios\/([^/]+)\/validacao$/;
const TAMANHO_MAXIMO_CORPO = 4096;

export { emailValido };

function json(r: Resposta): Response {
  return new Response(JSON.stringify(r.corpo), {
    status: r.status,
    headers: { ...r.cabecalhos, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

const invalida = () => json({ status: 400, corpo: { erro: "requisicao_invalida" } });

const grandeDemais = () => json({ status: 413, corpo: { erro: "corpo_grande_demais" } });

/**
 * Lê no máximo TAMANHO_MAXIMO_CORPO bytes: recusa antecipada pelo
 * Content-Length e, com ou sem esse cabeçalho, interrompe a leitura assim que
 * o corpo efetivo passa do limite.
 */
export async function lerBytesLimitados(requisicao: Request, limite: number): Promise<Uint8Array | "grande" | null> {
  const declarado = requisicao.headers.get("Content-Length");
  if (declarado !== null) {
    if (!/^\d+$/.test(declarado)) return null;
    if (Number(declarado) > limite) return "grande";
  }
  if (!requisicao.body) return null;
  const leitor = requisicao.body.getReader();
  const partes: Uint8Array[] = [];
  let total = 0;
  for (;;) {
    const { done, value } = await leitor.read();
    if (done) break;
    total += value.byteLength;
    if (total > limite) {
      await leitor.cancel().catch(() => {});
      return "grande";
    }
    partes.push(value);
  }
  const bytes = new Uint8Array(total);
  let posicao = 0;
  for (const parte of partes) {
    bytes.set(parte, posicao);
    posicao += parte.byteLength;
  }
  return bytes;
}

async function lerCorpo(requisicao: Request): Promise<Record<string, unknown> | "grande" | null> {
  if (!(requisicao.headers.get("Content-Type") ?? "").toLowerCase().startsWith("application/json")) return null;
  const bytes = await lerBytesLimitados(requisicao, TAMANHO_MAXIMO_CORPO);
  if (bytes === null || bytes === "grande") return bytes;
  try {
    const corpo = JSON.parse(new TextDecoder("utf-8", { fatal: true, ignoreBOM: false }).decode(bytes));
    return corpo && typeof corpo === "object" && !Array.isArray(corpo) ? corpo : null;
  } catch {
    return null;
  }
}

export function criarApp(deps: Dependencias) {
  return {
    async fetch(requisicao: Request): Promise<Response> {
      try {
        return await rotear(deps, requisicao);
      } catch (erro) {
        registrarFalha("requisição", erro);
        // Estado local de versão anterior num objeto: serviço indisponível.
        if (erro instanceof Error && erro.message === ERRO_ESQUEMA_INCOMPATIVEL) {
          return json({ status: 503, corpo: { erro: "servico_indisponivel" } });
        }
        return json({ status: 500, corpo: { erro: "erro_interno" } });
      }
    },
  };
}

async function rotear(deps: Dependencias, requisicao: Request): Promise<Response> {
  const url = new URL(requisicao.url);
  const ip = requisicao.headers.get("CF-Connecting-IP") ?? "0.0.0.0";
  const chave = requisicao.headers.get("Idempotency-Key") ?? "";

  if (url.pathname === "/v1/desafios") {
    if (requisicao.method !== "POST") return json({ status: 405, corpo: { erro: "metodo_nao_permitido" } });
    const corpo = await lerCorpo(requisicao);
    if (corpo === "grande") return grandeDemais();
    if (!corpo || !RE_CHAVE.test(chave)) return invalida();
    const { finalidade, email, contexto, segredo } = corpo;
    const semEnvio = corpo.sem_envio ?? false;
    if (
      !FINALIDADES.includes(finalidade as Finalidade) ||
      !emailValido(email) ||
      typeof contexto !== "string" || !RE_CONTEXTO.test(contexto) ||
      typeof segredo !== "string" || !RE_SEGREDO.test(segredo) ||
      typeof semEnvio !== "boolean" ||
      (semEnvio && finalidade !== "recuperacao_senha")
    ) {
      return invalida();
    }
    return json(
      await pedirDesafio(deps, { finalidade: finalidade as Finalidade, email, contexto, segredo, chave, semEnvio, ip }),
    );
  }

  const rota = RE_ROTA_VALIDACAO.exec(url.pathname);
  if (rota) {
    if (requisicao.method !== "POST") return json({ status: 405, corpo: { erro: "metodo_nao_permitido" } });
    const corpo = await lerCorpo(requisicao);
    if (corpo === "grande") return grandeDemais();
    if (!corpo || !RE_CHAVE.test(chave) || !RE_DESAFIO.test(rota[1])) return invalida();
    const { email, segredo, codigo } = corpo;
    if (
      !emailValido(email) ||
      typeof segredo !== "string" || !RE_SEGREDO.test(segredo) ||
      typeof codigo !== "string" || !RE_CODIGO.test(codigo)
    ) {
      return invalida();
    }
    return json(await validarDesafio(deps, { desafioId: rota[1], email, segredo, chave, codigo, ip }));
  }

  return json({ status: 404, corpo: { erro: "rota_nao_encontrada" } });
}
