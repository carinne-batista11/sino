// Vetores de assinatura e transcrições do contrato v1, compartilhados com o
// cliente Python (tests/test_conformidade_servico.py e
// tests/test_autorizacao_servico.py). O teste falha se o servidor deixar de
// produzir exatamente o que está versionado em servidor/test/conformidade/.
// Para regenerar depois de uma mudança intencional do contrato:
//   SINO_ATUALIZAR_CONFORMIDADE=1 npx vitest run --project nucleo conformidade

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { ed25519 } from "@noble/curves/ed25519.js";
import { bytesToHex, hexToBytes, utf8ToBytes } from "@noble/hashes/utils.js";
import { describe, expect, it } from "vitest";
import { INTERVALO_REENVIO_MS, TETO_GLOBAL_DIA } from "../../src/config";
import { emailValido, normalizarEmail } from "../../src/email";
import { criarApp } from "../../src/http";
import {
  PREFIXO_ASSINATURA,
  assinarAutorizacao,
  chavePublicaDe,
  verificarAutorizacao,
} from "../../src/nucleo/autorizacao";
import { paraBase64Url, sha256Hex } from "../../src/nucleo/cripto";
import type { DadosAutorizacao } from "../../src/nucleo/desafios";
import { CHAVE_ASSINATURA, KID, Mundo } from "./apoio";

const ATUALIZAR = process.env.SINO_ATUALIZAR_CONFORMIDADE === "1";

function conferirArquivo(nome: string, dados: unknown): void {
  const caminho = fileURLToPath(new URL(`../conformidade/${nome}`, import.meta.url));
  const texto = `${JSON.stringify(dados, null, 2)}\n`;
  if (ATUALIZAR) writeFileSync(caminho, texto);
  expect(readFileSync(caminho, "utf8")).toBe(texto);
}

/** Assina um conteúdo JSON arbitrário (para vetores malformados porém assinados). */
function assinarBruto(json: string, chave: Uint8Array = CHAVE_ASSINATURA): string {
  const payload = paraBase64Url(utf8ToBytes(json));
  return `${payload}.${paraBase64Url(ed25519.sign(utf8ToBytes(PREFIXO_ASSINATURA + payload), chave))}`;
}

// ------------------------------------------------------------------ vetores

const DADOS: DadosAutorizacao = {
  jti: "dmV0b3ItZGUtdGVzdGUtMQ",
  finalidade: "recuperacao_senha",
  contexto: sha256Hex("vetor-de-contexto"),
  validadoEm: Date.UTC(2026, 9, 1, 12, 3, 4, 567),
  expiraEm: Date.UTC(2026, 9, 1, 12, 10, 0, 999),
};

function vetores() {
  const valido = assinarAutorizacao(DADOS, KID, CHAVE_ASSINATURA);
  const [payload, assinatura] = valido.split(".");
  const conteudo = (o: Record<string, unknown>) => JSON.stringify(o);
  const base = {
    v: 1, kid: KID, jti: DADOS.jti, fin: DADOS.finalidade, ctx: DADOS.contexto,
    iat: Math.floor(DADOS.validadoEm / 1000), exp: Math.floor(DADOS.expiraEm / 1000),
  };
  const outraChave = new Uint8Array(32).fill(0x33);
  // Último caractere da assinatura com bits de preenchimento não nulos: o
  // decodificador tolerante aceitaria, o estrito precisa recusar.
  const ultimo = assinatura.at(-1)!;
  const naoCanonico = `${payload}.${assinatura.slice(0, -1)}${ultimo === "A" ? "B" : ultimo === "B" ? "C" : "B"}`;
  return {
    descricao: "Vetores Ed25519 da autorização v1 (chave de teste, não é credencial).",
    kid: KID,
    chave_publica_hex: bytesToHex(chavePublicaDe(CHAVE_ASSINATURA)),
    valido: { token: valido, conteudo: base },
    invalidos: [
      { motivo: "conteudo_alterado", token: `${paraBase64Url(utf8ToBytes(conteudo({ ...base, fin: "cadastro" })))}.${assinatura}` },
      { motivo: "assinatura_de_outro_conteudo", token: `${payload}.${assinarBruto(conteudo({ ...base, jti: "b3V0cm8tanRpLWRlLXRlc3Rl" })).split(".")[1]}` },
      { motivo: "kid_desconhecido", token: assinarBruto(conteudo({ ...base, kid: "outro-kid" })) },
      { motivo: "chave_errada", token: assinarBruto(conteudo(base), outraChave) },
      { motivo: "assinatura_curta", token: `${payload}.${assinatura.slice(0, 40)}` },
      { motivo: "base64_nao_canonico", token: naoCanonico },
      { motivo: "chave_duplicada", token: assinarBruto(conteudo(base).replace('"v":1,', '"v":1,"v":1,')) },
      { motivo: "ordem_de_chaves", token: assinarBruto(JSON.stringify({ kid: KID, v: 1, jti: base.jti, fin: base.fin, ctx: base.ctx, iat: base.iat, exp: base.exp })) },
      { motivo: "chave_extra", token: assinarBruto(conteudo({ ...base, email: "x@y.z" })) },
      { motivo: "booleano_como_inteiro", token: assinarBruto(conteudo({ ...base, v: true })) },
      { motivo: "exp_fracionario", token: assinarBruto(conteudo(base).replace(`"exp":${base.exp}`, `"exp":${base.exp}.5`)) },
      { motivo: "finalidade_desconhecida", token: assinarBruto(conteudo({ ...base, fin: "login" })) },
      { motivo: "contexto_maiusculo", token: assinarBruto(conteudo({ ...base, ctx: base.ctx.toUpperCase() })) },
      { motivo: "formato", token: `${payload}.${assinatura}.extra` },
      // jti com bits de sobra não nulos (22 caracteres terminando em B).
      { motivo: "jti_nao_canonico", token: assinarBruto(conteudo({ ...base, jti: `${base.jti.slice(0, 21)}B` })) },
    ],
  };
}

