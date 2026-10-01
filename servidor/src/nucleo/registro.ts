// Registro mínimo: só o contexto e o tipo do erro. Nunca códigos, e-mails,
// segredos, chaves, corpos de mensagem nem respostas de serviços externos.

export function tipoDoErro(erro: unknown): string {
  if (erro instanceof Error) return erro.name || "Error";
  return typeof erro;
}

export function registrarFalha(contexto: string, erro?: unknown): void {
  const tipo = erro === undefined ? "" : ` (${tipoDoErro(erro)})`;
  console.error(`sino: falha em ${contexto}${tipo}`);
}

export function registrarEvento(contexto: string): void {
  console.warn(`sino: ${contexto}`);
}
