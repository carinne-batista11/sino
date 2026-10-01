// Formato de e-mail aceito nos fluxos com código (contrato v1). A mesma regra
// vale no cliente Python (backend/servico_codigos.py) e na camada de dados
// (database/db.py); os casos compartilhados ficam em
// servidor/test/conformidade/emails.json.
//
//   * bordas: removem-se só espaços comuns (U+0020); qualquer outro espaço
//     ou caractere de controle torna o endereço inválido;
//   * depois disso: só ASCII imprimível (U+0021 a U+007E), exatamente um
//     "@", partes local e de domínio não vazias e até 254 caracteres;
//   * normalização para comparação: minúsculas ASCII (idênticas em
//     JavaScript, Python e SQLite para esse alfabeto).

export const TAMANHO_MAXIMO_EMAIL = 254;
const RE_EMAIL = /^[\x21-\x3f\x41-\x7e]+@[\x21-\x3f\x41-\x7e]+$/;

export function aparar(texto: string): string {
  return texto.replace(/^ +| +$/g, "");
}

export function emailValido(email: unknown): email is string {
  if (typeof email !== "string") return false;
  const e = aparar(email);
  return e.length <= TAMANHO_MAXIMO_EMAIL && RE_EMAIL.test(e);
}

/** E-mail como será usado (sem espaços nas bordas); só para endereços válidos. */
export function emailAparado(email: string): string {
  return aparar(email);
}

/** Forma de comparação: sem espaços nas bordas e em minúsculas ASCII. */
export function normalizarEmail(email: string): string {
  return aparar(email).toLowerCase();
}
