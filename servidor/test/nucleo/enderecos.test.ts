// Remetente e Reply-To obrigatórios do envio real (E4, T2; src/envio/enderecos.ts).
import { describe, expect, it } from "vitest";
import { enderecosDeEnvio, remetenteValido } from "../../src/envio/enderecos";

const RESPONDER = "contato@exemplo.com";

describe("remetente e endereço de resposta", () => {
  it("aceita 'Nome <email>' ou só o e-mail, e um e-mail de resposta", () => {
    for (const remetente of ["Sino <nao-responda@envios.exemplo.com>", "nao-responda@envios.exemplo.com"]) {
      expect(enderecosDeEnvio(remetente, RESPONDER)).toEqual({ remetente, responderPara: RESPONDER });
    }
  });

  it("ausentes, vazios ou de outro tipo: null", () => {
    for (const [r, p] of [
      [undefined, RESPONDER], ["Sino <a@b.com>", undefined], ["", RESPONDER], ["Sino <a@b.com>", ""],
      [null, RESPONDER], [42, RESPONDER], ["Sino <a@b.com>", ["a@b.com"]],
    ] as [unknown, unknown][]) {
      expect(enderecosDeEnvio(r, p)).toBeNull();
    }
  });

  it("remetentes malformados são recusados", () => {
    for (const r of [
      "Sino", "<a@b.com>", "Sino <>", "Sino <a@b.com", "Sino a@b.com>", "Sino <a@@b.com>", "Sino <a b@c.com>",
      " Sino <a@b.com>", "Sino <a@b.com> ", "Sino  <a@b.com>", "Si\"no <a@b.com>", "Sino\r\nBcc: x@y.com <a@b.com>",
      "Sino <a@b.com>\r\nBcc: x@y.com", "S".repeat(65) + " <a@b.com>", " a@b.com", "a@b.com\n", "Sino <ação@b.com>",
    ]) {
      expect(remetenteValido(r), JSON.stringify(r)).toBe(false);
      expect(enderecosDeEnvio(r, RESPONDER)).toBeNull();
    }
  });

  it("endereço de resposta precisa ser só o e-mail, sem nome nem espaços", () => {
    for (const p of ["Sino <a@b.com>", " a@b.com", "a@b.com ", "a@b.com\r\nBcc: x@y.com", "semarroba", "a@b.com,c@d.com", "<a@b.com>",
      "a@b.com;", "\"a\"@b.com"]) {
      expect(enderecosDeEnvio("Sino <a@b.com>", p), JSON.stringify(p)).toBeNull();
    }
  });
});
