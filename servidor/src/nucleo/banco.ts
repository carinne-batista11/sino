// Acesso síncrono a SQLite, comum ao Durable Object (ctx.storage.sql) e ao
// SQLite do Node usado nos testes do núcleo. As regras só usam esta interface,
// então os mesmos comandos SQL são exercitados nos dois ambientes.

export type ValorSql = string | number | null;

export interface BancoSql {
  /** Executa um comando; as alterações condicionais usam RETURNING + todos(). */
  executar(sql: string, ...parametros: ValorSql[]): void;
  todos<T>(sql: string, ...parametros: ValorSql[]): T[];
  um<T>(sql: string, ...parametros: ValorSql[]): T | null;
  /** Executa `fn` numa transação: tudo ou nada; exceções desfazem a transação. */
  transacao<T>(fn: () => T): T;
}
