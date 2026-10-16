# Notas da versão — Sino

Mudanças visíveis para quem usa o Sino e alterações nos Termos de Uso e na
Política de Privacidade. Regras completas na
[ERS v6.0](ERS_Controle_de_Contas_v6.0.md) e, para as entregas a partir da
Sino 6.1, nas mudanças descritas na [ERS v7.0](ERS_Controle_de_Contas_v7.0.md).

## Sino 6.7 — E8 e E11: calendários em português e seletor de mês e ano (16/10/2026)

Entrega conjunta da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (regras 5.47, M6, e 5.44, M3), implementada em 16/10/2026. ~~**Ainda não publicada:**~~ validação manual concluída em 16/10/2026 (24 de 24 testes aprovados); na data deste registro, o commit e a publicação no GitHub estavam pendentes. *Atualização (16/10/2026):* publicada no GitHub em 16/10/2026, no commit `feat: release Sino 6.7 calendars and month selector` (identificador no histórico do Git).

- **Calendários (E8):** os calendários de Nova conta e Editar conta (vencimento e data de pagamento) passam a aparecer em **português do Brasil**, com a semana começando no **domingo** e os textos "Selecione a data", "Cancelar" e "OK". O número do **dia de hoje** fica legível mesmo quando também é o dia selecionado.
- **Digitação da data:** continua pelo lápis do calendário, no formato **dd/mm/aaaa**, com barras; o campo se chama "Data (dd/mm/aaaa)" e as mensagens de erro estão em português. A inclusão automática das barras foi analisada e não entrou nesta versão (o calendário nativo usado pelo Sino não permite).
- **Seletor de mês e ano (E11):** em Início, tocar no mês e ano ("Outubro 2026 ▾") abre um diálogo com o ano e os 12 meses; escolher um mês vai direto para ele. **"Mês atual"** volta para o mês de hoje e **"Cancelar"** fecha sem mudar nada. As setas de mês continuam funcionando como antes.
- **Destaques:** o mês exibido aparece com fundo verde; o mês de hoje, com contorno.
- **Anos disponíveis:** do primeiro ano com contas (ou do ano atual) até o último ano com contas (ou cinco anos à frente), incluindo sempre o ano exibido.
- **Recorrências:** as contas de meses futuros das séries sem término continuam sendo criadas só quando o mês é aberto; abrir o seletor, trocar o ano ou cancelar não cria nada.
- **Acessibilidade e temas:** seletor acessível pelo teclado e com nomes para leitores de tela; legível nos temas Claro e Escuro.
- **Testes:** 1146 testes automáticos do aplicativo aprovados (35 novos), em bancos temporários e sem acesso à rede. Validação manual numa cópia isolada, com banco próprio e dados fictícios, feita pela autora: **24 de 24 testes aprovados** (11 dos calendários e 13 do seletor de mês e ano, inclusive com a janela estreita, de cerca de 380 px), sem nenhuma anomalia.
- **Sem mudanças** no banco de dados (nenhuma migração), nos Termos de Uso, na Política de Privacidade ou no serviço de códigos.
- **Continua valendo:** o Sino segue sem liberação pública; o envio de códigos continua restrito aos endereços autorizados da autora (Sino 6.3, abaixo).

## Sino 6.6 — E7: orientação para quem ainda não tem contas (16/10/2026)

Sexta entrega com código da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (regra 5.43, M2), implementada e validada em 16/10/2026. Na data deste registro, o commit e a publicação no GitHub ainda estavam pendentes. *Atualização (16/10/2026):* publicada no GitHub no commit `de06c4eaa2990cfb34a94d55da62a73d896f4e00`.

