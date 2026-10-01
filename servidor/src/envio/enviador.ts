// Fronteira entre as regras dos códigos e o provedor de e-mail. Trocar de
// provedor significa escrever outro Enviador; as regras não mudam.

export interface Mensagem {
  para: string;
  assunto: string;
  texto: string;
}

export type ResultadoEnviador =
  /** O provedor aceitou a mensagem. */
  | { tipo: "aceito" }
  /** Não se sabe se a mensagem foi aceita (tempo esgotado, rede, 5xx...). */
  | { tipo: "incerto" }
  /** A mensagem certamente não foi aceita. */
  | { tipo: "falha" };

export interface Enviador {
  /**
   * `chaveIdempotencia` identifica exatamente um e-mail; repetições com a
   * mesma chave precisam levar o mesmo conteúdo.
   */
  enviar(mensagem: Mensagem, chaveIdempotencia: string): Promise<ResultadoEnviador>;
}
