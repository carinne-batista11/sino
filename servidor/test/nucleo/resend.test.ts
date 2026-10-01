// Adaptador da Resend contra uma API simulada que reproduz a idempotência
// documentada: mesma chave + mesmo conteúdo devolve o e-mail original sem
// reenviar; conteúdo diferente -> 409 invalid_idempotent_request.

import { afterEach, describe, expect, it } from "vitest";
import { RESEND_URL } from "../../src/config";
import { montarMensagem } from "../../src/envio/mensagens";
import { EnviadorResend } from "../../src/envio/resend";
import { capturarRegistros } from "./apoio";

const API_KEY = "re_chave_que_nao_pode_vazar";
const PARA = "Pessoa.Teste@exemplo.com";
const CODIGO = "042137";
const CHAVE = "sino/cadastro/desafio-1";

type Passo =
  | "aceitar"
  | "aceitar_e_perder_resposta"
  | "falha_rede"
  | { status: number; name?: string };

/** API Resend simulada: registra entregas e respeita a idempotência. */
class ResendSimulada {
  readonly chamadas: { corpo: string; chave: string | null; autorizacao: string | null; url: string }[] = [];
  readonly entregas: string[] = [];
  private readonly porChave = new Map<string, { corpo: string; id: string }>();

  constructor(private readonly roteiro: Passo[]) {}

  readonly fetch = (async (url: RequestInfo | URL, init?: RequestInit) => {
    const corpo = String(init?.body);
    const cabecalhos = new Headers(init?.headers);
    const chave = cabecalhos.get("Idempotency-Key");
    this.chamadas.push({ corpo, chave, autorizacao: cabecalhos.get("Authorization"), url: String(url) });
    const passo = this.roteiro.shift() ?? "aceitar";

    if (passo === "falha_rede") throw new TypeError("network");
    if (typeof passo === "object") {
      return new Response(JSON.stringify({ name: passo.name ?? "erro", message: "detalhe" }), { status: passo.status });
    }
    // Idempotência documentada.
    const anterior = chave ? this.porChave.get(chave) : undefined;
    if (anterior && anterior.corpo !== corpo) {
      return new Response(JSON.stringify({ name: "invalid_idempotent_request" }), { status: 409 });
    }
    let id = anterior?.id;
    if (!id) {
      id = `email-${this.entregas.length + 1}`;
      this.entregas.push(corpo);
      if (chave) this.porChave.set(chave, { corpo, id });
    }
    if (passo === "aceitar_e_perder_resposta") {
      throw new DOMException("The operation was aborted due to timeout", "TimeoutError");
    }
    return new Response(JSON.stringify({ id }), { status: 200 });
  }) as typeof fetch;
}

function enviador(api: ResendSimulada, esperas: number[] = []) {
  return new EnviadorResend({
    apiKey: API_KEY,
    remetente: "Sino <onboarding@resend.dev>",
    fetch: api.fetch,
    esperar: async (ms) => void esperas.push(ms),
  });
}

const mensagem = montarMensagem("cadastro", PARA, CODIGO);

let registros = capturarRegistros();
afterEach(() => {
  const juntos = registros.linhas.join("\n");
  for (const proibido of [API_KEY, PARA, PARA.toLowerCase(), CODIGO, "detalhe"]) expect(juntos).not.toContain(proibido);
  registros.restaurar();
  registros = capturarRegistros();
});

