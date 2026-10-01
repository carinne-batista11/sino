// Textos aprovados dos e-mails (Etapa 8): só texto, sem links, sem o nome do
// usuário e sem o código no assunto.

import type { Finalidade } from "../config";
import type { Mensagem } from "./enviador";

const RODAPE =
  "O código vale por 10 minutos e só pode ser usado uma vez. Não compartilhe este código com ninguém.\n" +
  "Esta é uma mensagem automática do Sino; não é necessário respondê-la.";

const TEXTOS: Record<Finalidade, { assunto: string; abertura: string; aviso: string }> = {
  cadastro: {
    assunto: "Código para confirmar seu e-mail no Sino",
    abertura: "Olá! Use o código abaixo para confirmar seu e-mail e concluir seu cadastro no Sino:",
    aviso:
      "Se você não está criando uma conta no Sino, ignore esta mensagem. " +
      "Nenhuma conta é criada sem este código.",
  },
  alteracao_email: {
    assunto: "Código para confirmar seu novo e-mail no Sino",
    abertura: "Olá! Use o código abaixo para confirmar este endereço como o novo e-mail da sua conta no Sino:",
    aviso:
      "Se você não pediu essa alteração, ignore esta mensagem. " +
      "Sem este código, o e-mail da conta não é alterado.",
  },
  recuperacao_senha: {
    assunto: "Código para redefinir sua senha do Sino",
    abertura:
      "Olá! Recebemos um pedido para redefinir a senha da conta do Sino associada a este e-mail. " +
      "Use o código abaixo:",
    aviso: "Se você não pediu a redefinição, ignore esta mensagem. Sua senha continua a mesma.",
  },
};

export function montarMensagem(finalidade: Finalidade, para: string, codigo: string): Mensagem {
  const t = TEXTOS[finalidade];
  return {
    para,
    assunto: t.assunto,
    texto: `${t.abertura}\n\n${codigo}\n\n${t.aviso}\n\n${RODAPE}\n`,
  };
}