- **O que muda:** quem ainda não tem nenhuma conta, em nenhum mês, passa a ver em Início a orientação **"Registre suas primeiras contas e tenha tudo sob controle."**, com um ícone de adicionar, no lugar de "Suas contas estão em dia!" (que não fazia sentido para quem nunca cadastrou nada). A lista do mês deixa de mostrar "Nenhuma conta neste mês." nesse caso.
- **Só informativa:** a orientação não é um botão e não abre nada; as contas continuam sendo cadastradas pelo botão "+".
- **Quem já tem contas:** nada muda. Num mês vazio, continuam "Nenhuma conta neste mês." e os avisos de sempre ("Suas contas estão em dia!" ou "Você possui contas em atraso!").
- **Sempre pelos dados atuais:** ao cadastrar a primeira conta, a orientação some; se todas as contas forem excluídas, ela volta.
- **Temas:** legível nos temas Claro e Escuro.
- **Testes:** 1111 testes automáticos do aplicativo aprovados (14 novos), em bancos temporários e sem acesso à rede. Validação manual numa cópia isolada, com banco próprio e dados fictícios, depois removida: 7 de 7 cenários aprovados pela autora.
- **Sem mudanças** no banco de dados (nenhuma migração; só uma consulta nova, de leitura), nos Termos de Uso, na Política de Privacidade ou no serviço de códigos.
- **Continua valendo:** o Sino segue sem liberação pública; o envio de códigos continua restrito aos endereços autorizados da autora (Sino 6.3, abaixo).

## Sino 6.5 — E6: descrição de até 1000 caracteres (16/10/2026)

Quinta entrega com código da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (regra 5.45, M4), implementada e validada em 16/10/2026. Na data deste registro, o commit e a publicação no GitHub ainda estavam pendentes. *Atualização (16/10/2026):* publicada no GitHub no commit `3fc862b9fae5bd8fa787553b1d7f55dc41113e1c`.

- **O que muda:** a descrição de uma conta pode ter até **1000 caracteres** (antes, 500). Cada caractere percebido conta como um, inclusive emojis compostos, bandeiras e letras acentuadas.
- **Campo maior:** em Nova conta e Editar conta, o campo de descrição começa com 2 linhas e cresce até 8; depois da oitava linha, ele rola por dentro. O contador passa a mostrar "x/1000", e a dica, "Até 1000 caracteres".
- **Em todas as contas:** vale para contas únicas e recorrentes, tanto em "Somente este mês" quanto em "Este mês em diante". Em Detalhes, a descrição continua aparecendo inteira, com as quebras de linha.
- **Continua igual:** espaços e quebras de linha nas pontas são removidos ao salvar; nada é cortado automaticamente; além do limite, a digitação é recusada com o aviso "Limite atingido" e o som curto.
- **Compatibilidade:** uma descrição com mais de 500 caracteres, salva nesta versão, aparece inteira se a conta for aberta numa versão anterior do Sino (limite de 500), mas só pode ser salva lá depois de reduzida a 500. Nesta versão, o limite é 1000: uma descrição antiga acima de 1000 continua aparecendo inteira e só pode ser salva depois de reduzida a 1000.
- **Testes:** 1097 testes automáticos do aplicativo aprovados (15 novos), em bancos temporários e sem acesso à rede. Validação manual numa cópia isolada, com banco próprio e dados fictícios, depois removida: 7 de 7 cenários e 30 de 30 verificações aprovados pela autora, nos temas Claro e Escuro.
- **Sem mudanças** no banco de dados (nenhuma migração), nos Termos de Uso, na Política de Privacidade ou no serviço de códigos.
- **Continua valendo:** o Sino segue sem liberação pública; o envio de códigos continua restrito aos endereços autorizados da autora (Sino 6.3, abaixo).

## Sino 6.4 — E5: contador do nome do usuário oculto (16/10/2026)

Quarta entrega com código da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (regra 5.46, M5), implementada e validada em 16/10/2026. Na data deste registro, o commit e a publicação no GitHub ainda estavam pendentes. *Atualização (16/10/2026):* publicada no GitHub no commit `c2961587d7f7868efcb7b58ade1e7f73cf8178b3`.

