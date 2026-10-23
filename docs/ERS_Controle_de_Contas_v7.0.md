# Especificação de Requisitos de Software (ERS)

## Projeto: Aplicativo de Controle de Contas — Sino

**Autora:** Carinne Batista
**Versão:** 7.0
**Data:** 4 de outubro de 2026
**Versão anterior:** 6.0 (concluída para portfólio e demonstração local em 04/10/2026; preservada sem alterações)
**Status:** **Planejamento geral da v7.0, a implementar em entregas.** Revisão de 06/10/2026 (P33): a ERS v7.0 é o **plano geral**; cada entrega é implementada, testada, documentada e publicada separadamente como uma versão do aplicativo (seção 15). As decisões de produto estão na seção 13.1, as pendências na 13.4, e as propostas técnicas da 13.2 estão sujeitas a revisão na implementação. Prioridades: **1** licença (M9: MIT + Commons Clause escolhida em 06/10/2026, P36); **2** envio real de e-mails; **3** melhorias de UX; **4** disponibilização para outras pessoas (M14); **5** comprovantes, Faturas (candidata) e pendências.
**Origem:** decisões registradas em [ERS_v7.0_propostas.md](ERS_v7.0_propostas.md) (planejamento de 04/10/2026, preservado como histórico das escolhas e das análises).

---

## Como ler este documento

A ERS v7.0 **descreve só o que muda** em relação à [ERS v6.0](ERS_Controle_de_Contas_v6.0.md). Tudo o que não for alterado aqui continua valendo como está na v6.0: regras, requisitos, casos de teste e decisões. A numeração das seções acompanha a da v6.0; seções sem mudanças (por exemplo, 3 e 4) são omitidas.

Convenções:

* **[v7 novo]**: regra ou requisito criado nesta versão.
* **[v7 altera X]**: substitui ou completa o item X da v6.0; o restante de X continua valendo.
* **Mn**: melhoria do planejamento de origem (M1 a M14; M13 é candidata).
* **Pn**: decisão de produto (P1 a P12 vêm da v6.0; P13 em diante, desta versão).
* **Tn**: decisão técnica (T1 a T5 vêm da v6.0; T6 em diante, desta versão). As desta versão são **propostas técnicas sujeitas a revisão** na implementação.
* **En**: entrega publicada separadamente (seção 15).
* **Versões:** "ERS v7.0" é a versão **deste documento de planejamento**; as revisões dele são registradas por data no histórico. As **versões do aplicativo** (Sino 6.1, 6.2…) são outra numeração, uma por entrega publicada (seção 15.2).

---

# 1. Objetivo da v7.0

Melhorar a experiência de uso e a robustez do Sino, abrir caminho para o uso por outras pessoas com segurança jurídica e técnica, e acrescentar comprovantes em imagem às contas:

* tratar espaços acidentais em e-mails e senhas (M1);
* orientar o usuário que ainda não tem contas e facilitar a navegação entre meses (M2, M3);
* ampliar a descrição e simplificar o campo de nome (M4, M5);
* calendário em português e legível (M6);
* comparativo de gastos por categoria em colunas (M7);
* envio real de códigos por e-mail, inicialmente restrito (M8);
* comprovantes em imagem, com backup completo por ferramenta de manutenção (M10);
* linhas de conta legíveis em janelas estreitas (M11);
* versionamento e novo aceite dos Termos e da Política, com revisão jurídica antes de terceiros (M12);
* licença que preserve a possibilidade de a autora comercializar o Sino e impeça a comercialização por terceiros sem autorização (M9);
* avaliação da disponibilização para outras pessoas, em desktop e/ou mobile, com piloto restrito antes de uma liberação mais ampla (M14).

# 2. Escopo

## 2.1 Escopo completo da ERS v7.0

* **Prioridade 1 — Licença:** M9 (reaberta em 06/10/2026). *Atualização (16/10/2026):* licença MIT + Commons Clause escolhida (P36) e aplicada na E1, concluída e publicada em 06/10/2026 (commit `58b4382`); revisão jurídica e avaliação de registro no INPI pendentes, sem gasto autorizado (2.5, 13.4).
* **Prioridade 2 — Envio real de e-mails:** M12 (parte técnica: versões e registro do aceite) e M8, em **ambiente restrito** aos endereços autorizados da autora.
* **Prioridade 3 — Melhorias de UX:** M1, M2, M3, M4, M5, M6, M11 e M7, uma entrega por melhoria.
* **Prioridade 4 — Disponibilização para outras pessoas:** M14, avaliação de desktop e/ou mobile e preparação de um **piloto restrito**. A liberação mais ampla é uma etapa separada (seção 11.3).
* **Prioridade 5 — Funcionalidades maiores:** M10 (comprovantes), em entregas próprias.

## 2.2 Fora do escopo completo da v7.0

* **M13 — Faturas:** proposta **candidata** (seção 2.4). Só entra no escopo depois que as regras forem fechadas e a inclusão aprovada.
* **Notificações:** backlog, sem implementação aprovada.
* **Lançamento mobile:** sem compromisso. A versão mobile é **avaliada** na M14.
* Comprovantes em PDF, contorno nas fatias da rosca e as ideias deixadas fora da M1 (forma de gravação do e-mail, alfabeto internacional, ponto obrigatório no domínio): banco de ideias (seção 14).
* **L1 — limpeza das contas antigas de teste:** resolvida na instalação principal em 06/10/2026, por decisão da autora: banco reinicializado vazio (schema v8), com backup de recuperação fora do Git e nova referência.

## 2.3 Três metas distintas (P33)

* **Entrega publicada:** uma evolução do Sino, implementada, testada, documentada e publicada sozinha (critérios em 11.1). Não é preciso concluir todo o escopo para publicar melhorias.
* **Escopo completo da ERS v7.0:** todas as entregas do escopo (2.1) publicadas, **inclusive o envio real validado em ambiente restrito** (P30). Só então o aplicativo passa a se chamar **Sino 7.0** (critérios em 11.2).
* **Liberação para terceiros:** etapa posterior e separada, com **piloto restrito** antes da liberação mais ampla (11.3). Ter o provedor de e-mail funcionando **não** significa que o aplicativo está pronto para terceiros. O uso restrito **não** é tratado como isenção automática de obrigações legais.

## 2.4 Proposta candidata (não aprovada)

