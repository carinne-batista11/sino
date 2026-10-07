// Camada B da restrição de destinatários (contrato v1.1): envolve o enviador
// real (Resend ou caixa local) e confere a lista imediatamente antes de
// qualquer chamada ao provedor. Fora da lista, devolve "bloqueado" sem rede e
// sem repetir; as repetições do provedor ficam dentro do enviador envolvido,
// que nem chega a ser chamado. A camada A fica em fluxos.executarEnvio.

import { resumoDoEmail, type Destinatarios } from "../nucleo/destinatarios";
import { registrarEvento } from "../nucleo/registro";
import type { Enviador, Mensagem, ResultadoEnviador } from "./enviador";

export interface ConfiguracaoRestrita {
  chaveHmac: Uint8Array;
  destinatarios: Destinatarios;
}

export class EnviadorRestrito implements Enviador {
  /** `configuracao` null (serviço sem configuração válida): nada é enviado. */
  constructor(
    private readonly enviador: Enviador,
    private readonly configuracao: ConfiguracaoRestrita | null,
  ) {}

  async enviar(mensagem: Mensagem, chaveIdempotencia: string): Promise<ResultadoEnviador> {
    const c = this.configuracao;
    if (!c || !c.destinatarios.has(resumoDoEmail(c.chaveHmac, mensagem.para))) {
      registrarEvento("envio barrado pela lista de destinatários");
      return { tipo: "bloqueado" };
    }
    return this.enviador.enviar(mensagem, chaveIdempotencia);
  }
}