- **O que muda:** o contador "x/70" deixa de aparecer no campo de nome do **Cadastro** ("Nome completo") e de **Editar nome**, em Ajustes. Ele fica oculto o tempo todo, inclusive perto do limite.
- **Continua igual:** o limite de 70 caracteres (cada emoji conta como um), a recusa de qualquer caractere além disso, o aviso "Limite atingido" e o som curto, a mensagem para um nome antigo acima do limite (que aparece inteiro e só pode ser salvo depois de reduzido) e a validação ao salvar.
- **Outros campos:** os contadores do nome da conta, da descrição e do nome da categoria continuam visíveis.
- **Testes:** 1082 testes automáticos do aplicativo aprovados (12 novos), em bancos temporários e sem acesso à rede. Validação manual numa cópia isolada, com banco próprio e dados fictícios: 7 de 7 cenários aprovados pela autora, nos temas Claro e Escuro, sem problema visual.
- **Sem mudanças** no banco de dados (nenhuma migração), nos Termos de Uso, na Política de Privacidade ou no serviço de códigos.
- **Continua valendo:** o Sino segue sem liberação pública; o envio de códigos continua restrito aos endereços autorizados da autora (Sino 6.3, abaixo).

## Sino 6.3 — E4: envio real em produção restrita (encerrada em 15/10/2026; versão registrada em 16/10/2026)

Terceira entrega com código da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (regra 5.49, M8). A E4 foi **encerrada operacionalmente em 15/10/2026** pela autora, com ressalvas, e a versão **Sino 6.3** foi **registrada formalmente em 16/10/2026**. Ela corresponde ao código da E4 já publicado no GitHub (até o commit `db00f44`); o registro não envolve nova implantação e foi publicado no GitHub em 16/10/2026 (`a57d73f`).

- **O que muda para quem usa o Sino:** o aplicativo passa a confirmar e-mails pelo serviço de códigos definitivo, em **produção restrita**: só os endereços autorizados da autora recebem códigos. Para qualquer outro endereço, o cadastro e a troca de e-mail mostram "O envio de códigos está restrito nesta fase do Sino." e a recuperação de senha mantém a resposta neutra, sem envio. O login de contas existentes continua local.
- **Sem liberação pública:** o Sino continua sendo um projeto de portfólio e de uso pessoal da autora; a disponibilização a outras pessoas (M8 para terceiros, M14) continua pendente.
- **Ressalvas:** a meta original de desempenho do serviço (P43) continua **não atendida**, com risco aceito só para a produção restrita; revisão jurídica dos Termos e da Política pendente.
- **Sem mudanças** no banco de dados (continua na versão 9). Os Termos e a Política em vigor são os da versão de 13/10/2026, com novo aceite (seção abaixo).
- O detalhamento da preparação, dos testes e da implantação fica preservado abaixo, como registrado em cada data.

*Registro de 14/10/2026 (histórico, antes da produção restrita):* situação da E4: o **T1** (ambiente remoto de testes, sem Resend) está **encerrado** (12/10/2026). O **T2** (primeiro envio real de e-mail pela Resend) foi **implantado em 13/10/2026** num Worker temporário, e os e-mails reais foram entregues a **um único endereço autorizado**, numa cópia isolada do app. Os testes terminaram em 14/10/2026, e o ambiente temporário foi **desmontado no mesmo dia**. **A E4 não está concluída**: ainda faltam publicar o serviço definitivo, em uso restrito, e configurar o aplicativo para ele. O serviço não foi validado para uso amplo (produção). O aplicativo normal não mudou e nenhuma versão nova foi lançada.

### Publicado no GitHub em 13/10/2026 (commit `65a6b9d`): Termos de Uso e Política de Privacidade, versão de 13/10/2026 (mudança relevante)

Textos atualizados em preparação para o T2, aprovados pela autora (P41). Eles descrevem o funcionamento planejado do serviço real e não afirmam que ele já está em uso.

