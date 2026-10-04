# Notas da versão — Sino

Mudanças visíveis para quem usa o Sino e alterações nos Termos de Uso e na
Política de Privacidade. Regras completas na
[ERS v6.0](ERS_Controle_de_Contas_v6.0.md).

## v6.0 — concluída para portfólio e demonstração local (04/10/2026)

Todas as funcionalidades da v6.0 estão implementadas e verificadas no
computador da autora (suíte do aplicativo com 879 testes aprovados). Situação
completa na [ERS v6.0, seção 13.6](ERS_Controle_de_Contas_v6.0.md#136-encerramento-da-v60-para-portfólio-04102026).

- **Parcial:** cadastro, alteração de e-mail e recuperação de senha por código
  funcionam com o serviço de códigos no próprio computador; a entrega real de
  e-mails não foi validada. Contraste (RNF09) medido nos testes em todas as
  telas, campos, barras e estados principais, com limites registrados na ERS.
  Desempenho com 1.000 contas [medido](desempenho-v6.md) abaixo de 2 s na
  consulta ao banco e na montagem das telas, sem a renderização da janela.
  Termos de Uso e Política de Privacidade integrados ao app, com revisão pela
  autora e revisão jurídica pendentes.
- **Correção:** na tela Categorias, a inicial de uma categoria sem emoji passa
  a ser escrita em branco ou preto, o que for mais legível sobre a cor da
  categoria (antes, sempre em branco).
- **Adiado para uso por outras pessoas:** publicação do serviço de códigos e
  envio real de e-mails, revisão jurídica dos Termos e da Política e decisão
  sobre versionamento e novo aceite (P9).

### Etapa 10 — visual e experiência de uso (04/10/2026)

Implementada e validada: testes automáticos (suíte completa no fechamento) e
revisão visual em cópias isoladas do banco. Sem mudança nos Termos de Uso nem
na Política de Privacidade.

**Novidades**

- **Confirmar senha no cadastro:** a senha é digitada duas vezes; se forem
  diferentes, aparece "As senhas não coincidem." e nenhum código é pedido
  (ERS P11).
- **Contagem para reenviar o código:** "Reenviar código em N s" diminui até
  liberar "Reenviar código".
- **Detalhes da conta com campos fixos** (ERS P12): sempre Valor, Vencimento,
  Categoria, Parcela, Recorrência e Descrição, nesta ordem, com ícones no mesmo
  verde. Sem informação, o campo mostra "Sem categoria", "Não há parcelas",
  "Esta conta não é recorrente." ou "Sem descrição". Em janela larga, o rótulo
  fica à esquerda do conteúdo; em janela estreita, acima. A descrição aparece
  completa, com as quebras de linha.
- **Tema Claro mais legível:** verde de textos e botões e cinza secundário mais
  escuros; textos das etiquetas de status (Pendente, Pago em) e ícones de
  Detalhes e do Gráfico com mais contraste. As cores das categorias não mudaram.
- O aviso de Excluir conta explica que as contas incluem os meses futuros já
  gerados das recorrências.

**Correções**

- **Fechamento seguro da janela:** fechar sem gravação em andamento fecha na
  hora; durante a gravação de um cadastro, alteração de e-mail ou recuperação
  de senha, a janela mostra "Salvando… a janela será fechada quando terminar."
  e fecha sozinha ao terminar.
- **Falha passageira ao gravar** depois de confirmar o código: aparece "Tentar
  novamente", que repete a mesma gravação sem pedir outro código.
- Durante o envio, a confirmação e a gravação, os campos já informados ficam
  bloqueados; Voltar e Cancelar continuam disponíveis.

**Limitações conhecidas**

- O fechamento seguro aguarda só as gravações dos fluxos com código; as demais
  gravações são curtas e continuam protegidas pela transação. Não há tempo
  limite: se uma gravação travar, a janela continua aberta com o aviso.
- "Tentar novamente" aparece só para falhas passageiras do banco; outros erros
  recomeçam o fluxo. Uma falha permanente desse tipo continua oferecendo nova
  tentativa até o código expirar, sem gravar nada indevidamente.
- Contraste (RNF09) **parcialmente verificado**: os pares de cores mapeados e
  as telas percorridas nos testes, nos dois temas. Estados raros, as telas de
  entrada nessa varredura e os gráficos em detalhe não foram medidos.
- No Linux, ao fechar a janela, o Flutter/GTK pode registrar avisos técnicos no
  terminal; o aplicativo encerra normalmente.

### Etapa 9 — excluir conta (03/10/2026)

Implementada e validada: testes automáticos e validação visual em cópia
isolada do banco (item nos dois temas, cancelamento nos três passos, senha
errada, exclusão com retorno ao Login e recusa do login antigo, dados dos
demais usuários preservados). O texto da mensagem "Sua conta foi excluída." no
Login tem cobertura automática, sem confirmação visual. Revisão dos Termos e
da Política pendente.

**Novidades**

- **Excluir conta** em Ajustes > Conta e sessão, com aparência de ação
  destrutiva e separada de "Sair da conta". Três passos: aviso com as
  quantidades de contas, séries recorrentes e categorias; senha atual;
  confirmação final. Cancelar em qualquer passo não altera nada.
- As quantidades do aviso incluem as ocorrências futuras já geradas das
  recorrências.
- Confirmada, a exclusão apaga do banco de dados atual, de uma só vez, a conta
  de usuário e as suas contas, séries e categorias; se algo falhar, nada é
  apagado. Os outros usuários da instalação não são alterados. A sessão é
  encerrada e a tela de entrada mostra "Sua conta foi excluída.".
- A exclusão **não apaga** os backups já existentes em `database/backups/`,
  o registro técnico das confirmações por código (que não identifica usuários)
  nem o que o serviço de códigos e o provedor de envio já guardaram.

**Termos de Uso e Política de Privacidade (rascunho de 03/10/2026, em revisão)**

- Termos, item 4: Ajustes também permite excluir a conta de usuário.
- Termos, item 6 (agora "Sair da conta e excluir a conta"): descreve os passos,
  que a exclusão é definitiva no banco atual e não apaga backups existentes.
- Política, item 2: o registro técnico das confirmações não é apagado na
  exclusão, por não estar ligado a nenhum usuário.
- Política, item 8: descreve a exclusão, o que ela não alcança e o limite da
  medida adicional de sobrescrever o espaço liberado no arquivo.
- Política, item 10: excluir a conta de usuário não apaga as cópias de
  segurança.
- P9 mantida: sem versionamento do texto nem novo aceite; revisar antes do uso
  por outras pessoas.

### Etapa 8 — e-mail com código (02/10/2026; entrega local concluída, publicação adiada)

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

- Não há fechamento seguro da janela durante operações. *Resolvido na Etapa 10.*
- Pendências de experiência de uso: uma falha passageira ao gravar exige pedir
  novo código; o formulário de cadastro continua editável durante o envio; o
  tempo para reenviar não é mostrado em contagem regressiva; o cadastro não
  pede confirmação da senha. *Todas resolvidas na Etapa 10.*

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