describe("vetores de assinatura", () => {
  it("coincidem com o arquivo compartilhado e com o verificador de referência", () => {
    const v = vetores();
    const publicas = { [KID]: hexToBytes(v.chave_publica_hex) };
    expect(verificarAutorizacao(v.valido.token, publicas)).toEqual(v.valido.conteudo);
    for (const motivo of ["conteudo_alterado", "assinatura_de_outro_conteudo", "kid_desconhecido", "chave_errada"]) {
      const token = v.invalidos.find((i) => i.motivo === motivo)!.token;
      expect(verificarAutorizacao(token, publicas)).toBeNull();
    }
    conferirArquivo("autorizacao.json", v);
  });
});

// -------------------------------------------------------------- transcrições

/** Valores aleatórios de uma operação, como o cliente Python os sorteia. */
interface Aleatorios {
  nonce: string; // 32 bytes
  segredo: string; // 32 bytes
  chaves: string[]; // 18 bytes cada, na ordem em que o cliente as gera
}

function operacao(finalidade: string, email: string, a: Aleatorios) {
  const contexto = sha256Hex(`${finalidade}\x1f${email.trim().toLowerCase()}\x1f${a.nonce}`);
  return {
    contexto,
    segredo: paraBase64Url(hexToBytes(a.segredo)),
    chaves: a.chaves.map((c) => paraBase64Url(hexToBytes(c))),
  };
}

const hex = (rotulo: string, bytes: number) => sha256Hex(rotulo).slice(0, bytes * 2);
const aleatorios = (rotulo: string, chaves: number): Aleatorios => ({
  nonce: hex(`${rotulo}-nonce`, 32),
  segredo: hex(`${rotulo}-segredo`, 32),
  chaves: Array.from({ length: chaves }, (_, i) => hex(`${rotulo}-chave-${i}`, 18)),
});

type App = ReturnType<typeof criarApp>;