* **M13 — Categoria especial "Faturas"** (06/10/2026): agrupar despesas numa fatura, que aparece como uma única conta em Início, com o total calculado pela soma dos itens; os gráficos mostram as categorias reais dos itens, sem duplicar valores.
* A análise (impactos no modelo de dados, nas migrações, nas recorrências, nos totais, nos gráficos, na exclusão de usuários e nos comprovantes) e as decisões abertas (G1–G7) estão em [ERS_v7.0_propostas.md](ERS_v7.0_propostas.md#m13--categoria-especial-faturas-proposta-candidata-06102026).
* **Não faz parte do escopo nem dos critérios de conclusão** até a autora fechar as regras e aprovar a inclusão.
* Requisito já registrado pela autora (06/10/2026): parcelas e recorrências **não podem desaparecer silenciosamente** quando a fatura do mês for excluída ou estiver paga. O conflito com as propostas iniciais (casos C1–C4) será decidido antes das demais escolhas.
* Se aprovada, Faturas terá migração própria, conforme o modelo aprovado (9.1).

## 2.5 Licença (M9)

* **Objetivo da autora:** preservar a possibilidade de comercializar o Sino no futuro e impedir a comercialização por terceiros sem autorização.
* **Licença escolhida (P36, 06/10/2026): MIT + "Commons Clause" License Condition v1.0**, com os **textos oficiais sem alteração** de cláusulas (campos: Software: Sino; License: MIT License; Licensor: Carinne Batista). Substitui o caminho A (P35) e a licença própria, que ficam só no histórico do planejamento.
  * **Permitido** (licença-base MIT, sujeita à Commons Clause): usar (inclusive para fins pessoais, acadêmicos ou em empresas), estudar, copiar, modificar e redistribuir, inclusive versões modificadas e gratuitas, mantendo os avisos.
  * **Não concedido:** "Sell", ou seja, fornecer a terceiros, mediante pagamento ou outra contrapartida, um produto ou serviço cujo valor derive inteira ou substancialmente da funcionalidade do Sino. Cobranças por hospedagem, consultoria ou suporte relacionados ao Sino entram nessa condição **só quando** o valor deriva inteira ou substancialmente da funcionalidade dele; não se afirma que toda cobrança por esses serviços seja proibida. A autora **aceitou esse alcance**.
  * A autora continua livre para cobrar pela distribuição oficial (é a titular).
  * **Não é open source:** o resultado é apresentado como "MIT + Commons Clause" e "código-fonte disponível", nunca só como "MIT".
* **Alcance:** conteúdo de autoria da autora no repositório: código, testes, ferramentas e documentação associada (documentos, imagens, paleta, capturas, protótipos). Componentes de terceiros mantêm as próprias licenças. Isso resolve o bloco 3: os documentos e imagens seguem a mesma licença.
* **Histórico MIT:** até o commit `a8302c2` (último publicado sob MIT), inclusive, o repositório foi distribuído somente sob MIT; quem obteve essas versões mantém essas permissões sobre elas. O marco é o commit que introduz o novo `LICENSE`, logo depois de `a8302c2`. O commit local `33b8db2`, nunca publicado, foi refeito e consolidado com a licença (opção B, 06/10/2026), com uma referência local guardada para recuperação.
* **Revisão jurídica:** pendente. Inclui a contradição entre o texto da Commons Clause e as perguntas frequentes dela sobre consultoria, o critério "inteira ou substancialmente" e a leitura conjunta com a MIT.
* Histórico das decisões: bloco 1 (P34) e bloco 2 (P35, substituído) em [ERS_v7.0_propostas.md](ERS_v7.0_propostas.md#decisão-da-licença-em-blocos-06102026).

---

# 5. Regras de Negócio [v7 novo e alterações]

## 5.40 Caracteres de espaço e invisíveis (lista E1) [v7 novo, M1]

Lista fixa de **31 caracteres**, usada pelas regras 5.41 e 5.42:

| Grupo | Caracteres |
|---|---|
| Controles de espaço | U+0009, U+000A, U+000B, U+000C, U+000D, U+001C, U+001D, U+001E, U+001F, U+0085 |
| Espaços | U+0020, U+00A0, U+1680, U+2000 a U+200A, U+202F, U+205F, U+3000 |
| Separadores | U+2028, U+2029 |
| Invisíveis de largura zero | U+200B, U+FEFF |

Os 29 primeiros são o conjunto que o Python 3.11 considera espaço em branco; a lista explícita é a regra, independentemente da linguagem.

## 5.41 Entrada de e-mail [v7 novo, M1; completa 5.31]

* Em **Login, Cadastro, "Esqueci minha senha" e novo e-mail em Ajustes**, uma **limpeza de entrada única** do aplicativo remove os caracteres da lista 5.40 **somente das extremidades** do e-mail, antes de qualquer validação ou consulta.
* **Nada é removido do meio** do e-mail.
  * **Cadastro, "Esqueci minha senha" e novo e-mail:** se houver caractere da lista no meio, o e-mail é recusado com **"Remova os espaços ou caracteres invisíveis do meio do e-mail."**; nada é consultado nem enviado ao serviço.
  * **Login:** a consulta é feita normalmente com o e-mail limpo nas extremidades; a mensagem acima aparece **somente se o login falhar e a entrada contiver** caractere da lista no meio.
* **Ao enviar o formulário**, o campo de e-mail passa a mostrar a versão limpa nas extremidades, mesmo que outra validação impeça o envio; não muda durante a digitação nem ao sair do campo; mensagens que repetem o endereço usam a versão limpa.
* A **regra compartilhada de formato** (serviço, cliente e camada de dados) e o **contrato do serviço** não mudam; o login continua sem aplicar a regra de formato, para não bloquear contas antigas.
* Nenhum e-mail gravado é alterado; sem migração.

## 5.42 Espaços e invisíveis nas senhas [v7 novo, M1; completa 5.33]

* **Senhas existentes** são comparadas **exatamente** como digitadas: sem remover caracteres, sem normalização Unicode, sem segunda tentativa e sem alterar hashes.
* Nos **quatro lugares que conferem uma senha existente** (login, senha atual em "Alterar senha", senha em "Alterar e-mail" e senha em "Excluir conta"), **somente depois de uma recusa**, se a senha digitada tiver caractere da lista 5.40 no início ou no fim, a mensagem de recusa ganha: **"Verifique se há espaços ou caracteres invisíveis no início ou no fim da senha."** Se a senha for aceita, nada aparece. Quando 5.41 também se aplicar ao login, as duas orientações aparecem juntas, sem repetir a mensagem principal.
* **Senhas novas** (cadastro, "Alterar senha" e recuperação) são recusadas se tiverem, **em qualquer posição**, algum caractere da lista 5.40, com **"A senha não pode conter espaços nem caracteres invisíveis."** A proibição não se amplia a outros caracteres. A ordem das recusas é mantida: regras da senha antes de "As senhas não coincidem." (P11).

## 5.43 Usuário sem contas e mês vazio [v7 novo, M2; altera 5.15]

* **Usuário sem contas:** nenhuma conta dele em nenhum mês, calculado pelos dados atuais (sem marca de primeiro acesso); se todas forem excluídas, a regra volta a valer.
* Para esse usuário, no lugar do aviso "Suas contas estão em dia!" aparece **"Registre suas primeiras contas e tenha tudo sob controle."**, com ícone de adicionar na cor de ação e texto na cor principal, **sem aparência de confirmação de sucesso** e **sem ação de clique**. A lista do mês não mostra "Nenhuma conta neste mês.". O total (R$ 0,00) e o restante da tela não mudam; o cadastro continua pelo botão "+".
* **Usuário com contas e mês vazio:** "Nenhuma conta neste mês." e os avisos gerais atuais, sem a orientação acima.

## 5.44 Seletor de mês e ano [v7 novo, M3; completa 5.15 e 5.20]

* O mês e o ano de Início ganham um ícone de seta para baixo, na mesma cor do texto, e a dica **"Escolher mês e ano"**; texto e ícone formam uma única área clicável, separada das setas, acessível pelo teclado (Tab; Enter ou Espaço) e com nome acessível (por exemplo, "Escolher mês e ano, Outubro de 2026").
* O controle abre um **diálogo** em português com o **ano** (setas para trocar) e a **grade dos 12 meses**.
* **Faixa de anos:** do menor entre o ano atual e o primeiro ano com contas do usuário até o maior entre o ano atual + 5 e o último ano com contas; sem contas, do ano atual até + 5. *Atualização (16/10/2026, E11, decisão da autora):* a faixa inclui também o **ano exibido** em Início, mesmo quando ele está fora desses limites. As setas de ano param nos limites; as setas de mês de Início continuam livres.
* **Destaques:** período exibido com fundo preenchido; mês de hoje com contorno; os dois juntos quando coincidem, sem prejudicar a legibilidade; identificação acessível de cada estado.
* **Ações:** escolher um mês fecha e navega; **"Mês atual"** (ao lado de "Cancelar") navega para o mês de hoje e fecha, desativado quando ele já está exibido; **"Cancelar"** fecha sem mudar nada.
* **Geração sob demanda (5.20):** a regra não muda e só acontece **depois de selecionar um mês** (por clique ou "Mês atual"), nunca ao abrir o diálogo, trocar o ano ou cancelar.
* *Atualização (23/10/2026, correção da E11, Sino 6.9 em preparação):* a regra não muda. A estrutura anterior expunha elementos acessíveis separados (um elemento externo com o nome em volta do botão); na correção, o nome acessível fica no **próprio botão** que recebe o foco. O botão de abertura tem nome acessível ("Escolher mês e ano, <período>") atualizado a cada navegação; o estado "selecionado" pertence só aos **meses** do diálogo, e cada mês reúne nome, papel de botão e estado num único elemento focável. Ressalva: a inspeção pelo AT-SPI (Linux) confirmou o nome do botão de abertura, mas **não** verificou diretamente os nomes nem o estado "selecionado" dos 12 meses do diálogo; a acessibilidade integral do diálogo **não** está declarada aprovada (15.3, E11).

## 5.45 Descrição de até 1.000 caracteres [v7 altera 5.22 e 5.23, M4]

* Limite da descrição: **1.000 caracteres percebidos** (T5), em Nova conta, Editar conta (todos os escopos) e no modelo da série. Mantidos: remoção de espaços e quebras de linha nas pontas ao salvar, recusa sem corte automático e exibição completa em Detalhes.
* Campo do formulário: 2 a 8 linhas, com rolagem interna depois; contador "x/1000".
* Nenhum dado existente muda; sem migração. **Compatibilidade:** uma descrição com mais de 500 caracteres, aberta numa versão anterior do Sino, aparece inteira, mas só pode ser salva depois de reduzida a 500 (CT109 da v6.0).

## 5.46 Contador do nome do usuário [v7 altera 5.23, M5]

* O contador "x/70" do nome do usuário fica **sempre oculto** nos formulários de **Cadastro** e **Editar nome** (Ajustes).
* Continuam: o limite de 70 caracteres percebidos, a recusa da edição que o ultrapassaria, o aviso "Limite atingido", o som curto, a mensagem para nome antigo acima do limite e a validação ao salvar. Os demais contadores não mudam.

## 5.47 Calendário de datas [v7 novo, M6; completa 5.36 e RNF09]

* O calendário (Nova conta e Editar conta) aparece em **português do Brasil**, com textos "Selecione a data", "Cancelar", "OK" e mensagens de data inválida em português; a data continua **digitável** no formato **dd/mm/aaaa**; a semana começa no **domingo**.
* *Registro (16/10/2026, E8):* máscara automática de barras na digitação (por exemplo, `25122026` → `25/12/2026`) analisada a pedido da autora e **não adotada** nesta versão: o campo aberto pelo lápis é interno ao calendário nativo (DatePicker) do Flet 0.86.5, que não oferece filtro, máscara nem evento de digitação; a digitação continua em **dd/mm/aaaa**, com barras.
* O número do **dia de hoje** é legível em todos os estados, inclusive quando também é o dia selecionado (contraste mínimo de 4,5:1 nos dois temas).

## 5.48 Comparativo por categoria [v7 novo, M7; completa 5.28 e RF22]

* Novo cartão **"Comparativo por categoria"**, logo depois de "Gastos por categoria" (a rosca não muda): **colunas verticais**, uma por categoria do período exibido (mensal ou anual), com os **mesmos dados, ordem e cores** da rosca ("Sem categoria" por último, no cinza reservado).
* Valor em R$ acima de cada coluna; nome da categoria abaixo, completo, quebrando em até duas linhas; **todas** as categorias, com rolagem horizontal quando não couberem. Some quando o período não tem contas. Não gera ocorrências (P7).
* **Acessibilidade:** cada coluna tem **contorno** na cor do texto principal do tema (3:1 ou mais sobre o fundo do cartão nos dois temas), mantendo o preenchimento na cor da categoria; nome e valor em texto com 4,5:1; rótulos focáveis pelo teclado, e **clique, toque ou Enter** num rótulo mostram o nome completo e o valor, além da dica do mouse; nome acessível em cada rótulo.
* *Atualização (23/10/2026, E12, Sino 6.9 em preparação):* implementação. Subtítulo "Total de cada categoria no mês/ano" (D3). **Um gráfico de colunas por categoria** (alternativa A2), lado a lado numa área com rolagem horizontal, cada um com a **largura da sua categoria** — pela medição real do nome e do valor (W = (T + L) / 2 + margem, F6; heurística, não garantia universal) —, todos com a **mesma escala vertical**; valor em R$ fixo acima de cada coluna (balão G4, com espaço reservado acima da coluna mais alta). As larguras são ajustadas **sem recriar** os rótulos (o foco é preservado). Rótulo: botão com o nome inteiro (até duas linhas, sem reticências) e nome acessível "Casa, R$ 1.450,00"; Enter, clique ou toque mostram o aviso "Casa: R$ 1.450,00" (D2), **sem rolar** a área. **Rolagem híbrida:** com Tab e Shift+Tab o próprio sistema traz o rótulo focado à vista; para outros focos (por exemplo, pela tecnologia assistiva) o Sino rola o mínimo necessário depois de ~250 ms. Espaço de 5 px entre a base das colunas e o rótulo (o contorno de foco não toca a coluna) e de 10 px abaixo dos gráficos para a barra de rolagem. Ordem, cores, valores, rosca e "Sem categoria" por último inalterados. Sem migração. Resultados e limitações: 15.3 (E12).

## 5.49 Envio real de códigos em uso restrito [v7 novo, M8; completa 5.31 e 5.32]

* O serviço de códigos é publicado primeiro em **uso restrito aos endereços da autora**, com **restrição técnica de destinatários** no próprio serviço: fora da lista, nenhum código é enviado.
  * **Cadastro e alteração de e-mail:** recusa com a mensagem **"O envio de códigos está restrito nesta fase do Sino."**, no pedido, no reenvio e na validação do código (P39).
  * **Recuperação de senha:** mantém a resposta neutra e não envia; a resposta não revela se o endereço está na lista.
* Lista ausente **não** significa "aberto a todos"; a abertura exige uma mudança explícita de configuração, feita só depois das condições da seção 11.3.
* **Regras técnicas (E3, contrato v1.1; P39):**
  * a lista é um segredo de cada ambiente (`DESTINATARIOS_PERMITIDOS`), só com resumos HMAC dos endereços, até **50**; lista ausente, vazia ou inválida deixa o serviço **indisponível** (503); não existe modo sem restrição, nem no desenvolvimento;
  * a lista é conferida no pedido, imediatamente antes do envio (inclusive o envio em segundo plano da recuperação) e em **toda validação**: um destinatário removido não obtém nova autorização com um código antigo;
  * a comparação usa a regra de e-mail do contrato (espaços comuns nas bordas e minúsculas ASCII), sem a limpeza da M1;
  * o desenvolvimento e o modo de demonstração aceitam só três endereços fictícios (`pessoa1@demonstracao.invalid` a `pessoa3@…`), com envio apenas simulado na caixa local.
* **Limites aceitos e documentados (P39):**
  * a revogação **não é instantânea**: uma autorização já emitida continua válida até o `exp` original (no máximo o fim da validade do código); execuções já em andamento usam a configuração com que começaram;
  * a recusa pela lista vale para a lista **atual**; o desafio só fica invalidado de forma permanente quando uma validação acontece com o endereço fora da lista. Remover e incluir de novo, sem validação no meio, não invalida o desafio;
  * um pedido de cadastro ou alteração recusado não grava nada: a mesma `Idempotency-Key` pode ser aceita depois da inclusão do destinatário;
  * um desafio de recuperação sem envio nunca é reativado por repetição.
* Limites contra abuso do contrato v1 mantidos no uso restrito; reavaliados antes de abrir a terceiros.
* **Antes de habilitar o envio real**, os Termos e a Política são atualizados e o novo aceite é exigido (5.53).

## 5.50 Comprovantes em imagem [v7 novo, M10]

* **Onde:** em **qualquer** conta (paga, pendente ou atrasada). Anexar, trocar e remover em **Editar conta**; **"Ver comprovante"** em Detalhes abre a imagem num **diálogo**, ajustada à janela, com "Fechar"; sem miniatura permanente; sem abrir no visualizador do computador.
* **Tipos e limites:** só **JPEG e PNG**, identificados pelo conteúdo; até **5 MB** no arquivo original e na cópia guardada; até **10.000 px** no maior lado e **40 megapixels**; imagens animadas ou com vários quadros são recusadas; até **3 comprovantes por conta**. Arquivo inválido: "Não foi possível usar esta imagem. Use um arquivo JPEG ou PNG de até 5 MB."; nada é gravado.
* **Privacidade:** o Sino guarda uma **cópia** com a orientação correta, em sRGB e **sem metadados** (como localização GPS); o arquivo original do usuário nunca é alterado nem apagado.
* **Vínculo:** cada comprovante pertence a **uma ocorrência**; operações em séries nunca o copiam para outras ocorrências; ele acompanha a ocorrência ao mudar a data de vencimento e em "Transformar em recorrente".
* **Séries [altera 5.5 e 5.8]:** ao encerrar a recorrência ou alterar a frequência, ocorrências **com comprovante** são preservadas, como as pagas, com data de pagamento ou editadas individualmente; deixam de gerar novas repetições quando aplicável, mas mantêm dados e anexos.
* **Exclusões [completa 5.7 e 5.39]:** excluir a ocorrência, a série (no escopo escolhido) ou a conta de usuário apaga também os comprovantes ligados; os avisos de exclusão informam quantos comprovantes serão apagados; o resumo de "Excluir conta" inclui a quantidade. "Excluir este mês em diante" continua sem exceção para ocorrências pagas ou com comprovante. Apagar um arquivo do disco não garante que ele seja irrecuperável.
* **Consistência:** o banco nunca aponta para um arquivo incompleto; um arquivo só é apagado quando nenhum registro aponta para ele; remoções que falharem são refeitas na abertura do app; arquivos gerenciados pelo app sem referência vão para uma **quarentena de 30 dias**; se um arquivo sumir, a tela mostra "Comprovante indisponível" e permite remover o registro. Não há atomicidade entre o banco e os arquivos; a regra é a ordem das operações e a recuperação.
* **Habilitação:** a funcionalidade só fica disponível depois que os Termos e a Política forem atualizados e o novo aceite for exigido (5.53).

## 5.51 Backup e restauração da instalação [v7 novo, M10; completa RNF07]

* **Pacote completo** (banco, imagens referenciadas e manifesto com resumos SHA-256) criado e restaurado **somente por uma ferramenta externa de manutenção** (comando no terminal), **nunca** pelas telas dos usuários: o pacote contém os dados de **todos** os usuários da instalação.
* A ferramenta exige o **Sino fechado** e usa um **bloqueio compartilhado** com o app para impedir uso simultâneo; o controle de acesso também depende das permissões do sistema operacional sobre a pasta da instalação.
* O pacote é **criptografado com senha** definida na criação, pedida de forma interativa com confirmação, nunca guardada nem passada por comando, variável de ambiente ou log; perder a senha impede a restauração.
* **Restauração:** confere senha e integridade antes de extrair; recusa caminhos que saiam da pasta de destino, links simbólicos, nomes duplicados e conteúdos acima dos limites; extrai numa pasta temporária; guarda o estado atual num pacote antes de substituir; qualquer falha deixa o estado atual intacto.
* **Backups antes de migrações:** continuam **só do banco**, como na v6.0; isso **substitui** a ideia de um pacote completo antes de migrações. Esses backups **não garantem** a restauração das imagens. A documentação de atualização recomenda criar um pacote completo pela ferramenta antes de instalar uma versão nova.
* Os backups `sino_pre_migracao_*.db` existentes não são alterados.

## 5.52 Linhas de conta em janelas estreitas [v7 novo, M11; completa 5.15]

* Em Início, Ver status e Contas em atraso, abaixo de uma largura definida na implementação, a linha de conta se **empilha**: nome e subtítulo em cima, com toda a largura; valor, status e botões embaixo. Sem largura mínima de janela.
* Nomes **completos**, sem reticências, quebrando **entre palavras**; uma palavra que não caiba pode quebrar entre caracteres percebidos, sem separar emojis compostos.
* *Registro (16/10/2026, E10, decisão técnica da implementação):* a linha se empilha quando sobrariam menos de **100 px** para o nome lado a lado: abaixo de 370 px de página em Início e de 270 px em Ver status e Contas em atraso; o tamanho padrão do app (380 px) continua lado a lado. *Atualização (16/10/2026):* comportamento aprovado na validação manual da E10 (15.3).

## 5.53 Versões e aceite dos Termos e da Política [v7 altera 5.37 e P9, M12]

* Cada documento tem uma **versão** identificada pela data e exibida no texto ("Versão de dd/mm/aaaa"). As versões anteriores ficam preservadas no repositório; no app, só a vigente.
  * **Decisão P37 (06/10/2026):**
    * os textos aprovados em 04/10/2026 são a **primeira versão registrada** (classificação "inicial"), com a mesma data e o mesmo conteúdo;
    * a indicação "Versão de dd/mm/aaaa" aparece na tela do documento, fora do texto aprovado;
    * os textos históricos ficam em `docs/legal/`, um arquivo por documento e data (`termos-de-uso_AAAA-MM-DD.md`, `politica-de-privacidade_AAAA-MM-DD.md`).
* O Sino registra, por usuário, **qual versão** de cada documento foi aceita e quando. Usuários com aceite anterior ao versionamento ficam como "versão anterior ao versionamento".
  * **P37:** esses usuários **não recebem nenhuma versão atribuída** (a migração não cria registros; o aceite deles continua registrado só pela data em `termos_aceitos_em`) e **não precisam aceitar de novo** por causa da versão inicial.
  * **P38 (06/10/2026, substitui a parte da P37 sobre o momento do novo aceite):** os textos ganham a **versão de 06/10/2026**, classificada como **relevante**, porque introduz registros de dados antes não descritos. Ela corrige as afirmações de que não havia versionamento (Termos item 8; Política item 11) e descreve na Política os registros de aceite e de ciência, a finalidade, a exclusão e a permanência em backups (itens 2, 3, 8 e 10). **Todos os usuários existentes aceitam a versão de 06/10** no próximo login. O aceite original continua sem versão atribuída. Os textos de 04/10 ficam preservados em `docs/legal/`. O novo aceite das mudanças do envio real continua previsto na E4.
  * **P41 (13/10/2026, preparação do T2 da E4):** os textos ganham a **versão de 13/10/2026**, classificada como **relevante** nos dois documentos, porque muda o compartilhamento com provedores, a retenção, a localização e a transferência internacional dos dados e identifica quem opera o serviço. Termos itens 1, 2, 4 e 9; Política itens 1, 2, 7, 8, 10 e 12 (quem opera o serviço, fase restrita, Cloudflare, Resend, IP e localização, transferência internacional, contato). Os textos descrevem o funcionamento planejado do serviço real e **não afirmam que o envio real está ativo**. **Todos os usuários existentes aceitam a versão de 13/10** no próximo login. Os textos de 04/10 e 06/10 ficam preservados em `docs/legal/`. Revisão jurídica continua pendente (11.3, 13.4).
  * Além do aceite, o Sino registra a **ciência** de um ajuste menor ("Entendi" no aviso), para não repetir o aviso.
* **Mudança relevante** (dados tratados, finalidades, compartilhamento com terceiros ou provedores, retenção, direitos do titular, responsabilidades ou garantias, ou funcionalidade que trate dados pessoais de forma nova): **novo aceite** no próximo login, numa tela com o resumo das mudanças, "Aceitar" e "Sair"; sem aceite, o usuário não entra.
* **Ajuste menor** (redação, clareza, correções, links ou formatação, sem mudar o conteúdo): **aviso** com o resumo, sem bloquear.
* A classificação é feita pela **autora**, com apoio da revisão jurídica quando houver, e registrada nas notas da versão com o motivo; **na dúvida, a mudança é relevante**.
* Comprovantes (5.50) e envio real de e-mails (5.49) são mudanças relevantes: exigem textos atualizados e novo aceite **antes** de serem habilitados.
* O aceite continua obrigatório no cadastro (RF15).

---

# 6. Requisitos Funcionais [v7]

## 6.1 Requisitos alterados

| ID | Mudança na v7.0 | Regra |
|---|---|---|
| RF01 | Cadastro com limpeza das extremidades do e-mail, recusa de caracteres da lista no meio, recusa de senha nova com espaços ou invisíveis; contador do nome oculto | 5.41, 5.42, 5.46 |
| RF02 | Login com limpeza das extremidades do e-mail e orientações após recusa | 5.41, 5.42 |
| RF05 | Orientação para usuário sem contas; mês vazio diferenciado; linha empilhada em janela estreita | 5.43, 5.52 |
| RF08 | Exclusões também apagam comprovantes, com aviso da quantidade | 5.50 |
| RF15 | Aceite registra a versão de cada documento | 5.53 |
| RF22 | Complementado pelo comparativo em colunas | 5.48 |
| RF27, RF29 | Ocorrências com comprovante preservadas | 5.50 |
| RF31 | Detalhes ganha "Ver comprovante" quando houver | 5.50 |
| RF32, RF33 | Descrição de até 1.000 caracteres | 5.45 |
| RF35 | Contador do nome oculto | 5.46 |
| RF36, RF39 | Limpeza do e-mail; envio real em uso restrito | 5.41, 5.49 |
| RF37, RF38 | Senha nova sem espaços nem invisíveis; orientação após recusa da senha atual | 5.42 |
| RF41 | Documentos com versão exibida | 5.53 |
| RF43 | Resumo e exclusão incluem comprovantes | 5.50 |

## 6.2 Requisitos novos

| ID | Descrição | Regra |
|---|---|---|
| RF44 | Escolher mês e ano em Início por um diálogo, mantendo as setas | 5.44 |
| RF45 | Exibir o comparativo de gastos por categoria em colunas | 5.48 |
| RF46 | Anexar, trocar, remover e ver comprovantes em imagem | 5.50 |
| RF47 | Registrar a versão aceita dos Termos e da Política e exigir novo aceite em mudanças relevantes | 5.53 |
| RF48 | Criar e restaurar o pacote completo da instalação por ferramenta de manutenção | 5.51 |
| RF49 | Restringir tecnicamente os destinatários do serviço de códigos em uso restrito | 5.49 |

# 7. Requisitos Não Funcionais [v7]

| ID | Descrição | Situação |
|---|---|---|
| RNF09 | Legibilidade: novas telas e componentes (orientação de Início, seletor de mês, calendário, comparativo, comprovantes, tela de novo aceite) entram na verificação de contraste nos dois temas. *Atualização (23/10/2026, E12):* comparativo incluído na verificação; coluna com contorno visível exige 3:1 **do contorno** (preenchimento na cor da categoria é decorativo), sem contorno o preenchimento continua exigindo 3:1; contorno de foco dos botões (3:1) e aviso do comparativo (4,5:1) verificados; só a faixa técnica de medição invisível (opacity 0, fora da acessibilidade) fica fora da verificação (DF3) | v7 altera |
| RNF12 | Imagens de comprovantes processadas com limites de tamanho, dimensões e quadros, sem travar a interface, sem guardar metadados | v7 novo (5.50) |
| RNF13 | Pacote de backup com criptografia autenticada, senha nunca persistida, formato versionado e restauração que não grava fora da pasta de destino | v7 novo (5.51) |
| RNF14 | Acessibilidade pelo teclado e nomes acessíveis nos controles novos (seletor de mês, rótulos do comparativo, "Ver comprovante"). *Atualização (23/10/2026):* seletor de mês corrigido na Sino 6.9, em preparação (5.44); a verificação dos meses do diálogo por tecnologia assistiva continua pendente, e as setas de mês de Início continuam sem nome acessível (pendência anterior, 15.3). *Atualização (23/10/2026, E12):* rótulos do comparativo focáveis, com nome acessível "nome, valor"; Tab, Shift+Tab e foco pela tecnologia assistiva (AT-SPI) verificados na validação manual (5.48, 15.3); leitor de tela real não testado | v7 novo |

---

# 8. Interface e UX [v7]

* **Tela Principal:** 5.43, 5.44 e 5.52.
* **Nova conta / Editar conta:** descrição de 2 a 8 linhas (5.45); calendário em português (5.47); seção de comprovantes em Editar (5.50).
* **Detalhes:** botão "Ver comprovante" quando houver (5.50).
* **Gráfico:** cartão "Comparativo por categoria" (5.48).
* **Login, Cadastro, Ajustes:** 5.41, 5.42, 5.46; tela de novo aceite (5.53).

---

# 9. Modelo de Dados [v7]

## 9.1 Migrações da v7.0 [v7 altera, P31 de 06/10/2026]

As estruturas novas entram em **migrações separadas**, uma por entrega, para permitir entregas incrementais. Cada migração faz **backup do banco antes** e roda numa **transação única**: uma falha desfaz tudo e o app mostra a tela de erro, como na v6.0.

| Migração | Estrutura | Conteúdo (proposta técnica) | Melhoria | Entrega |
|---|---|---|---|---|
| **v9** | Aceites | Por usuário e documento: versão aceita e data e hora do aceite. Usuários existentes ficam como "anterior ao versionamento" quando a versão não puder ser determinada | M12 | 1 (M12 técnica) |
| **v10** | Comprovantes | Ocorrência à qual pertence, nome interno aleatório do arquivo, tipo, tamanho, resumo de integridade e data | M10 | M10 |
| v10 | Remoções pendentes | Nomes de arquivos a apagar depois de exclusões bem-sucedidas | M10 | M10 |
| posterior | Faturas | Conforme o modelo que vier a ser aprovado (M13, candidata) | M13 | Só se aprovada |

* A numeração segue a ordem real de implementação. Se a ordem das entregas mudar, a numeração acompanha, e cada migração continua cuidando só da sua estrutura.
* **Criar as estruturas de comprovantes não habilita anexos:** a interface fica **indisponível** até que os novos textos estejam publicados e o novo aceite seja exigido (5.50, 5.53).
* Antes da v10 ainda não existem comprovantes, então uma falha dela não afeta imagens. Migrações seguintes alteram só o banco.
* Os arquivos de imagem ficam fora do banco, em `database/comprovantes/` (fora do Git), com quarentena numa subpasta própria.
* Nenhuma outra melhoria do escopo exige migração.

---

# 10. Casos de Teste [v7 novo]

Os casos CT01–CT118 continuam válidos como regressão, com as alterações indicadas.

| ID | Cenário | Resultado esperado | Regra |
|---|---|---|---|
| CT119 | E-mail com espaços e U+FEFF nas extremidades no cadastro | Aceito; campo mostra a versão limpa ao enviar | 5.41 |
| CT120 | E-mail com espaço no meio no cadastro, na recuperação e no novo e-mail | "Remova os espaços ou caracteres invisíveis do meio do e-mail."; nada é enviado | 5.41 |
| CT121 | Login com espaço no meio do e-mail e credenciais erradas | "E-mail ou senha incorretos." mais a orientação do e-mail | 5.41 |
| CT122 | Login de conta antiga cujo e-mail gravado tem espaço no meio, digitado igual | Login aceito | 5.41 |
| CT123 | Login recusado com senha terminada em espaço | Mensagem de recusa mais a orientação da senha; nenhum hash alterado | 5.42 |
| CT124 | Login aceito com senha antiga que contém espaço | Aceito, sem orientação | 5.42 |
| CT125 | Senha nova com U+200B ou U+00A0 em qualquer posição | "A senha não pode conter espaços nem caracteres invisíveis." | 5.42 |
| CT126 | Usuário sem contas abre Início | Orientação de primeiro cadastro; sem "Suas contas estão em dia!" e sem "Nenhuma conta neste mês." | 5.43 |
| CT127 | Usuário com contas só em outros meses abre um mês vazio | "Nenhuma conta neste mês." e avisos atuais | 5.43 |
| CT128 | Abrir o seletor, trocar o ano e cancelar | Período inalterado; nenhuma ocorrência gerada | 5.44 |
| CT129 | Selecionar um mês futuro no seletor | Navega; geração sob demanda igual à das setas | 5.44 |
| CT130 | Faixa de anos com contas antes do ano atual e depois de + 5 | Faixa inclui todos os anos com contas | 5.44 |
| CT131 | "Mês atual" com o mês de hoje já exibido | Botão desativado | 5.44 |
| CT132 | Seletor pelo teclado | Abre com Tab + Enter; meses e botões acessíveis | 5.44, RNF14 |
| CT133 | Descrição com 1.000 e com 1.001 caracteres percebidos | 1.000 aceita; 1.001 recusada sem corte | 5.45 |
| CT134 | Nome do usuário no cadastro e em Editar nome | Sem contador; limite e "Limite atingido" mantidos | 5.46 |
| CT135 | Calendário com hoje selecionado | Número legível (4,5:1) nos dois temas; textos em português; semana a partir do domingo | 5.47 |
| CT136 | Comparativo no mensal e no anual | Mesmas categorias, ordem e cores da rosca; contorno com 3:1; valor e nome legíveis | 5.48 |
| CT137 | Nome completo de uma categoria pelo teclado e por clique | Exibido nos dois casos | 5.48 |
| CT138 | Pedido de código para endereço fora da lista em uso restrito | Cadastro e alteração recusados; recuperação neutra; nada enviado | 5.49 |
| CT157 | Código enviado; endereço removido da lista antes da validação | Cadastro e alteração: "O envio de códigos está restrito nesta fase do Sino.", sem contar tentativa e sem autorização; recuperação: mesma resposta de código incorreto, nunca autoriza; incluir o endereço de novo não reativa o desafio | 5.49 |
| CT158 | Envio barrado pela lista imediatamente antes do provedor (inclusive em segundo plano) | Nada enviado nem repetido; desafio registrado como bloqueado, nunca como falha do provedor; nenhuma autorização | 5.49 |
| CT139 | Anexar JPEG com GPS | Cópia guardada sem metadados e com orientação correta; original intacto | 5.50 |
| CT140 | Anexar arquivo acima de 5 MB, PNG animado, imagem de 12.000 px ou arquivo corrompido | Recusado com mensagem; nada gravado | 5.50 |
| CT141 | Quarto comprovante numa conta | Recusado | 5.50 |
| CT142 | Falha ao gravar o registro depois de gravar o arquivo | Nenhuma referência quebrada; arquivo removido ou enviado à quarentena | 5.50 |
| CT143 | Arquivo de comprovante apagado fora do app | "Comprovante indisponível"; tela não quebra | 5.50 |
| CT144 | Encerrar recorrência com ocorrência futura com comprovante | Ocorrência e comprovante preservados | 5.50 |
| CT145 | "Excluir este mês em diante" com ocorrências com comprovante | Aviso informa a quantidade; comprovantes apagados | 5.50 |
| CT146 | Excluir a conta de usuário com comprovantes | Registros e arquivos apagados; resumo informa a quantidade | 5.50 |
| CT147 | Ferramenta de backup com o Sino aberto | Recusa e orienta a fechar | 5.51 |
| CT148 | Restaurar pacote com senha errada ou conteúdo alterado | Recusado antes de extrair; estado atual intacto | 5.51 |
| CT149 | Restaurar pacote com caminho que sai da pasta de destino | Recusado; nada gravado fora | 5.51 |
| CT150 | Linha de conta em janela estreita | Linha empilhada; nome inteiro, sem quebra letra a letra | 5.52 |
| CT151 | Nova versão relevante dos Termos | Tela de novo aceite no próximo login; sem aceite, não entra | 5.53 |
| CT152 | Ajuste menor da Política | Aviso, sem bloquear | 5.53 |
| CT153 | Banco v8 com usuários existentes passa pela v9 | Backup criado; tabela de aceites criada; aceites antigos marcados; nenhum dado perdido | 9.1 |
| CT154 | Falha simulada no meio da v9 | Banco permanece v8; tela de erro | 9.1 |
| CT155 | Banco v9 passa pela v10 | Backup criado; estruturas de comprovantes e de remoções pendentes criadas; nenhum dado perdido; comprovantes ainda indisponíveis | 9.1 |
| CT156 | Falha simulada no meio da v10 | Banco permanece v9; tela de erro | 9.1 |

---

# 11. Critérios de Aceitação [v7 altera, P33]

## 11.1 Entrega publicada

Uma entrega (seção 15) está **concluída** quando:

* o conteúdo previsto para ela está implementado;
* os testes específicos passam e a suíte completa passa no fechamento, sem repetir validações já aprovadas sem motivo;
* a validação acompanhada foi feita, quando aplicável (conferência visual curta só dos pontos novos);
* uma migração, quando houver, roda sem perda de dados (RNF08), com backup do banco antes, e os casos de migração da entrega passam;
* nada depende de uma condição ainda não cumprida (por exemplo: comprovantes só depois do novo aceite; envio real só com textos atualizados e novo aceite);
* a documentação está atualizada:
  * notas da versão com o que ficou **concluído**, **parcial** e **pendente**;
  * situação da entrega na seção 15.3;
  * README, quando aplicável;
* commit e publicação no GitHub foram feitos **sem force**, com a versão do aplicativo identificada (15.2).

Uma entrega publicada com parte do conteúdo fica registrada como **parcial**, com as pendências explícitas. Ela não conta como concluída.

## 11.2 Escopo completo da ERS v7.0 (Sino 7.0)

O escopo completo está atendido quando:

* as entregas do escopo (2.1) estão **concluídas** (11.1);
* em particular:
  * a licença foi decidida e aplicada (E1);
  * o **envio real está publicado e validado em ambiente restrito** com os destinatários autorizados, com a restrição técnica verificada (CT138) (E4);
  * as melhorias de UX estão publicadas (E5–E12);
  * a avaliação de disponibilização está registrada, com as decisões da M14 e o plano do piloto (E13);
  * os comprovantes estão habilitados depois do novo aceite (E16–E18);
* as migrações v9 (aceites) e v10 (comprovantes) rodaram sem perda de dados;
* a escolha criptográfica do pacote de backup foi revisada (T8);
* a legibilidade (RNF09) e o acesso pelo teclado (RNF14) dos componentes novos foram verificados nos dois temas;
* os casos CT119–CT158 aplicáveis foram aprovados, com a regressão CT01–CT118 passando.

Sem o envio real validado em ambiente restrito (E4), o escopo **não** é declarado completo, mesmo com as demais entregas publicadas (P30).

**O escopo completo não libera o Sino para terceiros.**

## 11.3 Liberação para terceiros

**Piloto restrito** (primeiro passo, com pessoas convidadas e em número limitado), só depois de:

* as decisões da M14 tomadas (público, plataformas, empacotamento, instalação, atualizações, preservação dos dados, backup e recuperação, custos, segurança, privacidade e suporte);
* os Termos e a Política revistos para o piloto, com novo aceite. A exigência de **revisão jurídica concluída já para o piloto** é decisão aberta da M14; o planejamento propõe que sim;
* a lista de destinatários do serviço ampliada **explicitamente** só para os participantes, com registro.

**Liberação mais ampla**, só depois de, cumulativamente:

* piloto concluído e avaliado;
* revisão jurídica concluída (Termos, Política, licença, contrato do serviço de códigos e restrição de destinatários), incluindo as obrigações aplicáveis também ao uso restrito;
* pendências da M8 resolvidas (domínio, remetente, responsável pela operação, contato para titulares, planos e custos, prazos reais de retenção documentados);
* proteção contra abuso reavaliada;
* textos revisados publicados, com novo aceite;
* mudança explícita e registrada da configuração de destinatários;
* canais de distribuição (e lojas, se for o caso) definidos.

---

# 12. Rastreabilidade v6.0 → v7.0

| Item da v6.0 | Situação na v7.0 |
|---|---|
| 5.5, 5.8 | Alterados: ocorrências com comprovante preservadas (5.50) |
| 5.7, 5.39 | Completados: exclusões apagam comprovantes (5.50) |
| 5.15, 5.16 | Completados: 5.43, 5.44, 5.52 |
| 5.20 | Mantido; disparo só após selecionar mês no seletor (5.44) |
| 5.22, 5.23 | Alterados: 5.45, 5.46 |
| 5.28 | Completado: 5.48 |
| 5.31–5.35 | Completados: 5.41, 5.42, 5.49 |
| 5.36 | Completado: 5.47 |
| 5.37, P9 | Alterados: 5.53 |
| RNF07 | Completado: 5.51 |
| RNF09 | Ampliado para os componentes novos |
| Demais itens | Inalterados |

---

# 13. Decisões

## 13.1 Decisões de produto aprovadas (04/10/2026)

| ID | Decisão | Onde |
|---|---|---|
| P13 | Lista E1 de 31 caracteres; limpeza só nas extremidades do e-mail; nada removido no meio | 5.40, 5.41 |
| P14 | Limpeza centralizada no app; regra compartilhada e contrato do serviço preservados | 5.41 |
| P15 | Mensagens para caractere no meio do e-mail e para extremidades da senha; login preserva a consulta | 5.41, 5.42 |
| P16 | Campo de e-mail mostra a versão limpa ao enviar | 5.41 |
| P17 | Senha existente com comparação exata; senha nova sem os 31 caracteres | 5.42 |
| P18 | Usuário sem contas calculado pelos dados; orientação informativa, sem clique | 5.43 |
| P19 | Seletor de mês e ano: diálogo, faixa de anos, destaques, "Mês atual", geração só após seleção | 5.44 |
| P20 | Descrição de 1.000 caracteres; campo de 2 a 8 linhas | 5.45 |
| P21 | Contador do nome oculto nos dois formulários | 5.46 |
| P22 | Calendário em português, dd/mm/aaaa digitável, domingo primeiro | 5.47 |
| P23 | Comparativo em cartão próprio, colunas, valor acima, todas as categorias, contorno contrastante | 5.48 |
| P24 | Serviço em uso restrito com restrição técnica de destinatários; Cloudflare na conta da autora, plano gratuito priorizado, sem contratação autorizada; menor retenção adequada | 5.49 |
| P25 | Comprovantes: tipos, limites, privacidade, vínculo, preservação em séries, quarentena de 30 dias | 5.50 |
| P26 | Backup completo só por ferramenta externa, com o Sino fechado, criptografado com senha | 5.51 |
| P27 | Linhas empilhadas em janela estreita; nomes inteiros | 5.52 |
| P28 | Versões e aceite; critério de relevância; revisão jurídica antes de terceiros; histórico no repositório | 5.53 |
| P29 | M9 adiada; MIT mantida até pedido explícito da autora. **Reaberta em 06/10/2026** pelo pedido explícito previsto (P32) | 2.2 |
| P43 | (13/10/2026) **Caso 8 (CPU) no T2:** o critério original ("tempo de CPU por requisição abaixo de 10 ms nas métricas") é preservado e registrado como **não atendido** (P99 de tempo de CPU de 17,84 ms numa amostra de 13 invocações; mediana de 8,43 ms; 0 erros nas métricas agregadas; erros 1102 não auditados individualmente, com os Logs desligados). Segundo a documentação oficial da Cloudflare (13/10/2026), o limite nominal do Workers Free é 10 ms por requisição, com tolerância a excessos infrequentes, e os percentis podem passar do limite sem erro por amostragem e *rollover*. Critério operacional revisado para continuar os testes restritos: nenhum erro de CPU nas métricas agregadas, mediana abaixo de 10 ms e acompanhamento durante o T2 — atendido na amostra. Capacidade e desempenho para produção não validados; nenhuma mudança de plano nem otimização decidida. *Atualização (14/10/2026):* plano mantido (Workers Free, decisões 2 e 4 da produção restrita); otimização **O1** (assinatura Ed25519 pela WebCrypto nativa, `981d1e8`) publicada no GitHub, sem implantação na Cloudflare, com medições só locais; a P43 continua **pendente de medição real na Cloudflare** e o critério original, **não atendido**. *Atualização (15/10/2026):* medição na **produção restrita** (métricas agregadas, 11 invocações): CPU P50 5,54 ms; P90, P99 e P99,9 **14,4 ms**; 0 erros totais, 0 erros de CPU e 0 exceções não tratadas. O critério original continua **NÃO ATENDIDO**. **Decisão da autora: aceitação formal do risco, exclusivamente para a produção restrita**, com Workers Free mantido e sem otimização imediata (causa provável, não comprovada: início a frio; detalhes nas propostas). Reavaliar se surgirem erros, se a mediana passar de 10 ms e antes da liberação a terceiros | 5.49 |
| P42 | (13/10/2026) **T2 — preparação técnica do primeiro envio real:** Worker temporário `sino-servico-codigos-t2` (máximo de 7 dias, excluído ao encerrar) com token exclusivo (`TOKEN_ACESSO`, barreira adicional à lista de destinatários; não incorporado ao app, só no ambiente da cópia isolada); remetente `Sino <nao-responda@envios.appsino.com.br>` e Reply-To `sino.lembrete.contas@gmail.com`, obrigatórios e sem valor padrão; rodapé "Esta é uma mensagem automática do Sino. Precisa de ajuda? Entre em contato: sino.lembrete.contas@gmail.com"; Workers Logs e Traces desligados, com p99 de CPU e erros 1102 consultados sem ligá-los (inconclusivo se não disponível); campo `reply_to` conforme a documentação da Resend | 5.49 |
| P41 | (13/10/2026) **Versão de 13/10/2026 dos Termos e da Política**, relevante nos dois (muda compartilhamento com provedores, retenção, localização e transferência internacional; identifica quem opera o serviço): texto consolidado com quatro ajustes e dois refinamentos aprovados pela autora (12/10/2026); descreve o serviço real em fase restrita sem afirmar que o envio real está ativo; usuários existentes aceitam a nova versão no próximo login; versões de 04/10 e 06/10 preservadas em `docs/legal/`. Regras de operação (fora dos textos): não usar links públicos de e-mails nem recursos de IA da Resend com mensagens do Sino. Revisão jurídica pendente (papéis dos agentes de tratamento, pedidos dos titulares, transferência internacional) | 5.53 |
| P39 | (07/10/2026) **E3 — restrição de destinatários:** lista de resumos HMAC em segredo por ambiente, até 50 únicos; ausente, vazia ou inválida = 503; contrato v1.1 com `403 destinatario_nao_permitido` só no cadastro e na alteração (pedido, reenvio e validação), com a mensagem "O envio de códigos está restrito nesta fase do Sino."; recuperação neutra; conferência também na validação; ferramenta local sem mostrar e-mails, segredos ou resumos; restrição também no desenvolvimento e na demonstração, com três endereços fictícios (`pessoa1@demonstracao.invalid` a `pessoa3@…`) e envio só simulado. Limites aceitos: sem revogação instantânea (autorizações emitidas valem até o `exp`; execuções em andamento usam a configuração inicial); invalidação permanente só com validação durante a remoção; pedido recusado sem gravação pode ser aceito com a mesma chave depois da inclusão; recuperação sem envio nunca reativada. Sino 6.2 como versão candidata da E3, separada da publicação do serviço. Nenhum destinatário real autorizado | 5.49 |
| P38 | (06/10/2026) **Versão de 06/10/2026 dos Termos e da Política**, relevante (introduz registros de dados antes não descritos): corrige as afirmações sobre versionamento e descreve os registros de aceite e de ciência, a finalidade, a exclusão e a permanência em backups; usuários existentes aceitam a nova versão no próximo login, sem versão atribuída ao aceite original; textos de 04/10 preservados em `docs/legal/` | 5.53 |
| P37 | (06/10/2026) **E2 — versões e aceite:** textos atuais = primeira versão registrada (mesma data e conteúdo); quem aceitou antes do versionamento não recebe versão atribuída nem precisa aceitar de novo por esta mudança técnica; novo aceite obrigatório só com as mudanças relevantes do envio real; textos históricos em `docs/legal/` | 5.53 |
| P36 | (06/10/2026) **Licença: MIT + Commons Clause v1.0**, textos oficiais sem alteração, para usar um texto pronto. Substitui a P35 (caminho A e licença própria, mantidos só no histórico). A autora aceita as permissões de modificação e redistribuição gratuita da MIT, sujeitas à Commons Clause, e o alcance da restrição sobre produtos e serviços pagos. Alcance: código, documentos e imagens da autora; terceiros com as próprias licenças; histórico MIT até `a8302c2` preservado; não é open source | 2.5 |
| P35 | ~~(06/10/2026) **Licença, bloco 2 — caminho A:** uso pessoal, acadêmico e interno em empresas, estudo, compilação e modificação para uso próprio permitidos (compilar para si sem comprar a distribuição oficial é aceito); redistribuir cópias, distribuir versões modificadas e publicar em lojas exigem autorização prévia e por escrito, mesmo sem cobrança; comercialização por terceiros exige autorização; código público; licença própria separada das condições da distribuição oficial. Serviços pagos de suporte, instalação, consultoria e aulas pendentes~~ (substituída pela P36) | 2.5 |
| P34 | (06/10/2026) **Licença, bloco 1 — opção 1A:** uso livre (pessoal, acadêmico e em empresas, sem autorização individual, conforme a distribuição oficial gratuita ou paga) e estudo do código permitidos; proibido a terceiros vender, revender ou comercializar o aplicativo ou versões derivadas sem autorização; a autora preserva a cobrança pela distribuição oficial. Texto não escolhido (T1 ou T2); modificação e redistribuição gratuita no bloco 2 | 2.5 |
| P33 | (06/10/2026) **Organização da v7.0 em entregas** (substitui as ordens de prioridade anteriores, inclusive P32): a ERS v7.0 é o planejamento geral; cada entrega é publicada separadamente como versão do aplicativo. Prioridades: 1 licença; 2 envio real de e-mails (M12 técnica e M8, em ambiente restrito); 3 UX, uma entrega por melhoria; 4 disponibilização (M14) com piloto restrito; 5 comprovantes, Faturas (candidata) e pendências. Critérios distintos para entrega publicada, escopo completo e liberação para terceiros | 2, 11, 15 |
| P32 | ~~(06/10/2026) **Nova ordem:** primeiro a licença (M9 reaberta; decisão antes do próximo push), depois as melhorias simples de UX, uma por entrega, e depois o envio real de e-mails (M12 técnica e M8). Registro histórico da MIT preservado~~ (substituída pela P33) | 2.2, 15 |
| P31 | (06/10/2026) **Migrações separadas por entrega:** v9 só para versionamento e aceites (M12); comprovantes (M10) e Faturas (M13, se aprovada) em migrações posteriores. **Entregas incrementais**, um requisito por vez, cada uma com testes necessários, validação quando aplicável, documentação, commit e publicação no GitHub sem force; prioridade para a M8, que depende da M12 técnica (5.49). *A parte das migrações continua valendo; a ordem de prioridades foi substituída pela P33* | 9.1, 15 |
| P30 | A M8 faz parte da conclusão em uso restrito: sem o serviço publicado e validado com os destinatários autorizados, as melhorias locais são uma entrega parcial e a v7.0 não é declarada concluída; a abertura a terceiros continua separada e condicionada à revisão jurídica | 2.3, 11 *Com a P33, "conclusão" passa a ser "escopo completo" (11.2); cada entrega publicada tem situação própria (15.3).* |

## 13.2 Propostas técnicas sujeitas a revisão na implementação

| ID | Proposta |
|---|---|
| T6 | ~~Migração v9 única~~ (substituída por P31): cada migração (v9 aceites; v10 comprovantes e remoções pendentes) em transação única, com backup do banco antes |
| T7 | Comprovantes em arquivos com nome aleatório fora do banco, processados com biblioteca de imagens (Pillow) de versão fixada, fora da linha da interface |
| T8 | Pacote de backup: formato versionado, chave derivada por scrypt, AES-256-GCM em blocos autenticados com marca de fim. **Não é um formato aprovado como seguro:** na implementação, comparar com formatos e ferramentas de criptografia estabelecidos antes de criar um formato próprio, e submeter a escolha a revisão |
| T9 | Bloqueio compartilhado app/ferramenta por trava do sistema operacional; diferenças entre Linux e Windows testadas |
| T10 | Restrição de destinatários comparada por HMAC no serviço, com evolução do contrato (novo código de erro e testes de conformidade). *Concluída na E3 (contrato v1.1), publicada com a Sino 6.2; naquela data, o serviço continuava sem deploy. Atualização (16/10/2026): serviço implantado em produção restrita em 15/10/2026 (E4), com a lista de destinatários restrita aos endereços autorizados da autora.* |
| T11 | Calendário: idioma da página (pt-BR) e cor do número de hoje dependente do estado; pares de cores do calendário em `test_cores` |
| T12 | Rótulos do comparativo como controles focáveis; contorno das colunas entre 1 e 1,5 px |
| T13 | Linha de conta empilhada abaixo de uma largura medida na implementação; testes em três larguras |
| T14 | Seletor de mês como controle de botão (focável), com `Semantics` para o nome acessível |

## 13.3 Itens adiados (fora do escopo completo da v7.0)

* Notificações (backlog, sem implementação aprovada).
* Lançamento mobile (só avaliado na M14, sem compromisso).
* M13 — Faturas, enquanto for candidata.
* Comprovantes em PDF; contorno nas fatias da rosca; ideias deixadas fora da M1.

## 13.4 Pendências

* **M9 (licença):** escolhida (P36): MIT + Commons Clause. ~~Alterações preparadas, ainda não commitadas nem publicadas.~~ *Atualização (16/10/2026):* aplicada e publicada na E1, concluída em 06/10/2026 (commit `58b4382`). Pendentes: revisão jurídica e avaliação de registro no INPI (sem gasto autorizado).
* **M8 (envio real):** em andamento (E4; T2 encerrado em 14/10/2026; produção restrita implantada e validada em 15/10/2026, ver a atualização no fim deste item; ver propostas, "E4 — preparação", "continuação" e "E4 — T2: execução e testes reais"). Fatos: `appsino.com.br` registrado pela autora (R$ 40, até 07/10/2027; gasto assumido por ela); `envios.appsino.com.br` **verificado** na Resend (08/10/2026; TLS obrigatório "Aplicado"); conta na Cloudflare criada (sem projetos; `carinnebatista11.workers.dev`); DNS permanece no Registro.br. Aprovados em 08/10/2026: remetente `Sino <nao-responda@envios.appsino.com.br>`; Reply-To e contato de suporte e de dados pessoais `sino.lembrete.contas@gmail.com` (acompanhado por Carinne); textos atuais dos e-mails com o contato de ajuda (em 13/10/2026, P42, a frase "não é necessário respondê-la" foi substituída por "Esta é uma mensagem automática do Sino. Precisa de ajuda? Entre em contato: sino.lembrete.contas@gmail.com"). P40 (08/10/2026): ambiente remoto de testes separado aprovado (envio fictício, token, máximo de 7 dias após o deploy; IP da autora tratado pela Cloudflare, com ciência dela; `carinnebatista11.workers.dev` mantido); implementado, validado e revisado localmente (T0). **T1 encerrado** (12/10/2026): ambiente remoto de testes implantado em 08/10/2026, sem Resend; casos aprovados, com o caso 8 (CPU) só parcialmente validado; Worker excluído pela autora no painel (ver propostas, "T1 — encerramento"). Rastreamento de abertura e cliques na Resend conferido visualmente pela autora em 12/10/2026 (seção "Enable tracking metrics" só com "Configure", sem subdomínio de rastreamento; TLS "Enforced"); de novo em 13/10/2026, antes do primeiro envio real (sem configuração ativa; TLS "Enforced"; relato da autora, recuperado do histórico das conversas em 14/10/2026, sem captura técnica); e de novo em 13/10/2026, depois dos testes (só "Configure"; TLS "Enforced"); fontes públicas oficiais da Resend e da Cloudflare reconferidas em 14/10/2026, sem divergência com a Política (confirmadas ou parcialmente confirmadas; limitações e revisão jurídica pendente registradas nas propostas); passo 4 do T2 cumprido com ressalvas. **Textos dos Termos e da Política preparados para o T2** (versão de 13/10/2026, relevante, P41; publicados no repositório em 13/10/2026, commit 65a6b9d). **T2 preparado no código** (P42, 13/10/2026): Reply-To, rodapé com contato, remetente e Reply-To obrigatórios sem valor padrão, entrada `src/t2.ts` com token exclusivo, configuração `wrangler.t2.jsonc` e ferramentas `t2_segredos.py` e `t2_app.py`, com auditoria de segurança e correções (ver propostas, "E4 — T2: preparação técnica"). Código do T2 publicado em 13/10/2026 (00b45da). **T2 implantado em 13/10/2026** (Worker temporário, um destinatário autorizado): quatro e-mails reais entregues (Delivered na Resend); aprovados: cadastro, recuperação, código incorreto, restrição fora da lista e recuperação neutra para endereço sem conta; reenvio aprovado (liberação após 60 s e código novo aceito); **testes de 14/10/2026** (cópia isolada reaberta às 12h01, depois do reinício do computador; quatro envios, **oito no T2**): invalidação do código antigo depois do reenvio **aprovada**, esgotamento das 5 tentativas com recusa posterior do código verdadeiro **aprovado**, conteúdo dos e-mails **aprovado** por conferência visual (Reply-To igual à configuração), expiração **aprovada em parte** (recusa local do app, sem chamada ao Worker; expiração no serviço coberta pelos testes automáticos, não validada diretamente no T2); alteração de e-mail **fora do T2** por decisão da autora (cobertura automatizada e validação da E3); oito envios Delivered no painel da Resend (conferência visual da autora); passo 11 do T2 cumprido com ressalvas; métricas finais da Cloudflare (14/10/2026, janela "Last 24 hours", agregadas): 24 invocações, 92 subrequisições, 0 erros agregados, CPU P50 de 9,72 ms e P90/P99/P99,9 de 21,01 ms, oito respostas 2xx de `api.resend.com` — sem auditoria individual de requisições e sem valor de validação de produção; **T2 encerrado em 14/10/2026** (passo 12): cópia isolada auditada e removida, Worker `sino-servico-codigos-t2` excluído (sem Durable Objects listados) e chave `sino-t2-temporario` excluída na Resend (conferências visuais da autora), segredos locais removidos com validação prévia, logout do Wrangler e 14 registros locais do Wrangler removidos; `envios.appsino.com.br` e o DMARC `p=none` mantidos; `_dmarc.appsino.com.br` ausente (o domínio principal **não** está protegido por `p=reject`; causa desconhecida, investigação pendente); banco real e cinco backups iguais à ref7; `_dmarc.envios.appsino.com.br` publicado com `p=none` (o antigo `_dmarc.appsino.com.br` `p=reject` não existe na zona atual); primeiro DMARC FAIL inconclusivo, segundo PASS; caso 8 (CPU) com critério original não atendido e critério operacional revisado atendido na amostra (P43). Detalhes em propostas, "E4 — T2: execução e testes reais" e "E4 — avaliação dos critérios". E4 **não concluída** naquele momento (situação de 14/10/2026; ver as atualizações de 15/10/2026 no fim deste item): faltavam a produção restrita (serviço definitivo publicado e validado) e a configuração da versão do app; nenhum deploy definitivo; infraestrutura **não validada para produção** (revisão de segurança, política DMARC e pendências legais em aberto). **Nenhuma outra contratação ou cobrança autorizada; envio real só no T2 restrito (um destinatário autorizado); nenhum envio a terceiros.** Produção restrita (14 e 15/10/2026): decisões 1 a 6 aprovadas (5: Workers Secrets, KID exclusivo `prod-1`, cópias de recuperação da `CHAVE_HMAC` e da semente Ed25519, `.env` protegido; 6: observabilidade desligada, métricas agregadas, `wrangler tail` só em incidente autorizado), com 5 e 6 implementadas localmente em 15/10/2026 (sem commit nem deploy); decisões 1 a 4 (`workers.dev` com subdomínio neutro, sem DNS; Workers Free e Resend Free, sem plano pago; proteções atuais contra abuso mantidas na produção restrita, com risco residual aceito e proteção adicional por dispositivo a reavaliar antes da disponibilização a terceiros; investigar a CPU antes do deploy); decisões 7 a 9 e lançamento da versão do app **pendentes**; otimização O1 publicada no GitHub, sem implantação na Cloudflare (`981d1e8`: assinatura Ed25519 nativa, pacotes cerca de 46% menores no dry-run local; serviço 254/254, app 1034/1034); teste de carga local intermitente (1 de 3 antes e depois da O1, causa não comprovada); P43 pendente de medição real. Detalhes em propostas, "E4 — produção restrita: planejamento, decisões e otimização O1". Pendentes também: DMARC, M8-A, M8-F e M12. **Atualização (15/10/2026, à noite): produção restrita implantada e validada** — Worker `sino-servico-codigos` em `https://sino-servico-codigos.appsino.workers.dev` (Workers Free e Resend Free; dois destinatários autorizados da autora; segredos novos nos Workers Secrets, KID `prod-1`; deploy feito pela autora); app configurado para ela (commit B `db00f44`, publicado; app 1070/1070 com bloqueio de rede); teste de fumaça fora da lista com HTTP 403 e sem envio; primeiro cadastro definitivo da autora no banco principal (ref8); CT138 cumprido (alteração de e-mail fora da lista recusada, sem envio); decisão 8 cumprida (expiração recusada pelo próprio serviço: 201, 422 e 410); 2 envios Delivered na Resend; P43 com critério original **não atendido** e risco aceito só para a produção restrita. Ainda em 15/10/2026: **limpeza de segurança concluída** (cópia de recuperação criptografada confirmada, com cópia externa; segredos locais removidos; `wrangler logout`; registros locais do Wrangler removidos) e **decisão 9 atendida para a produção restrita** (`_dmarc.appsino.com.br` restaurado com `p=reject`; `envios` mantido com `p=none`). Continuam pendentes: lançamento formal da versão do app (15.2) (*pendente em 15/10/2026; cumprido em 16/10/2026 com o registro da Sino 6.3*); reavaliações antes de terceiros (limites, CPU/P43, abuso, observabilidade, DMARC de `envios` com `quarantine` ou `reject` e relatórios); M8-A, M8-F e M12. **M8 não concluída**; o Sino **não** está liberado ao público. **E4 encerrada formalmente pela autora em 15/10/2026** (produção restrita concluída e validada; P43 não atendida, com risco aceito só para a produção restrita). Pendências futuras da M8: reavaliação de desempenho e da P43; limites, cotas e proteção contra abuso; observabilidade e alertas; planos pagos, recursos e custos (M8-A; contratação **não aprovada**, só possibilidade futura); retenção dos provedores (M8-F); revisão jurídica (M12); DMARC do subdomínio de envio; ampliação segura dos destinatários; ~~lançamento formal da versão do app (15.2)~~ (cumprido em 16/10/2026: código da E4 registrado como **Sino 6.3**, 15.2 e 15.3).
* **M12:** ~~redação dos novos textos dos Termos e da Política~~ *Atualização (16/10/2026):* textos das versões de 06/10/2026 (P38) e de 13/10/2026 (P41, envio real em fase restrita) publicados, com novo aceite. Pendentes: contratação e realização da revisão jurídica; textos para os comprovantes (M10), a redigir e aprovar antes de habilitar essa funcionalidade (5.50, 5.53).
* **M14 (disponibilização):** todas as decisões da avaliação (seção 15.1, E13).
* **M10:** revisão da escolha criptográfica (T8); trava de arquivos em Linux e Windows (T9).
* **M13 (Faturas):** conflito C1–C4 e decisões G1–G7 abertos; inclusão no escopo a aprovar.
* ~~**L1:** limpeza das contas antigas de teste.~~ Resolvida em 06/10/2026 pela reinicialização do banco da instalação principal (backup de recuperação e ref6).

---

# 14. Fora dos Requisitos Funcionais

## 14.1 Banco de ideias (não aprovado para a v7.0)

Os itens da seção 14.1 da v6.0, mais: comprovantes em PDF; contorno nas fatias da rosca; forma de gravação do e-mail (normalizado ou em duas colunas); e-mails internacionais; ponto obrigatório no domínio do e-mail.

---

# 15. Plano de Implementação [v7 altera, P33 de 06/10/2026]

Esta organização **substitui as ordens de prioridade anteriores** (P32 e a ordem da P31). As migrações separadas da P31 continuam valendo (9.1).

**Cada entrega passa por:**

* implementação e testes necessários, sem repetir os já aprovados sem motivo;
* validação, quando aplicável;
* documentação;
* commit e publicação no GitHub, **sem force**.

Uma entrega só começa com a autorização da autora. Uma entrega que só registra decisões (sem código) atualiza a ERS e é publicada junto da próxima entrega com código, ou sozinha, se a autora preferir.

## 15.1 Entregas

| Entrega | Prioridade | Conteúdo | Depende de | Migração |
|---|---|---|---|---|
| **E1** | 1 — Licença | M9: decidir em blocos; aplicar o `LICENSE` escolhido, o aviso dos documentos e materiais, o registro do marco e das versões publicadas sob MIT, o README e as notas da versão. **Antes do próximo push** | Decisões da autora; revisão jurídica conforme o bloco correspondente | — |
| **E2** | 2 — E-mail | M12 técnica: versão nos Termos e na Política ("Versão de dd/mm/aaaa"), histórico dos textos no repositório, registro do aceite por versão, tela de novo aceite (relevante) e aviso (menor) | — | **v9** (aceites) |
| **E3** | 2 — E-mail | Restrição técnica de destinatários no serviço (T10), evolução do contrato (novo código de erro, testes de conformidade) e mensagem do app. **Sem publicar o serviço** | — | — |
| **E4** | 2 — E-mail | Envio real em ambiente restrito: escolha do provedor (Resend ou outro) e da alternativa de envio; domínio e remetente, ou a alternativa sem domínio, se aprovada; responsável e contato; textos atualizados (provedores, retenção real, responsável, contato) com novo aceite; segredos e configuração; publicação do ambiente de teste, medição de CPU e validação; produção restrita; configuração da versão do app; validação (CT138, entrega real, expiração, tentativas, reenvio, neutralidade da recuperação) | E2, E3; pendências da M8 (13.4); sem contratação nem cobrança | — |
| **E5** | 3 — UX | M5: contador do nome oculto, mantendo o limite | — | — |
| **E6** | 3 — UX | M4: descrição de até 1.000 caracteres (campo de 2 a 8 linhas) | — | — |
| **E7** | 3 — UX | M2: mensagem para usuário sem contas | — | — |
| **E8** | 3 — UX | M6: calendário em português e contraste do dia atual | — | — |
| **E9** | 3 — UX | M1: espaços e invisíveis no e-mail; orientações e regras das senhas | — (toca os mesmos fluxos de Login e Cadastro que E3 e E4, por isso vem depois delas) | — |
| **E10** | 3 — UX | M11: nomes e ações legíveis em janelas estreitas | — | — |
| **E11** | 3 — UX | M3: seletor de mês e ano | E7 recomendada antes (mesma área de Início) | — |
| **E12** | 3 — UX | M7: comparativo por categoria em colunas | E10 recomendada antes (larguras e quebras de texto) | — |
| **E13** | 4 — Disponibilização | M14: avaliação de desktop e/ou mobile e decisões (ver propostas, M14). Resultado: plano do piloto restrito. Entrega de decisões | E4 recomendada (o piloto depende do e-mail real) | — |
| **E14** | 4 — Disponibilização | Preparação do piloto conforme as decisões da E13: empacotamento, instalação, atualização, preservação dos dados, backup e recuperação, avisos de terceiros, suporte. Pode virar várias entregas | E13 | — |
| **E15** | 4 — Disponibilização | **Piloto restrito** com pessoas convidadas (11.3) | E14; condições de 11.3 | — |
| **E16** | 5 — Maiores | M10, parte 1: armazenamento, consistência, processamento seguro das imagens, telas, regras de séries e exclusões. **Sem habilitar** | E2 | **v10** (comprovantes e remoções pendentes) |
| **E17** | 5 — Maiores | M10, parte 2: ferramenta de manutenção (bloqueio compartilhado, pacote criptografado, restauração segura) | E16; revisão de T8 e T9 | — |
| **E18** | 5 — Maiores | M10, parte 3: habilitar comprovantes | E16, E17; textos atualizados e novo aceite (5.53) | — |
| **F1** | 5 — Maiores | M13: fechar as regras de Faturas (C1–C4, depois G1–G7 em blocos menores) e decidir a inclusão. Entrega de decisões; as entregas de implementação só são definidas depois da aprovação | Decisão da autora | Própria, se aprovada |

* **Ordem da prioridade 3:** sugerida pela complexidade e pelas dependências, das mais simples para as mais complexas. A autora pode reordenar.
* **Antecipação:** se a avaliação da E13 concluir que o piloto precisa do pacote de backup completo, a E17 pode ser antecipada (depois da E16).
* **Liberação mais ampla:** só com as condições de 11.3, depois da E15.

## 15.2 Versões

* **Documento:** a ERS continua como **v7.0** (planejamento geral); cada revisão é registrada por data no histórico.
* **Aplicativo:** na revisão de 06/10/2026, a última versão publicada era a **Sino 6.0**. *Atualização (16/10/2026):* versões publicadas até agora:
  * **Sino 6.0** — 04/10/2026 (ERS v6.0, concluída para portfólio e demonstração local);
  * **Sino 6.1** — E2, 06/10/2026;
  * **Sino 6.2** — E3, 07/10/2026;
  * **Sino 6.3** — E4, registro formal em 16/10/2026. Corresponde ao código da E4 já publicado no GitHub, até o commit `db00f44`; a E4 foi encerrada operacionalmente em 15/10/2026, com ressalvas (15.3). O registro **não** é uma nova implantação, **não** abre o Sino ao público e **não** amplia os destinatários do serviço de códigos. Registro publicado no GitHub em 16/10/2026 (`a57d73f`).
  * **Sino 6.4** — E5 (M5, contador do nome do usuário oculto), implementada e validada em 16/10/2026. Na data deste registro, o commit e a publicação no GitHub estavam pendentes (15.3). *Atualização (16/10/2026):* publicada no GitHub no commit `c2961587d7f7868efcb7b58ade1e7f73cf8178b3`.
  * **Sino 6.5** — E6 (M4, descrição de até 1000 caracteres percebidos), implementada e validada em 16/10/2026. Na data deste registro, o commit e a publicação no GitHub estavam pendentes (15.3). *Atualização (16/10/2026):* publicada no GitHub no commit `3fc862b9fae5bd8fa787553b1d7f55dc41113e1c`.
  * **Sino 6.6** — E7 (M2, orientação para o usuário sem contas), implementada e validada em 16/10/2026. Na data deste registro, o commit e a publicação no GitHub estavam pendentes (15.3). *Atualização (16/10/2026):* publicada no GitHub no commit `de06c4eaa2990cfb34a94d55da62a73d896f4e00`.
  * **Sino 6.7** — E8 (M6, calendários) e E11 (M3, seletor de mês e ano), validadas e publicada no GitHub em 16/10/2026, no commit `feat: release Sino 6.7 calendars and month selector` (identificador no histórico do Git), numa publicação conjunta (validação manual 24/24; 1146 testes automatizados aprovados). *Registro anterior, preservado:* (prevista) implementadas em 16/10/2026 para publicação conjunta. ~~Validação manual parcial~~ *Atualização (16/10/2026):* validação manual concluída, 24/24 testes aprovados (15.3). Na data deste registro, o commit e a publicação no GitHub estavam pendentes.
  * **Sino 6.8** — E9 (M1, espaços e invisíveis no e-mail e nas senhas) e E10 (M11, linhas de conta em janelas estreitas), implementadas, validadas e **publicada no GitHub em 16/10/2026**, no commit `cc2395c24d9435e8ca1ea511ffab73abf5a0f13a`, numa publicação conjunta (validação manual 15/15; 1188 testes automatizados aprovados). *Registro anterior, preservado:* ~~(aguardando publicação)~~ implementadas e validadas em 16/10/2026 para publicação conjunta (validação manual 15/15; 1188 testes automatizados aprovados). *Registro anterior, preservado:* (em preparação) implementadas em 16/10/2026 para publicação conjunta. Na data deste registro, ~~a validação manual,~~ o commit e a publicação no GitHub estavam pendentes (15.3). *Atualização (16/10/2026):* validação manual concluída, 15/15 testes aprovados (15.3); commit e publicação no GitHub continuam pendentes.
  * **Sino 6.9** — correção da E11 (M3) e E12 (M7), implementadas, validadas e **publicada no GitHub em 23/10/2026**, nos commits `1141d68b84b23e09a5a1dfd98217fe4120f3abd7` (E11) e `6e3241ce87c637fa911797989616fdf972ffc9b6` (E12), em commits separados (suíte completa 1264/1264 depois da A2; validação manual F9 concluída). *Registro anterior, preservado:* ~~**em preparação, não publicada**~~: correção da E11 (M3, seletor de mês e ano; decisão D4 da autora) e E12 (M7, gráfico de colunas), em commits separados. Na data deste registro (23/10/2026), a correção da E11 estava implementada e testada, sem commit (15.3); a implementação da E12 não tinha sido iniciada. Commit e publicação no GitHub pendentes. *Atualização (23/10/2026):* correção da E11 registrada em commit local (sem publicação); E12 implementada (alternativa A2) e validada manualmente (F9), **sem commit**; documentação (F10) atualizada nesta revisão; revisão final, commit da E12 e publicação (F11) pendentes. Sino 6.9 **não publicada**.
* Cada entrega com código publicada recebe a próxima versão **menor**:
  * a primeira entrega com código publicada recebe a Sino 6.1; as seguintes recebem 6.2, 6.3, e assim por diante, **na ordem em que forem publicadas**, mesmo que a ordem da tabela mude;
  * uma correção sem funcionalidade nova recebe uma versão de **correção** (por exemplo, 6.3.1).
* **Sino 7.0:** nome reservado para quando o **escopo completo** (11.2) for atendido.
* **Proposta técnica:** marcar cada versão publicada com uma etiqueta no Git (por exemplo, `v6.1.0`). *Situação (16/10/2026):* proposta não aplicada; nenhuma etiqueta de versão foi criada (6.1, 6.2 e 6.3 registradas só na documentação e nas mensagens dos commits). As notas da versão ganham uma seção por versão, com as entregas incluídas e o que ficou concluído, parcial ou pendente.

## 15.3 Situação das entregas

| Entrega | Situação | Versão do app |
|---|---|---|
| E1 | **Concluída** (publicada em 06/10/2026, commit 58b4382): licença MIT + Commons Clause | — (sem código) |
| E2 | **Concluída** (publicada em 06/10/2026): versões dos documentos (04/10 inicial; 06/10 relevante, P38), registro dos aceites e da ciência, tela de novo aceite e aviso, migração v9. 926 testes aprovados (bancos temporários); validação visual em cópia isolada aprovada (leitura dos documentos; novo aceite com "Sair" e "Aceitar"; aviso de ajuste menor com versão fictícia). Banco principal na v9 desde 06/10 21:25 (abertura de origem não confirmada; mantido pela autora; ref7) | Sino 6.1 |
| E3 | **Concluída** (publicada no GitHub em 07/10/2026; código no commit a76da70): restrição de destinatários, contrato v1.1, P39. Publicação do código no GitHub: o serviço de códigos **não** foi publicado (sem deploy), não há envio real de e-mails nem liberação para terceiros (E4 e 11.3). Suítes: 950 testes do aplicativo e 215 do serviço aprovados (bancos temporários e ambientes isolados); validação manual em demonstração isolada do commit local a76da70 (07/10/2026): as mensagens das telas foram observadas pela autora (restrição no cadastro e na alteração fora da lista; mensagem neutra na recuperação); os efeitos foram confirmados pelos artefatos (caixa local com exatamente duas mensagens, cadastro para `pessoa1@demonstracao.invalid` e alteração para `pessoa2@demonstracao.invalid`; banco da demonstração com uma conta, no e-mail alterado, e nenhuma conta dos pedidos recusados; registro do serviço com os dois 403 e o 202 neutro). CT157 e CT158 cobertos só pelos testes automáticos. | Sino 6.2 |
| E4 | **Concluída em 15/10/2026 por decisão formal da autora** (produção restrita, com ressalvas: P43 não atendida e risco aceito só para a produção restrita; M8 aberta; Sino não liberado ao público) — preparação: domínio e conta da Resend (07/10/2026); domínio de envio verificado, remetente e Reply-To aprovados, conta da Cloudflare criada (08/10/2026); ambiente remoto de testes (P40) implantado em 08/10/2026 sem Resend; **T1 encerrado** em 12/10/2026 (casos aprovados, caso 9 de IP real aprovado, caso 8 de CPU parcialmente validado; Worker excluído); textos dos Termos e da Política **preparados para o T2** (versão de 13/10/2026, relevante, P41; publicados em 13/10/2026, 65a6b9d); **T2 preparado no código** (P42: entrada com token, Reply-To, remetente obrigatório, `wrangler.t2.jsonc`, ferramentas dos segredos e da cópia isolada; publicado em 00b45da); **T2 executado e encerrado** (13 e 14/10/2026: envio real restrito a um destinatário; oito envios Delivered; testes concluídos com a expiração aprovada em parte e a alteração de e-mail fora do T2; desmontagem técnica concluída em 14/10/2026). Produção restrita em planejamento (14/10/2026): decisões 1 a 4 aprovadas, 5 a 9 pendentes; otimização O1 publicada no GitHub (`981d1e8`), sem deploy. **15/10/2026:** decisões 5 e 6 publicadas (`8a659cc`); app configurado para a produção (commit B, `db00f44`, publicado); **produção restrita implantada e validada** (dois destinatários autorizados; cadastro definitivo; CT138 e expiração no serviço cumpridos; 2 envios Delivered); P43 não atendida, com risco aceito só para a produção restrita. Critérios da E4 atendidos para a produção restrita **com ressalvas** (P43; restrição da lista na recuperação só por testes automáticos; DMARC de `envios` com `p=none`); limpeza de segurança concluída e decisão 9 atendida para a produção restrita (15/10/2026); **encerramento formal pela autora em 15/10/2026**; ~~lançamento formal da versão do app pendente~~ **versão registrada formalmente como Sino 6.3 em 16/10/2026** (código da E4 já publicado, até `db00f44`; sem nova implantação, sem abertura ao público e sem ampliação dos destinatários) | Sino 6.3 |
| E5 | **Concluída** (publicada no GitHub em 16/10/2026, commit `c2961587d7f7868efcb7b58ade1e7f73cf8178b3`; critérios de 11.1 atendidos). *Registro anterior, preservado:* **Implementada e validada; publicação pendente** (16/10/2026; M5, regra 5.46; RF01 e RF35 na parte do contador; CT134): contador "x/70" sempre oculto em "Nome completo" (Cadastro) e em "Nome" (Editar nome, em Ajustes); preservados o limite de 70 caracteres percebidos, a recusa do 71º, "Limite atingido", o aviso sonoro, a mensagem para nome antigo acima do limite e a validação ao salvar; contadores dos demais campos (nome da conta, descrição, nome da categoria) mantidos. Sem migração. 1082 testes do aplicativo aprovados (12 novos), em bancos temporários, sem rede e com bloqueio de acesso ao banco real; validação manual em cópia isolada (banco próprio, serviço de códigos desativado, dois usuários fictícios): 7/7 cenários aprovados pela autora, nos temas Claro e Escuro, sem deslocamento visual percebido; banco real e backups preservados (metadados conferidos). **Publicação no GitHub pendente na data deste registro**: pelo critério 11.1, a entrega se completa com o commit e a publicação; até lá, pela legenda abaixo, continua **Pendente** (não publicada) | Sino 6.4 |
| E6 | **Concluída** (publicada no GitHub em 16/10/2026, commit `3fc862b9fae5bd8fa787553b1d7f55dc41113e1c`; critérios de 11.1 atendidos). *Registro anterior, preservado:* **Implementada e validada; publicação pendente** (16/10/2026; M4, regra 5.45; RF32 e RF33; CT133; decisões M4-1 e M4-2): limite da descrição de 500 para **1000 caracteres percebidos** (`LIMITE_DESCRICAO`), com a contagem por grafemas, a normalização (espaços e quebras nas pontas), a recusa sem corte automático, "Limite atingido" e o aviso sonoro preservados; contador "x/1000" e dica "Até 1000 caracteres" (sem separador, decisão Q1 de 16/10/2026); campo de descrição de 2 a 8 linhas, com rolagem interna depois, em Nova conta e Editar conta; limite aplicado em contas únicas, ocorrências ("Somente este mês"), "Este mês em diante" e modelo da série; Detalhes com a descrição inteira; descrição legada acima de 1000 exibida inteira e salva só depois de reduzida. Sem migração. 1097 testes do aplicativo aprovados (15 novos), em bancos temporários, sem rede e com bloqueio de acesso ao banco real; validação manual em cópia isolada (banco próprio, serviço de códigos desativado, dados fictícios), depois encerrada e removida: 7/7 cenários e 30/30 verificações aprovados pela autora, nos temas Claro e Escuro; banco real e backups preservados (metadados conferidos). **Publicação no GitHub pendente na data deste registro**: pelo critério 11.1, a entrega se completa com o commit e a publicação; até lá, pela legenda abaixo, continua **Pendente** (não publicada) | Sino 6.5 |
| E7 | **Concluída** (publicada no GitHub em 16/10/2026, commit `de06c4eaa2990cfb34a94d55da62a73d896f4e00`; critérios de 11.1 atendidos). *Registro anterior, preservado:* **Implementada e validada; publicação pendente** (16/10/2026; M2, regra 5.43; RF05; CT126, CT127; RNF09; decisões U1–U4): usuário **sem nenhuma conta, em nenhum mês** (calculado pelos dados atuais a cada atualização de Início, depois da geração sob demanda; sem marca de primeiro acesso; nova consulta só de leitura `usuario_tem_contas` em `database/db.py`) vê, no lugar de "Suas contas estão em dia!", a orientação **"Registre suas primeiras contas e tenha tudo sob controle."**, com ícone de adicionar (`ADD_CIRCLE_OUTLINE`, 16) na cor de ação e texto em negrito, tamanho 13, na cor principal, sem aparência de sucesso e **sem ação de clique**; a lista do mês não mostra "Nenhuma conta neste mês."; total, aviso dos próximos 7 dias e botão "+" inalterados. Usuário com contas, inclusive só em outros meses ou em séries: avisos e "Nenhuma conta neste mês." como antes (U3). A primeira conta tira a orientação; excluir todas faz ela voltar. "Ver status" mantém "Nenhuma conta cadastrada neste mês." (fora do escopo). Contraste nos dois temas (RNF09). Sem migração. 1111 testes do aplicativo aprovados (14 novos), em bancos temporários, sem rede e com bloqueio de acesso ao banco real; validação manual em cópia isolada (banco próprio, serviço de códigos desativado, três usuárias fictícias), depois encerrada e removida: 7/7 cenários aprovados pela autora em 16/10/2026; banco real e backups preservados (metadados conferidos). **Publicação no GitHub pendente na data deste registro**: pelo critério 11.1, a entrega se completa com o commit e a publicação; até lá, pela legenda abaixo, continua **Pendente** (não publicada) | Sino 6.6 |
| E8 | **Concluída** (publicada no GitHub em 16/10/2026, no commit `feat: release Sino 6.7 calendars and month selector` (identificador no histórico do Git), junto da E11; validação manual 11/11; critérios de 11.1 atendidos). *Registro anterior, preservado:* **Implementada e validada; publicação pendente** (validação manual: 11/11 testes aprovados, 16/10/2026; ver E11) (16/10/2026; M6, regra 5.47; P22; CT135; RNF09; decisões M6-A e M6-B): número do dia de hoje com cor por estado (selecionado: texto sobre ação, 5,36:1 no Claro e 5,53:1 no Escuro; sem seleção: cor de ação com contorno); **português do Brasil** declarado à página (`locale_configuration`); textos próprios nos **três** calendários (vencimento em Nova conta e em Editar conta; data de pagamento em Editar conta): "Selecione a data", "Cancelar", "OK", "Data (dd/mm/aaaa)", "Formato inválido. Use dd/mm/aaaa." e "Data fora do intervalo permitido."; digitação dd/mm/aaaa pelo lápis mantida (M6-A); semana a partir do domingo pelo idioma pt-BR (M6-B, conferida na validação manual). Intervalos (2000–2100), gravação em ISO, recusa de data de pagamento futura e recorrências inalterados. Máscara automática de barras na digitação (por exemplo, `25122026` → `25/12/2026`) analisada a pedido da autora e **não adotada** nesta versão: o campo aberto pelo lápis é interno ao calendário nativo (DatePicker) do Flet 0.86.5, que não oferece filtro, máscara nem evento de digitação; a digitação continua em **dd/mm/aaaa**, com barras. Sem migração. Testes e validação manual: ver E11 (publicação conjunta). Pela legenda abaixo, continua **Pendente** (não publicada) | Sino 6.7 |
| E9 | **Concluída** (implementada, validada e publicada no GitHub em 16/10/2026, commit `cc2395c24d9435e8ca1ea511ffab73abf5a0f13a`, junto da E10; validação manual 15/15 conjunta com a E10; 1188 testes automatizados aprovados; critérios de 11.1 atendidos). *Registro anterior, preservado:* **Implementada e validada; publicação pendente** (validação manual conjunta da E9 e da E10: 15/15 testes aprovados, 16/10/2026; a tentativa específica com U+200B (espaço de largura zero) no Cadastro não teve confirmação manual independente; esse caso está coberto pelos testes automatizados; ver E10). *Registro anterior, preservado:* **Implementada; validação manual pendente; publicação pendente** (16/10/2026; M1, regras 5.40, 5.41 e 5.42; P13–P17; CT119–CT125; decisões E1–E4, S1 e S2): lista E1 de 31 caracteres num módulo comum (`database/espacos.py`); **limpeza única** do e-mail digitado só nas extremidades em Login, Cadastro, "Esqueci minha senha" e novo e-mail em Ajustes, com o campo mostrando a versão limpa ao enviar, mesmo que outra validação impeça o envio; caractere da lista no meio do e-mail: "Remova os espaços ou caracteres invisíveis do meio do e-mail." (Cadastro, recuperação e novo e-mail, sem consultar nem enviar; no Login, só depois da recusa, com a consulta preservada); depois de uma recusa nos quatro lugares que conferem uma senha existente (login, senha atual em "Alterar senha", senha em "Alterar e-mail" e em "Excluir conta"), "Verifique se há espaços ou caracteres invisíveis no início ou no fim da senha." quando a senha digitada tem caractere da lista nas pontas (as duas orientações juntas no login, sem repetir a mensagem principal); senhas novas recusadas com qualquer caractere da lista em qualquer posição: "A senha não pode conter espaços nem caracteres invisíveis.". Senhas existentes comparadas exatamente, hashes e e-mails gravados intactos; regra compartilhada de formato e contrato do serviço inalterados; sem migração. Testes: ver E10. Observação: os Termos de Uso vigentes dizem que a senha "não pode conter espaços"; com a 5.42, ela também não pode conter caracteres invisíveis. O texto **não** foi alterado (mudança nos Termos segue a 5.53 e depende da autora). Pela legenda abaixo, continua **Pendente** (não publicada) | Sino 6.8 (prevista) |
| E10 | **Concluída** (implementada, validada e publicada no GitHub em 16/10/2026, commit `cc2395c24d9435e8ca1ea511ffab73abf5a0f13a`, junto da E9; validação manual 15/15 conjunta com a E9; 1188 testes automatizados aprovados; critérios de 11.1 atendidos). *Registro anterior, preservado:* **Implementada e validada; publicação pendente** (validação manual conjunta da E9 e da E10: 15/15 testes aprovados, 16/10/2026, nos temas Claro e Escuro, com a janela estreitada e alargada de novo; nenhuma falha de implementação confirmada). *Registro anterior, preservado:* **Implementada; validação manual pendente; publicação pendente** (16/10/2026; M11, regra 5.52; CT150; decisões M11-A e M11-B): em Início, Ver status e Contas em atraso, a linha de conta se **empilha** (nome e subtítulo em cima, com toda a largura; valor, status e botões embaixo) quando sobrariam menos de 100 px para o nome lado a lado; na prática, abaixo de 370 px de página em Início (duas ações por linha) e de 270 px em Ver status e Contas em atraso. O tamanho padrão do app (380 px) continua lado a lado. Sem largura mínima de janela; nomes inteiros, sem reticências nem limite de linhas; ao redimensionar, só a lista da tela aberta é refeita, e só quando o empilhamento muda. Sem migração. **E9 + E10:** 1188 testes do aplicativo aprovados (42 novos: 29 da E9 em `tests/test_espacos_m1.py` e 13 da E10 em `tests/test_linhas_estreitas.py`; mensagens e casos de cinco testes anteriores atualizados para as regras 5.41 e 5.42), em bancos temporários, sem rede e com bloqueio de acesso ao banco real e aos backups; os testes da E10 são **estruturais** (controles criados pela interface); a quebra real das linhas e a aparência só se conferem na validação manual, porque o ambiente não tem tela virtual para capturas automáticas. **Validação manual pendente.** Pela legenda abaixo, continua **Pendente** (não publicada) | Sino 6.8 (prevista) |
| E11 | **Concluída** (publicada no GitHub em 16/10/2026, no commit `feat: release Sino 6.7 calendars and month selector` (identificador no histórico do Git), junto da E8; validação manual 13/13; critérios de 11.1 atendidos). *Registro anterior, preservado:* **Implementada e validada; publicação pendente** (16/10/2026; M3, regra 5.44; RF44; RNF09, RNF14; P19; CT128–CT132; decisões M3-1 a M3-4): mês e ano de Início com seta para baixo numa única área clicável (botão com a dica "Escolher mês e ano", foco visível e nome acessível com o período), separada das setas, que continuam livres; diálogo com o ano (setas limitadas à faixa) e a grade 4 × 3 dos meses abreviados; destaques do período exibido (fundo) e do mês de hoje (contorno) — quando coincidem, o contorno usa a cor do texto principal para continuar visível sobre o fundo (decisão técnica da implementação); "Mês atual" (desativado quando já exibido) e "Cancelar"; faixa de anos com o ano exibido (5.44, decisão de 16/10/2026); abrir, trocar o ano e cancelar não navegam nem geram ocorrências, e a escolha de um mês segue o mesmo caminho das setas (5.20). Consulta existente `anos_com_contas`; sem migração. **E8 + E11:** 1146 testes do aplicativo aprovados (35 novos: 10 da E8 e 25 da E11), em bancos temporários, sem rede e com bloqueio de acesso ao banco real e aos backups; **validação manual concluída em 16/10/2026: 24/24 testes aprovados** (E8: 11/11; E11: 13/13), conforme resultados informados pela autora após a execução manual em cópia isolada (banco próprio, serviço de códigos desativado, sem rede, duas usuárias fictícias, temas Claro e Escuro); **nenhuma anomalia identificada**. O teste 23 (janela estreita) foi feito com a janela reduzida manualmente para cerca de 380 px: todos os componentes ficaram visíveis, legíveis e acessíveis. *Registro anterior, preservado:* 13 de 24 testes com aprovação individual (1–11 da E8; 12 e 13 da E11) e testes 14–24 sem resultados individuais documentados. Pela legenda abaixo, continua **Pendente** (não publicada). *Atualização (23/10/2026, correção na Sino 6.9, em preparação; decisão D4 da autora):* a estrutura anterior expunha elementos acessíveis separados (um `Semantics` externo com o nome em volta do botão); foi escolhida a **variante EB** para reunir nome acessível, papel de botão e estado "selecionado" num único elemento focável. **Meses do diálogo:** cada mês é `MergeSemantics` → `Semantics(selected)` → `Button` → `Text(semantics_label)`; o estado "selecionado" (período exibido) pertence só aos meses. **Botão de abertura:** `TextButton` sem `Semantics` externo; o nome acessível ("Escolher mês e ano, <período>") fica no `semantics_label` do texto do período e é atualizado a cada navegação (`atualizar_dados`); a abertura não tem estado "selecionado". **Contraste:** a varredura de legibilidade passa a medir o texto dos botões (`Button` e `TextButton`) sobre o fundo do próprio botão e, sem fundo próprio, sobre o fundo herdado. Sem migração. Resultados registrados no checkpoint de 22/10/2026: **1197/1197 testes automatizados aprovados** (9 a mais que na Sino 6.8; seletor 29/29 e legibilidade 19/19), em bancos temporários e sem rede; **validação manual** em cópia isolada (banco fictício, sem rede, serviço de códigos desativado, banco real oculto): **testes 1–6 aprovados**, conforme relato da autora; **teste 7 (inspeção pelo AT-SPI): parcialmente aprovado** — o botão de abertura aparece como um único botão com o nome correto; os 12 meses do diálogo **não** apareceram na árvore do AT-SPI, embora a autora confirme o diálogo visível, de modo que os nomes e o estado "selecionado" dos meses **não** puderam ser verificados diretamente; a hipótese de limitação do Flet/Flutter no Linux para diálogos **não** foi confirmada; **não** houve teste com leitor de tela real. A acessibilidade integral do diálogo **não** está declarada aprovada. Evidências da suíte e do teste 7: evidência bruta não preservada; resultado consta do checkpoint de 22/10/2026. A situação da E11 (Concluída, Sino 6.7) não muda; ~~commit e publicação da correção pendentes~~ *atualização (23/10/2026, publicação):* correção publicada no GitHub na Sino 6.9, commit `1141d68b84b23e09a5a1dfd98217fe4120f3abd7`, com as ressalvas acima (teste 7 do AT-SPI parcial; acessibilidade integral do diálogo não declarada aprovada; setas de mês sem nome acessível) | Sino 6.7 (correção: Sino 6.9) |
| E12 | **Concluída** (publicada no GitHub em 23/10/2026, commit `6e3241ce87c637fa911797989616fdf972ffc9b6`; suíte completa 1264/1264 depois da A2, sem falhas, erros nem testes ignorados; validação manual F9 concluída; critérios de 11.1 atendidos, com as limitações conhecidas abaixo). *Registro anterior, preservado:* **Implementada e validada; publicação pendente** (23/10/2026; M7, regra 5.48; RF45; RNF09, RNF14; P23; CT136, CT137; decisões M7-A a M7-D, D1–D3, DF1–DF5): cartão "Comparativo por categoria" com **um gráfico por categoria** (alternativa A2, escolhida depois de provas isoladas A2 × A1), larguras individuais pela medição, escala vertical compartilhada, valor em R$ acima de cada coluna (G4), contorno contrastante, rótulos acessíveis com aviso "nome: valor" (sem rolagem ao clicar), rolagem horizontal híbrida, espaços de 5 px (rótulo) e 10 px (barra de rolagem); ordem, cores, valores, rosca e "Sem categoria" inalterados; sem migração. **Testes automatizados:** 126/126 aprovados nos testes específicos depois da A2 (`tests/test_grafico.py` 59, `tests/test_comparativo_categoria.py` 23, `tests/test_legibilidade_temas.py` 28, `tests/test_legibilidade_rnf09.py` 5, `tests/test_sessao_tema.py` 11); a suíte completa (1256/1256, 23/10/2026) foi executada **antes** da A2 e ~~**ainda não foi repetida** depois dela~~ *atualização (23/10/2026):* foi repetida depois da A2, com 1264/1264 aprovados. **Validação manual (F9), em cópia isolada** (sem rede, banco real oculto, serviço de códigos desativado, dados fictícios), **concluída**: *verificado pelo Claude, com capturas e registros:* outubro/2026 com 19 categorias no Claro (mensal; anual 2026; mês sem despesas sem o cartão) e no Escuro, e com 31 categorias no Claro; valores iguais aos esperados; Tab (18/18, 18/18, 30/30), Shift+Tab (18/18 nos dois temas), foco pela tecnologia assistiva (AT-SPI) trazendo à vista rótulos fora da área, clique mostrando o aviso sem rolar, Shift + roda até o fim e de volta, nomes Unicode completos (palavras únicas longas, emojis com ZWJ, marcas combinantes, RTL) e 4 px livres entre a coluna e o contorno de foco; *confirmado manualmente pela autora, sem evidência técnica adicional:* 31 categorias no tema Escuro e a barra de rolagem horizontal visível durante o movimento sem sobrepor os rótulos. **Limitações conhecidas:** deslocamento cosmético de ~6 px ao trazer o primeiro rótulo pela tecnologia assistiva; escala de texto, touchpad real (a roda horizontal X11 não teve efeito na prova anterior) e leitor de tela real não verificados; desempenho de desenho não medido formalmente; a fórmula de largura não é garantia universal; caracteres sem glifo na fonte. ~~Commit e publicação pendentes (F11)~~ *Atualização (23/10/2026):* publicada (F11) | Sino 6.9 |
| E13 a E18, F1 | **Pendente** | — |

**Pendência registrada fora das entregas (23/10/2026):** as setas de mês anterior e próximo de Início **não têm nome acessível**. A falha é anterior à E11 e **não** faz parte da correção da Sino 6.9; o tratamento depende de decisão da autora (RNF14).

Legenda:

* **Concluída:** publicada com os critérios de 11.1.
* **Parcial:** publicada com parte do conteúdo e pendências registradas.
* **Pendente:** não iniciada ou não publicada.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 6.0 | 23/09/2026 – 04/10/2026 | Ver a [ERS v6.0](ERS_Controle_de_Contas_v6.0.md) (preservada sem alterações). |
| 7.0 (revisão) | 23/10/2026 (publicação da Sino 6.9) | **Sino 6.9 publicada** no GitHub em 23/10/2026: correção da **E11 (M3)** no commit `1141d68b84b23e09a5a1dfd98217fe4120f3abd7` e **E12 (M7)** no commit `6e3241ce87c637fa911797989616fdf972ffc9b6`, em commits separados. Suíte completa depois da A2: **1264/1264** aprovados, sem falhas, erros nem testes ignorados; validação manual F9 concluída (verificações do Claude com capturas e registros; 31 categorias no Escuro e barra de rolagem confirmadas manualmente pela autora). E11 e E12 concluídas, com as ressalvas e limitações registradas em 15.3. Atualizados 15.2 (Sino 6.9) e 15.3 (E11, E12; registros anteriores preservados). Sem mudança de requisitos ou decisões; E13 a E18 e F1 pendentes; revisão jurídica pendente; Sino não liberado ao público. |
| 7.0 (revisão) | 23/10/2026 (E12, Sino 6.9 em preparação) | **E12 (M7)** implementada e validada, **não publicada**: comparativo por categoria com um gráfico por categoria (alternativa A2), larguras individuais, escala compartilhada, valores acima das colunas, rótulos acessíveis com aviso, rolagem híbrida e espaços de 5 e 10 px (5.48). Testes específicos 126/126 depois da A2; suíte completa 1256/1256 executada antes da A2, ainda não repetida. Validação manual (F9) concluída em cópia isolada com dados fictícios — verificações do Claude com capturas e registros; 31 categorias no Escuro e barra de rolagem confirmadas manualmente pela autora, sem evidência técnica adicional. Limitações conhecidas em 15.3 (E12). Atualizados 5.48, RNF09, RNF14, 15.2 (Sino 6.9) e 15.3 (E12). Revisão final, commit e publicação (F11) pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 23/10/2026 (correção da E11, Sino 6.9 em preparação) | Correção da **E11 (M3)** na Sino 6.9 (decisão D4 da autora), **não publicada**: variante EB (`MergeSemantics`) nos meses do diálogo, reunindo nome acessível, papel de botão e estado "selecionado" num único elemento focável; nome acessível do botão de abertura no próprio botão, atualizado a cada navegação; varredura de contraste com o fundo dos botões. Sem migração. Testes automatizados 1197/1197; validação manual 1–6 aprovada (relato da autora); teste 7 (AT-SPI) **parcialmente aprovado**, sem verificação direta dos nomes e do estado "selecionado" dos 12 meses do diálogo, hipótese de limitação do Flet/Flutter no Linux não confirmada e sem teste com leitor de tela real; acessibilidade integral do diálogo **não** declarada aprovada. Evidência bruta não preservada; resultado consta do checkpoint de 22/10/2026. Registrada a pendência anterior das setas de mês sem nome acessível, fora da correção. Atualizados 5.44, RNF14, 15.2 (Sino 6.9) e 15.3 (E11; registros anteriores preservados). E12 não iniciada; commit e publicação pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 16/10/2026 (publicação da Sino 6.8) | **Sino 6.8 publicada** no GitHub em 16/10/2026, no commit `cc2395c24d9435e8ca1ea511ffab73abf5a0f13a` (`feat: release Sino 6.8 invisible characters and narrow account rows`): **E9 (M1)** e **E10 (M11)** concluídas numa publicação conjunta (critérios de 11.1), com 1188 testes automatizados aprovados e validação manual 15/15 informada pela autora; continua registrada a ressalva de que a tentativa específica com U+200B (espaço de largura zero) no Cadastro não teve confirmação manual independente (caso coberto pelos testes automatizados). Atualizados 15.2 (Sino 6.8) e 15.3 (E9, E10; registros anteriores preservados). Sem mudança de requisitos ou decisões: Termos de Uso inalterados (a observação sobre "não pode conter espaços" continua dependendo da autora, 5.53); E4 continua concluída em produção restrita, com P43 **não atendida** (risco aceito só para essa produção); M8 para terceiros continua adiada; revisão jurídica pendente; M13 candidata; E12–E18 e F1 pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 16/10/2026 (validação da Sino 6.8) | **Validação manual da Sino 6.8 concluída** pela autora em 16/10/2026: **15/15 testes aprovados** (E9 e E10, numa cópia isolada com banco próprio, dados fictícios e serviço de códigos desativado), com os 1188 testes automatizados aprovados e nenhuma falha de implementação confirmada; a tentativa específica com U+200B (espaço de largura zero) no Cadastro não teve confirmação manual independente; esse caso está coberto pelos testes automatizados. **E9 (M1)** e **E10 (M11)** registradas como implementadas e validadas; Sino 6.8 **aguardando publicação** (commit e publicação no GitHub pendentes na data deste registro). Atualizados 5.52 (largura aprovada), 15.2 (Sino 6.8) e 15.3 (E9, E10; registros anteriores preservados). Sem mudança de requisitos, código ou Termos de Uso: a observação sobre o texto dos Termos ("não pode conter espaços") continua valendo e depende da autora (5.53); E4 continua concluída em produção restrita, com P43 **não atendida** (risco aceito só para essa produção); M8 para terceiros continua adiada; revisão jurídica pendente; M13 candidata; E12–E18 e F1 pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 16/10/2026 (E9 + E10) | **E9 (M1)** e **E10 (M11)** implementadas para publicação conjunta como **Sino 6.8** (em preparação): limpeza única do e-mail nas extremidades, mensagens para invisíveis no meio do e-mail e nas pontas da senha, senhas novas sem os 31 caracteres da lista E1 (5.40–5.42, CT119–CT125); linhas de conta empilhadas em janelas estreitas (5.52, CT150; largura registrada em 5.52). 1188 testes do aplicativo aprovados (42 novos: 29 da E9 em `tests/test_espacos_m1.py` e 13 da E10 em `tests/test_linhas_estreitas.py`; mensagens e casos de cinco testes anteriores atualizados para as regras 5.41 e 5.42), em bancos temporários, sem rede e com bloqueio de acesso ao banco real e aos backups; os testes da E10 são **estruturais** (controles criados pela interface); a quebra real das linhas e a aparência só se conferem na validação manual, porque o ambiente não tem tela virtual para capturas automáticas. **Validação manual pendente**; commit e publicação pendentes. Observação: os Termos de Uso vigentes dizem que a senha "não pode conter espaços"; com a 5.42, ela também não pode conter caracteres invisíveis. O texto **não** foi alterado (mudança nos Termos segue a 5.53 e depende da autora). Atualizados 5.52, 15.2 (Sino 6.8) e 15.3 (E9, E10). Sem mudança nas demais decisões: E4 concluída em produção restrita (P43 **não atendida**, risco aceito só para essa produção); M8 para terceiros adiada; revisão jurídica pendente; M13 candidata; E12–E18 e F1 pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 16/10/2026 (publicação da Sino 6.7) | **Sino 6.7 publicada** no GitHub em 16/10/2026, no commit `feat: release Sino 6.7 calendars and month selector`: **E8 (M6)** e **E11 (M3)** concluídas numa publicação conjunta (critérios de 11.1), com 1146 testes automatizados aprovados e validação manual 24/24 (E8: 11/11; E11: 13/13) informada pela autora. Atualizados 15.2 (Sino 6.7) e 15.3 (E8, E11; registros anteriores preservados). Sem mudança de requisitos ou decisões: máscara automática de barras não adotada; E4 continua concluída em produção restrita, com P43 **não atendida** (risco aceito só para essa produção); M8 para terceiros continua adiada; revisão jurídica pendente; M13 candidata; E9, E10, E12–E18 e F1 pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 16/10/2026 (validação E8 + E11) | **Validação manual da Sino 6.7 concluída**: 24/24 testes aprovados (E8: 11/11; E11: 13/13), conforme resultados informados pela autora após a execução manual em cópia isolada com dados fictícios; nenhuma anomalia identificada; teste 23 feito com a janela reduzida manualmente para cerca de 380 px. Atualizados 15.2 (Sino 6.7) e 15.3 (E8, E11; registro parcial anterior preservado). Sem mudança de código, testes ou decisões: máscara automática de barras não adotada; seleção do mês aplicada na hora; faixa de anos com o ano exibido; setas de mês livres. Sino 6.7 continua **em preparação** (commit e publicação pendentes); E4 concluída em produção restrita; M8 para terceiros continua adiada. |
| 7.0 (revisão) | 16/10/2026 (E8 + E11) | **E8 (M6)** e **E11 (M3)** implementadas para publicação conjunta como **Sino 6.7**: calendários em português com textos próprios, digitação dd/mm/aaaa pelo lápis e número do dia de hoje legível em todos os estados (5.47, CT135); seletor de mês e ano em Início, com faixa de anos, destaques, "Mês atual" e geração só depois de escolher um mês (5.44, CT128–CT132). Decisão da autora (16/10/2026): a faixa de anos inclui o ano exibido (5.44). Máscara automática de barras na digitação (por exemplo, `25122026` → `25/12/2026`) analisada a pedido da autora e **não adotada** nesta versão: o campo aberto pelo lápis é interno ao calendário nativo (DatePicker) do Flet 0.86.5, que não oferece filtro, máscara nem evento de digitação; a digitação continua em **dd/mm/aaaa**, com barras (5.47). 1146 testes do aplicativo aprovados (35 novos: 10 da E8 e 25 da E11), em bancos temporários, sem rede e com bloqueio de acesso ao banco real e aos backups; validação manual em cópia isolada (banco próprio, serviço de códigos desativado, duas usuárias fictícias, temas Claro e Escuro): **13 de 24 testes com aprovação individual** (1–11 da E8; 12 e 13 da E11: abertura pelo mouse, inclusive o contorno do mês atual quando também é o período exibido, e pelo teclado); testes 14–24 sem resultados individuais documentados; **nenhuma anomalia relatada**. **E7 concluída**: Sino 6.6 publicada em `de06c4eaa2990cfb34a94d55da62a73d896f4e00` (registro anterior de publicação pendente preservado). Atualizados 5.44, 5.47, 15.2 (Sino 6.6 publicada; Sino 6.7 prevista) e 15.3 (E7, E8, E11). Sino 6.7 **não publicada** na data deste registro (commit e publicação pendentes). Sem mudança nas demais decisões: E4 encerrada com P43 **não atendida** (risco aceito só para a produção restrita); M8 aberta e envio de códigos a terceiros adiado; revisão jurídica pendente; M13 candidata; E9, E10, E12–E18 e F1 pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 16/10/2026 (E7) | **E7 (M2)** implementada e validada como **Sino 6.6**: orientação "Registre suas primeiras contas e tenha tudo sob controle." para o usuário sem nenhuma conta (5.43, CT126), sem clique e sem aparência de sucesso; mês vazio de quem tem contas como antes (CT127); contraste nos dois temas (RNF09); nova consulta `usuario_tem_contas`, sem migração; 1111 testes aprovados (14 novos); 7/7 cenários manuais em cópia isolada. **E6 concluída**: Sino 6.5 publicada em `3fc862b9fae5bd8fa787553b1d7f55dc41113e1c` (registro anterior de publicação pendente preservado). Atualizados 15.2 (Sino 6.5 publicada; Sino 6.6) e 15.3 (E6, E7). Commit e publicação da E7 pendentes na data deste registro. Sem mudança de requisitos nem de decisões: P43 continua **não atendida** (risco aceito só para a produção restrita); M8 aberta; revisão jurídica pendente; M13 candidata; E8–E18 e F1 pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 16/10/2026 (E6) | **E6 (M4)** implementada e validada como **Sino 6.5**: descrição de até 1000 caracteres percebidos (5.45, CT133), campo de 2 a 8 linhas com rolagem interna, contador "x/1000"; normalização, recusa sem corte, aviso e som preservados; sem migração; 1097 testes aprovados (15 novos); 7/7 cenários manuais (30/30 verificações) em cópia isolada. **E5 concluída**: Sino 6.4 publicada em `c2961587d7f7868efcb7b58ade1e7f73cf8178b3` (registro anterior de publicação pendente preservado). Atualizados 15.2 (Sino 6.4 publicada; Sino 6.5) e 15.3 (E5, E6). Commit e publicação da E6 pendentes na data deste registro. Sem mudança de requisitos nem de decisões: P43 continua **não atendida** (risco aceito só para a produção restrita); M8 aberta; revisão jurídica pendente; M13 candidata; E7–E18 e F1 pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 16/10/2026 (E5) | **E5 (M5)** implementada e validada como **Sino 6.4**: contador do nome do usuário oculto no Cadastro e em Editar nome (5.46, CT134), com limite, recusa, "Limite atingido", som e tratamento de nome antigo preservados; 1082 testes aprovados (12 novos); 7/7 cenários manuais aprovados em cópia isolada; sem migração. Atualizados 15.2 (Sino 6.4; Sino 6.3 publicada em `a57d73f`) e 15.3 (E5). Commit e publicação pendentes na data deste registro. Sem mudança de requisitos nem de decisões: P43 continua **não atendida** (risco aceito só para a produção restrita); M8 aberta; revisão jurídica pendente; M13 candidata; E6–E18 e F1 pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 16/10/2026 | Revisão documental: **registro formal da Sino 6.3** (E4; código já publicado até `db00f44`; encerramento operacional em 15/10/2026, com ressalvas; sem nova implantação, abertura ao público ou ampliação dos destinatários); 15.2 com as versões publicadas (6.0, 6.1, 6.2 e 6.3) e a proposta de etiquetas registrada como não aplicada; 15.3 (E4) com a versão; estados atualizados sem reescrever o histórico: 2.1 e 13.4 (M9 aplicada na E1, `58b4382`), T10 (produção restrita em 15/10/2026), 13.4 (M12: textos de 06/10 e 13/10 publicados; revisão jurídica e textos da M10 pendentes; M8: lançamento formal da versão cumprido). Sem mudança de decisões: P43 continua **não atendida** (risco aceito só para a produção restrita); M8 aberta; revisão jurídica pendente; M13 candidata; E5–E18 e F1 pendentes; Sino não liberado ao público. |
| 7.0 (revisão) | 15/10/2026 (encerramento) | **E4 encerrada formalmente pela autora** (produção restrita concluída e validada; envio real funcionando para os destinatários autorizados). P43 continua **não atendida**, com risco aceito só para a produção restrita; M8 aberta; Sino não liberado ao público. Pendências futuras registradas (desempenho e P43, limites e abuso, observabilidade, M8-A, M8-F, M12, DMARC de `envios`, ampliação dos destinatários, lançamento formal da versão do app); contratação paga só como possibilidade futura, não aprovada. Atualizados 13.4 e 15.3. |
| 7.0 (revisão) | 15/10/2026 (fim da noite) | E4/M8: limpeza de segurança concluída (cópia de recuperação criptografada confirmada, com cópia externa; segredos locais removidos; `wrangler logout`; 14 registros locais do Wrangler removidos) e decisão 9 (DMARC) atendida para a produção restrita (`_dmarc.appsino.com.br` restaurado com `p=reject`; `envios` com `p=none`). P43 continua não atendida (risco aceito só para a produção restrita). Atualizados 13.4 (M8) e 15.3 (E4). M8 não concluída; E4 com encerramento formal a decidir. |
| 7.0 (revisão) | 15/10/2026 (noite) | Produção restrita (E4/M8) **implantada e validada**: segredos novos gerados pela autora; commit B (`db00f44`: URL de produção e chave pública `prod-1` no app; 1070/1070); deploy pela autora (Workers Free, Resend Free, dois destinatários); teste de fumaça 403; primeiro cadastro definitivo (ref8); CT138 cumprido; decisão 8 (expiração no serviço) cumprida; 2 envios Delivered; P43 com critério original não atendido e risco aceito só para a produção restrita. Atualizados P43, 13.4 (M8) e 15.3 (E4). Pendentes: decisão 9, lançamento formal da versão do app, guarda das cópias de recuperação, limpeza dos segredos locais, `wrangler logout`, reavaliações antes de terceiros. E4 com encerramento formal a decidir. |
| 7.0 (revisão) | 15/10/2026 | Produção restrita (E4/M8): decisões 5 (segredos: Workers Secrets, KID `prod-1`, cópias de recuperação da `CHAVE_HMAC` e da semente Ed25519, `.env` no `.gitignore`) e 6 (observabilidade desligada, como no T2) aprovadas e implementadas localmente: `wrangler.jsonc` de produção completo, teste de configuração, ferramenta `producao_segredos.py` (sem segredos reais gerados); serviço 260/260, app 1064/1064, dry-run local 70,72 KiB. Subdomínio pretendido `appsino` (sujeito à disponibilidade); segundo endereço da autora na lista para o CT138. Sem commit, sem deploy. P43 continua não atendida. E4 não concluída. |
| 7.0 (revisão) | 14/10/2026 | Produção restrita (E4/M8): decisões 1 a 4 da autora registradas, 5 a 9 pendentes; otimização O1 registrada (commit `981d1e8`: assinatura Ed25519 pela WebCrypto nativa; equivalência em 200 casos e integração no `workerd`; serviço 254/254, app 1034/1034; pacotes cerca de 46% menores no dry-run local, sem comprovar ganho de CPU; teste de carga local intermitente, 1 de 3 antes e depois); P43 com atualização (pendente de medição real); 13.4 (M8) e 15.3 (E4) atualizadas; item 8 das propostas atualizado (pasta pessoal deixou de ser repositório Git; cópias preservadas). Sem deploy. E4 não concluída. |
| 7.0 (revisão) | 14/10/2026 | T2 encerrado: oito envios Delivered; métricas finais agregadas registradas; cópia, Worker, chave da Resend, segredos, sessão e registros locais do Wrangler removidos; DMARC `p=none` de `envios` mantido; ausência do `p=reject` do domínio principal em investigação; 13.4 (M8) e 15.3 (E4) atualizadas. Critérios da E4 avaliados sem alteração: E4 não concluída (faltam produção restrita e configuração da versão do app). |
| 7.0 (revisão) | 14/10/2026 | Testes do T2 concluídos (quatro envios em 14/10, oito no T2): invalidação do código antigo, esgotamento das tentativas e conteúdo dos e-mails aprovados; expiração aprovada em parte (recusa local do app; serviço coberto pelos testes automáticos); alteração de e-mail fora do T2 por decisão da autora; passo 11 cumprido com ressalvas; 13.4 (M8) e 15.3 (E4) atualizadas. E4 não concluída até a desmontagem e o registro final. |
| 7.0 (revisão) | 14/10/2026 | Revisão documental do T2: 13.4 (M8) corrigida (envio real só no T2 restrito; reenvio aprovado em parte; recuperação neutra aprovada; pendências completas; reinício de 14/10 e estado do Worker não confirmado depois de 13/10; conferências antes do envio registradas conforme a evidência); P43 com tempo de CPU e erros 1102 não auditados individualmente; 15.3 (E4) com os pendentes. E4 não concluída. |
| 7.0 (revisão) | 13/10/2026 | T2 implantado e testado em uso restrito (quatro envios reais; resultados, DNS/DNSSEC/DMARC, painéis e métricas registrados nas propostas); P43 (caso 8: critério original não atendido; critério operacional revisado); 13.4 (M8) e 15.3 (E4) atualizadas; E4 em andamento, encerramento do T2 até 20/10/2026. |
| 7.0 (revisão) | 13/10/2026 | P42: preparação técnica do T2 no código (Reply-To, rodapé, remetente obrigatório, entrada com token, `wrangler.t2.jsonc`, ferramentas dos segredos e da cópia isolada, auditoria e correções de segurança); 13.4 (M8) e 15.3 (E4) atualizadas; sem deploy nem envio real. Corrigido em 13.4: os textos de 13/10/2026 já estão publicados (65a6b9d). |
| 7.0 (revisão) | 13/10/2026 | P41: versão de 13/10/2026 dos Termos e da Política, relevante nos dois, em preparação para o T2 da E4 (serviço real em fase restrita, Cloudflare, Resend, retenção, transferência internacional, contato); 5.53, 13.4 (M8) e 15.3 (E4) atualizadas: T1 encerrado, T2 não iniciado, envio real desativado. |
| 7.0 (revisão) | 08/10/2026 | P40: ambiente remoto de testes separado aprovado (envio fictício sem Resend, token, até 7 dias após o deploy); T0 implementado, validado e revisado localmente (sem deploy; commit local, sem push); horários do roteiro conforme os limites; caso de IP pendente de validação remota. |
| 7.0 (revisão) | 08/10/2026 | E4 (preparação): domínio de envio verificado; remetente, Reply-To e contato de suporte e de dados pessoais aprovados; linha de ajuda nos e-mails; conta da Cloudflare criada; rastreamento da Resend não confirmado; plano do ambiente remoto de testes proposto (sem deploy). |
| 7.0 (revisão) | 07/10/2026 | E3 concluída e publicada no GitHub como Sino 6.2 (validação manual na demonstração do commit a76da70; CT157 e CT158 só por testes automáticos); serviço de códigos sem deploy, sem envio real e sem liberação para terceiros. |
| 7.0 (revisão) | 07/10/2026 | P39: decisões da E3 (restrição de destinatários, contrato v1.1); 5.49 com as regras técnicas e os limites aceitos; CT157 e CT158; E3 implementada, aguardando revisão e validação (Sino 6.2 candidata, não publicada). |
| 7.0 (revisão) | 06/10/2026 | E2 concluída e publicada como Sino 6.1 (926 testes; validação visual aprovada); banco principal na v9 (ref7). |
| 7.0 (revisão) | 06/10/2026 | P38: versão de 06/10/2026 dos Termos e da Política, relevante; usuários existentes aceitam a nova versão. |
| 7.0 (revisão) | 06/10/2026 | P37: decisões da E2 (versão inicial, aceites anteriores sem versão atribuída, `docs/legal/`); E1 concluída; E2 implementada, não publicada. |
| 7.0 (revisão) | 06/10/2026 | P36: licença MIT + Commons Clause v1.0 (textos oficiais), substituindo a P35; alcance sobre código, documentos e imagens da autora; histórico MIT até a8302c2; planejamento e licença consolidados num só commit (o commit local 33b8db2, não publicado, foi refeito). |
| 7.0 (revisão) | 06/10/2026 | P35: licença, bloco 2 = caminho A (redistribuição, versões modificadas e lojas só com autorização; compilar e modificar para uso próprio permitidos); rascunho de licença própria e das condições da distribuição oficial. |
| 7.0 (revisão) | 06/10/2026 | P34: licença, bloco 1 = 1A (uso livre; terceiros não podem vender nem comercializar o app ou derivados sem autorização); textos candidatos T1 e T2 em análise. |
| 7.0 (revisão) | 06/10/2026 | P33: ERS v7.0 como planejamento geral em entregas publicadas separadamente (E1–E18, F1); prioridades licença → e-mail → UX → disponibilização (M14, nova) → comprovantes e Faturas; critérios separados para entrega publicada, escopo completo (Sino 7.0) e liberação para terceiros (piloto restrito antes da ampla); numeração das versões do app (Sino 6.1 em diante). Migrações separadas mantidas. |
| 7.0 (planejamento) | 06/10/2026 | P32: M9 (licença) reaberta, antes das entregas de UX; MIT mantida no `LICENSE` até a decisão, com registro histórico preservado. P31: migrações separadas (v9 aceites; v10 comprovantes; Faturas depois, se aprovada) e entregas incrementais com prioridade para a M8. Proposta candidata M13 (Faturas) registrada, sem aprovação, com conflito sobre parcelas e recorrências. Conferência dos provedores da M8. L1 resolvida pela reinicialização do banco da instalação principal. |
| 7.0 | 04/10/2026 | Consolidação do planejamento ([ERS_v7.0_propostas.md](ERS_v7.0_propostas.md)): M1–M8, M10–M12 no escopo; M9 adiada; migração v9 única; distinção entre conclusão em uso restrito (com a M8), entrega parcial e liberação para terceiros (P30). A implementar. |
