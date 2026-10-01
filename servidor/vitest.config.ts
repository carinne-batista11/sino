import { cloudflareTest } from "@cloudflare/vitest-pool-workers";
import { defineConfig } from "vitest/config";

// Valores fixos apenas para os testes: não são credenciais e não valem fora
// do simulador local.
const VARIAVEIS_DE_TESTE = {
  CHAVE_HMAC: "11".repeat(32),
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