- **Termos, itens 1, 2, 4 e 9:** a exceção da confirmação por código passa a citar o serviço real, operado pela desenvolvedora, e o provedor de envio; o item 2 registra a versão aceita nas contas criadas a partir de 06/10/2026; o item 4 descreve a fase restrita de testes (só endereços autorizados recebem códigos), o remetente `nao-responda@envios.appsino.com.br` e que os e-mails nunca pedirão a senha; o item 9 inclui pedidos sobre dados pessoais e as respostas aos e-mails de código.
- **Política, itens 1, 2, 7, 8, 10 e 12:**
  - item 2: o Sino não pede a localização do dispositivo; o IP recebido pelo serviço pode permitir inferir uma localização aproximada, e o serviço o usa só para limitar abusos, guardando apenas um resumo;
  - item 7: quem opera o serviço; fase restrita; hospedagem na Cloudflare (Durable Objects, que podem ficar fora do Brasil; restauração possível dentro de 30 dias; Workers Logs e Traces desligados na configuração prevista); envio pela Resend (sem rastreamento de abertura e de cliques; região de envio São Paulo, dados guardados nos Estados Unidos; 30 dias de retenção e cópias de segurança por 7 dias; conteúdo visível no painel, inclusive os códigos; amostra analisada para segurança; lista oficial de suboperadores); transferência internacional;
  - itens 8, 10 e 12: canal para pedidos sobre os dados do serviço e dos provedores; prazos dos provedores; contato acompanhado pela desenvolvedora, com mensagens tratadas pelo Google (Gmail).
- **Classificação da autora:** relevante nos dois documentos, porque muda o compartilhamento com provedores, a retenção, a localização e a transferência internacional dos dados e identifica quem opera o serviço. Todos os usuários existentes aceitam a nova versão no próximo login; novos cadastros registram a versão de 13/10/2026.
- As versões de 04/10/2026 e de 06/10/2026 ficam preservadas em [`docs/legal/`](legal/).
- **Conferências nos painéis (13/10/2026):** os Logs e Traces desligados foram conferidos na Cloudflare antes do primeiro envio real; o rastreamento desligado e o TLS foram conferidos na Resend antes do primeiro envio (segundo a autora, conforme o histórico das conversas) e conferidos de novo depois dos testes.
- **Fontes oficiais (14/10/2026):** as páginas públicas da Resend e da Cloudflare citadas na Política foram conferidas de novo, sem divergência com o texto; alguns pontos dependem de contrato ou de configuração e não podem ser comprovados por essas páginas.
- **Pendente:** revisão jurídica antes de terceiros.

### Preparação técnica do T2 (código e documentação)

Preparada e revisada em 13/10/2026 (P42), com auditoria de segurança e correções, e publicada no GitHub (commit `00b45da`).

- **E-mails de código** (no envio real; até agora, só no T2 restrito): o rodapé passa a ser "Esta é uma mensagem automática do Sino. Precisa de ajuda? Entre em contato: sino.lembrete.contas@gmail.com", e as respostas vão para esse endereço (Reply-To). Remetente aprovado: `Sino <nao-responda@envios.appsino.com.br>`.
- **Serviço:** remetente e Reply-To obrigatórios, sem valor padrão (sem eles, o serviço responde indisponível e não chama a Resend); entrada temporária do T2 com um token exclusivo, além da lista de destinatários; configuração própria (`servidor/wrangler.t2.jsonc`) com registros, rastreamento e URLs de prévia desligados e armazenamento separado. O serviço de produção continua sem publicação.
- **Aplicativo:** só uma cópia isolada, aberta por ferramenta própria, recebe o token, pelo ambiente do processo. A instalação normal do Sino não muda: sem a variável, as requisições são as mesmas de antes.
- **Ferramentas locais:** `servidor/ferramentas/t2_segredos.py` (segredos exclusivos do T2, em pasta privada, com a chave da Resend só digitada num terminal) e `servidor/ferramentas/t2_app.py` (cópia isolada de uma revisão publicada, com banco próprio, e remoção controlada).
- **Testes:** 1034 do aplicativo e 246 do serviço aprovados, com dados fictícios, sem rede e sem abrir o aplicativo.
- **Ambiente temporário:** usado nos testes de 13 e 14/10/2026 e desmontado em 14/10/2026.

