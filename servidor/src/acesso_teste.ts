// Autenticação do AMBIENTE REMOTO DE TESTES (src/teste.ts): toda requisição
// precisa de `Authorization: Bearer <TOKEN_TESTE>`. A conferência acontece
// antes de ler o corpo e de tocar nos Durable Objects; sem o token certo (ou
// com o segredo ausente ou malformado) a resposta é a mesma 404 de uma rota
// inexistente, sem revelar o serviço. O token nunca é registrado.

import { iguaisTempoConstante } from "./nucleo/cripto";
import { registrarEvento } from "./nucleo/registro";

/** 32 bytes aleatórios em base64url, sem preenchimento. */
const RE_TOKEN = /^[A-Za-z0-9_-]{43}$/;

export function tokenDeTeste(texto: string | undefined): string | null {
  return texto !== undefined && RE_TOKEN.test(texto) ? texto : null;
}

function naoEncontrada(): Response {
  return new Response(JSON.stringify({ erro: "rota_nao_encontrada" }), {
    status: 404,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}

export function autorizada(requisicao: Request, token: string | null): boolean {
  if (token === null) return false;
  return iguaisTempoConstante(requisicao.headers.get("Authorization") ?? "", `Bearer ${token}`);
}

/**
 * Envolve o aplicativo: `criar` só é chamado (e os objetos só são tocados)
 * quando o token confere.
 */
export async function comToken(
  requisicao: Request,
  textoDoToken: string | undefined,
  criar: () => { fetch(requisicao: Request): Promise<Response> },
): Promise<Response> {
  const token = tokenDeTeste(textoDoToken);
  if (token === null) registrarEvento("token do ambiente de teste ausente ou inválido; respondendo 404");
  if (!autorizada(requisicao, token)) return naoEncontrada();
  return criar().fetch(requisicao);
}