describe("EnviadorResend", () => {
  it("envia uma vez, só texto, com a chave de idempotência e o remetente Sino", async () => {
    const api = new ResendSimulada(["aceitar"]);
    expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "aceito" });
    expect(api.chamadas).toHaveLength(1);
    const c = api.chamadas[0];
    expect(c.url).toBe(RESEND_URL);
    expect(c.chave).toBe(CHAVE);
    expect(c.autorizacao).toBe(`Bearer ${API_KEY}`);
    const corpo = JSON.parse(c.corpo);
    expect(Object.keys(corpo).sort()).toEqual(["from", "subject", "text", "to"]);
    expect(corpo.from).toBe("Sino <onboarding@resend.dev>");
    expect(corpo.to).toEqual([PARA]);
    expect(corpo.subject).toBe("Código para confirmar seu e-mail no Sino");
    expect(corpo.subject).not.toContain(CODIGO);
    expect(corpo.text).toContain(`\n\n${CODIGO}\n\n`);
    expect(corpo.text).not.toMatch(/https?:|www\./);
  });

  it("resposta perdida após o aceite: repete com a mesma chave e o mesmo corpo, sem duplicar", async () => {
    const api = new ResendSimulada(["aceitar_e_perder_resposta", "aceitar"]);
    const esperas: number[] = [];
    expect(await enviador(api, esperas).enviar(mensagem, CHAVE)).toEqual({ tipo: "aceito" });
    expect(api.entregas).toHaveLength(1);
    expect(api.chamadas).toHaveLength(2);
    expect(api.chamadas[1].corpo).toBe(api.chamadas[0].corpo);
    expect(api.chamadas.map((c) => c.chave)).toEqual([CHAVE, CHAVE]);
    expect(esperas).toEqual([500]);
  });

  it("todas as respostas perdidas: resultado incerto, nunca com outra chave", async () => {
    const api = new ResendSimulada(["aceitar_e_perder_resposta", "aceitar_e_perder_resposta", "aceitar_e_perder_resposta"]);
    expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "incerto" });
    expect(api.entregas).toHaveLength(1);
    expect(new Set(api.chamadas.map((c) => c.chave))).toEqual(new Set([CHAVE]));
  });

  it("409 concurrent_idempotent_requests é repetido", async () => {
    const api = new ResendSimulada([{ status: 409, name: "concurrent_idempotent_requests" }, "aceitar"]);
    expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "aceito" });
    expect(api.chamadas).toHaveLength(2);
  });

  it("409 invalid_idempotent_request não é repetido nem troca a chave: incerto", async () => {
    const api = new ResendSimulada([{ status: 409, name: "invalid_idempotent_request" }]);
    expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "incerto" });
    expect(api.chamadas).toHaveLength(1);
  });

  it("429 é repetido; esgotadas as tentativas só com 429, é falha (nada foi aceito)", async () => {
    const ok = new ResendSimulada([{ status: 429, name: "rate_limit_exceeded" }, "aceitar"]);
    expect(await enviador(ok).enviar(mensagem, CHAVE)).toEqual({ tipo: "aceito" });
    const falha = new ResendSimulada([{ status: 429 }, { status: 429 }, { status: 429 }]);
    const esperas: number[] = [];
    expect(await enviador(falha, esperas).enviar(mensagem, CHAVE)).toEqual({ tipo: "falha" });
    expect(falha.chamadas).toHaveLength(3);
    expect(esperas).toEqual([500, 1000]);
  });

  it("5xx e falha de rede são repetidos; esgotados, o resultado é incerto", async () => {
    const ok = new ResendSimulada([{ status: 500 }, "aceitar"]);
    expect(await enviador(ok).enviar(mensagem, CHAVE)).toEqual({ tipo: "aceito" });
    const incerto = new ResendSimulada([{ status: 503 }, "falha_rede", { status: 503 }]);
    expect(await enviador(incerto).enviar(mensagem, CHAVE)).toEqual({ tipo: "incerto" });
  });

  it("cota diária ou mensal esgotada não é repetida: falha definitiva", async () => {
    for (const name of ["daily_quota_exceeded", "monthly_quota_exceeded"]) {
      const api = new ResendSimulada([{ status: 429, name }]);
      expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "falha" });
      expect(api.chamadas).toHaveLength(1);
    }
  });

  it("cota esgotada depois de uma tentativa incerta mantém o resultado incerto", async () => {
    const api = new ResendSimulada(["aceitar_e_perder_resposta", { status: 429, name: "daily_quota_exceeded" }]);
    expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "incerto" });
    expect(api.chamadas).toHaveLength(2);
    expect(api.entregas).toHaveLength(1);
  });

  it("409 resource_locked é repetido após a espera", async () => {
    const esperas: number[] = [];
    const api = new ResendSimulada([{ status: 409, name: "resource_locked" }, "aceitar"]);
    expect(await enviador(api, esperas).enviar(mensagem, CHAVE)).toEqual({ tipo: "aceito" });
    expect(esperas).toEqual([500]);
  });

  it("409 desconhecido não é repetido e fica incerto", async () => {
    const api = new ResendSimulada([{ status: 409, name: "outro_conflito" }]);
    expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "incerto" });
    expect(api.chamadas).toHaveLength(1);
  });

  it("só 500 e 503 são repetidos; outros 5xx param como incertos", async () => {
    const quinhentos = new ResendSimulada([{ status: 500, name: "application_error" }, "aceitar"]);
    expect(await enviador(quinhentos).enviar(mensagem, CHAVE)).toEqual({ tipo: "aceito" });
    for (const status of [502, 504]) {
      const api = new ResendSimulada([{ status }]);
      expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "incerto" });
      expect(api.chamadas).toHaveLength(1);
    }
  });

  it("recusa definitiva depois de 5xx mantém a incerteza da tentativa anterior", async () => {
    const api = new ResendSimulada([{ status: 503, name: "service_unavailable" }, { status: 422, name: "validation_error" }]);
    expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "incerto" });
  });

  it("nomes de erro desconhecidos do provedor não vão para o registro", async () => {
    const api = new ResendSimulada([{ status: 400, name: "texto_livre_do_provedor" }]);
    await enviador(api).enviar(mensagem, CHAVE);
    expect(registros.linhas.join("\n")).not.toContain("texto_livre_do_provedor");
    expect(registros.linhas.join("\n")).toContain("Resend recusou o envio (400)");
  });

  it("400/401/403/422 são definitivos e não são repetidos", async () => {
    for (const status of [400, 401, 403, 422]) {
      const api = new ResendSimulada([{ status }]);
      expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "falha" });
      expect(api.chamadas).toHaveLength(1);
    }
  });

  it("recusa definitiva depois de uma tentativa incerta continua incerta", async () => {
    const api = new ResendSimulada(["falha_rede", { status: 401 }]);
    expect(await enviador(api).enviar(mensagem, CHAVE)).toEqual({ tipo: "incerto" });
  });
});

describe("textos aprovados", () => {
  it("três finalidades, sem código no assunto, sem links, com rodapé", () => {
    const assuntos = {
      cadastro: "Código para confirmar seu e-mail no Sino",
      alteracao_email: "Código para confirmar seu novo e-mail no Sino",
      recuperacao_senha: "Código para redefinir sua senha do Sino",
    } as const;
    for (const [finalidade, assunto] of Object.entries(assuntos)) {
      const m = montarMensagem(finalidade as keyof typeof assuntos, PARA, CODIGO);
      expect(m.assunto).toBe(assunto);
      expect(m.texto).toContain("O código vale por 10 minutos e só pode ser usado uma vez.");
      expect(m.texto).toContain("Esta é uma mensagem automática do Sino; não é necessário respondê-la.");
      expect(m.texto).not.toMatch(/https?:|www\./);
    }
    expect(montarMensagem("recuperacao_senha", PARA, CODIGO).texto).toContain("Sua senha continua a mesma.");
  });
});