### Testes reais do T2 (13 e 14/10/2026; uso restrito, um endereço autorizado)

- **Aprovados em 13/10:** quatro e-mails reais entregues; cadastro confirmado por código; recuperação de senha com código incorreto recusado (4 tentativas restantes) e código correto aceito, cancelada sem trocar a senha; reenvio liberado depois de 60 segundos, com o código novo aceito; cadastro com endereço fora da lista recusado com a mensagem de restrição; recuperação para endereço sem conta com resposta neutra e nenhum e-mail.
- **Aprovados em 14/10** (mais quatro e-mails, oito no total, todos com entrega confirmada no painel da Resend): depois do reenvio, o código antigo deixa de valer; depois de cinco códigos errados, nem o código certo é aceito; os e-mails trazem o remetente, o texto e o rodapé aprovados, sem links, e as respostas vão para o contato do projeto.
- **Aprovado em parte:** código vencido. Depois de cerca de 11 minutos, o próprio aplicativo recusou o código, sem consultar o serviço. A recusa pelo serviço depois de 10 minutos é coberta pelos testes automáticos, mas não foi vista diretamente neste teste.
- **Fora desta fase:** a troca de e-mail não foi testada com envio real, por decisão da autora; ela é coberta pelos testes automáticos e já foi validada em demonstração (Sino 6.2).
- **Autenticação dos e-mails:** o primeiro e-mail falhou no DMARC, sem causa confirmada; o segundo passou em SPF, DKIM e DMARC, depois da publicação de um registro DMARC para o domínio de envio.
- **Desempenho:** o tempo de CPU por requisição ficou acima da meta original do projeto em parte da pequena amostra, sem erros nas métricas gerais do painel (que não mostram cada requisição individualmente); no fim dos testes, a mediana ficou pouco abaixo da meta. A continuidade dos testes seguiu um critério operacional revisado, e o desempenho para uso amplo (produção) não foi validado.
- **Encerramento (14/10/2026):** o Worker temporário foi excluído, a chave da Resend foi apagada, a cópia isolada e os arquivos privados de teste foram removidos, e a sessão do Wrangler foi encerrada. O domínio de envio e o seu registro DMARC de monitoramento foram mantidos para a próxima fase. O domínio principal está sem registro DMARC, por motivo ainda não identificado; isso será investigado.
- **O que falta para concluir a E4:** publicar o serviço definitivo em uso restrito e configurar o aplicativo para ele.

### Otimização do serviço de códigos (O1; publicada no GitHub em 14/10/2026, commit `981d1e8`)

- **O que mudou:** o serviço de códigos passou a assinar as autorizações com a criptografia nativa do ambiente da Cloudflare, em vez de uma biblioteca em JavaScript. As autorizações continuam **idênticas** às anteriores: o aplicativo, o contrato do serviço e as configurações não mudaram, e nada muda para quem usa o Sino.
- **Por quê:** reduzir o trabalho do serviço, porque o tempo de CPU medido no T2 ficou acima da meta original do projeto em parte da amostra.
- **Testes:** 254 do serviço e 1034 do aplicativo aprovados, com dados fictícios; assinaturas idênticas às da versão anterior em 200 casos de teste e no ambiente local que simula a Cloudflare.
- **Tamanho:** o pacote do serviço ficou cerca de 46% menor no teste local. Isso não comprova, sozinho, que o serviço ficou mais rápido na Cloudflare.
- **Ressalvas:** um teste antigo de carga, executado localmente, passa só em parte das execuções, tanto antes quanto depois desta mudança, provavelmente por limitação do simulador (não comprovado). O desempenho real só será conhecido depois de medir o serviço publicado.
- **Situação:** o serviço definitivo ainda não foi publicado; esta mudança não envolveu nenhum deploy. A E4 continua em andamento.

