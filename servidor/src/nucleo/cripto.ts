// Primitivas síncronas (podem rodar dentro de transactionSync dos Durable
// Objects, que não aceita await): HMAC-SHA256, SHA-256, comparação em tempo
// constante, base64url e geração do código de 6 dígitos.

import { hmac } from "@noble/hashes/hmac.js";
import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex, hexToBytes, utf8ToBytes } from "@noble/hashes/utils.js";
import { CODIGO_DIGITOS } from "../config";

export interface Aleatorio {
  bytes(n: number): Uint8Array;
}

export const aleatorioSeguro: Aleatorio = {
  bytes(n) {
    return crypto.getRandomValues(new Uint8Array(n));
  },
};

const SEPARADOR = "\x1f";

/** HMAC-SHA256 em hex, com rótulo de domínio para separar os usos da chave. */
export function hmacHex(chave: Uint8Array, rotulo: string, ...partes: string[]): string {
  return bytesToHex(hmac(sha256, chave, utf8ToBytes([rotulo, ...partes].join(SEPARADOR))));
}

export function sha256Hex(texto: string): string {
  return bytesToHex(sha256(utf8ToBytes(texto)));
}

/** Compara dois textos sem encerrar no primeiro caractere diferente. */
export function iguaisTempoConstante(a: string, b: string): boolean {
  const x = utf8ToBytes(a);
  const y = utf8ToBytes(b);
  let diferenca = x.length ^ y.length;
  const n = Math.max(x.length, y.length);
  for (let i = 0; i < n; i++) diferenca |= (x[i] ?? 0) ^ (y[i] ?? 0);
  return diferenca === 0;
}

export function paraBase64Url(bytes: Uint8Array): string {
  let binario = "";
  for (const b of bytes) binario += String.fromCharCode(b);
  return btoa(binario).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function deBase64Url(texto: string): Uint8Array {
  const base64 = texto.replace(/-/g, "+").replace(/_/g, "/");
  const binario = atob(base64 + "=".repeat((4 - (base64.length % 4)) % 4));
  return Uint8Array.from(binario, (c) => c.charCodeAt(0));
}

export function identificadorAleatorio(aleatorio: Aleatorio, bytes = 16): string {
  return paraBase64Url(aleatorio.bytes(bytes));
}

/** Código numérico uniforme de 6 dígitos (amostragem por rejeição). */
export function gerarCodigo(aleatorio: Aleatorio): string {
  const total = 10 ** CODIGO_DIGITOS;
  const limite = Math.floor(0x1_0000_0000 / total) * total;
  for (;;) {
    const b = aleatorio.bytes(4);
    const valor = ((b[0] << 24) >>> 0) + (b[1] << 16) + (b[2] << 8) + b[3];
    if (valor < limite) return String(valor % total).padStart(CODIGO_DIGITOS, "0");
  }
}

/** Lê uma chave de 32 bytes em hex; null se ausente ou malformada. */
export function chaveDeHex(hex: string | undefined): Uint8Array | null {
  if (!hex || !/^[0-9a-fA-F]{64}$/.test(hex)) return null;
  return hexToBytes(hex);
}
