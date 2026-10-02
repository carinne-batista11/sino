# Notas da versão — Sino

Mudanças visíveis para quem usa o Sino e alterações nos Termos de Uso e na
Política de Privacidade. Regras completas na
[ERS v6.0](ERS_Controle_de_Contas_v6.0.md).

## v6.0 — em implementação

### Etapa 8 — e-mail com código (02/10/2026, em andamento)

Entrega local de códigos **concluída e validada**; publicação para outras
pessoas **pendente**.

**Novidades**

- **Cadastro com confirmação do e-mail:** a conta só é criada depois que o
  código de 6 dígitos enviado ao e-mail é informado no Sino.
- **Alterar o e-mail** em Ajustes, com a senha atual e um código enviado ao
  novo endereço. O e-mail atual continua valendo até a confirmação.
- **Esqueci minha senha**, a partir da tela de entrada: e-mail, código e nova
  senha. A resposta ao pedido não revela se o endereço corresponde a uma conta
  que pode recuperar a senha; limite de pedidos, serviço indisponível ou falha
  de conexão podem gerar mensagens diferentes.
- Regras dos códigos: validade de 10 minutos, até 5 tentativas, uso único e
  reenvio depois de 60 segundos (o novo código invalida o anterior).
- Ajustes mostra o selo "Verificado" quando o e-mail foi confirmado.

**Como funciona agora**

- Os códigos são gerados, enviados e conferidos por um serviço próprio. Ele
  já funciona no próprio computador (desenvolvimento e demonstração). A
  integração com a Resend está implementada, mas **o serviço ainda não foi
  publicado** e a entrega real de e-mails ainda não foi validada.
- Sem o serviço configurado, criar conta, alterar o e-mail e recuperar a senha
  mostram "A confirmação por e-mail não está disponível nesta instalação." e
  não são concluídos.
- **O login continua local:** e-mail e senha são conferidos no computador,
  sem internet. Contas criadas antes desta etapa continuam entrando; só contas
  com e-mail confirmado podem recuperar a senha por código.

**Correções**

- As telas de entrada, cadastro, código e recuperação passam a rolar quando o
  conteúdo não cabe na janela, mantendo todos os botões alcançáveis.
- Fechar a janela durante uma gravação não deixa mais o aplicativo preso em
  segundo plano; a gravação termina de forma completa ou não acontece.

**Para desenvolvimento**

- Caixa local de mensagens e **modo de demonstração**
  ([`servidor/README.md`](../servidor/README.md#modo-de-demonstração-desenvolvimento)):
  janela "Sino — Demonstração", aviso nas telas com código e banco próprio,
  separado do banco real. Um e-mail confirmado na demonstração **não comprova**
  acesso ao endereço.

**Termos de Uso e Política de Privacidade (atualização de 02/10/2026, em revisão)**

- Termos, item 1: a confirmação por código é a única função que conversa com
  um serviço fora do aplicativo (pela internet, quando publicado; no próprio
  computador, na demonstração).
- Termos, item 3: os únicos e-mails são os de código.
- Termos, item 4: cadastro, alteração de e-mail e recuperação de senha por
  código; regras dos códigos; dependência do serviço, ainda não publicado;
  login local; o que a confirmação demonstra com envio real e na
  demonstração; resposta da recuperação que não revela se há conta elegível.
  Removidas as frases "o Sino não verifica" o e-mail e "não é possível
  recuperar uma senha esquecida".
- Política, itens 1, 3 e 4: a confirmação por código, distinguindo o serviço
  publicado do modo de demonstração.
- Política, item 2: indicador de e-mail confirmado e registro técnico das
  confirmações usadas (sem e-mail, nome ou senha).
- Política, item 7: o que é enviado ao serviço de códigos e ao provedor de
  envio; o que o serviço guarda como resumo HMAC-SHA256 (e-mail, IP, código) e
  o que fica legível; prazos pela configuração atual; o que ainda não foi
  definido (hospedagem, domínio, responsável pela operação, tratamento pelos
  provedores); e o modo de demonstração, que grava as mensagens como texto
  legível em arquivos com acesso restrito.
- Política, item 8: alterar o e-mail e recuperar a senha passam a estar
  disponíveis com o serviço; excluir o usuário continua indisponível.
- Política, item 10: referência aos prazos do serviço.
- Revisão jurídica pendente. Como antes, o Sino não registra qual versão do
  texto foi aceita nem pede novo aceite (ERS P9); essa decisão precisa ser
  revista antes do uso por outras pessoas.

**Limitações conhecidas**

- Não há fechamento seguro da janela durante operações (previsto na Etapa 10).
- Pendências de experiência de uso para a Etapa 10: uma falha passageira ao
  gravar exige pedir novo código; o formulário de cadastro continua editável
  durante o envio; o tempo para reenviar não é mostrado em contagem regressiva;
  o cadastro não pede confirmação da senha.

### Etapas 1 a 7 (concluídas)

- Descrição opcional nas contas, limites de caracteres e escopo de edição nas
  séries estendido a categoria e descrição.
- Tela Principal com todas as contas do mês e atalho de edição; tela "Ver
  status".
- Detalhes da conta reformulada; tela Gráfico.
- Ajustes: nome, tema claro/escuro, Termos de Uso e Política de Privacidade
  dentro do app, sair da conta.
- Senha mínima de 8 caracteres, sem espaços, e alteração de senha.
- **Termos de Uso e Política de Privacidade:** primeira versão exibida no app
  (30/09/2026), incluindo a regra de senha da Etapa 7.

## v5.0 — concluída (22/09/2026)

Descrita na [ERS v5.0](ERS_Controle_de_Contas_v5.0.md).