### Preparação da produção restrita (decisões 5 e 6; 15/10/2026, ainda sem publicação)

- **Segredos:** os segredos do serviço definitivo serão novos, guardados no armazenamento de segredos da Cloudflare e nunca no repositório. A autora guarda cópias de recuperação das duas chaves principais no gerenciador de senhas dela. O serviço definitivo usa um identificador de chave próprio, diferente dos ambientes de teste. Arquivos de ambiente (`.env`) ficam fora do Git.
- **Registros:** os registros detalhados e o rastreamento da Cloudflare continuam desligados, como já informa a Política de Privacidade; o acompanhamento usa só números agregados dos painéis.
- **Ferramenta:** nova ferramenta local para preparar e conferir os segredos sem mostrá-los. Testada só com dados fictícios; nenhum segredo real foi gerado.
- **Testes:** 260 do serviço e 1064 do aplicativo aprovados.
- **Situação (na preparação):** nada foi publicado; o endereço definitivo dependia da disponibilidade do nome na Cloudflare. *Atualização:* publicado em 15/10/2026 (seção abaixo).

### Produção restrita publicada e validada (15/10/2026; uso só da autora)

- **Serviço definitivo:** o serviço de códigos foi publicado na Cloudflare em `https://sino-servico-codigos.appsino.workers.dev`, nos planos gratuitos da Cloudflare e da Resend. Por enquanto, só **dois endereços da autora** podem receber códigos; o Sino continua **sem liberação para outras pessoas**.
- **Aplicativo:** passa a usar o serviço definitivo, com a chave pública própria da produção (commit `db00f44`, publicado no GitHub). Os ambientes de desenvolvimento e de teste continuam podendo indicar outro serviço pelas variáveis de ambiente. Para abrir o app, use o ambiente do projeto (`.venv`): sem o pacote `cryptography`, a confirmação por e-mail aparece como indisponível. Testes: 1070 do aplicativo aprovados, sem acesso à rede.
- **Testes reais:** primeiro cadastro definitivo da autora, com o código recebido por e-mail e aceito; endereço fora da lista recusado no cadastro e na troca de e-mail, sem envio; código vencido recusado pelo próprio serviço depois de 10 minutos; dois e-mails entregues, confirmados no painel da Resend.
- **Desempenho:** o tempo de CPU por requisição ficou acima da meta original do projeto em parte da pequena amostra (mediana abaixo da meta; nenhum erro). A autora aceitou esse risco só para o uso restrito atual, a reavaliar antes de qualquer liberação a terceiros.
- **Sem mudanças** nos Termos de Uso, na Política de Privacidade ou no banco de dados (o primeiro cadastro usou o banco já existente, versão 9).
- **Encerramento da implantação (15/10/2026):** os arquivos locais com os segredos da implantação foram apagados (a cópia de recuperação criptografada foi conferida antes, com cópia externa), a sessão local da Cloudflare foi encerrada e os registros locais da ferramenta foram removidos. A proteção do domínio `appsino.com.br` contra e-mails falsificados (DMARC `p=reject`) foi restaurada; o domínio de envio continua com uma política de monitoramento nesta fase.
- **E4 encerrada (15/10/2026):** a autora encerrou formalmente esta etapa. O envio real de códigos funciona só para os endereços autorizados; o Sino continua **sem liberação para outras pessoas**, e a meta original de desempenho continua não atendida (risco aceito só para o uso restrito).
- **Pendente (antes de liberar a terceiros):** desempenho, limites e proteção contra abuso, monitoramento e alertas, avaliação de planos pagos e custos (nenhuma contratação aprovada), retenção dos provedores, revisão jurídica, política DMARC do domínio de envio e ampliação segura dos destinatários. ~~Lançamento formal de uma versão do app~~: feito em 16/10/2026 (Sino 6.3, acima).