async function passo(app: App, caminho: string, chave: string, corpo: Record<string, unknown>) {
  const texto = JSON.stringify(corpo);
  const resposta = await app.fetch(
    new Request(`https://servico.teste${caminho}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": chave },
      body: texto,
    }),
  );
  return {
    requisicao: { metodo: "POST", caminho, idempotency_key: chave, corpo: texto },
    resposta: {
      status: resposta.status,
      content_type: resposta.headers.get("Content-Type"),
      retry_after: resposta.headers.get("Retry-After"),
      corpo: await resposta.text(),
    },
  };
}

const corpoPedido = (finalidade: string, email: string, op: ReturnType<typeof operacao>, semEnvio?: boolean) => ({
  finalidade, email, contexto: op.contexto, segredo: op.segredo, ...(semEnvio === undefined ? {} : { sem_envio: semEnvio }),
});
const corpoValidacao = (email: string, op: ReturnType<typeof operacao>, codigo: string) => ({
  email, segredo: op.segredo, codigo,
});
const idDe = (p: { resposta: { corpo: string } }) => JSON.parse(p.resposta.corpo).desafio_id as string;

async function transcricoes() {
  const EMAIL = "Pessoa@Exemplo.com";
  const cenarios: Record<string, unknown> = {};

  {
    const mundo = new Mundo();
    const app = criarApp(mundo.deps());
    const a = aleatorios("cadastro", 2);
    const op = operacao("cadastro", EMAIL, a);
    const p1 = await passo(app, "/v1/desafios", op.chaves[0], corpoPedido("cadastro", EMAIL, op));
    const codigo = mundo.enviador.ultimoCodigo(EMAIL)!;
    const p2 = await passo(app, `/v1/desafios/${idDe(p1)}/validacao`, op.chaves[1], corpoValidacao(EMAIL, op, codigo));
    cenarios.cadastro_validado = { finalidade: "cadastro", email: EMAIL, aleatorios: a, codigo, passos: [p1, p2] };
  }
  {
    const mundo = new Mundo();
    const app = criarApp(mundo.deps());
    const a = aleatorios("sem-envio", 2);
    const op = operacao("recuperacao_senha", EMAIL, a);
    const p1 = await passo(app, "/v1/desafios", op.chaves[0], corpoPedido("recuperacao_senha", EMAIL, op, true));
    const p2 = await passo(app, `/v1/desafios/${idDe(p1)}/validacao`, op.chaves[1], corpoValidacao(EMAIL, op, "000000"));
    cenarios.recuperacao_sem_envio = {
      finalidade: "recuperacao_senha", sem_envio: true, email: EMAIL, aleatorios: a, codigo: "000000", passos: [p1, p2],
    };
  }
  {
    const mundo = new Mundo();
    const app = criarApp(mundo.deps());
    const a = aleatorios("com-envio", 1);
    const op = operacao("recuperacao_senha", EMAIL, a);
    const p1 = await passo(app, "/v1/desafios", op.chaves[0], corpoPedido("recuperacao_senha", EMAIL, op, false));
    await mundo.concluirSegundoPlano();
    cenarios.recuperacao_com_envio = { finalidade: "recuperacao_senha", sem_envio: false, email: EMAIL, aleatorios: a, passos: [p1] };
  }
  {
    const mundo = new Mundo();
    const app = criarApp(mundo.deps());
    const a = aleatorios("aguarde", 2);
    const op = operacao("cadastro", EMAIL, a);
    const p1 = await passo(app, "/v1/desafios", op.chaves[0], corpoPedido("cadastro", EMAIL, op));
    const p2 = await passo(app, "/v1/desafios", op.chaves[1], corpoPedido("cadastro", EMAIL, op));
    cenarios.reenvio_antes_de_60s = { finalidade: "cadastro", email: EMAIL, aleatorios: a, passos: [p1, p2] };
  }
  {
    const mundo = new Mundo();
    let liberar = () => {};
    const portao = new Promise<void>((r) => (liberar = r));
    const deps = mundo.deps();
    deps.tetoGlobal = () => ({
      esgotado: async (x: number) => mundo.teto.esgotado(x),
      reservar: async (x: number) => {
        await portao;
        return mundo.teto.reservar(x);
      },
    });
    const app = criarApp(deps);
    const a = aleatorios("processamento", 1);
    const op = operacao("cadastro", EMAIL, a);
    const corpo = corpoPedido("cadastro", EMAIL, op);
    const primeira = passo(app, "/v1/desafios", op.chaves[0], corpo); // o cliente não recebe esta resposta
    await new Promise((r) => setImmediate(r));
    const p2 = await passo(app, "/v1/desafios", op.chaves[0], corpo);
    liberar();
    const p1 = await primeira;
    const p3 = await passo(app, "/v1/desafios", op.chaves[0], corpo);
    cenarios.em_processamento = {
      finalidade: "cadastro", email: EMAIL, aleatorios: a,
      passos: [{ requisicao: p1.requisicao, falha_conexao: true }, p2, p3],
    };
  }
  {
    const mundo = new Mundo();
    mundo.enviador.programar({ tipo: "falha" });
    const app = criarApp(mundo.deps());
    const a = aleatorios("falha", 1);
    const op = operacao("alteracao_email", EMAIL, a);
    const p1 = await passo(app, "/v1/desafios", op.chaves[0], corpoPedido("alteracao_email", EMAIL, op));
    cenarios.falha_envio = { finalidade: "alteracao_email", email: EMAIL, aleatorios: a, passos: [p1] };
  }
  {
    const mundo = new Mundo();
    for (let i = 0; i < TETO_GLOBAL_DIA; i++) mundo.teto.reservar(mundo.relogio.agora);
    const app = criarApp(mundo.deps());
    const a = aleatorios("teto", 1);
    const op = operacao("recuperacao_senha", EMAIL, a);
    const p1 = await passo(app, "/v1/desafios", op.chaves[0], corpoPedido("recuperacao_senha", EMAIL, op, false));
    cenarios.teto_global = { finalidade: "recuperacao_senha", sem_envio: false, email: EMAIL, aleatorios: a, passos: [p1] };
  }
  {
    // Outra instalação pede um código para o mesmo e-mail depois de 60 s:
    // o desafio desta operação é substituído e a validação recebe 410.
    const mundo = new Mundo();
    const app = criarApp(mundo.deps());
    const a = aleatorios("substituido", 2);
    const op = operacao("cadastro", EMAIL, a);
    const p1 = await passo(app, "/v1/desafios", op.chaves[0], corpoPedido("cadastro", EMAIL, op));
    const codigo = mundo.enviador.ultimoCodigo(EMAIL)!;
    mundo.relogio.avancar(INTERVALO_REENVIO_MS);
    const outra = operacao("cadastro", EMAIL, aleatorios("outra-instalacao", 1));
    await passo(app, "/v1/desafios", outra.chaves[0], corpoPedido("cadastro", EMAIL, outra));
    const p2 = await passo(app, `/v1/desafios/${idDe(p1)}/validacao`, op.chaves[1], corpoValidacao(EMAIL, op, codigo));
    cenarios.desafio_substituido = { finalidade: "cadastro", email: EMAIL, aleatorios: a, codigo, passos: [p1, p2] };
  }
  return {
    descricao: "Transcrições do contrato v1 geradas pelo servidor com relógio e aleatoriedade fixos.",
    kid: KID,
    chave_publica_hex: bytesToHex(chavePublicaDe(CHAVE_ASSINATURA)),
    cenarios,
  };
}

describe("transcrições do contrato", () => {
  it("coincidem com o arquivo compartilhado", async () => {
    conferirArquivo("transcricoes.json", await transcricoes());
  });
});

// ------------------------------------------------------------------ e-mails

const ENTRADAS_EMAIL = [
  "pessoa@exemplo.com",
  "  Pessoa@Exemplo.COM  ",
  "PESSOA+tag@Sub.Example.ORG",
  "a@b",
  `${"a".repeat(64)}@${"b".repeat(185)}.com`, // 254 caracteres
  `${"a".repeat(64)}@${"b".repeat(186)}.com`, // 255 caracteres
  ` ${"a".repeat(64)}@${"b".repeat(185)}.com `, // 254 depois de aparar
  "\"aspas\"@exemplo.com",
  "",
  "   ",
  "sem-arroba.exemplo.com",
  "a@@b",
  "a@b@c",
  "@exemplo.com",
  "pessoa@",
  "pes soa@exemplo.com",
  "josé@exemplo.com",
  "pessoa@exemplo.çom",
  "\u212Aelvin@exemplo.com", // K de Kelvin: minúscula Unicode viraria "k"
  "\u0130stanbul@exemplo.com",
  "pessoa@exemplo.com\u00a0", // espaço não separável na borda
  "\u3000pessoa@exemplo.com", // espaço ideográfico na borda
  "\tpessoa@exemplo.com",
  "pessoa@exemplo.com\n",
  "pessoa@exemplo.com\u001f",
  "\u001cpessoa@exemplo.com",
  "pessoa@exemplo.com\u007f",
];

describe("formato de e-mail compartilhado", () => {
  it("coincide com o arquivo compartilhado", () => {
    const casos = ENTRADAS_EMAIL.map((entrada) => {
      const valido = emailValido(entrada);
      return { entrada, valido, normalizado: valido ? normalizarEmail(entrada) : null };
    });
    expect(casos.filter((c) => c.valido).map((c) => c.normalizado)).toEqual([
      "pessoa@exemplo.com",
      "pessoa@exemplo.com",
      "pessoa+tag@sub.example.org",
      "a@b",
      `${"a".repeat(64)}@${"b".repeat(185)}.com`,
      `${"a".repeat(64)}@${"b".repeat(185)}.com`,
      "\"aspas\"@exemplo.com",
    ]);
    conferirArquivo("emails.json", {
      descricao: "Formato de e-mail dos fluxos com código: aparar só espaços U+0020 nas bordas; "
        + "ASCII imprimível, exatamente um @, partes não vazias, até 254; minúsculas ASCII.",
      casos,
    });
  });
});
