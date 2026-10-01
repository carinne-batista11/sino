// Enviador simulado para os testes automatizados: guarda as mensagens em
// memória e devolve o resultado programado. Nunca é usado pelo Worker
// publicado (o default export usa sempre o EnviadorResend).

import type { Enviador, Mensagem, ResultadoEnviador } from "./enviador";

export class EnviadorSimulado implements Enviador {
  readonly enviadas: { mensagem: Mensagem; chave: string }[] = [];
  private proximos: (ResultadoEnviador | Error)[] = [];

  /** Programa os próximos resultados (um por chamada); depois, "aceito". */
  programar(...resultados: (ResultadoEnviador | Error)[]): void {
    this.proximos.push(...resultados);
  }

  async enviar(mensagem: Mensagem, chave: string): Promise<ResultadoEnviador> {
    this.enviadas.push({ mensagem, chave });
    const resultado = this.proximos.shift() ?? { tipo: "aceito" };
    if (resultado instanceof Error) throw resultado;
    return resultado;
  }

  /** Código de 6 dígitos da última mensagem enviada a `para`. */
  ultimoCodigo(para: string): string | null {
    for (let i = this.enviadas.length - 1; i >= 0; i--) {
      if (this.enviadas[i].mensagem.para === para) {
        return this.enviadas[i].mensagem.texto.match(/^\d{6}$/m)?.[0] ?? null;
      }
    }
    return null;
  }
}
