import { cloudflareTest } from "@cloudflare/vitest-pool-workers";
import { defineConfig } from "vitest/config";
import { createHmac } from "node:crypto";

// Valores fixos apenas para os testes: não são credenciais e não valem fora
// do simulador local. Os destinatários são endereços de exemplo dos testes;
// a lista segue o formato de src/nucleo/destinatarios.ts (os testes do
// simulador falham com 503 se ela não for aceita).
const CHAVE_HMAC_DE_TESTE = "11".repeat(32);
const hmac = (texto: string) => createHmac("sha256", Buffer.from(CHAVE_HMAC_DE_TESTE, "hex")).update(texto).digest("hex");
const DESTINATARIOS_DE_TESTE = ["x@exemplo.com", "teto@exemplo.com", "reserva@exemplo.com", "ninguem@exemplo.com"];
const VARIAVEIS_DE_TESTE = {
  CHAVE_HMAC: CHAVE_HMAC_DE_TESTE,
  DESTINATARIOS_PERMITIDOS: [
    `v1:${hmac("verificacao-lista")}`,
    ...DESTINATARIOS_DE_TESTE.map((e) => hmac(`email\x1f${e}`)),
  ].join(","),
  CHAVE_ASSINATURA: "22".repeat(32),
  KID_ASSINATURA: "teste-1",
  RESEND_API_KEY: "re_teste_nao_e_credencial",
};

export default defineConfig({
  test: {
    projects: [
      {
        // Regras puras, SQLite do Node, sem nada da Cloudflare.
        test: {
          name: "nucleo",
          include: ["test/nucleo/**/*.test.ts"],
          environment: "node",
          setupFiles: ["test/nucleo/sem_rede.ts"],
        },
      },
      {
        // Durable Objects reais no simulador local (Miniflare/workerd).
        plugins: [
          cloudflareTest({
            wrangler: { configPath: "./wrangler.jsonc" },
            miniflare: {
              bindings: VARIAVEIS_DE_TESTE,
              // Nenhuma requisição sai do simulador durante os testes.
              outboundService: () => new Response("rede externa bloqueada nos testes", { status: 599 }),
            },
          }),
        ],
        test: { name: "workers", include: ["test/workers/**/*.test.ts"] },
      },
    ],
  },
});
