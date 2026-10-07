// Regras fixas da ERS v6.0 (5.32) e valores aprovados para a v1 do serviço.
// Todos os prazos em milissegundos.

export const CODIGO_DIGITOS = 6;
export const VALIDADE_CODIGO_MS = 10 * 60_000;
export const MAX_TENTATIVAS = 5;
export const INTERVALO_REENVIO_MS = 60_000;

// Um envio em "enviando" há mais que isso vira "incerto" (cobre o tempo
// limite de cada chamada à Resend e as repetições dentro da mesma execução).
export const PRAZO_ENVIANDO_MS = 60_000;

// Um desafio que não passou de "pendente_reserva"/"reservado" para "enviando"
// nesse prazo foi abandonado pela execução que o criou e é encerrado; uma
// execução atrasada não consegue mais reservar nem iniciar o envio.
export const PRAZO_RESERVA_MS = 60_000;

// Repetição de um pedido cuja reserva ainda está em andamento: o cliente
// repete a mesma requisição depois deste intervalo (cabeçalho Retry-After).
export const REPETIR_APOS_S = 2;

// Limites contra abuso (janelas fixas: hora cheia e dia UTC).
export const LIMITE_DESTINO_HORA = 5;
export const LIMITE_DESTINO_DIA = 10;
export const LIMITE_IP_PEDIDOS_HORA = 10;
export const LIMITE_IP_PEDIDOS_DIA = 30;
export const LIMITE_IP_VALIDACOES_HORA = 30;
export const TETO_GLOBAL_DIA = 80;

// Restrição de destinatários (ERS v7.0, 5.49): máximo de resumos na lista.
export const LIMITE_DESTINATARIOS = 50;

// Retenção.
export const HORA_MS = 3_600_000;
export const DIA_MS = 24 * HORA_MS;
export const RETENCAO_DESAFIO_MS = 24 * HORA_MS;
export const RETENCAO_CONTADOR_HORA_MS = 2 * HORA_MS;
export const RETENCAO_CONTADOR_DIA_MS = 48 * HORA_MS;
export const RETENCAO_TOTAIS_GLOBAIS_DIAS = 35;

// Envio pela Resend.
export const RESEND_URL = "https://api.resend.com/emails";
export const RESEND_TENTATIVAS = 3;
export const RESEND_TEMPO_LIMITE_MS = 10_000;
export const RESEND_ESPERAS_MS = [500, 1_000];
export const REMETENTE_PADRAO = "Sino <onboarding@resend.dev>";

export const FINALIDADES = ["cadastro", "alteracao_email", "recuperacao_senha"] as const;
export type Finalidade = (typeof FINALIDADES)[number];