## Sino 6.2 — publicada em 07/10/2026 (E3: restrição de destinatários)

Segunda entrega com código da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (regra 5.49, P39, contrato v1.1). A publicação é **do código no GitHub**: o serviço de códigos continua sem deploy, não há envio real de e-mails e o Sino não foi liberado para terceiros (E4 e seção 11.3 da ERS). Suítes: 950 testes do aplicativo e 215 do serviço aprovados, em bancos temporários e ambientes isolados. Validação manual no modo de demonstração, só com endereços fictícios e a caixa local: as mensagens foram observadas pela autora, e os efeitos (duas mensagens na caixa, a conta criada e o e-mail alterado, nenhuma conta dos pedidos recusados) foram conferidos nos arquivos da demonstração.

- **Envio restrito:** no cadastro e na alteração de e-mail, um endereço fora da lista do serviço recebe "O envio de códigos está restrito nesta fase do Sino." (no pedido, no reenvio e na confirmação do código). Nada é gravado.
- **Recuperação de senha:** continua com a mesma mensagem neutra; nada é enviado a endereços fora da lista.
- **Modo de demonstração:** aceita só três endereços fictícios (`pessoa1@demonstracao.invalid`, `pessoa2@…` e `pessoa3@…`), mostrados no terminal e num arquivo de orientação; as mensagens continuam só na caixa local. Pastas de demonstração antigas não são reaproveitadas.
- **Sem mudanças** no banco de dados, nos Termos de Uso ou na Política de Privacidade.
- **Concluído:** E3 inteira. **Pendente para as próximas entregas:** envio real em ambiente restrito (E4), com textos atualizados e novo aceite; revisão jurídica.

## Sino 6.1 — publicada em 06/10/2026 (E2: versões e aceite dos Termos e da Política)

Primeira entrega com código da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (regra 5.53). Suíte com 926 testes aprovados. Validação visual em cópia isolada aprovada: leitura dos documentos, novo aceite com "Sair" e "Aceitar", e aviso de ajuste menor (com uma versão fictícia, só para o teste).

- **Versões dos documentos:** os Termos de Uso e a Política de Privacidade mostram a versão vigente ("Versão de 06/10/2026"). Os textos de cada versão ficam guardados em [`docs/legal/`](legal/); a de 04/10/2026 é a primeira registrada.
- **Registro do aceite:** no cadastro, o Sino registra qual versão de cada documento foi aceita, com data e hora. Também registra a ciência de um aviso de ajuste menor ("Entendi"), que não equivale a um aceite.
- **Mudanças futuras:**
  - mudança relevante: no próximo login, uma tela mostra o resumo e pede o novo aceite ("Aceitar" ou "Sair"); sem aceite, não é possível entrar;
  - ajuste menor: só um aviso, sem bloquear.
- **Banco de dados:** na primeira abertura, o banco é atualizado para a versão 9, com uma cópia de segurança automática antes. Os dados existentes não mudam.
- **Concluído:** E2 inteira. **Pendente para as próximas entregas:** envio real de e-mails (E3 e E4), com nova versão relevante dos textos e novo aceite; revisão jurídica.

### Termos de Uso e Política de Privacidade (versão de 06/10/2026, mudança relevante)

- **Termos, item 8:** cada versão é identificada pela data; o Sino registra a versão aceita no cadastro; mudanças relevantes pedem novo aceite e ajustes menores geram aviso.
- **Política, itens 2, 3, 8, 10 e 11:** descrevem os registros de aceite e de ciência dos documentos, para que servem, que são apagados na exclusão da conta e que podem continuar nas cópias de segurança já feitas; e como funcionam as versões.
- **Classificação da autora:** relevante, porque introduz registros de dados antes não descritos.
  - Quem já tem conta aceita a nova versão no próximo login.
  - O aceite original continua registrado só pela data, sem versão.
  - As versões de 04/10/2026 ficam preservadas em `docs/legal/`.

