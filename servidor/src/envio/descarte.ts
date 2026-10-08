// Enviador do AMBIENTE REMOTO DE TESTES (src/teste.ts): descarta a mensagem.
// Sem rede, sem gravar e sem registrar nada dela (nem código, nem e-mail, nem
// assunto). Devolve "aceito" para que o fluxo siga como num envio real
// (reserva global, estado "enviado", tentativas); o código gerado nunca sai do
// serviço, então ninguém consegue validá-lo com o código correto.

import type { Enviador, Mensagem, ResultadoEnviador } from "./enviador";

export class EnviadorDescarte implements Enviador {
  async enviar(_mensagem: Mensagem, _chaveIdempotencia: string): Promise<ResultadoEnviador> {
    return { tipo: "aceito" };
  }
}
