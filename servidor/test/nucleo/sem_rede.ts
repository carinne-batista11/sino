// Os testes do núcleo nunca acessam a rede: qualquer fetch global falha.
globalThis.fetch = (() => {
  throw new Error("rede externa bloqueada nos testes");
}) as typeof fetch;