## Licença: MIT + Commons Clause (decidida em 06/10/2026; vale a partir do commit que a introduz)

Mudança só de licença: o funcionamento do aplicativo, o banco e os Termos de Uso não mudam, e não há nova versão do aplicativo.

- **Nova licença:** licença MIT com a condição "Commons Clause" v1.0, com os textos oficiais sem alteração (veja o [`LICENSE`](../LICENSE)). **Não é uma licença open source:** o código-fonte está disponível, mas o direito de vender o Sino não é concedido.
- **Continua permitido:** usar, estudar, copiar, modificar e redistribuir, inclusive versões modificadas, mantendo os avisos de licença.
- **Não concedido:** fornecer a terceiros, mediante pagamento ou outra contrapartida, um produto ou serviço cujo valor derive inteira ou substancialmente da funcionalidade do Sino. Cobranças por hospedagem, consultoria ou suporte relacionados ao Sino só entram nessa condição quando o valor do serviço deriva inteira ou substancialmente da funcionalidade do Sino; serviços que não se enquadram nisso não são afetados por ela. Para o que se enquadra, é preciso autorização da autora.
- **Alcance:** código, testes, ferramentas, documentos e imagens de autoria da autora neste repositório. Componentes de terceiros mantêm as próprias licenças.
- **Versões anteriores:** até o commit `a8302c2`, inclusive, o repositório foi distribuído somente sob a licença MIT. Quem obteve essas versões mantém, sobre elas, as permissões da MIT.
- **Revisão jurídica:** pendente (ERS v7.0, seção 13.4).

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
  Termos de Uso e Política de Privacidade integrados ao app e aprovados pela
  autora em 04/10/2026 para portfólio e demonstração local; revisão jurídica
  pendente.
- **Correção:** na tela Categorias, a inicial de uma categoria sem emoji passa
  a ser escrita em branco ou preto, o que for mais legível sobre a cor da
  categoria (antes, sempre em branco).
- **Correção:** na Tela Principal, o botão "+" fica numa faixa própria acima da
  barra de navegação, com o mesmo estilo, e não cobre mais "Ver status" nem os
  botões das linhas.
- **Limitações conhecidas:** o calendário de escolha de datas aparece em
  inglês (padrão do Flutter); em janelas mais estreitas que o tamanho padrão,
  o nome das contas na Tela Principal quebra letra a letra.
- **Adiado para uso por outras pessoas:** publicação do serviço de códigos e
  envio real de e-mails, revisão jurídica dos Termos e da Política e decisão
  sobre versionamento e novo aceite (P9).

### Termos de Uso e Política de Privacidade (ajustes de 04/10/2026)

- Termos, item 4: desde a primeira frase, distingue o envio real (o código
  confirma acesso à mensagem enviada ao endereço informado) da demonstração
  (o código apenas conclui o fluxo local).
- Política, item 2: a afirmação de que o Sino não coleta outros dados passa a
  ressalvar os dados técnicos da confirmação por código (como o endereço IP do
  pedido), com referência ao item 7.
- **Revisão pela autora concluída em 04/10/2026:** o texto atual dos Termos e
  da Política está aprovado para a versão de portfólio e demonstração local,
  com apoio de revisão técnica e de clareza. A **revisão jurídica continua
  pendente** e é necessária antes do uso por outras pessoas; P9 mantida.

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
da Política pendente (04/10/2026: revisão da autora concluída; revisão
jurídica pendente).

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

**Termos de Uso e Política de Privacidade (rascunho de 03/10/2026; aprovado pela autora em 04/10/2026, revisão jurídica pendente)**

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

**Termos de Uso e Política de Privacidade (atualização de 02/10/2026; aprovada pela autora em 04/10/2026, revisão jurídica pendente)**

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
