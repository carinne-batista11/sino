# ERS v7.0 — propostas em planejamento

**Situação:** planejamento iniciado em 04/10/2026. Nada aqui está decidido nem implementado. A [ERS v6.0](ERS_Controle_de_Contas_v6.0.md) continua sendo a especificação vigente, e o código atual não muda nesta fase.

**Organização vigente (06/10/2026, P33):** a ERS v7.0 consolidada é o planejamento geral, dividido em entregas publicadas separadamente (E1–E18 e F1, seção 15 da ERS). Prioridades: 1 licença; 2 envio real de e-mails; 3 UX; 4 disponibilização (M14); 5 comprovantes, Faturas e pendências. As ordens de implementação registradas mais abaixo neste documento são **histórico**.

**Regras desta fase:** uma melhoria por vez; cada uma traz o comportamento atual, os impactos e as decisões que a autora precisa tomar. Contas de teste não são excluídas e a licença não muda.

## Lista de melhorias propostas

| ID | Melhoria | Situação |
|---|---|---|
| M1 | Tratar espaços acidentais no e-mail e avaliar espaços no final da senha | **Decidida** (E1–E4, S1–S2); a implementar |
| M2 | Primeiro acesso sem nenhuma conta: mostrar "Registre suas primeiras contas e tenha tudo sob controle" em vez de "Suas contas estão em dia"; diferenciar usuário sem contas de mês vazio | **Decidida** (U1–U4); a implementar |
| M3 | Em Início, clicar no mês/ano abre um seletor de mês e ano, mantendo as setas | **Decidida** (M3-1 a M3-4); a implementar |
| M4 | Descrição da conta: limite de 500 para 1.000 caracteres | **Decidida** (M4-1, M4-2); a implementar |
| M5 | Ocultar o contador "0/70" do nome do usuário, mantendo o limite e o aviso | **Decidida** (M5-A, M5-B); a implementar |
| M6 | Calendário: corrigir o contraste do dia atual e traduzir para português | **Decidida** (M6-A, M6-B); a implementar |
| M7 | Gráfico de colunas por categoria (nome, valor e cor), complementando a rosca | **Decidida** (M7-A a M7-D e critério de acessibilidade); a implementar |
| M8 | Envio real de e-mails pela Resend e publicação do serviço de códigos | **Planejada com condições e pendências** (domínio, remetente e responsável a definir); nada contratado |
| M9 | Reavaliar a restrição de uso comercial nas próximas versões, preservando as permissões MIT das anteriores (a licença não muda agora) | **Reaberta em 06/10/2026**, prioridade 1; **escolhida em 06/10/2026: MIT + Commons Clause v1.0** (P36); alterações preparadas, sem commit; revisão jurídica e INPI pendentes; `LICENSE` inalterado (MIT) |
| M10 | Anexar imagens de comprovantes (opcional), acessadas por um botão em Detalhes, sem exibição permanente | **Decidida** (M10-A a M10-L); a implementar |
| M11 | Corrigir a quebra dos nomes das contas em janelas muito estreitas | **Decidida** (M11-A, M11-B); a implementar |
| M12 | Revisão jurídica, versionamento e novo aceite dos Termos e da Política antes do uso por terceiros | **Decidida** (M12-A a M12-D); revisão jurídica pendente |
| M13 | Categoria especial "Faturas": agrupar despesas numa fatura, com uma conta em Início e as categorias reais nos gráficos, sem duplicar valores | **Proposta candidata** (06/10/2026); análise registrada; decisões G1–G7 **abertas**; nada aprovado |
| M14 | Disponibilização para outras pessoas (desktop e/ou mobile), com piloto restrito antes da liberação ampla | **Planejada** (06/10/2026) como prioridade 4; decisões a tomar na E13 |

**Backlog futuro (fora do escopo confirmado da v7.0):** notificações (sem implementação aprovada). A versão mobile passa a ser **avaliada** na M14, sem compromisso de lançamento.

## Decisões separadas

| ID | Decisão | Situação |
|---|---|---|
| L1 | Descartar as contas antigas que são apenas de teste | **Resolvida na instalação principal em 06/10/2026**: por decisão da autora, o banco foi reinicializado vazio (schema v8), com backup de recuperação fora do Git e nova referência (ref6). As cópias de validação não foram alteradas. |

---

## M1 — Espaços acidentais no e-mail e espaços no final da senha

### Escopo (definido pela autora em 04/10/2026)

* O objetivo é tratar **espaços acidentais**, não mudar a normalização Unicode das senhas.
* **Senha:** preservar a comparação exata, sem NFC/NFKC e sem migração automática dos hashes.
* **E-mail:** remover espaços nas extremidades e **avisar** sobre espaços internos, sem juntá-los silenciosamente.
* Antes de concluir que há migração, explicar qual mudança persistente a exigiria e se o tratamento da entrada pode ser separado.

### Comportamento atual (v6.0)

| Tela | Espaços nas extremidades do e-mail | Espaço interno |
|---|---|---|
| Login | removidos (qualquer espaço em branco: `strip()` do Python) | a busca não encontra a conta: "E-mail ou senha incorretos." |
| Cadastro, "Esqueci minha senha", novo e-mail em Ajustes | só o espaço comum (U+0020) é removido; tabulação, quebra de linha ou espaço não separável nas bordas tornam o endereço inválido | "Informe um e-mail válido." (mensagem genérica, não cita o espaço) |

* A regra dos fluxos com código é a mesma no serviço, no cliente e no banco, conferida por `servidor/test/conformidade/emails.json`.
* O e-mail é gravado como digitado (sem os espaços comuns das bordas) e comparado em minúsculas ASCII.
* **Senha:** nunca é transformada; senhas novas recusam qualquer espaço ("A senha não pode conter espaços."); o login compara a senha exatamente como digitada (senhas antigas com espaços continuam valendo, CT82).

### Migração: é necessária?

**Não, para o escopo da M1.** Uma migração só é necessária quando muda algo **gravado**:

* mudar a forma em que o e-mail é armazenado (por exemplo, gravar sempre em minúsculas ou criar uma coluna de comparação);
* corrigir valores já gravados que violem a regra nova (por exemplo, e-mails com espaços nas bordas);
* converter hashes de senha (fora do escopo, por decisão da autora).

Remover espaços das extremidades e recusar espaços internos é **tratamento da entrada**: acontece antes de validar e consultar, não muda o que já está gravado e pode ser feito **separadamente**. Os dados confirmam isso: no banco real, **0** e-mails têm espaço nas bordas e **0** têm maiúsculas. Os e-mails antigos fora do formato (15) não dependem desta mudança: continuam entrando como hoje; o destino deles fica com a decisão L1.

### Dados existentes no banco real (contagem somente leitura, 04/10/2026)

| Verificação | Resultado |
|---|---|
| Usuários | 22 (contas de teste da autora; nenhuma será excluída agora) |
| E-mails com espaço nas bordas | 0 |
| E-mails com maiúsculas | 0 |
| E-mails com caracteres não ASCII | 3 |
| E-mails fora da regra de formato v6.0 | 15 (10 com parte vazia antes ou depois do "@", 4 sem "@", 1 não ASCII) |
| E-mails verificados por código | 0 |
| Senhas ainda no hash antigo (sha256) | 5 de 22 (convertidas no próximo login, como hoje) |

### Decisões (uma por vez)

| # | Decisão | Situação |
|---|---|---|
| E1 | Quais caracteres das extremidades do e-mail são removidos | **Decidida (04/10/2026): opção (c)**, detalhada abaixo |
| E2 | Onde o tratamento acontece (só na entrada das telas, mantendo a regra compartilhada com o serviço, ou na regra compartilhada) | **Decidida (04/10/2026): opção (a)**, detalhada abaixo |
| E3 | Espaço interno: mensagem específica, inclusive no login | **Decidida (04/10/2026): opção (a)**, detalhada abaixo |
| E4 | Mostrar no campo o e-mail já sem os espaços das extremidades | **Decidida (04/10/2026): opção (b)**, detalhada abaixo |
| S1 | Espaço no final da senha: como avisar sem transformar a senha | **Decidida (04/10/2026): opção (b)**, detalhada abaixo |
| S2 | Senhas novas com espaço ou caractere invisível | **Decidida (04/10/2026): opção (c)**, detalhada abaixo |

#### E1 — Caracteres removidos das extremidades do e-mail (decidida em 04/10/2026)

**Decisão:** opção (c). Antes de validar ou consultar um e-mail digitado, removem-se das **extremidades** (início e fim), repetidamente, os 31 caracteres abaixo. **Nenhum caractere interno é removido ou juntado**: se algum deles aparecer no meio do endereço, o e-mail continua inválido e o usuário é avisado (forma do aviso: decisão E3).

| Grupo | Caracteres |
|---|---|
| Controles de espaço | U+0009 (tabulação), U+000A (nova linha), U+000B (tabulação vertical), U+000C (avanço de página), U+000D (retorno de carro), U+001C, U+001D, U+001E, U+001F (separadores de informação), U+0085 (próxima linha) |
| Espaços | U+0020 (espaço), U+00A0 (espaço não separável), U+1680 (espaço ogham), U+2000 a U+200A (espaços tipográficos de diversas larguras), U+202F (espaço estreito não separável), U+205F (espaço matemático médio), U+3000 (espaço ideográfico) |
| Separadores | U+2028 (separador de linha), U+2029 (separador de parágrafo) |
| Invisíveis de largura zero | U+200B (espaço de largura zero), U+FEFF (marca de ordem de bytes / espaço não separável de largura zero) |

* Os 29 primeiros são exatamente o conjunto que o Python 3.11 classifica como espaço em branco (`str.isspace`); a lista explícita vale como regra, para não depender da definição de cada linguagem (a de JavaScript é diferente).
* Vale **somente para o e-mail**, nas quatro telas em que ele é digitado: Login, Cadastro, "Esqueci minha senha" e novo e-mail em Ajustes. **Não vale para a senha.**
* Não altera registros já gravados e não é implementada nesta fase.

#### E2 — Onde o tratamento acontece (decidida em 04/10/2026)

**Decisão:** opção (a). Uma **limpeza de entrada centralizada no aplicativo**, uma única função usada pelas quatro telas (Login, Cadastro, "Esqueci minha senha" e novo e-mail em Ajustes), aplicada **antes** de qualquer validação ou consulta.

* A **regra compartilhada de formato** (serviço de códigos, cliente e camada de dados) e o **contrato do serviço** continuam como estão, estritos: o serviço recebe o e-mail já limpo e continua recusando o que não estiver no formato. Os testes de conformidade (`servidor/test/conformidade/emails.json`) não mudam.
* O login deixa de ter um aparo próprio (`strip()`) e passa a usar a mesma limpeza.
* Não exige migração: nada do que está gravado muda.

*Dado relevante para a E3 (contagem somente leitura, 04/10/2026):* **1** e-mail gravado (conta antiga de teste) tem um dos 31 caracteres **no meio** do endereço.

#### E3 — Caracteres da lista no meio do e-mail (decidida em 04/10/2026)

**Decisão:** opção (a). Vale para os 31 caracteres da E1 quando aparecem **no meio** do e-mail, depois da limpeza das extremidades.

* **Cadastro, "Esqueci minha senha" e novo e-mail em Ajustes:** o e-mail é recusado com a mensagem **"Remova os espaços ou caracteres invisíveis do meio do e-mail."**; nada é consultado nem enviado ao serviço de códigos.
* **Login:** a consulta é preservada, feita com o e-mail limpo só nas extremidades. A mensagem acima aparece **somente se o login falhar e a entrada contiver** algum desses caracteres no meio; nos demais casos de falha continua "E-mail ou senha incorretos.".
* O aviso depende apenas do que foi digitado, não da existência da conta; a neutralidade da recuperação de senha é preservada.
* Nada é removido do meio do e-mail; nenhuma conta antiga é alterada. A conta antiga de teste com caractere da lista no meio do e-mail continua entrando como hoje.
* Outros erros de formato mantêm as mensagens atuais; o login continua sem aplicar a regra de formato.

#### E4 — Campo de e-mail mostra a versão limpa (decidida em 04/10/2026)

**Decisão:** opção (b).

* **Ao enviar o formulário**, o campo de e-mail passa a mostrar a versão limpa nas extremidades (E1), **mesmo que outra validação impeça o envio** (por exemplo, senha curta no cadastro).
* O campo **não** é alterado durante a digitação nem ao sair dele.
* O conteúdo interno é preservado; caracteres da lista no meio do e-mail continuam no campo e são tratados pela E3.
* As mensagens que repetem o endereço (por exemplo, "Enviamos um código para…") usam a versão limpa.
* Vale para o campo de e-mail das quatro telas; **não se aplica à senha**.

#### S1 — Dica sobre espaços nas extremidades de uma senha existente (decidida em 04/10/2026)

**Decisão:** opção (b), nos **quatro lugares que conferem uma senha existente**: login, senha atual em "Alterar senha", senha em "Alterar e-mail" e senha em "Excluir conta".

* A senha é comparada **exatamente** como digitada. Não se remove nenhum caractere, não há segunda tentativa automática e nenhum hash é alterado.
* **Só depois de uma recusa**, se a senha digitada tiver no início ou no fim algum dos 31 caracteres da E1, a mensagem de recusa ganha: **"Verifique se há espaços ou caracteres invisíveis no início ou no fim da senha."**
* Se a senha for aceita, nenhuma dica é mostrada.
* Quando a E3 também se aplicar (login recusado com caractere da lista no meio do e-mail), as duas orientações aparecem juntas, **sem repetir a mensagem principal**. Por exemplo: "E-mail ou senha incorretos." seguida das duas orientações.
* A dica depende apenas do que foi digitado, não da existência da conta.
* Rejeitada: tentar de novo sem os espaços das pontas (transformaria a senha).

#### S2 — Senhas novas com espaço ou caractere invisível (decidida em 04/10/2026)

**Decisão:** opção (c).

* Senhas **novas** (cadastro, "Alterar senha" e "Esqueci minha senha") são recusadas se tiverem, **em qualquer posição**, algum dos 31 caracteres da E1, com a mensagem **"A senha não pode conter espaços nem caracteres invisíveis."**
* Fecha a brecha atual: hoje U+200B e U+FEFF são aceitos em senhas novas (não contam como espaço para o Python) e podem gravar uma senha impossível de redigitar.
* A proibição **não** se amplia a outros caracteres Unicode.
* Nada é removido automaticamente: a senha é recusada como veio.
* Senhas existentes, comparação exata (CT82) e hashes são preservados.
* A ordem das recusas não muda: regras da senha (5.33) antes de "As senhas não coincidem." (P11).

### Resumo da M1 (decidida em 04/10/2026; a implementar)

| | Regra |
|---|---|
| Caracteres tratados | Lista fixa de 31: os 29 espaços em branco do Python 3.11 mais U+200B e U+FEFF (E1) |
| E-mail, extremidades | Removidos antes de validar ou consultar, nas quatro telas, por uma limpeza única no aplicativo (E1, E2) |
| E-mail, meio | Nunca removidos. Cadastro, recuperação e novo e-mail recusam com "Remova os espaços ou caracteres invisíveis do meio do e-mail."; no login, a consulta é preservada e o aviso só aparece se o login falhar (E3) |
| Campo de e-mail | Ao enviar, mostra a versão limpa nas extremidades, mesmo se outra validação impedir o envio; mensagens usam a versão limpa (E4) |
| Senha existente | Comparação exata; após recusa, dica sobre espaços ou invisíveis nas extremidades, nos quatro lugares que conferem a senha (S1) |
| Senha nova | Recusa os 31 caracteres em qualquer posição, com "A senha não pode conter espaços nem caracteres invisíveis." (S2) |
| Preservado | Regra compartilhada de formato e contrato do serviço; senhas, hashes e e-mails gravados; contas antigas |
| Migração | Nenhuma |
| Impacto previsto na implementação | `database/db.py` (validação de senha nova), `backend/main.py` (limpeza e mensagens nas quatro telas de e-mail e nos quatro pontos de senha), um módulo comum para a lista de caracteres, testes das telas de autenticação e de senha, ERS v7.0 (5.31–5.35 e casos de teste) |

*Registro da análise anterior (04/10/2026):* foram levantadas também a forma de gravação do e-mail (como digitado, normalizado ou em duas colunas), o alfabeto aceito, a exigência de ponto no domínio, a canonização por provedor e a normalização Unicode das senhas. Ficam **fora da M1**; a normalização Unicode das senhas foi descartada nesta versão pela autora, e as demais podem voltar como propostas separadas.

---

## M2 — Usuário sem contas e mês vazio na Tela Principal

### Proposta (autora, 04/10/2026)

No primeiro acesso, sem nenhuma conta cadastrada, mostrar **"Registre suas primeiras contas e tenha tudo sob controle"** em vez de "Suas contas estão em dia". Diferenciar usuário sem contas de mês vazio.

### Comportamento atual (v6.0)

* Abaixo dos avisos, a Tela Principal mostra **"Suas contas estão em dia!"** (ícone e texto verdes) sempre que **não há nenhuma conta atrasada em nenhum mês**. Isso inclui o usuário que ainda não cadastrou nada, para quem a frase não faz sentido.
* Com contas atrasadas, o lugar mostra "Você possui contas em atraso!" e "Ver essas contas".
* Na lista do mês exibido, sem contas, aparece **"Nenhuma conta neste mês."**, tanto para o usuário novo quanto para quem tem contas só em outros meses.
* O card "Total do mês" mostra R$ 0,00 e o aviso dos próximos 7 dias fica oculto quando não há contas.

### Decisões (uma por vez)

| # | Decisão | Situação |
|---|---|---|
| U1 | Critério de "usuário sem contas" | **Decidida (04/10/2026): opção (a)**, detalhada abaixo |
| U2 | Onde e como a frase aparece (e o que acontece com "Nenhuma conta neste mês.") | **Decidida (04/10/2026): opção (b)**, detalhada abaixo |
| U3 | Texto para mês vazio quando o usuário tem contas em outros meses | **Decidida (04/10/2026): opção (a)**, detalhada abaixo |
| U4 | Atalho para cadastrar a primeira conta junto da frase | **Decidida (04/10/2026): opção (a)**, detalhada abaixo |

#### U1 — Critério de "usuário sem contas" (decidida em 04/10/2026)

**Decisão:** opção (a).

* O usuário está "sem contas" quando **não existe nenhuma conta dele, em nenhum mês**.
* A situação é calculada pelos dados atuais sempre que a Tela Principal é montada: **sem marca de primeiro acesso e sem migração**.
* Se todas as contas forem excluídas, a orientação volta a aparecer.
* Quem tem contas, mesmo só em outros meses, continua com os avisos atuais ("Suas contas estão em dia!" ou "Você possui contas em atraso!").

#### U2 — Onde e como a orientação aparece (decidida em 04/10/2026)

**Decisão:** opção (b), para o usuário sem nenhuma conta (U1).

* No lugar do aviso "Suas contas estão em dia!" aparece **"Registre suas primeiras contas e tenha tudo sob controle."**
* Estilo: ícone de **adicionar** na cor de ação e texto na cor principal, no mesmo tamanho do aviso atual; **sem aparência de confirmação de sucesso** (nada de ícone de "ok" nem texto verde). As cores vêm da paleta, nos dois temas.
* A lista do mês **não** mostra "Nenhuma conta neste mês." para esse usuário; a orientação basta.
* O card "Total do mês" (R$ 0,00) e o restante da tela não mudam.

#### U3 — Mês vazio para quem tem contas em outros meses (decidida em 04/10/2026)

**Decisão:** opção (a).

* A lista do mês continua mostrando **"Nenhuma conta neste mês."** quando o mês exibido está vazio e o usuário tem contas em outros meses.
* Os avisos gerais de situação das contas ("Suas contas estão em dia!" ou "Você possui contas em atraso!") são preservados.
* Nesse caso **não** aparece a orientação de primeiro cadastro (U2).

#### U4 — Atalho para a primeira conta (decidida em 04/10/2026)

**Decisão:** opção (a). A frase da U2 é **apenas informativa**, sem link nem ação de clique. O cadastro continua pelo botão "+".

### Resumo da M2 (decidida em 04/10/2026; a implementar)

| Situação | Lugar dos avisos | Lista do mês |
|---|---|---|
| Usuário **sem nenhuma conta**, em nenhum mês (calculado pelos dados; sem marca de primeiro acesso; volta a valer se todas as contas forem excluídas) | **"Registre suas primeiras contas e tenha tudo sob controle."**, com ícone de adicionar na cor de ação e texto na cor principal; sem aparência de sucesso; sem clique | Vazia, sem "Nenhuma conta neste mês." |
| Usuário com contas, mês exibido **vazio** | Avisos atuais: "Suas contas estão em dia!" ou "Você possui contas em atraso!" | "Nenhuma conta neste mês." |
| Usuário com contas no mês exibido | Avisos atuais | Contas do mês, como hoje |

* Sem migração. O card "Total do mês", o aviso dos próximos 7 dias e o botão "+" não mudam.
* Impacto previsto na implementação: `backend/main.py` (montagem dos avisos e da lista na Tela Principal), uma consulta de existência de contas do usuário em `database/db.py` (ou reaproveitamento de uma existente), testes da Tela Principal e de legibilidade nos dois temas, ERS v7.0 (5.15–5.16 e casos de teste).

---

## M3 — Seletor de mês e ano na Tela Principal

### Proposta (autora, 04/10/2026)

Em Início, clicar no mês/ano abre um seletor de mês e ano, mantendo as setas.

### Comportamento atual (v6.0)

* O seletor mostra "‹ Outubro 2026 ›". As setas avançam ou voltam um mês; não há limite de ano. O texto do mês não é clicável.
* Ao exibir um mês futuro, as séries **sem término** geram as ocorrências que faltam até esse mês (5.20). A geração não duplica nem toca no histórico, e as ocorrências geradas ficam gravadas.
* "Ver status" usa o mês exibido em Início. O Gráfico tem a própria navegação e não gera ocorrências (P7).
* O calendário de datas do Flutter (usado em Nova/Editar conta) escolhe dias, aparece em inglês (M6) e não tem modo só de mês e ano no Flet.

### Ponto de atenção

Com as setas, a geração sob demanda avança um mês por vez. Um seletor permite saltar muitos anos com um clique e, com isso, gravar de uma vez muitas ocorrências de cada série sem término (por exemplo, 2035 a partir de 2026: cerca de 110 ocorrências por série mensal). Isso é tratado na decisão M3-2.

### Decisões (uma por vez)

| # | Decisão | Situação |
|---|---|---|
| M3-1 | Tipo de seletor | **Decidida (04/10/2026): opção (a)**, detalhada abaixo |
| M3-2 | Faixa de anos permitida e geração sob demanda ao saltar | **Decidida (04/10/2026): opção (b), com faixa ajustada**, detalhada abaixo |
| M3-3 | Como o seletor é aberto e indicado (clique no texto, ícone) | **Decidida (04/10/2026): opção (b)**, detalhada abaixo |
| M3-4 | Destaques no seletor (mês exibido, mês atual) e atalho para o mês atual | **Decidida (04/10/2026): opções (b) e (b)**, detalhada abaixo |

#### M3-1 — Tipo de seletor (decidida em 04/10/2026)

**Decisão:** opção (a), um diálogo próprio do app.

* Clicar no mês/ano de Início abre um diálogo com o **ano** (com setas para trocar) e uma **grade dos 12 meses**.
* O período **atualmente exibido** em Início aparece destacado.
* **Selecionar um mês** fecha o diálogo e navega para ele, como se tivesse chegado pelas setas.
* **Cancelar** fecha sem mudar o período e **sem gerar ocorrências**. Trocar o ano dentro do diálogo também não navega nem gera nada; só a escolha de um mês navega.
* As setas de Início são preservadas.
* Em português e com as cores da paleta, nos dois temas.

#### M3-2 — Faixa de anos e geração sob demanda (decidida em 04/10/2026)

**Decisão:** opção (b), com a faixa ajustada pela autora.

* **Faixa de anos do diálogo:**
  * início: o **menor** entre o ano atual e o primeiro ano com contas do usuário;
  * fim: o **maior** entre o ano atual + 5 e o último ano com contas do usuário;
  * usuário sem contas: do ano atual até o ano atual + 5.
  * "Contas do usuário" inclui as ocorrências já geradas das séries; assim, todo ano que já tem contas fica acessível.
* As setas de ano do diálogo param nos limites da faixa. As setas de mês de Início continuam **livres**, como hoje.
* A regra de geração sob demanda (5.20) **não muda**. A geração acontece **somente depois de selecionar um mês**, exatamente como ao chegar pelas setas; **nunca** ao abrir o diálogo, trocar o ano ou cancelar.
* Sem confirmação extra e sem prévia (mostrar sem gravar) nesta melhoria.

*Dimensionamento (banco real, somente leitura, 04/10/2026):* 2 séries mensais sem término, geradas até set/2027 e mar/2028. Com o limite padrão (ano atual + 5 = 2031), o maior salto pelo diálogo grava cerca de 96 ocorrências; hoje as setas já permitem ir além.

#### M3-3 — Indicação e acesso ao seletor (decidida em 04/10/2026)

**Decisão:** opção (b).

* O mês e o ano ganham um pequeno ícone de **seta para baixo** ao lado, na mesma cor do texto, e a dica **"Escolher mês e ano"**.
* Texto e ícone formam **uma única área clicável**, separada das setas de navegação; as setas continuam fazendo só "mês anterior" e "próximo mês".
* **Teclado:** o controle precisa receber foco pela tecla Tab e abrir o diálogo com Enter ou Espaço, com indicação de foco visível nos dois temas. No Flet 0.86, isso pede um controle de botão (por exemplo, `TextButton` com o texto e o ícone), e não o `Container` atual, que não recebe foco.
* **Nome acessível:** o controle é identificado como botão, com um nome que inclua a ação e o período, por exemplo "Escolher mês e ano, Outubro de 2026" (`Semantics` do Flet).
* Cores da paleta nos dois temas, incluídas na verificação de contraste (texto 4,5:1; ícone e indicação de foco 3:1).

#### M3-4 — Destaques e atalho "Mês atual" (decidida em 04/10/2026)

**Decisão:** (b) e (b).

* **Período exibido em Início:** destacado com **fundo preenchido** na cor de ação e texto contrastante.
* **Mês de hoje:** destacado com **contorno** na cor de ação.
* **Quando coincidem:** os dois estados aparecem juntos (fundo e contorno), sem prejudicar a legibilidade do texto.
* Os dois sinais são distinguíveis sem depender só da cor (fundo cheio × contorno) e têm identificação acessível (por exemplo, "Outubro de 2026, exibido, mês atual").
* **Botão "Mês atual"** ao lado de "Cancelar": seleciona o mês de hoje e fecha o diálogo, com a mesma regra de geração de qualquer seleção (M3-2). Fica **desativado** quando Início já mostra esse período.
* Meses, setas de ano e botões do diálogo recebem foco e funcionam pelo teclado; cores da paleta nos dois temas, verificadas; tudo em português.

### Resumo da M3 (decidida em 04/10/2026; a implementar)

| | Regra |
|---|---|
| Abertura | Mês e ano de Início com ícone de seta para baixo e dica "Escolher mês e ano"; uma única área clicável, separada das setas; foco pelo teclado (Tab, Enter/Espaço) e nome acessível (M3-3) |
| Diálogo | Ano com setas e grade dos 12 meses, em português, nas cores da paleta (M3-1) |
| Faixa de anos | Do menor entre o ano atual e o primeiro ano com contas até o maior entre o ano atual + 5 e o último ano com contas; sem contas, do ano atual até + 5 (M3-2) |
| Destaques | Período exibido com fundo preenchido; mês de hoje com contorno; os dois juntos quando coincidem (M3-4) |
| Ações | Escolher um mês navega e fecha; "Mês atual" navega para hoje e fecha (desativado se já exibido); "Cancelar" fecha sem mudar nada |
| Geração sob demanda | Regra 5.20 inalterada; só depois de selecionar um mês, nunca ao abrir, trocar o ano ou cancelar |
| Preservado | Setas de Início, livres; "Ver status" continua usando o mês exibido; Gráfico com a própria navegação |
| Migração | Nenhuma |
| Impacto previsto na implementação | `backend/main.py` (controle do período, diálogo e foco), testes da Tela Principal (faixa de anos, destaques, "Mês atual", nenhuma geração ao cancelar), testes de legibilidade nos dois temas, ERS v7.0 (5.15, 5.20 e casos de teste) |

---

## M4 — Descrição de até 1.000 caracteres

### Proposta (autora, 04/10/2026)

Aumentar o limite da descrição da conta de 500 para 1.000 caracteres.

### Comportamento atual (v6.0)

* O limite é só uma regra de validação: `LIMITE_DESCRICAO = 500` em `database/limites.py`, lida pela tela (dica "Até 500 caracteres", contador "0/500") e pela gravação. O banco **não** tem restrição de tamanho na coluna: **não há migração**.
* Contagem por caractere percebido (T5); vale para contas avulsas, ocorrências de séries e o modelo da série ("Este mês em diante").
* Ao salvar, espaços e quebras de linha nas pontas são removidos; nada é cortado; um valor acima do limite aparece inteiro e só é salvo depois de respeitar o limite (CT109).
* Em Detalhes, a descrição aparece completa, com quebras de linha e altura automática (P12). Termos e Política não citam o número.

### Decisões (uma por vez)

| # | Decisão | Situação |
|---|---|---|
| M4-1 | Alcance do novo limite | **Decidida (04/10/2026): opção (a)**, detalhada abaixo |
| M4-2 | Altura do campo de descrição no formulário | **Decidida (04/10/2026): opção (b)**, detalhada abaixo |

#### M4-1 — Alcance do novo limite (decidida em 04/10/2026)

**Decisão:** opção (a).

* Limite de **1.000 caracteres percebidos** (contagem T5 preservada) em Nova conta, Editar conta (todos os escopos das séries) e no modelo da série.
* Preservados: o tratamento atual ao salvar (remoção de espaços e quebras de linha nas pontas), a recusa sem corte automático e a exibição completa em Detalhes.
* Nenhum dado existente é alterado; sem migração.
* **Nota de compatibilidade:** uma descrição com mais de 500 caracteres, salva numa versão nova, se aberta por uma versão anterior do Sino (limite de 500), aparece inteira, mas só pode ser salva depois de reduzida a 500 (CT109 da v6.0). É consequência normal de aumentar um limite; não há conversão de dados.
* Impacto previsto na implementação: `database/limites.py` (constante), testes que fixam 500/501 em `test_limites_caracteres`, ERS v7.0 (5.22, 5.23, RF32, tabela de dados e CT59).

#### M4-2 — Altura do campo de descrição (decidida em 04/10/2026)

**Decisão:** opção (b). Em Nova conta e Editar conta, o campo de descrição começa com 2 linhas, cresce até **8** e, a partir daí, rola por dentro. O contador "x/1000" e o aviso de limite continuam; Detalhes continua mostrando a descrição completa (P12).

### Resumo da M4 (decidida em 04/10/2026; a implementar)

* Limite da descrição: **1.000 caracteres percebidos** (T5), em Nova conta, Editar conta (todos os escopos) e no modelo da série.
* Campo do formulário: 2 a 8 linhas, com rolagem interna depois; contador "x/1000".
* Preservados: tratamento ao salvar, recusa sem corte automático, exibição completa em Detalhes, dados existentes.
* Sem migração. Nota de compatibilidade com versões anteriores registrada na M4-1.
* Impacto previsto: `database/limites.py`, `backend/main.py` (altura do campo nas duas telas), `test_limites_caracteres`, ERS v7.0 (5.22, 5.23, RF32, tabela de dados, CT59).

## Forma de trabalho a partir da M5 (autora, 04/10/2026)

As perguntas de cada melhoria passam a ser **agrupadas**. Detalhes técnicos rotineiros (nomes internos, estrutura do código, testes, reaproveitamento de componentes, consistência com padrões já usados no app) são decididos no planejamento sem consulta individual e registrados como **"decisão técnica do planejamento"**; à autora vão só as escolhas de produto, texto ou risco.

---

## M5 — Ocultar o contador do nome do usuário

### Proposta (autora, 04/10/2026)

Ocultar o contador "0/70" do nome do usuário, mantendo o limite e o aviso.

### Comportamento atual (v6.0)

* O nome do usuário aparece em dois formulários: **Cadastro** e **Editar nome** (Ajustes). Os dois usam o mesmo mecanismo dos demais limites (`LimiteDoCampo`): contador "x/70", recusa da edição que passaria de 70 caracteres percebidos (o campo volta ao último valor válido, sem cortar nada), aviso **"Limite atingido"** sob o campo e um som curto.
* Um nome antigo acima de 70 aparece inteiro, com a mensagem de limite, e só é salvo depois de reduzido (P4). A validação ao salvar continua na camada de dados.

### Decisões técnicas do planejamento

* O mecanismo de limite ganha uma opção para **não exibir o contador**, usada só no nome do usuário; recusa, "Limite atingido", som, mensagem para nome antigo acima do limite e validação ao salvar continuam iguais.
* Os demais contadores (nome da conta, nome da categoria, descrição) não mudam.
* Sem migração. Impacto: `backend/main.py`, testes de limites e das duas telas, ERS v7.0 (5.23 e casos de teste).

### Decisões da autora (04/10/2026)

* **M5-A:** contador oculto nos **dois** formulários (Cadastro e Editar nome, em Ajustes).
* **M5-B:** contador **sempre oculto**, sem reaparecer perto do limite; limite de 70, aviso "Limite atingido" e som mantidos.

**M5 decidida; a implementar.**

---

## M6 — Calendário: contraste do dia atual e português

### Proposta (autora, 04/10/2026)

Corrigir o contraste do dia atual no calendário e traduzir o calendário para português.

### Comportamento atual (v6.0)

* O calendário de datas (Nova conta e Editar conta) é o do Flutter, configurado pelo tema do app (`tema_flet`). O dia de hoje usa a cor de ação no texto e no contorno.
* **Defeito confirmado:** quando o dia de hoje é também o **dia selecionado** (o caso comum ao abrir o calendário numa conta nova), o fundo e o número ficam na mesma cor de ação: contraste **1:1**, o número desaparece, nos dois temas. Sem seleção, hoje fica legível (5,36:1 no Claro; 4,53:1 no Escuro).
* O calendário aparece **em inglês** ("Select date", "Cancel", "OK", nomes de meses e dias, entrada digitada no formato americano), porque o app não define idioma para o Flutter.
* A varredura de contraste dos testes não alcança o interior do calendário (desenhado pelo Flutter).

### Decisões técnicas do planejamento

* **Contraste:** a cor do número de hoje passa a depender do estado: selecionado, usa a cor de texto sobre ação (5,36:1 no Claro; 5,53:1 no Escuro); não selecionado, continua com a cor de ação e o contorno. Os pares de cores do calendário entram nos testes de contraste (`test_cores`), já que a varredura não enxerga o interior do componente.
* **Idioma:** o app passa a declarar **português do Brasil** ao Flutter (configuração de idioma da página, disponível no Flet 0.86) e o calendário ganha textos próprios: "Selecione a data", "Cancelar", "OK", rótulo e mensagem de data inválida em português. Isso também traduz textos padrão do Flutter em outros pontos (por exemplo, menus de copiar e colar nos campos); efeito esperado e positivo.
* Sem migração. Impacto: `backend/main.py` (tema do calendário, idioma da página, textos do calendário), testes de cores e das telas de conta, ERS v7.0 (5.36/RNF09 e casos de teste). O registro da pendência em 13.6 da ERS v6.0 passa a apontar para esta melhoria.

### Decisões da autora (04/10/2026)

* **M6-A:** a data continua **digitável** pelo lápis do calendário, no formato **dd/mm/aaaa**.
* **M6-B:** a semana começa no **domingo**.

**M6 decidida; a implementar.**

---

## M7 — Gráfico de colunas por categoria

### Proposta (autora, 04/10/2026)

Adicionar um gráfico de colunas por categoria, com nome, valor e cor, complementando a rosca.

### Comportamento atual (v6.0)

* A tela Gráfico tem, para o período escolhido (mensal ou anual): totais do período, evolução dos gastos (colunas por mês ou por ano), **gastos por categoria** (rosca com legenda: nome, valor e percentual) e comparação com o período anterior.
* A distribuição por categoria segue a ordem do maior valor para o menor, com "Sem categoria" sempre por último (RF22, 5.25), nas cores das categorias (paleta oficial, fora do tema) e no cinza reservado para "Sem categoria".
* Um usuário pode ter até 30 categorias, mais "Sem categoria". Período sem contas: "Ainda não há dados para exibir neste período."
* As fatias da rosca, em cores pastéis, não atingem 3:1 sobre o fundo; a legenda em texto identifica cada fatia, e isso é verificado nos testes (RNF09, 13.6).

### Decisões técnicas do planejamento

* **Mesmos dados e mesma ordem da rosca:** total por categoria no período exibido (mensal ou anual), do maior para o menor, "Sem categoria" por último. Acompanha a troca de período e de modo, sem gerar ocorrências (P7).
* **Mesmas cores:** cor de cada categoria e cinza reservado para "Sem categoria"; nenhuma cor de categoria é alterada.
* **Componente:** o mesmo tipo de gráfico de colunas já usado em "Evolução dos gastos" (`flet_charts`), com o mesmo estilo de rótulo de valor.
* **Legibilidade (RNF09):** ver o critério de acessibilidade abaixo; as colunas **não** são declaradas isentas de contraste.
* **Período sem contas:** o gráfico novo não aparece; vale a mensagem atual do bloco de categorias.
* Sem migração. Impacto: `backend/main.py` (tela Gráfico), testes do Gráfico e de legibilidade, ERS v7.0 (RF22, 5.25, 5.28 e casos de teste).

### Perguntas apresentadas à autora (agrupadas)

* **M7-A — Onde fica:** (a) no mesmo cartão "Gastos por categoria", abaixo da rosca e da legenda; (b) num **cartão próprio** logo depois, por exemplo "Comparativo por categoria"; (c) um alternador "Rosca | Colunas" no cartão atual, mostrando um de cada vez. *Proposto: (b); a rosca fica como está e o novo gráfico ganha espaço próprio.*
* **M7-B — Formato:** (a) **colunas verticais**, com o nome sob cada coluna, quebrando em até duas linhas e com o nome completo na dica ao passar o mouse; (b) **barras horizontais**, com o nome completo à esquerda (cabe melhor um nome de até 30 caracteres). *Proposto: (a), como na proposta; (b) se preferir nomes sempre inteiros.*
* **M7-C — Rótulos:** (a) **só o valor** em R$ acima de cada coluna; (b) valor e percentual. *Proposto: (a); o percentual já está na legenda da rosca.*
* **M7-D — Muitas categorias:** (a) **todas** as categorias do período, com rolagem horizontal quando não couberem; (b) as 8 maiores e uma coluna "Outras" somando as demais; (c) todas, estreitando as colunas. *Proposto: (a); nenhuma categoria fica escondida numa soma.*

### Decisões da autora (04/10/2026)

* **M7-A (b):** cartão próprio **"Comparativo por categoria"**, logo depois de "Gastos por categoria"; a rosca não muda.
* **M7-B (a):** **colunas verticais**, com o nome sob cada coluna (até duas linhas).
* **M7-C (a):** **valor em R$** acima de cada coluna.
* **M7-D (a):** **todas** as categorias do período, com **rolagem horizontal** quando não couberem.
* Dados, ordem e cores iguais aos da rosca.

### Critério de acessibilidade das colunas (decidido em 04/10/2026)

Avaliação (04/10/2026), cores da paleta oficial sobre o fundo do cartão: no Claro, **17 das 30** cores ficam abaixo de 3:1; no Escuro, **3 das 30**. "Sem categoria" passa nos dois temas (3,61:1 e 6,17:1).

* **Forma (WCAG 1.4.11, 3:1):** toda coluna recebe um **contorno** na cor do texto principal do tema (#0B1410 no Claro, 18,72:1 sobre o cartão; #E8EBE7 no Escuro, 13,84:1). O contorno delimita a coluna contra o fundo; o **preenchimento continua sendo a cor da categoria**, sem alteração. O contorno vale para todas as colunas, nos dois temas, para manter o gráfico uniforme. *Decisão técnica do planejamento:* espessura entre 1 e 1,5 px, a ajustar na conferência visual.
* **Identificação sem depender da cor (WCAG 1.4.1):** cada coluna tem o nome da categoria sob ela e o valor em R$ acima, em texto com 4,5:1 nos dois temas (verificado pela varredura de contraste).
* **Nome completo por mouse, teclado e toque:** os rótulos sob as colunas são controles **focáveis** (Tab); **clique, toque ou Enter** num rótulo mostra o nome completo e o valor da categoria (por exemplo, num pequeno balão ou aviso), além da dica ao passar o mouse. Cada rótulo tem nome acessível com a categoria e o valor (por exemplo, "Casa, R$ 1.450,00"). *Motivo técnico:* as colunas do `flet_charts` não recebem foco pelo teclado; os rótulos, sim.
* **Testes:** contorno presente em todas as colunas e com 3:1 sobre o fundo nos dois temas; rótulos e valores com 4,5:1; rótulos focáveis com nome acessível.
* **Rosca existente:** continua como está, com a exceção documentada em 13.6 da ERS v6.0 (identificação pela legenda). Aplicar contorno também às fatias fica como **proposta separada**, não decidida.

### Resumo da M7 (decidida em 04/10/2026; a implementar)

* Cartão "Comparativo por categoria", depois da rosca: colunas verticais, uma por categoria do período, na ordem e nas cores da rosca, com valor acima e nome abaixo; rolagem horizontal quando necessário; some quando o período não tem contas.
* Acessibilidade: contorno contrastante em todas as colunas, nome e valor em texto, nome completo por mouse, teclado e toque.
* Sem migração. Impacto: `backend/main.py` (tela Gráfico), testes do Gráfico e de legibilidade, ERS v7.0 (RF22, 5.25, 5.28, RNF09 e casos de teste).

---

## M8 — Envio real de e-mails e publicação do serviço de códigos

### Proposta (autora, 04/10/2026)

Configurar o envio real de e-mails pela Resend e publicar o serviço de códigos. **Nesta fase, nada é contratado, publicado ou configurado.**

### Situação atual (v6.0)

* O serviço está implementado (`servidor/`: Cloudflare Workers + Durable Objects com SQLite, envio pela Resend), com contrato v1 (`docs/contrato-servico-codigos.md`), 151 testes e verificação de tipos. Funciona localmente (caixa local e modo de demonstração).
* **Já definidos no contrato v1:** regras dos códigos (5.32), limites contra abuso (por destino, por IP e global de 80 envios por dia), retenção (desafios 24 h; contadores 2 h e 48 h; totais globais 35 dias), dados guardados só como HMAC, nada sensível em logs, segredos fora do repositório (`CHAVE_HMAC`, `CHAVE_ASSINATURA`, `KID_ASSINATURA`, `RESEND_API_KEY`, `REMETENTE`).
* **No aplicativo:** `URL_PRODUCAO = None` e nenhuma chave pública de produção; sem configuração, cadastro, alteração de e-mail e recuperação mostram "A confirmação por e-mail não está disponível nesta instalação." e o login continua local.
* **Pendentes desde a Etapa 8 (ERS v6.0, 13.3):** empresa de hospedagem e responsável pela operação; domínio e remetente; tratamento e retenção dos dados pelos provedores; limites adicionais contra abuso. Termos e Política dizem que serão atualizados **antes** da publicação.

### Decisões técnicas do planejamento

* **Contrato:** manter o contrato v1 (a M1 não o altera). Mudanças só se a publicação exigir, com nova versão do contrato e dos testes de conformidade.
* **Ambientes:** um ambiente de **teste** publicado antes do de produção, com o mesmo código e segredos próprios; a produção só depois de o teste passar pela validação manual (entrega real, expiração, tentativas, reenvio, neutralidade).
* **Segredos:** gerados para cada ambiente e guardados só no gerenciador de segredos da hospedagem; nunca no repositório, no app ou em mensagens. Rotação da chave de assinatura pelo identificador (`KID`), com o app aceitando a chave antiga e a nova durante a troca.
* **App:** o endereço e a(s) chave(s) **públicas** de produção entram na configuração de uma versão do app (não são segredos); o modo de demonstração continua separado e nunca aponta para produção.
* **E-mail:** domínio de envio verificado na Resend com os registros de DNS exigidos (SPF, DKIM e, recomendado, DMARC).
* **Operação:** registros de funcionamento sem e-mail, código ou IP em texto (como no contrato); alerta ao atingir o limite global diário.
* **Documentos:** Termos e Política atualizados e revisados antes de abrir para terceiros (depende da M12); ERS v7.0 (5.31–5.35, RNF02, RNF10, RNF11 e 13.x).

### Perguntas apresentadas à autora (agrupadas)

* **M8-A — Hospedagem e conta:** publicar na **Cloudflare** (para onde o serviço foi feito), numa conta **sua**? Plano e custos vigentes devem ser conferidos no momento da contratação. *Proposto: Cloudflare, conta da autora, começando pelo plano gratuito se ele atender aos limites do contrato.*
* **M8-B — Domínio e remetente:** registrar um **domínio próprio** para o Sino ou usar um **subdomínio** de um domínio que você já tenha? E qual remetente (por exemplo, `Sino <nao-responda@…>`)? *Sem domínio verificado, a Resend só entrega ao próprio dono da conta.*
* **M8-C — Responsável e dados pessoais:** você será a **responsável pela operação** e pelo tratamento dos dados do serviço (e-mail e IP, ainda que guardados como resumo), com um contato para pedidos de titulares? *Afeta a Política e a revisão jurídica (M12).*
* **M8-D — Quem pode usar e quando:** (a) publicar primeiro em **uso restrito** (só endereços seus, para validação) e abrir a terceiros **só depois da M12**; (b) abrir a terceiros junto com a publicação. *Proposto: (a).*
* **M8-E — Limites contra abuso:** manter os limites do contrato v1 (incluindo 80 envios por dia no total) ou acrescentar proteção extra no pedido de código, como um desafio anti-robô da hospedagem? *Proposto: manter os do v1 no uso restrito e reavaliar antes de abrir a terceiros.*
* **M8-F — Retenção pelos provedores:** aceitar a retenção padrão de registros da Resend e da Cloudflare, ou configurar o menor prazo que cada uma permitir? Os prazos vigentes serão conferidos e escritos na Política. *Proposto: o menor prazo disponível.*

### Decisões da autora (04/10/2026)

* **M8-A:** Cloudflare, na conta da autora, **priorizando o plano gratuito**, condicionado à conferência dos recursos e custos **antes** de qualquer configuração. **Nenhuma contratação autorizada.**
* **M8-B:** domínio e remetente **a definir**.
* **M8-C:** responsável pela operação e contato para titulares **a definir antes da publicação**.
* **M8-D:** opção (a). Publicação inicial em **uso restrito aos endereços da autora**, com **restrição técnica de destinatários** (não apenas uma orientação). Abertura a terceiros só depois da M12.
* **M8-E:** manter os limites do contrato v1 no uso restrito; **reavaliar a proteção contra abuso antes de abrir a terceiros**.
* **M8-F:** priorizar a **menor retenção adequada** disponível em cada provedor; conferir o que pode ser configurado e quais registros são obrigatórios; documentar os **prazos reais** (na Política e no contrato).

### Restrição técnica de destinatários (decisão técnica do planejamento)

* O serviço ganha uma **lista de destinatários permitidos**, configurada por ambiente como segredo (não no repositório nem no app). Para não guardar e-mails em texto, a lista é comparada pelo mesmo resumo HMAC já usado para os destinos.
* Com a lista ativa, o serviço **não envia** código a nenhum endereço fora dela, mesmo que o pedido chegue por outro cliente:
  * **cadastro e alteração de e-mail:** recusa com um código de erro próprio, que o app mostra como **"O envio de códigos está restrito nesta fase do Sino."** (texto a confirmar na implementação);
  * **recuperação de senha:** mantém a **resposta neutra** de hoje e simplesmente não envia, para não revelar quais endereços são permitidos.
* Lista vazia ou ausente no ambiente de produção **não** significa "aberto a todos": a abertura a terceiros exige uma mudança explícita de configuração, registrada e feita só depois da M12.
* Exige uma pequena evolução do contrato (novo código de erro e a regra da lista), com testes de conformidade. A limitação da própria Resend sem domínio verificado não substitui essa regra.

### Restrição de destinatários — decisões da E3 (autora, 07/10/2026; P39)

Implementação e contrato v1.1 aprovados a partir do plano revisado. **Concluída e publicada no GitHub como Sino 6.2** (07/10/2026; código no commit a76da70). Só o código foi publicado: o serviço de códigos continua sem deploy, sem envio real de e-mails e sem liberação para terceiros. Validação manual em demonstração isolada do commit local a76da70 (07/10/2026): as mensagens das telas foram observadas pela autora (restrição no cadastro e na alteração fora da lista; mensagem neutra na recuperação); os efeitos foram confirmados pelos artefatos (caixa local com exatamente duas mensagens, cadastro para `pessoa1@demonstracao.invalid` e alteração para `pessoa2@demonstracao.invalid`; banco da demonstração com uma conta, no e-mail alterado, e nenhuma conta dos pedidos recusados; registro do serviço com os dois 403 e o 202 neutro). CT157 e CT158 cobertos só pelos testes automáticos.

* **Configuração:** segredo `DESTINATARIOS_PERMITIDOS` por ambiente, só com resumos HMAC: `v1:<verificação>,<resumo>,…`, até 50 únicos. A verificação é um HMAC fixo pela `CHAVE_HMAC` e **só detecta** uma lista gerada com outra chave; não prova a integridade do restante do conteúdo. Ausente, vazia ou inválida (inclusive com resumo repetido): 503. Trocar a `CHAVE_HMAC` exige gerar a lista de novo.
* **Ferramenta local** (`servidor/ferramentas/destinatarios.py`): lê os e-mails sem eco, aplica a regra de e-mail do contrato (sem a M1), ignora repetidos, grava um arquivo novo com permissão 600 e mostra só contagens.
* **Respostas (contrato v1.1):** `403 destinatario_nao_permitido` só no cadastro e na alteração, no pedido (inclusive reenvio e repetição) e na validação; o app mostra "O envio de códigos está restrito nesta fase do Sino.". Recuperação: resposta neutra, desafio sem envio, nunca autoriza.
* **Pontos de conferência:** no pedido (antes do objeto do destinatário); camada A no início do envio (antes da reserva global; estado `bloqueado`); camada B (`EnviadorRestrito`) imediatamente antes do provedor, sem rede e sem repetição; e em toda validação.
* **Desenvolvimento e demonstração:** a lista é exigida também ali, sem modo irrestrito; três endereços fictícios (`pessoa1@demonstracao.invalid`, `pessoa2@…`, `pessoa3@…`), mostrados no terminal e em `destinatarios_ficticios.txt`; envio só na caixa local. Nenhum destinatário real está autorizado.
* **Limites aceitos e documentados:**
  * sem revogação instantânea: autorizações já emitidas valem até o `exp` original; execuções em andamento usam a configuração com que começaram;
  * a recusa pela lista atual é diferente da invalidação persistida do desafio: só uma validação feita com o endereço fora da lista invalida o desafio de forma permanente; remover e incluir de novo sem validação no meio não invalida (limitação registrada; a arquitetura não foi ampliada para isso nesta entrega);
  * pedido de cadastro ou alteração recusado não grava nada e pode ser aceito com a mesma chave depois da inclusão;
  * recuperação sem envio nunca é reativada por repetição.
* **Neutralidade da revogação na recuperação (ajuste da revisão, 07/10/2026):** a marca que impede a reativação só é aplicada quando o código tinha sido enviado, com o instante de invalidação igual ao fim da validade, e é substituída por um novo pedido como qualquer desafio; assim, retenção, repetição e substituição continuam iguais às de um endereço dentro da lista.
* **Estado local antigo:** os objetos do destinatário ganharam uma marca de versão do esquema (v2); estado local de versão anterior não é reaproveitado (503). Aceitável sem migração porque o serviço nunca foi publicado.
* **Versão do app:** Sino 6.2 como candidata para a conclusão da E3, separada da publicação do serviço.

### E4 — preparação (07/10/2026; nada habilitado)

Registro do que a autora já fez e proposta técnica da E4. **Nenhum envio real, chave, segredo, deploy ou alteração de código** nesta fase. Nada aqui é decisão aprovada, salvo o que a autora fez por conta própria (marcado como "fato").

**Fatos (autora, 07/10/2026)**

* Domínio **`appsino.com.br`** registrado no Registro.br, R$ 40 por um ano (válido até 07/10/2027). Equivale à alternativa C; o gasto foi feito e assumido pela autora.
* Conta na **Resend** criada (login pelo GitHub). Domínio de envio **`envios.appsino.com.br`** adicionado, região **São Paulo (sa-east-1)**.
* Registros de DNS **fornecidos pelo painel da Resend** e adicionados pela autora no Registro.br (nomes relativos a `appsino.com.br`):
  * `TXT` `resend._domainkey.envios` — conteúdo DKIM fornecido pela Resend;
  * `CNAME` `rsend.envios` → `rsend-sae1.forge.rmta.net`;
  * `CNAME` `send.envios` → `send.forge.rmta.net`.

  Na Resend, o status continua **"Pending"**. Rastreamento de cliques e de abertura ainda a conferir.
* Contato já publicado nos Termos (item 9) e na Política (item 12): `sino.lembrete.contas@gmail.com`.

**Conferência técnica (somente leitura, 07/10/2026)**

* O estado do projeto é o do encerramento da E3: `main` = `origin/main` = 5b43a60, árvore limpa; banco principal e cinco backups iguais à ref7.
* DNS público (consulta de 07/10/2026, 22:19): os servidores do domínio são os do Registro.br (`a.auto.dns.br`, `b.auto.dns.br`).
  * **Solicitados** (os três acima): `TXT resend._domainkey.envios.appsino.com.br`, `CNAME rsend.envios.appsino.com.br`, `CNAME send.envios.appsino.com.br`.
  * **Encontrados:** nenhum. Os dois servidores do Registro.br respondem com autoridade `NXDOMAIN` para os três nomes (e também para `envios.appsino.com.br`); o resolvedor local também não os encontra. O número de série da zona (SOA) mudou entre as consultas (2026281040 → 2026281050), mas os registros ainda não aparecem.
  * Isso é coerente com o "Pending" da Resend. Não se conclui daqui que falte algum registro nem que os tipos devam mudar: os registros a usar são os do painel da Resend. Conferir de novo depois da publicação da zona.
* Já existe `_dmarc.appsino.com.br` com `v=DMARC1; p=reject;` (sem `sp=`, por isso a política vale também para os subdomínios). O DMARC é uma **orientação publicada para os servidores que recebem** as mensagens: pede que mensagens que falham na autenticação alinhada (SPF ou DKIM) sejam rejeitadas. **Não é uma trava de envio** do Sino nem da Resend. São condições separadas:
  * a **verificação do domínio na Resend**, que a Resend exige para enviar com remetente desse domínio;
  * os **controles do serviço** (lista de destinatários, camadas A e B, configuração do ambiente);
  * o DMARC, que só afeta como o destinatário trata a mensagem que receber.
* Segundo a Resend, a região escolhida define **de onde** os e-mails saem, não onde os dados ficam: os dados da conta (conteúdo, registros) ficam **nos EUA**. Retenção fixa de 30 dias nos planos Free e Pro; remoção até 90 dias após o encerramento da conta (backups por 7 dias).
* Rastreamento de abertura (pixel) e de cliques (troca dos links) vem **desligado por padrão** na Resend; os e-mails do Sino são só texto, sem links nem imagens.

**Integração existente (sem mudança necessária no envio)**

* `servidor/src/envio/resend.ts`: `POST https://api.resend.com/emails` com `from`, `to`, `subject` e `text` (só texto), `Idempotency-Key` = `sino/<finalidade>/<id>`, até 3 tentativas (10 s cada), classificação incerto/falha documentada no contrato.
* Camada B (`EnviadorRestrito`) e lista de destinatários da E3: com domínio verificado, a Resend aceita **qualquer** destinatário; a lista do serviço passa a ser a **única** restrição.
* Configuração: `REMETENTE` (variável) e `RESEND_API_KEY` (segredo); hoje `wrangler.jsonc` usa `Sino <onboarding@resend.dev>`.

**Proposta técnica**

* **Remetente:** `Sino <nao-responda@envios.appsino.com.br>`, coerente com "não é necessário respondê-la". Opcional (exige mudança no adaptador): `reply_to` para o contato público.
* **Chave da API:** criada pela autora no painel, com permissão **só de envio** e restrita ao domínio `envios.appsino.com.br`; **uma por ambiente** (teste e produção). Aparece uma única vez: a autora a digita diretamente em `wrangler secret put RESEND_API_KEY` (com o ambiente certo), sem colar no chat, em arquivos, no `.dev.vars` ou no repositório. Apagar a de teste ao fim da validação, se não for mais usada.
* **Ambiente isolado:** um Worker de teste separado (por exemplo, `sino-servico-codigos-teste` no `workers.dev`), com segredos próprios (`CHAVE_HMAC`, `CHAVE_ASSINATURA`, `KID_ASSINATURA` próprio, `DESTINATARIOS_PERMITIDOS`, `RESEND_API_KEY` de teste), registros do Worker desligados, sem rotas no domínio. O app só o usa numa **cópia isolada** em `~/.local/share/sino-validacao/` com `SINO_SERVICO_URL` e `SINO_SERVICO_CHAVES` próprios. Produção é outro Worker, depois. Exige conta na Cloudflare (ainda não criada) e uma configuração `teste` no `wrangler.jsonc` (mudança de configuração na implementação).
* **Destinatários:** lista gerada com `servidor/ferramentas/destinatarios.py` a partir da `CHAVE_HMAC` do ambiente de teste, com endereços **digitados pela autora**; nenhum endereço é escolhido ou preenchido pelo planejamento.
* **Textos dos e-mails:** manter os aprovados na Etapa 8 (só texto, sem links, sem o nome do usuário, código fora do assunto). Opcional: uma linha de contato no rodapé.
* **Termos e Política (nova versão relevante, novo aceite, antes do primeiro envio real pelo app):** Política item 7 — substituir o parágrafo "ainda não foi publicado" por: hospedagem do serviço (Cloudflare: IP do pedido e resumos, prazos do contrato; registros do Worker desligados ou prazo real); provedor de envio (Resend: recebe o endereço e a mensagem com o código; dados nos EUA; 30 dias; remoção após encerramento da conta); envio a partir de `envios.appsino.com.br`; fase restrita (só endereços autorizados recebem código); transferência internacional (ponto de revisão jurídica); responsável pela operação e canal para titulares (item 12); Política item 1 e Termos item 4 — tirar "quando o serviço estiver publicado"/"ainda não foi publicado" na medida do que for verdade na versão do app que apontar para o serviço; Política item 10 — prazos dos provedores. A versão do app que habilita o envio real só sai depois disso.

**Testes**

* **T0** (local, fictício): mudanças de configuração e adaptador com o enviador simulado.
* **T1** (serviço real na Cloudflare, endereços e conteúdo fictícios; nenhuma chamada à Resend esperada): rotas inválidas, 503 sem configuração, cadastro fora da lista (403), recuperação para endereço fora da lista (202 sem envio), medição de CPU.
  * **Não é um teste sem dados pessoais.** A Cloudflare trata, no mínimo: o **endereço IP real** da conexão de quem testa (a autora), os cabeçalhos e metadados da requisição (horário, país, agente do cliente) nos sistemas próprios da Cloudflare; no serviço, o resumo HMAC do IP (IPv4 inteiro ou prefixo /64) nos contadores, pelos prazos do contrato (2 h e 48 h); os registros do Worker, se ligados (3 dias); e os dados da conta da autora na Cloudflare. Os e-mails usados são fictícios e só entram como resumo.
  * **Decisões a fechar antes do T1:** conta e plano da Cloudflare (sem cartão nem cobrança, a confirmar no cadastro); registros do Worker desligados ou ligados por 3 dias; aceitar o tratamento do próprio IP pela Cloudflare no teste (e registrar os prazos da Cloudflare que forem conferidos); lista do ambiente de teste só com endereços fictícios (por exemplo, `.invalid`) para o T1; e se o Worker de teste recebe já a chave da Resend de teste ou um valor sem uso durante o T1 (sem chave, o serviço responde 503 em tudo). Nenhuma dessas decisões está aprovada.
* **T2** (dados reais aos provedores): só depois do novo aceite, só com endereços autorizados pela autora, pela cópia isolada do app.

### E4 — preparação, continuação (08/10/2026; nada habilitado)

Rodada só de conferência, registro e planejamento. **Nenhum deploy, login pelo Wrangler, configuração remota, chave da Resend, envio real, alteração de DNS, contratação, commit ou push.** Banco principal e backups não foram alterados.

**Conferência do estado (somente leitura, 08/10/2026)**

* `main`; HEAD = `origin/main` = 5b43a60 (Sino 6.2). Alterados só os dois documentos de planejamento (registro de 07/10, não commitado).
* Nenhum processo do aplicativo, da demonstração ou do serviço; portas 8787, 8025 e 9229 livres.
* Banco principal: `quick_check` ok, `user_version` 9, 0 usuários, 0 contas, 0 aceites, sem violações de chave estrangeira, sem `-wal`/`-journal`. Banco e cinco backups com SHA-256, tamanho e mtime iguais à ref7.
* Wrangler: nenhuma sessão de login no computador (sem `~/.config/.wrangler/config`); nenhuma variável `CLOUDFLARE_*` ou `RESEND_*` no ambiente.

**Fatos (autora, 08/10/2026)**

* `envios.appsino.com.br` **verificado** na Resend; "TLS obrigatório" aparece como **"Aplicado"**.
* **Remetente aprovado:** `Sino <nao-responda@envios.appsino.com.br>`.
* **Reply-To aprovado:** `sino.lembrete.contas@gmail.com`. Esse Gmail é o **contato de suporte e de solicitações sobre dados pessoais**; Carinne acompanha a caixa. (Resolve M8-B e M8-C para o uso restrito; a redação nos Termos e na Política continua pendente.)
* **Textos dos e-mails:** manter os atuais (Etapa 8) e acrescentar a linha "Precisa de ajuda? Entre em contato: sino.lembrete.contas@gmail.com".
* **Cloudflare:** conta criada; painel sem projetos; subdomínio da conta `carinnebatista11.workers.dev`. O DNS de `appsino.com.br` **permanece no Registro.br** (nenhuma rota ou domínio próprio na Cloudflare).
* **Rastreamento de abertura e de cliques: NÃO confirmado como desligado.** A tela que estava aberta era o **formulário de criação de subdomínio de rastreamento**, com "cliques" marcado e "abertura" desmarcada; um formulário não mostra o estado salvo do domínio. Nenhuma criação foi confirmada.
  * Segundo a documentação da Resend (conferida em 08/10/2026), o rastreamento é configurado por domínio, vem desligado por padrão e só fica ativo com uma opção ligada **e** um subdomínio de rastreamento verificado. **Um subdomínio de rastreamento, depois de criado, pode ser trocado, mas não removido.** Por isso: **não enviar esse formulário**.
  * Como confirmar: Resend → Domains → `envios.appsino.com.br` → aba **Configuration** → "Enable tracking metrics": abertura e cliques desligados e nenhum subdomínio de rastreamento listado. Conferência obrigatória antes do T2.

**Mudanças necessárias para o envio real (T2; não feitas)**

* `servidor/src/envio/mensagens.ts`: acrescentar ao rodapé a linha de ajuda (o resto dos textos inalterado). Atualizar `test/nucleo/resend.test.ts` e as transcrições de conformidade afetadas.
* `servidor/src/envio/resend.ts`: campo `reply_to` (nome e tipo conferidos na API da Resend: `string | string[]`) a partir de uma variável `RESPONDER_PARA`; ausente = sem `reply_to`. Atualizar a tabela de configuração do contrato (sem mudança nos endpoints; contrato continua v1.1).
* Variáveis: `REMETENTE = Sino <nao-responda@envios.appsino.com.br>`, `RESPONDER_PARA = sino.lembrete.contas@gmail.com`.

**Compatibilidade com a Cloudflare (documentação oficial, conferida em 08/10/2026)**

* **Durable Objects no Workers Free:** disponíveis, **só com SQLite** (o serviço já usa `new_sqlite_classes`). Limites diários (zeram 00:00 UTC; acima deles a operação falha com erro): 100.000 requisições, 13.000 GB-s, 5 milhões de linhas lidas, 100.000 linhas gravadas; 5 GB armazenados no total (a página cita 10 GB e 1 GB por objeto no Free sem conciliar; o serviço guarda poucos KB por objeto). 100 classes por conta (usa 3). Alarmes sem limite específico do Free.
* **Workers Free:** 100.000 requisições/dia; **10 ms de CPU por requisição**; 50 subrequisições; 128 MB; 64 variáveis/segredos de até 5 KB cada (a lista de 50 resumos tem cerca de 3,3 KB). Acima do limite diário: erro 1027.
* **Configuração (Wrangler 4.146.0, o fixado no projeto):** `durable_objects` não é herdado por ambientes; `migrations`, `main`, `observability`, `workers_dev` e `preview_urls` são herdáveis; `send_metrics` só no nível superior. Existe o campo novo `exports`, que substitui o `migrations`; os dois são aceitos, mas um Worker publicado com `exports` não volta ao `migrations`. **Decisão técnica do planejamento:** manter `migrations` (o mesmo usado nos testes e no desenvolvimento).
* **Workers Logs:** ligados por padrão em Workers novos; retenção de 3 dias no Free; o registro de invocação inclui a requisição e metadados. Desligar com `observability.enabled = false` e `observability.logs.invocation_logs = false` (o desligamento completo por `enabled = false` não está descrito explicitamente; conferir no painel depois do deploy).
* **`workers.dev`:** ligado por padrão sem rotas; `preview_urls` deve ser desligado explicitamente. O endereço do Worker de teste seria `sino-servico-codigos-teste.carinnebatista11.workers.dev`; o subdomínio da conta contém o nome da autora e pode ser trocado no painel (decisão da autora; não é necessário para o teste).
* **IP da conexão:** o serviço lê `CF-Connecting-IP` (`src/http.ts`); a Cloudflare o envia a partir da borda. A documentação não diz expressamente se um valor enviado pelo cliente é sobrescrito em `workers.dev`: **conferir no T1** (caso 9 abaixo). O valor `0.0.0.0` usado quando o cabeçalho falta só ocorre fora da Cloudflare (testes locais). IPv6 é agrupado por /64 (`prefixoIp`).

**Revisão do serviço existente**

* `wrangler.jsonc` (produção, nunca publicado): entrada `src/index.ts` (só Resend), remetente `onboarding@resend.dev`, sem `observability`, `workers_dev` nem `preview_urls` explícitos. **Não serve para o ambiente de teste** e não deve ser publicado nesta fase.
* `wrangler.dev.jsonc` (só local): entrada `src/dev.ts`, caixa local em `127.0.0.1`; `urlDaCaixaLocal` recusa outro endereço. Não pode ser publicado (o receptor local não existe na Cloudflare, e o serviço responderia 503 em tudo).
* Bindings: `DESTINO`, `LIMITE_IP`, `TETO_GLOBAL`; migração `v1` com as três classes SQLite. Segredos: `CHAVE_HMAC`, `CHAVE_ASSINATURA`, `DESTINATARIOS_PERMITIDOS`, `RESEND_API_KEY`; variáveis `REMETENTE`, `KID_ASSINATURA`.
* `EnviadorSimulado` (testes) não é usado por nenhuma entrada publicada. `EnviadorRestrito` (camada B) envolve qualquer enviador; a camada A está em `fluxos.executarEnvio`.
* Respostas HTTP nunca trazem código, e-mail ou segredo; `registro.ts` só escreve contexto e tipo do erro. A demonstração do app só vale com o serviço em `127.0.0.1` (`backend/fluxos_codigo.py`), então não se aplica ao ambiente remoto.

**Proposta do ambiente remoto de testes (T1; não aprovada)**

* **Worker separado** `sino-servico-codigos-teste`, em configuração própria `servidor/wrangler.teste.jsonc` (mesmo padrão do `wrangler.dev.jsonc`; o `wrangler.jsonc` de produção fica intocado). Todo comando leva `-c wrangler.teste.jsonc`; um `wrangler deploy` sem `-c` publicaria a produção, por isso nenhum comando sem `-c` faz parte do plano.
* **Entrada própria `src/teste.ts`, sem envio real por construção:** usa um `EnviadorDescarte` (sem rede, sem registro do conteúdo; devolve "aceito"), envolvido pelo `EnviadorRestrito`. Não importa `resend.ts` nem `caixa_local.ts`, e `RESEND_API_KEY` não é lida (`segredosDoAmbiente(env, false)`). O código gerado não sai do serviço: **ninguém consegue obtê-lo**, então o caminho do código correto continua coberto só pelos testes locais.
* **Autenticação do teste:** segredo `TOKEN_TESTE` (32 bytes aleatórios, base64url) exigido em `Authorization: Bearer …`, comparado em tempo constante **antes** de ler o corpo e de tocar nos Durable Objects. Falta ou erro → `404 rota_nao_encontrada` (não revela o serviço nem consome objetos). O app não envia esse cabeçalho; o T1 é feito por um roteiro local, não pelo app.
* **Configuração `wrangler.teste.jsonc` proposta:** `name` `sino-servico-codigos-teste`; `main` `src/teste.ts`; mesma `compatibility_date`; `send_metrics: false`; `workers_dev: true`; `preview_urls: false`; `observability: { enabled: false, logs: { enabled: false, invocation_logs: false } }`; os mesmos bindings e a migração `v1`; `vars`: `KID_ASSINATURA = "teste-1"`; sem `REMETENTE`, sem rotas.
* **Segredos exclusivos do teste:** `CHAVE_HMAC`, `CHAVE_ASSINATURA`, `TOKEN_TESTE` gerados localmente (nunca reaproveitados em produção) e `DESTINATARIOS_PERMITIDOS` gerado com `destinatarios.py` a partir dessa `CHAVE_HMAC`, só com endereços fictícios `.invalid` (por exemplo `pessoa1@teste.invalid`, `pessoa2@teste.invalid`). Ficam numa pasta nova `~/.local/share/sino-validacao/e4-teste-<data>/` (permissão 700, arquivos 600), fora do repositório; vão à Cloudflare com `--secrets-file` no próprio deploy (sem janela sem segredos). Nenhum segredo no chat, no `.dev.vars` ou no Git. **Sem `RESEND_API_KEY`** no T1.
* **Limites:** os do contrato (5/h e 10/dia por destino; 10/h e 30/dia de pedidos por IP; 30 validações/h por IP; teto global 80/dia), mais os do Free. Pedidos sem token param no 404 antes de qualquer objeto, o que limita o custo de varreduras ao Worker.
* **Retenção e descarte:** dados dos objetos pelos prazos do contrato (desafios 24 h, contadores 2 h e 48 h, totais globais 35 dias); Workers Logs desligados; nenhum `wrangler tail` gravado em arquivo (se usado, só na tela). Duração do ambiente: até o fim do T1 e **no máximo 7 dias** depois do deploy; então é removido (procedimento abaixo).
* **Dados pessoais no T1:** os e-mails são fictícios e só entram como resumo; o IP real da autora é tratado pela Cloudflare (borda e metadados da requisição) e, no serviço, como resumo HMAC por até 48 h; os dados da conta da autora ficam na Cloudflare. Aceitar esse tratamento é decisão da autora (já listada em 07/10).

**Testes e critérios de aprovação**

* **T0 (local, sem rede, antes do deploy):** testes novos de `src/teste.ts` (sem token e token errado → 404 sem tocar nos objetos; token certo → contrato normal; `EnviadorDescarte` nunca chama `fetch`); suítes atuais aprovadas (app 950, serviço 215 mais os novos; typecheck); `wrangler deploy --dry-run --outdir` com o pacote gerado **sem** `api.resend.com`, `127.0.0.1` e `RESEND_API_KEY`; `wrangler dev -c wrangler.teste.jsonc` local respondendo ao roteiro do T1.
* **T1 (remoto; roteiro local `servidor/ferramentas/teste_remoto.py`, só biblioteca padrão, que lê URL e token de arquivo 600 e mostra só status e nomes de erro):**
  1. sem token e com token errado → 404;
  2. rota inexistente → 404; `GET /v1/desafios` → 405; corpo acima de 4096 bytes → 413; JSON inválido → 400;
  3. cadastro para endereço da lista → 201; repetição com a mesma chave → mesma resposta;
  4. validação com código errado → 422 com `tentativas_restantes` decrescendo; esgotar → desafio encerrado conforme o contrato;
  5. cadastro e alteração para endereço fora da lista → 403 `destinatario_nao_permitido`;
  6. recuperação para endereço fora da lista → 202 neutro;
  7. pedido para o mesmo destino antes de 60 s → 429 `aguarde`; sexto pedido para o mesmo destino na hora (com intervalos de 60 s) → 429 `limite_excedido`;
  8. painel: nenhum erro de CPU (1102) e tempo de CPU por requisição abaixo de 10 ms nas métricas;
  9. IP: pedidos para endereços fora da lista com `CF-Connecting-IP` forjado e variado ainda contam no mesmo limite por IP (o limite é consumido antes da conferência da lista: os 10 primeiros pedidos da hora → 403, o seguinte → 429 `limite_excedido`), provando que o valor do cliente não é usado. Como os casos 3 a 7 também consomem os 10 pedidos/hora do IP, o roteiro conta os pedidos e faz o caso 9 numa hora cheia separada;
  10. painel: Workers Logs desligados, só `workers.dev` (sem Preview URLs), segredos listados só por nome, três namespaces de Durable Objects, nenhuma chamada de saída à Resend.
  * **Aprovação:** todos os casos com o resultado esperado, nenhum código, e-mail ou segredo em respostas, terminal ou registros, e nenhum gasto.
* **T2 (envio real):** fora desta proposta; só depois do novo aceite dos Termos e da Política e de autorização própria.

**Comandos propostos (não executados; ordem; todos em `servidor/`, com o Node do projeto)**

1. `npx wrangler login` — abre o navegador para autorizar o Wrangler na conta da autora; grava um token OAuth em `~/.config/.wrangler/config/default.toml`. Não cria recursos.
2. `npx wrangler whoami` — mostra a conta conectada (conferir que é a da autora). Não altera nada.
3. `python3 ferramentas/teste_remoto.py preparar --pasta ~/.local/share/sino-validacao/e4-teste-<data> --url https://sino-servico-codigos-teste.carinnebatista11.workers.dev` — cria só a pasta local (700) com `segredos.json`, `segredos.env` e `teste_remoto.json` (600, nunca sobrescritos), com a lista dos três endereços fictícios `.invalid`; não mostra segredos.
4. `npx wrangler deploy -c wrangler.teste.jsonc --dry-run --outdir <pasta>/pacote` — compila sem enviar nada; o pacote é inspecionado (T0).
5. `npx wrangler deploy -c wrangler.teste.jsonc --secrets-file <pasta>/segredos.json` — **cria** o Worker `sino-servico-codigos-teste`, os três namespaces de Durable Objects (migração `v1`), a rota `workers.dev` e os quatro segredos; não toca em DNS nem no `appsino.com.br`.
6. `npx wrangler secret list -c wrangler.teste.jsonc` — lista só os nomes dos segredos. Não altera nada.
7. `python3 ferramentas/teste_remoto.py basico --config <pasta>/teste_remoto.json`; numa hora UTC seguinte, `… limite-destino …`; noutra, `… ip …` — executam o T1 (casos 1–7 e 9). Gravam só nos objetos do Worker de teste e em `<pasta>/janelas.json`.
8. Conferência no painel (sem comando): Logs, domínios e rotas, métricas de CPU, Durable Objects.

**Encerramento e remoção (até 7 dias depois do deploy)**

1. `npx wrangler delete -c wrangler.teste.jsonc --dry-run` e depois sem `--dry-run` — remove o Worker de teste, seus segredos, a rota `workers.dev` e os recursos associados. A documentação não diz expressamente o que acontece com os dados dos Durable Objects: conferir no painel (Workers & Pages e Durable Objects) que os três namespaces sumiram; se restarem, removê-los pelo painel.
2. Apagar a pasta local `e4-teste-<data>` (segredos, token, pacote) com `shred -u` nos arquivos de segredo.
3. `npx wrangler logout` — revoga o token OAuth e apaga a credencial local.
4. Registrar a remoção nestes documentos (data, conferência no painel).

**P40 — decisões da autora (08/10/2026)**

* **Aprovado** o desenho do ambiente remoto de testes separado (Worker `sino-servico-codigos-teste`, `wrangler.teste.jsonc`, entrada `src/teste.ts` com envio fictício sem acesso à Resend, autenticação por `TOKEN_TESTE`, proteção dos códigos e dados sensíveis), com **duração máxima de 7 dias após o deploy**.
* A autora está **ciente e concorda** que a Cloudflare processe o seu IP real durante os testes.
* **Mantido** o subdomínio `carinnebatista11.workers.dev`.
* **Autorizada só a implementação e a validação locais** (código, testes, roteiro, compilação de verificação, documentos). **Não autorizados:** deploy, login pelo Wrangler, configuração remota, envio real, commit e push.
* Continua pendente: rastreamento da Resend (conferir na aba Configuration antes do T2); Termos e Política novos (redação, revisão e aprovação).

**T0 — implementação e validação locais (08/10/2026; commit local depois da revisão, sem push)**

* **Arquivos novos:** `servidor/src/teste.ts` (entrada), `servidor/src/acesso_teste.ts` (token; 404 antes de qualquer objeto; comparação em tempo constante), `servidor/src/envio/descarte.ts` (`EnviadorDescarte`), `servidor/src/ambiente.ts`, `servidor/wrangler.teste.jsonc`, `servidor/ferramentas/teste_remoto.py`, `servidor/test/nucleo/ambiente_teste.test.ts`, `tests/test_teste_remoto.py`.
* **Arquivos alterados:** `servidor/src/index.ts` (só reorganização, sem mudança de comportamento: a leitura dos segredos e a montagem das dependências passaram para `src/ambiente.ts`, que não importa nenhum enviador, para que o pacote de teste não leve o adaptador da Resend), `servidor/test/workers/objetos.test.ts` (2 testes da entrada de teste no simulador), `servidor/test/nucleo/tsconfig.json`, `servidor/README.md`. `wrangler.jsonc` de produção **inalterado**.
* **Decisões técnicas do planejamento:** `observability.traces` também desligado; roteiro dividido em três comandos (`basico`, `limite-destino`, `ip`), cada um numa hora UTC diferente, porque os casos consomem o limite de 10 pedidos/hora do IP (7 + 6 + 11 = 24 dos 30 diários); o roteiro registra as horas usadas e recusa repetir a mesma; o caso 8 (CPU) e o 10 (painel) ficam como conferência visual no painel. O token errado ou ausente gera um aviso genérico no registro do Worker (sem o token), que fica desligado no ambiente remoto.
* **Resultados:**
  * serviço: **224 testes aprovados** (215 + 9 novos), typecheck ok (225 depois da revisão pré-commit, abaixo); os testes conferem que a entrada de teste não alcança `resend.ts`, `caixa_local.ts`, `simulado.ts`, `index.ts` nem `dev.ts`;
  * aplicativo: **960 testes aprovados** (950 + 10 do roteiro), sem rede (964 depois da revisão pré-commit);
  * compilação de verificação `wrangler deploy -c wrangler.teste.jsonc --dry-run --outdir …` (nada enviado): pacote de 127 KiB **sem** `api.resend.com`, `resend`, `RESEND_API_KEY`, `127.0.0.1`, caixa local nem `onboarding`, e **sem nenhuma chamada `fetch` de saída** (só os manipuladores de entrada); bindings: os três Durable Objects e `KID_ASSINATURA`. A configuração de produção continua compilando igual (`--dry-run`);
  * ensaio local com `wrangler dev -c wrangler.teste.jsonc` (127.0.0.1, segredos descartáveis, estado novo por comando): `basico` 20/20 aprovado; `limite-destino` 6/6 aprovado; `ip` com o 11.º pedido **403** em vez de 429 — esperado fora da Cloudflare, porque o simulador local usa o `CF-Connecting-IP` enviado pelo cliente; isso mostra que o caso 9 distingue as duas situações e só o resultado remoto vale. Nenhum token, e-mail ou evento do serviço nos registros do ensaio. Segredos do ensaio apagados com `shred`; portas livres ao fim;
  * banco principal e cinco backups iguais à ref7 depois de tudo.
* **O que o T1 remoto consegue validar:** token (1), rotas e formato (2), cadastro e repetição (3), código errado até esgotar e segredo que não confere (4), fora da lista no cadastro e na alteração (5), recuperação neutra (6), intervalo de 60 s e limite por destino (7), CPU no painel (8), tratamento do `CF-Connecting-IP` forjado pela borda (9) e configuração no painel (10).
* **O que não consegue validar:** a validação com o **código correto** (200 e autorização assinada), porque o código é descartado e ninguém o conhece; a autorização, a verificação pelo app e o fluxo completo pelo app ficam com os testes locais e com o T2. Também não testa a Resend, o remetente, o Reply-To nem os textos dos e-mails. (O `wrangler dev` local expõe ferramentas de inspeção em `127.0.0.1/cdn-cgi/local/…`; isso só existe no simulador local, não no Worker publicado.)

**Revisão pré-commit do T0 (08/10/2026)**

* **Escopo:** só os arquivos da implementação do T0 e a documentação; nenhum banco, backup, segredo ou arquivo temporário. Varredura sem chaves hexadecimais de 64 caracteres, tokens, `account_id` ou chaves da Resend; os únicos e-mails são fictícios (`.invalid`, `exemplo.com`), o remetente aprovado e o contato público já publicado nos Termos.
* **Produção preservada:** `wrangler.jsonc` inalterado. Comparação dos pacotes de produção (`--dry-run`) do HEAD 5b43a60 e da árvore atual, módulo a módulo: 26 de 28 módulos idênticos; só `src/index.ts` e o novo `src/ambiente.ts` diferem, com o mesmo código redistribuído (mesmas condições, mesmos avisos na mesma ordem, mesmo relógio padrão, mesmas exportações).
* **Isolamento do envio fictício:** a entrada de teste não alcança `resend.ts`, `caixa_local.ts`, `simulado.ts`, `index.ts` nem `dev.ts` (teste automático); o pacote de teste não tem `api.resend.com`, `RESEND_API_KEY`, `127.0.0.1`, caixa local nem `onboarding`, e não tem nenhuma chamada `fetch` de saída.
* **Logs e traces:** desligados em `wrangler.teste.jsonc` (`enabled: false` no geral, nos logs e nos traces; `invocation_logs: false`). **Correção da revisão:** acrescentados `head_sampling_rate: 0` (geral, logs e traces) e `persist: false` (logs e traces), porque a documentação não descreve expressamente que `enabled: false` basta; novo teste automático fixa toda a configuração de teste (Worker separado, entrada, só `workers.dev`, sem rotas, registros desligados, sem `account_id`, só `KID_ASSINATURA` nas variáveis, objetos e migração iguais aos da produção). A conferência no painel depois do deploy continua no caso 10.
* **Limites (sem alteração; o roteiro se planeja por eles):** janelas fixas em UTC (hora cheia; dia de 00:00 a 23:59 UTC = 21:00 a 20:59 em Brasília, UTC−3). Só contam requisições ao Worker de teste; recusas pelo token (404) não contam.

  | Comando | Pedidos do IP | Pedidos por destino | Validações do IP | Reservas do teto | Duração |
  |---|---|---|---|---|---|
  | `basico` | 7 (de 10/h) | pessoa1 1, pessoa2 1 (de 5/h) | 7 (de 30/h) | 2 (de 80/dia) | < 1 min |
  | `limite-destino` | 6 (de 10/h) | pessoa3 5 aceitos + 1 recusado | 0 | 5 | ~5 min |
  | `ip` | 11 (10 + 1 que deve ser recusado) | nenhum (fora da lista) | 0 | 0 | < 1 min |

  **Correção da revisão:** o registro de janelas só impedia dois comandos na mesma hora; uma repetição no mesmo dia UTC passaria dos 30 pedidos diários do IP (24 + 7 = 31) e uma terceira execução de `limite-destino` bateria no limite diário de 10 do destino, gerando falhas que não seriam do serviço. O roteiro agora recusa, antes de enviar qualquer pedido: dois comandos na mesma hora UTC; passar de 30 pedidos do IP no dia UTC; `limite-destino` mais de 2 vezes no dia UTC; `limite-destino` depois do minuto 51. Testes novos conferem essas regras e que os valores usados pelo roteiro são os de `servidor/src/config.ts`.
* **Horários possíveis:** cada comando numa hora UTC diferente, no mesmo dia UTC ou em dias diferentes, dentro dos 7 dias do ambiente. Exemplo em Brasília, num só dia UTC: `basico` às 10:05; `limite-destino` entre 11:00 e 11:51; `ip` às 12:05. Repetir qualquer comando: depois das 21:00 em Brasília (novo dia UTC). Se um comando falhar por conexão, a hora fica registrada: repetir na hora seguinte, respeitando o limite diário.
* **Caso de IP (9): continua pendente de validação remota.** No ensaio local o 11.º pedido deu 403 (o simulador usa o cabeçalho do cliente), o que mostra que o caso distingue as duas situações. No remoto, um 403 no 11.º pode indicar que a borda usou o valor do cliente **ou** que a conexão alternou entre IPv4 e IPv6 (limites separados); repetir noutra hora antes de concluir.
* **Checks depois das correções:** serviço **225** testes aprovados e typecheck ok; aplicativo **964** aprovados (950 + 14 do roteiro); compilação de verificação da configuração de teste igual (127 KiB, mesmas ausências); ensaio local `basico` 20/20 aprovado com a configuração final (sem token ou e-mails no registro; segredos do ensaio apagados com `shred`; portas livres); banco principal e backups iguais à ref7.

### Pendências da M8 (não resolvidas)

* ~~Domínio e remetente (M8-B).~~ Resolvido para o uso restrito em 08/10/2026 (remetente e Reply-To aprovados).
* ~~Responsável pela operação e contato para titulares (M8-C).~~ Resolvido para o uso restrito em 08/10/2026 (Carinne; `sino.lembrete.contas@gmail.com`); falta a redação nos Termos e na Política.
* Rastreamento de abertura e de cliques na Resend: confirmar desligado (08/10/2026: não confirmado).
* Conferência de recursos, limites e custos dos planos da Cloudflare e da Resend, antes de configurar (M8-A).
* Conferência dos prazos de retenção configuráveis e obrigatórios de cada provedor (M8-F).
* Termos, Política e revisão jurídica antes de abrir a terceiros (M12).

### Conferência dos provedores (06/10/2026, fontes oficiais; nada contratado nem configurado)

Os valores abaixo valem na data da consulta e precisam ser conferidos de novo **imediatamente antes** de criar contas ou publicar.

**Recursos que o serviço usa** (conferido em `servidor/wrangler.jsonc` e `src/`): um Worker; três classes de Durable Objects **com SQLite** (`DestinoDO`, `LimiteIpDO`, `TetoGlobalDO`), com **alarmes** para limpeza e retenção; chamadas HTTP à API da Resend. Sem KV, D1, R2 nem tarefas agendadas. A criptografia é HMAC-SHA256 e Ed25519, sem derivação de chave pesada.

**Cloudflare Workers — plano gratuito**

| Item | Gratuito | Pago (referência) |
|---|---|---|
| Preço | US$ 0 | mínimo de US$ 5 por mês por conta |
| Requisições do Worker | 100.000 por dia (zera à meia-noite UTC; acima disso, erro 1027) | 10 milhões por mês incluídos |
| CPU por requisição | 10 ms | 30 milhões de ms de CPU por mês incluídos |
| Subrequisições | 50 por requisição | — |
| Durable Objects | **só com SQLite** (o caso do serviço): 100.000 requisições por dia, 13.000 GB-s por dia, 5 milhões de linhas lidas e 100.000 escritas por dia, 5 GB no total. Acima do limite, a operação **falha com erro**, sem cobrança | 1 milhão de requisições por mês, 400.000 GB-s, 25 bilhões de leituras e 50 milhões de escritas incluídas |
| Alarmes | cada `setAlarm()` conta como uma linha escrita | idem |
| Endereço | subdomínio `workers.dev` gratuito, "para projetos pessoais ou hobby", no formato `<nome-do-worker>.<subdominio>.workers.dev` | — |
| Registros (Workers Logs) | **ativados por padrão** nos Workers novos; retenção de **3 dias**; até 200.000 por dia. Podem ser desligados com `"observability": { "enabled": false }` | retenção de 7 dias |

* **Cartão:** a documentação oficial consultada **não diz** se o plano gratuito exige cartão. Relatos da comunidade indicam que não. Isso fica **a conferir no cadastro**: se for pedido cartão ou qualquer cobrança, o trabalho para e a autora decide.
* **Adequação:** o uso restrito (alguns códigos por dia, teto global de 80 envios por dia no contrato v1) fica muito abaixo dos limites. O limite de **10 ms de CPU** parece suficiente (só HMAC e Ed25519), mas precisa ser **medido** no ambiente de teste antes da produção.
* Desligar o `workers.dev` não desliga as URLs de versão e de pré-visualização, que continuam acessíveis.

**Resend — plano gratuito (e-mails transacionais)**

| Item | Gratuito | Pro (referência) |
|---|---|---|
| Preço | US$ 0 por mês | US$ 20 por mês |
| Cota | 3.000 e-mails por mês, **100 por dia** | 50.000 por mês, sem limite diário |
| Domínios | 3, segundo a página de preços (a conferir no cadastro) | 10 |
| Velocidade | 10 requisições por segundo por equipe | idem |
| Retenção | **30 dias** de dados de e-mail (conteúdo, metadados, eventos, registros) **em todos os planos**; só o plano Enterprise tem retenção flexível. Backups mantidos por 7 dias; dados guardados nos EUA | idem |
| Reputação | taxa de devolução abaixo de 4% e de spam abaixo de 0,08%; acima disso, o envio pode ser suspenso | idem |

* **Cartão:** a página de preços apresenta o plano gratuito sem cobrança. A exigência de cartão fica a conferir no cadastro, com a mesma regra acima.
* **Sem domínio próprio:** pelo domínio de testes `resend.dev` (remetente `onboarding@resend.dev`, que é o que está hoje em `wrangler.jsonc`), a Resend **só entrega ao e-mail da própria conta Resend**. Para qualquer outro destinatário, a API recusa (erro 403) e exige um domínio verificado.
* **Retenção não configurável:** como a Resend guarda o conteúdo do e-mail (que inclui o código) por 30 dias, a decisão M8-F ("menor retenção adequada") fica limitada a esse prazo no plano gratuito. Isso precisa entrar na Política (5.49, M12). O código perde a validade bem antes, pelo contrato.

**Domínio** (só se a autora quiser mais de um endereço ou um remetente próprio)

* Subdomínio de um domínio que a autora já tenha: sem custo novo. Exige acesso ao DNS para os registros de SPF e DKIM (DMARC recomendado).
* Domínio `.com.br` novo: cerca de **R$ 40 por ano** no Registro.br, exige CPF ou CNPJ (valor de fontes secundárias, a conferir no Registro.br). **Não há gasto autorizado.**
* Cloudflare Registrar: preço de custo, sem margem, segundo a Cloudflare. A página não traz valores; seria um gasto, igualmente não autorizado.

**Alternativas para o uso restrito**

| | Remetente | Quem recebe | Custo | Limitações |
|---|---|---|---|---|
| **A** | `onboarding@resend.dev` + `workers.dev` | **Só o e-mail da conta Resend** (um endereço da autora) | US$ 0 | Um único destinatário; remetente genérico; domínio destinado a testes; não serve para terceiros |
| **B** | Subdomínio de domínio já existente da autora + `workers.dev` | Os endereços da lista permitida | US$ 0 extra | Exige ter um domínio e acesso ao DNS |
| **C** | Domínio novo + `workers.dev` | Os endereços da lista permitida | cerca de R$ 40 por ano (`.com.br`) | **Exige autorização de gasto** |

Nas três alternativas, a **restrição técnica de destinatários** do serviço (5.49, T10) continua obrigatória: na A, a regra da Resend não substitui a regra do serviço.

**Caminho até um código real no e-mail da autora** *(exemplo com a alternativa A, que **não está aprovada**; a escolha entre A, B e C e a do provedor continuam abertas)*

1. A autora define o responsável pela operação e o contato para titulares, e escolhe a alternativa A, B ou C.
2. A autora cria as contas gratuitas na Cloudflare e na Resend (na A, com o e-mail que vai receber os códigos), conferindo que não há cartão nem cobrança.
3. **Entrega 1:** M12 técnica com a migração v9 (aceites).
4. **Entrega 2:**
   * no serviço: restrição de destinatários, evolução do contrato e testes;
   * no app: mensagem do erro novo;
   * textos dos Termos e da Política (provedores, retenção de 30 dias da Resend, 3 dias de registros da Cloudflare ou registros desligados, responsável, contato), com novo aceite;
   * segredos gerados e cadastrados só na Cloudflare;
   * publicação do ambiente de teste e medição de CPU;
   * validação com envio real;
   * produção restrita e configuração da versão do app.

**Provedor (06/10/2026):** o envio pode usar a Resend (já integrada ao serviço) **ou outro provedor**, a avaliar na E4 com os mesmos critérios: plano sem cobrança, destinatários permitidos sem domínio próprio, retenção, limites e exigência de cartão. Trocar de provedor exige um novo adaptador no serviço (`src/envio/`), com testes. **Nenhuma contratação ou cobrança autorizada.**

**Pergunta para a autora:** o envio real no **ambiente de teste**, usado só numa cópia de validação apontada por `SINO_SERVICO_URL`, pode acontecer **antes** dos textos novos e do novo aceite? A versão publicada do app só apontaria para a produção depois deles (5.49). *Proposto: sim. O teste não habilita o envio na versão publicada.*

**Nada é criado, contratado, configurado (incluindo DNS) ou publicado nesta fase.**

---

## M9 — Reavaliar a restrição de uso comercial

### Proposta (autora, 04/10/2026)

Reavaliar a restrição de uso comercial nas próximas versões, preservando as permissões MIT das versões anteriores. **A licença não muda agora.**

### Situação atual

* **Decisão vigente (04/10/2026):** o Sino continua sob a **licença MIT** (arquivo `LICENSE` e README), até uma nova escolha explícita da autora.
* Em 04/10/2026 foi preparada e **descartada** uma proposta: PolyForm Noncommercial 1.0.0 para código, testes e ferramentas, e "todos os direitos reservados" (com visualização permitida) para documentos, paleta e imagens. Uma cópia fica guardada fora do repositório, só como referência (`~/.local/share/sino-validacao/proposta-licenca-descartada-20261004/`).
* Pontos já levantados nessa análise:
  * permissões MIT já concedidas **não podem ser revogadas**: quem obteve uma versão sob MIT mantém esses direitos sobre ela;
  * uma licença nova só vale a partir de uma versão ou commit identificado;
  * restringir o uso comercial faz o projeto deixar de ser "open source" no sentido da OSI (passa a "código-fonte disponível");
  * componentes de terceiros mantêm as próprias licenças;
  * os Termos de Serviço do GitHub permitem ver e fazer fork de repositórios públicos.

### Decisões técnicas do planejamento

* Nada muda em `LICENSE`, README, metadados ou documentos até uma escolha explícita da autora.
* Quando houver nova escolha, o planejamento seguirá o que já foi preparado: texto oficial sem alteração de cláusulas, alcance explícito por tipo de arquivo, marco claro da versão a partir da qual vale, registro de que as versões anteriores continuam sob MIT, canal de pedidos de autorização e atualização das notas da versão.

### Perguntas apresentadas à autora (agrupadas)

* **M9-A — Momento da reavaliação:** (a) antes de lançar a v7.0; (b) antes de abrir o serviço de códigos a terceiros (junto da M8 e da M12); (c) sem data, só quando a autora pedir. *Proposto: (b), porque é quando outras pessoas passam a depender do Sino.*
* **M9-B — Ponto de partida:** reaproveitar a proposta descartada como base, ou reabrir todas as opções (PolyForm Noncommercial, todos os direitos reservados, CC BY-NC só para documentos, Business Source License, manter MIT)? *Proposto: reabrir as opções, usando a proposta descartada como referência.*
* **M9-C — Revisão jurídica:** incluir a escolha da licença na mesma revisão jurídica da M12? *Proposto: sim.*

### Decisões da autora (04/10/2026)

* **M9-A (c):** manter a **MIT** e reavaliar **somente quando a autora solicitar explicitamente**.
* **M9-B:** se a reavaliação acontecer, **reabrir as opções**, usando a proposta descartada **apenas como referência**.
* **M9-C:** qualquer futura mudança de licença entra na **revisão jurídica**.
* **Situação (04/10/2026):** M9 **adiada** e **fora das condições de conclusão da v7.0**. Nada muda na licença atual.

### Reabertura da M9 (autora, 06/10/2026)

**Pedido explícito da autora**, como previsto na decisão M9-A (c): revisar a licença **antes** das melhorias de UX da v7.0.

**Objetivo declarado:** poder **comercializar o Sino no futuro, no Android e no iOS**, e impedir que terceiros comercializem o aplicativo ou versões derivadas sem autorização.

**Situação:** a decisão de manter a MIT está **reaberta**. O arquivo `LICENSE` **não muda** nesta fase. O registro histórico da MIT é preservado.

#### Fatos conferidos (06/10/2026)

* O repositório `carinne-batista11/sino` é **público** no GitHub desde 06/08/2026, com a **MIT** no arquivo `LICENSE` desde o primeiro commit (`e4274d8`). O GitHub mostra 1 estrela e nenhum fork visível. **Não dá para saber quem clonou ou baixou**, então a análise **não presume** que ninguém obteve versões sob MIT.
* A MIT cobre "o software e os arquivos de documentação associados". Os documentos, imagens e capturas que estavam no repositório nessas versões podem estar cobertos por ela. **Ponto de revisão jurídica.**
* **Último commit publicado:** `a8302c2`. O commit local `33b8db2` (ERS v7.0), ainda **não publicado**, também contém o `LICENSE` MIT. Publicá-lo antes da mudança de licença publicaria mais uma versão sob MIT.
* **Autoria:** commits da autora; parte do código foi escrita com assistência de IA (commits com "Co-Authored-By: Claude"). Não há contribuições de outras pessoas.
* **Dependências do app** (conferidas nos metadados dos pacotes instalados): todas são de licenças **permissivas**, compatíveis com distribuição comercial e fechada, com **obrigação de avisos**:
  * flet, flet-desktop e flet-charts: Apache-2.0;
  * regex: Apache-2.0 e CNRI-Python;
  * httpx, httpcore, idna, oauthlib, pycparser: BSD-3-Clause;
  * cryptography: Apache-2.0 ou BSD-3-Clause;
  * anyio, h11, repath, rich, six, markdown-it-py, mdurl: MIT;
  * cffi: MIT-0;
  * pygments: BSD-2-Clause;
  * typing_extensions: PSF-2.0;
  * msgpack: Apache-2.0;
  * **certifi: MPL-2.0**, que exige compartilhar só os arquivos dela **se forem modificados**;
  * no app móvel entram também o Flutter (BSD-3-Clause, mais as dependências do motor) e o Python embarcado.

  No serviço de códigos: `@noble/curves` 2.4.0 e `@noble/hashes` 2.4.0, ambos MIT.

#### O que cada alternativa permite (linguagem simples)

| Alternativa | Uso pessoal | Estudo | Modificação | Compartilhar | Uso comercial por terceiros | Vender por terceiros |
|---|---|---|---|---|---|---|
| **MIT (atual)** | Sim | Sim | Sim | Sim, com o aviso | Sim | **Sim** |
| **PolyForm Noncommercial 1.0.0** | Sim, sem fim comercial | Sim | Sim, para fins não comerciais | Sim, cópias e versões modificadas, com o texto da licença e os "Required Notice" | **Não** (nenhum uso comercial) | **Não** |
| **PolyForm Strict 1.0.0** | Sim, sem fim comercial | Sim | **Não** | **Não** | Não | Não |
| **PolyForm Shield 1.0.0** | Sim | Sim | Sim | Sim | Sim, **exceto** um produto que concorra com o Sino ou com o que a autora oferece com ele | Só o que não concorre |
| **Proprietária ("todos os direitos reservados")** | Só o que a autora permitir por escrito (por exemplo, o contrato de uso da loja) | Ler o código, se o repositório for público; nada além disso sem permissão | Não | Não (no GitHub público, os Termos permitem ver e fazer fork **pela plataforma**) | Não | Não |

**PolyForm Noncommercial**, pelo texto oficial:

* permite "qualquer finalidade não comercial";
* inclui uso pessoal para pesquisa, estudo, entretenimento privado e projetos de hobby "sem aplicação comercial prevista";
* inclui uso por instituições de ensino, beneficentes, de pesquisa pública e órgãos de governo;
* permite **modificar e distribuir** (inclusive versões modificadas), sempre para fins não comerciais e com os avisos;
* tem prazo de **32 dias** para corrigir uma violação depois de notificada;
* **não fala de marcas**;
* não deixa transferir nem sublicenciar.

**Proibir a venda × proibir qualquer uso comercial:**

* **Proibir só a venda** (ou a redistribuição comercial) deixaria uma empresa ou um profissional **usar** o Sino no próprio negócio, mas não vendê-lo nem vender versões derivadas. **Nenhuma licença padronizada conferida faz exatamente isso**; seria preciso um texto próprio, redigido com advogado. A Shield chega perto por outro caminho: ela proíbe **concorrer**, não vender.
* **Proibir qualquer uso comercial** (PolyForm Noncommercial, Strict) também impede, por exemplo, que um autônomo use o Sino para controlar as contas do próprio negócio. Onde fica o limite entre uso pessoal e comercial (uso doméstico misturado com o de um MEI, por exemplo) é **ponto de revisão jurídica**.

**Nenhuma dessas alternativas, exceto a MIT, é "open source" no sentido da OSI.** O critério 6 da definição proíbe restringir o uso "em um negócio". O correto passa a ser "código-fonte disponível".

#### Lojas (Android e iOS)

* **A autora, como titular dos direitos, não fica presa à licença que oferece a terceiros.** Ela pode publicar o app nas lojas, cobrar por ele e oferecer outros termos (uma licença comercial) qualquer que seja a licença do repositório. **Revisão jurídica:** confirmar isso considerando o histórico MIT e a autoria assistida por IA.
* **Apple:**
  * sem contrato próprio, vale o **contrato padrão de uso (Standard EULA)** da Apple, que proíbe ao usuário redistribuir, modificar ou criar obras derivadas do app; o desenvolvedor pode usar um contrato próprio;
  * as diretrizes 4.1 (cópias) e 5.2.1 (propriedade intelectual) exigem que o app seja enviado por quem detém os direitos;
  * há formulário para denunciar infração.
* **Google Play:** proíbe apps que violem direito autoral ou marca; tem formulários de denúncia (direito autoral e marca).
* **O efeito prático:**
  * com **MIT**, um terceiro pode publicar legalmente um clone, inclusive pago, e as denúncias às lojas têm pouco fundamento;
  * com **PolyForm Noncommercial**, um clone **pago** viola a licença, mas um clone **gratuito** e não comercial pode ser permitido, e isso compete com uma versão paga da autora;
  * com **Strict** ou **proprietária**, qualquer redistribuição de terceiros viola a licença.
* **A marca (o nome "Sino" e o ícone) não é protegida por licença de código.** Contra clones com o mesmo nome, o caminho é o **registro de marca no INPI**. É um gasto, não autorizado agora, e a viabilidade de um nome comum como "Sino" é ponto de revisão jurídica.

#### Documentação e materiais

* A Creative Commons **recomenda não usar** licenças CC para software, mas aceita o uso em **documentação** e elementos artísticos.
* Opções para `docs/`, README, capturas, paleta e capa:
  * (a) "todos os direitos reservados", permitindo visualizar (como na proposta descartada de 04/10);
  * (b) CC BY-NC-ND 4.0: compartilhar com crédito, sem uso comercial e sem obras derivadas.
* Capturas e protótipos mostram elementos de terceiros (emojis, fontes, ícones), que seguem as próprias licenças.

#### Dependências e avisos de terceiros

* Qualquer licença escolhida vale **só para o que é da autora**. As bibliotecas mantêm as licenças delas.
* Na distribuição (inclusive nas lojas) é preciso **incluir os avisos**: textos das licenças Apache, BSD, MIT e MPL; o arquivo NOTICE da Apache-2.0, quando existir; e a licença do Flutter e das dependências do motor. O Flutter orienta exibir as licenças no app (página de licenças).
* **Proposta técnica:** gerar um arquivo de avisos de terceiros a partir das dependências instaladas e exibi-lo em Ajustes, numa entrega futura ligada ao empacotamento móvel.
* O empacotamento Android e iOS ainda **não foi validado** (`requirements.txt`).

#### Versões já publicadas sob MIT

* A mudança de licença vale **a partir de um commit identificado**. As versões anteriores continuam **visíveis** no histórico público e **foram oferecidas sob MIT**. O planejamento parte da premissa de que **quem as obteve mantém as permissões da MIT sobre elas**: a MIT não diz que pode ser revogada, e não se presume que ninguém as obteve. **A confirmação é ponto de revisão jurídica.**
* Tornar o repositório privado **não revoga** essas permissões. Apenas evita oferecer versões novas.
* O registro histórico é preservado: o `LICENSE` MIT continua no histórico, e um aviso indica até qual commit valia a MIT.

#### Pontos para a revisão jurídica

1. Se as permissões MIT já concedidas sobre versões publicadas (até `a8302c2`, ou além, se algo mais for publicado antes da troca) podem ser limitadas ou não; e se elas cobrem os documentos e imagens do repositório.
2. O limite entre uso pessoal e comercial na licença escolhida (uso doméstico misturado com pequenos negócios).
3. Titularidade e proteção do código escrito com assistência de IA. A Lei 9.610/98 considera autor a pessoa física criadora; avaliar o efeito na proteção e na licença.
4. Validade e exequibilidade, no Brasil, de uma licença em inglês (PolyForm) e a necessidade de tradução ou de foro.
5. Licença comercial ou contrato de uso próprio para as lojas, inclusive em relação ao contrato padrão da Apple, e compatibilidade com os Termos e a Política (M12).
6. Registro de marca ("Sino", ícone) e registro do programa no INPI. O registro do programa é **opcional**: a proteção independe de registro (Lei 9.609/98, art. 2º, § 3º), mas o registro ajuda a provar a autoria.
7. Cumprimento das licenças de terceiros no app móvel (avisos, NOTICE, MPL do certifi).

#### Recomendação do planejamento (não aprovada; substituída em 06/10/2026 pela decisão em blocos, abaixo)

Para o objetivo declarado (vender nas lojas e impedir a venda por terceiros), a MIT **não serve** para as versões futuras.

* Se o **portfólio público com código legível** for importante:
  * **PolyForm Strict** (uso não comercial, sem modificar nem redistribuir) é a opção padronizada **mais próxima** do objetivo;
  * a **PolyForm Noncommercial** é mais aberta (permite forks e redistribuição não comercial, inclusive apps gratuitos), mas deixa espaço para clones gratuitos.
* Se o portfólio público **não** for necessário: **licença proprietária** nas versões futuras, de preferência com **repositório privado**, mantendo público o histórico MIT, ou uma versão de portfólio congelada.
* **Documentos:** "todos os direitos reservados", permitindo visualizar.
* **Marco:** trocar a licença **antes** do próximo push, para que `33b8db2` e os documentos novos não saiam sob MIT.

#### Perguntas para a autora (agrupadas; substituídas pelos blocos abaixo)

* **L1 — O que restringir:**
  * (a) só a **venda e a redistribuição comercial** (texto próprio, com advogado);
  * (b) **qualquer uso comercial**, mas permitindo forks e redistribuição não comercial (PolyForm Noncommercial);
  * (c) qualquer uso comercial **e** qualquer redistribuição ou modificação (PolyForm Strict);
  * (d) **tudo reservado** (proprietária).
* **L2 — Repositório:** (a) continuar público, com o código legível sob a nova licença; (b) tornar privado nas versões futuras, mantendo público só o histórico até o marco ou uma versão de portfólio.
* **L3 — Documentos e imagens:** (a) todos os direitos reservados, com visualização; (b) CC BY-NC-ND 4.0.
* **L4 — Marco:** fazer a troca **antes** do próximo push (recomendado) ou aceitar que `33b8db2` saia sob MIT.
* **L5 — Revisão jurídica:** fazer antes da troca, ou trocar já pela licença mais restritiva escolhida e revisar depois? Uma licença mais restritiva pode ser aberta mais tarde sem prejuízo; o contrário não desfaz o que já foi concedido.
* **L6 — Registros no INPI** (marca e programa): só registrar como pendência futura, já que **não há gasto autorizado**.


### Decisão da licença em blocos (06/10/2026)

**Orientação da autora (06/10/2026, P33):**

* preservar a possibilidade de comercializar o Sino no futuro e impedir a comercialização por terceiros sem autorização;
* **nenhuma licença está escolhida**;
* **não se presume** que a autora queira proibir estudo, modificação ou uso pessoal;
* preservar o histórico das versões publicadas sob MIT.

A "Recomendação do planejamento" acima (PolyForm Strict ou proprietária) partia dessa presunção e fica **substituída** por esta sequência de blocos. A análise acima continua como ponto de partida.

Os blocos são decididos **um por vez**. A resposta de um bloco pode mudar as perguntas seguintes.

#### Bloco 1: impedir a venda × impedir qualquer uso comercial (decidido em 06/10/2026: 1A)

As duas opções **permitem** uso pessoal, estudo e modificação, e permitem compartilhar sem fins comerciais (inclusive versões modificadas). A diferença é o que fica proibido para terceiros.

| | **1A — Impedir venda e redistribuição comercial** | **1B — Impedir qualquer uso comercial** |
|---|---|---|
| Uso pessoal, estudo, modificação | Permitidos | Permitidos (fins não comerciais) |
| Compartilhar cópias, também modificadas, sem cobrar | Permitido | Permitido |
| **Usar** o Sino dentro de um negócio (por exemplo, um autônomo controlando as contas da empresa) | **Permitido** | **Proibido** sem autorização |
| Vender o Sino ou versões derivadas (inclusive nas lojas) | Proibido | Proibido |
| Oferecer um serviço pago baseado no Sino | Proibido, se o valor vier "inteira ou substancialmente" do Sino | Proibido |
| Texto disponível | **Commons Clause** acrescentada a uma licença permissiva (por exemplo, MIT ou Apache-2.0), ou um texto próprio redigido com advogado | **PolyForm Noncommercial 1.0.0**, texto padronizado e completo (cláusula de patentes, prazo de 32 dias para corrigir violações) |
| Pontos fracos | O critério "inteira ou substancialmente" é vago; a Commons Clause é um acréscimo curto a outra licença; um texto próprio custa uma redação jurídica | Bloqueia também o uso comercial interno; o limite entre uso pessoal e comercial (uso doméstico misturado com MEI) é zona cinzenta |
| "Open source" (OSI) | Não; o resultado é "código-fonte disponível" | Não; o resultado é "código-fonte disponível" |

**Em comum:**

* nas duas, um terceiro pode distribuir uma cópia **gratuita**, inclusive modificada, e isso pode chegar às lojas. Restringir isso é o bloco 2;
* nas duas, a autora continua livre para vender o próprio app e oferecer licenças comerciais;
* nenhuma das duas protege o nome "Sino" nem o ícone (isso é marca).

**Recomendação:** **1B (PolyForm Noncommercial)**. Ela atende ao objetivo com um texto padronizado, sem precisar definir o que é "vender", e bloqueia também apps pagos e serviços pagos baseados no Sino. O custo é proibir o uso comercial interno, que pesa pouco num app de finanças pessoais; o caso do MEI vai para a revisão jurídica. Escolha **1A** se for importante que empresas e profissionais possam **usar** o Sino livremente no trabalho.

#### Bloco 1 — decidido (autora, 06/10/2026): 1A

**Decisão:** **1A, impedir a venda e a comercialização por terceiros**, não qualquer uso comercial.

* **Uso livre:** qualquer pessoa pode instalar e usar o Sino para fins **pessoais, acadêmicos ou dentro de empresas**, sem autorização individual. O uso segue as condições da **distribuição oficial**, que pode ser gratuita ou paga.
* **Proibido sem autorização da autora:** terceiros **venderem, revenderem ou comercializarem** o aplicativo ou **versões derivadas**.
* **Preservado:** a possibilidade de a autora **cobrar pela distribuição oficial** (por exemplo, nas lojas).
* **Estudo do código:** permitido.
* **Modificação e redistribuição gratuita:** a decidir no bloco 2.
* **Nenhum texto de licença aprovado.** O `LICENSE` continua MIT até a aplicação (E1).

#### Proposta de texto (rascunho de 06/10/2026; não aprovado, não aplicado)

##### Candidata T1 — Commons Clause v1.0 + licença-base

Texto oficial, sem alteração, acrescentado a uma licença-base:

> "Commons Clause" License Condition v1.0
>
> The Software is provided to you by the Licensor under the License, as defined below, subject to the following condition.
>
> Without limiting other conditions in the License, the grant of rights under the License will not include, and the License does not grant to you, the right to Sell the Software.
>
> For purposes of the foregoing, "Sell" means practicing any or all of the rights granted to you under the License to provide to third parties, for a fee or other consideration (including without limitation fees for hosting or consulting/support services related to the Software), a product or service whose value derives, entirely or substantially, from the functionality of the Software. Any license notice or attribution required by the License must also include this Commons Clause License Condition notice.
>
> Software: Sino — License: [licença-base] — Licensor: Carinne Batista

**Como ela atende ao objetivo:**

* **Uso** (pessoal, acadêmico, em empresas), estudo e o que a licença-base permitir continuam livres.
* Vender ou cobrar por um produto ou serviço cujo valor venha "inteira ou substancialmente" do Sino fica proibido, inclusive versões derivadas e apps pagos nas lojas.
* A autora não fica limitada (ela é a titular).
* Pelas perguntas frequentes do site oficial, a condição vale "daqui para a frente", o que é coerente com preservar o histórico MIT.

**Onde T1 proíbe mais do que a autora pretende:**

| Atividade de terceiros | Intenção da autora | T1 |
|---|---|---|
| Vender ou revender o app ou versão derivada (inclusive nas lojas) | Proibir | Proíbe |
| Cobrar assinatura para acesso ao Sino hospedado por terceiros | Proibir (é comercializar o app) | Proíbe ("hosting") |
| App "gratuito" de terceiros com anúncios ou compras internas | Proibir (é comercializar) | Provavelmente proíbe ("other consideration"); **ambíguo** |
| **Suporte, consultoria ou instalação pagos**, sem cobrar pelo app | Não declarado | **Proíbe** se o valor vier "substancialmente" do Sino ("consulting/support services related to the Software"). As perguntas frequentes dizem o contrário ("You may even provide consulting services"): **contradição a resolver na revisão jurídica** |
| Curso ou aula paga que ensina a usar ou programar com o Sino | Não declarado | **Ambíguo** |
| Empresa usando o Sino internamente | Permitir | Permite (não é fornecer a terceiros) |
| Produto pago maior que inclui o Sino como parte pequena | Não declarado | Permite, se o valor não vier "substancialmente" do Sino; **critério vago** |

**Outros pontos de T1:**

* A **licença-base** define o que é permitido além do uso. Com MIT ou Apache-2.0, **modificar e redistribuir de graça ficam permitidos**, o que depende do bloco 2. Se o bloco 2 restringir isso, T1 deixa de servir sem uma licença-base diferente.
* MIT + Commons Clause é uma combinação estranha: o texto da MIT diz "sem restrição... vender", e a cláusula retira esse direito. A cláusula diz expressamente que prevalece, mas a leitura conjunta é ponto de revisão jurídica.
* Apache-2.0 traz cláusula de patentes e arquivo NOTICE; a MIT é mais simples e é a licença histórica do projeto.
* O nome "Commons Clause" só pode ser usado com o texto **sem alteração**.

##### Candidata T2 — texto próprio, com a estrutura da Commons Clause e o alcance da intenção

Um texto próprio (sem usar o nome "Commons Clause"), redigido ou revisado por advogado, que:

* **proíba**, sem autorização escrita da autora:
  * vender, revender, alugar ou cobrar por cópias, downloads, pacotes de instalação ou **acesso** ao Sino ou a versões derivadas, inclusive em lojas de aplicativos e marketplaces;
  * oferecer o Sino ou versões derivadas como serviço hospedado pago ou por assinatura;
  * monetizar o Sino ou versões derivadas distribuídas por terceiros (anúncios, compras internas, assinaturas);
* **permita expressamente:**
  * uso pessoal, acadêmico e dentro de empresas;
  * estudo;
* **serviços pagos que não cobram pelo aplicativo** (suporte, consultoria, instalação, treinamento, aulas): **pendente**. A autora não aprovou permitir nem proibir (06/10/2026);
* defina modificação e redistribuição gratuita conforme o bloco 2;
* preserve o histórico MIT (o texto vale a partir do marco; bloco 5).

**Recomendação do planejamento:** **T2**, porque pode seguir exatamente a intenção declarada. T1 fica como alternativa padronizada, se a autora aceitar que ela possa alcançar suporte, consultoria e hospedagem pagos. Em qualquer caso, o texto final passa pela revisão jurídica (bloco 6). **A autora (06/10/2026) não aprovou T1 nem T2.** O tratamento de serviços pagos que não cobram pelo app (suporte, instalação, consultoria, aulas) continua **pendente**.

**Pontos de revisão jurídica acrescentados:**

* contradição entre o texto da Commons Clause e as perguntas frequentes dela sobre consultoria;
* critério "inteira ou substancialmente";
* leitura conjunta com a licença-base;
* redação de T2 em português e/ou inglês;
* relação com o contrato de uso da distribuição oficial (lojas).

#### Bloco 2 — perguntas (modificação e distribuição gratuita; decidido em 06/10/2026: caminho A, abaixo)

**Esclarecimento pedido pela autora (06/10/2026), antes de responder:**

* **Caminho A:** código público para estudo e modificação privada; redistribuição (cópias, versões modificadas, lojas) **só com autorização** da autora.
* **Caminho B:** além disso, cópias e versões modificadas **gratuitas** permitidas, mantendo a proibição de comercialização.
* **Compilar e usar sem a distribuição oficial:**
  * se a licença permitir **usar** cópias compiladas pela própria pessoa, isso fica permitido **nos dois caminhos**. A diferença é que, em A, cada pessoa precisa compilar sozinha (barreira técnica); em B, qualquer pessoa pode repassar um pacote pronto e gratuito;
  * para exigir a distribuição oficial também para o uso, a licença teria de limitar as cópias compiladas a estudo e testes, ou o código teria de deixar de ser público. Isso afeta a P34, que prevê uso livre conforme a distribuição oficial; é ponto de redação e de revisão jurídica;
  * as versões já publicadas sob MIT (até `a8302c2`) podem ser compiladas, usadas, redistribuídas e até vendidas por quem as obteve, qualquer que seja a nova licença (premissa sujeita à revisão jurídica).
* As perguntas 2.1–2.5 abaixo continuam abertas.


* **2.1 — Modificar para uso próprio** (pessoal, acadêmico ou dentro de uma empresa), sem distribuir: permitir?
* **2.2 — Distribuir de graça cópias sem modificação** (por exemplo, repassar o código ou um pacote a outra pessoa, manter um espelho do repositório): permitir? Com quais condições (manter os avisos e a licença, indicar a fonte oficial)?
* **2.3 — Distribuir de graça versões modificadas** (forks públicos): permitir? Se sim, com quais condições? Por exemplo: indicar que é uma versão modificada; não usar o nome "Sino" nem o ícone; manter os avisos e a restrição de venda.
* **2.4 — Distribuição gratuita por terceiros em lojas de aplicativos** (sem cobrar, sem anúncios): permitir ou reservar as lojas à distribuição oficial? (Afeta uma futura distribuição oficial paga.)
* **2.5 — Compilar a partir do código e usar sem passar pela distribuição oficial** (por exemplo, se a versão oficial for paga): aceitar como consequência de manter o código disponível, ou restringir?

#### Bloco 2 — decidido (autora, 06/10/2026): caminho A *(substituído no mesmo dia pela decisão MIT + Commons Clause, abaixo; mantido como histórico)*

* **Permitido sem autorização individual:**
  * uso pessoal, acadêmico e interno em empresas;
  * estudo do código;
  * **compilação** e **modificação para uso próprio**.

  A autora **aceita** que alguém compile o Sino para si sem comprar a distribuição oficial.
* **Exige autorização prévia e por escrito da autora, mesmo sem cobrança:**
  * redistribuir cópias (código ou programa compilado);
  * distribuir versões modificadas;
  * publicar em lojas de aplicativos.
* **Comercialização por terceiros:** também exige autorização (P34).
* **Serviços pagos de suporte, instalação, consultoria e aulas:** continuam **pendentes**.
* **Código público:** o caminho A pressupõe o código-fonte **público** para estudo (bloco 4 resolvido nesse ponto).
* **Texto:** **licença própria**, separando as permissões do código das condições da distribuição oficial. T1 (Commons Clause) não atende ao caminho A sem uma licença-base restritiva. A proposta abaixo substitui T2 como base da redação.

#### Proposta de licença própria (rascunho para revisão jurídica, 06/10/2026) — *descartada como proposta vigente; só histórico*

**Situação:** rascunho de planejamento, **não aprovado e não aplicado**. Não é texto jurídico definitivo. Os trechos marcados **[PENDENTE]** dependem de decisões da autora; os marcados **[REVISÃO]**, da revisão jurídica.

**Estrutura proposta:**

* **Documento 1, "Licença do Código-Fonte do Sino"** (arquivo `LICENSE` na raiz, quando aprovado): o que qualquer pessoa pode fazer com o **código**.
* **Documento 2, "Condições da Distribuição Oficial"** (fora do `LICENSE`; ligado aos Termos de Uso, M12, e às lojas, M14): como a **autora** distribui o Sino compilado (gratuito ou pago), atualizações e suporte da distribuição oficial.

O código não dá direito à distribuição oficial, e a distribuição oficial não amplia a licença do código.

##### Documento 1 — Licença do Código-Fonte do Sino (rascunho)

> **Licença do Código-Fonte do Sino — versão de [data]**
>
> Copyright (c) 2026 Carinne Batista. Todos os direitos não concedidos expressamente nesta licença são reservados.
>
> **1. Objeto.** Esta licença vale para o código-fonte, os testes e as ferramentas do Sino publicados no repositório oficial (https://github.com/carinne-batista11/sino) a partir do commit [marco] ("o Software"). Documentos, imagens e demais materiais seguem [PENDENTE: bloco 3]. Componentes de terceiros seguem as suas próprias licenças.
>
> **2. O que você pode fazer sem pedir autorização.** Desde que cumpra esta licença, você pode, sem custo:
> (a) usar o Software para fins pessoais, acadêmicos ou internos de uma empresa ou organização;
> (b) ler e estudar o código-fonte;
> (c) compilar o Software e usar a cópia compilada nas finalidades do item (a);
> (d) modificar o Software para uso próprio, nas finalidades do item (a). [PENDENTE: se "uso próprio" inclui o uso interno da versão modificada por pessoas da mesma empresa ou organização.]
>
> **3. O que exige autorização prévia e por escrito da autora**, mesmo que sem cobrança:
> (a) redistribuir cópias do Software, em código-fonte ou compilado, a qualquer outra pessoa ou organização;
> (b) distribuir, publicar ou disponibilizar versões modificadas ou obras derivadas do Software;
> (c) publicar o Software ou versões derivadas em lojas de aplicativos ou plataformas de distribuição;
> (d) disponibilizar o Software ou versões derivadas para uso de terceiros por rede (por exemplo, hospedado) [PENDENTE: confirmar];
> (e) vender, revender, alugar, sublicenciar ou de qualquer forma comercializar o Software, versões derivadas ou o acesso a eles, inclusive por anúncios, compras internas ou assinaturas.
>
> **4. Serviços relacionados.** [PENDENTE: tratamento de serviços pagos de suporte, instalação, consultoria e aulas que não cobram pelo Software.]
>
> **5. Plataforma do repositório.** Nada nesta licença limita o que os Termos de Serviço do GitHub permitem em repositórios públicos, como visualizar e criar forks pela plataforma. Isso não concede nenhum direito além do previsto nesta licença. [PENDENTE: forks públicos com modificações, usados para propor contribuições.] [REVISÃO]
>
> **6. Avisos.** Cópias e versões modificadas mantidas para uso próprio devem conservar este aviso de copyright e esta licença.
>
> **7. Marcas.** Esta licença não concede direito de usar o nome "Sino", o ícone ou outros sinais distintivos da autora.
>
> **8. Contribuições.** [PENDENTE: se contribuições de terceiros serão aceitas e em que termos, para preservar a possibilidade de comercialização pela autora.] [REVISÃO]
>
> **9. Versões anteriores.** As versões do Sino publicadas até o commit [marco anterior], inclusive, foram oferecidas sob a licença MIT. Esta licença não altera as permissões de quem obteve essas versões sobre elas. [REVISÃO]
>
> **10. Encerramento.** Se você descumprir esta licença, os direitos concedidos a você terminam [PENDENTE: imediatamente ou após um prazo para correção depois de notificado, por exemplo 30 dias]. [REVISÃO]
>
> **11. Sem garantia e limitação de responsabilidade.** O Software é fornecido "no estado em que se encontra", sem garantias de qualquer tipo, na máxima extensão permitida pela lei. A autora não responde por danos decorrentes do uso do Software, na máxima extensão permitida pela lei. [REVISÃO: compatibilidade com o Código de Defesa do Consumidor e com os Termos de Uso.]
>
> **12. Lei aplicável e foro.** [PENDENTE / REVISÃO]
>
> **13. Pedidos de autorização.** Pelo canal [PENDENTE: por exemplo, uma *issue* no repositório ou um e-mail]. Um pedido não concede nenhuma permissão: a autorização só existe quando dada por escrito pela autora.

##### Documento 2 — Condições da Distribuição Oficial (esboço de conteúdo)

* **Quem distribui:** só a autora (ou quem ela autorizar por escrito) distribui o Sino compilado: pacotes oficiais e, se houver, lojas.
* **Preço:** a distribuição oficial pode ser gratuita ou paga, por plataforma e por versão. O pagamento corresponde à distribuição oficial (pacote pronto, atualizações e, se houver, suporte). Não muda o que a licença do código permite.
* **Uso:** quem obtém a distribuição oficial pode usá-la para fins pessoais, acadêmicos ou internos de empresas, conforme os Termos de Uso e, nas lojas, o contrato de uso da loja (por exemplo, o contrato padrão da Apple ou um contrato próprio).
* **Redistribuição:** os pacotes oficiais não podem ser redistribuídos sem autorização (mesma regra do item 3 da licença do código).
* **Atualizações e suporte:** a definir na M14 (E13).
* **Onde fica:** proposta técnica: integrar aos Termos de Uso (M12) e, se houver lojas, a um contrato de uso próprio ou ao padrão da loja. A decisão fica na M14.

#### Decisão final da licença (autora, 06/10/2026): MIT + Commons Clause (P36)

* **Escolha:** MIT + "Commons Clause" License Condition v1.0, para usar um **texto pronto**. Os textos oficiais são usados **sem alterar** as cláusulas; só os campos são preenchidos (Software: Sino; License: MIT License; Licensor: Carinne Batista).
* **Substitui** o caminho A (P35) e a licença própria, que ficam só como histórico acima.
* **Aceito pela autora:**
  * as permissões de modificação e redistribuição gratuita da MIT, sujeitas à Commons Clause;
  * o alcance da restrição sobre produtos e serviços pagos cujo valor derive inteira ou substancialmente da funcionalidade do Sino. Hospedagem, consultoria e suporte relacionados entram **só quando** se enquadram nessa condição; não se afirma que toda cobrança por esses serviços seja proibida.

  Com isso, a pendência sobre serviços pagos é resolvida pelo próprio texto, e a contradição com as perguntas frequentes vai para a revisão jurídica.
* **Apresentação:** sempre "MIT + Commons Clause" e "código-fonte disponível"; **nunca** só "MIT", nem "open source".
* **Alcance (bloco 3 resolvido):** código, testes, ferramentas e documentação associada da autora, inclusive documentos e imagens. Componentes de terceiros com as próprias licenças, inclusive os que aparecem em capturas e protótipos.
* **Marco (bloco 5), opção B (06/10/2026):** o commit local `33b8db2` (nunca publicado) é **refeito**, reunindo o planejamento atualizado e a mudança de licença num só commit, logo depois de `a8302c2`. **`a8302c2` é o último commit do histórico MIT publicado**; as versões até ele, inclusive, ficam registradas como distribuídas somente sob MIT. Uma referência local ao `33b8db2` original fica guardada para recuperação. Nenhum commit publicado é reescrito.
* **Arquivos preparados (06/10/2026, sem commit):**
  * `LICENSE`: Commons Clause, MIT e aviso de alcance e histórico, fora dos textos oficiais;
  * `README.md`: selo e seção "Licença";
  * `servidor/package.json` e `servidor/package-lock.json`: `"license": "SEE LICENSE IN ../LICENSE"`;
  * `servidor/README.md`: seção "Licença";
  * `docs/notas-da-versao.md`: seção da mudança de licença.

  Código de funcionamento, banco e Termos do aplicativo **não** foram alterados.
* **Pendentes:** revisão jurídica (bloco 6); registros no INPI (bloco 7, sem gasto autorizado).

#### Blocos seguintes

* **Bloco 2 — Modificação e distribuição gratuita:** **decidido** (caminho A).
* **Bloco 3 — Documentos e imagens:** todos os direitos reservados, com visualização permitida; ou CC BY-NC-ND 4.0; ou a mesma licença do código.
* **Bloco 4 — Repositório:** ~~continuar público ou tornar privado~~ **público**, pressuposto do caminho A (06/10/2026).
* **Bloco 5 — Marco e histórico MIT:** a troca vale a partir de qual commit; aviso de que as versões até ele foram publicadas sob MIT (sem presumir que ninguém as obteve); trocar **antes do próximo push**, para que `33b8db2` não saia sob MIT.
* **Bloco 6 — Revisão jurídica:** antes da troca, ou trocar já e revisar depois. Uma licença mais restritiva pode ser aberta mais tarde; o contrário não desfaz o que já foi concedido.
* **Bloco 7 — Registros no INPI** (marca e programa): pendência futura; **sem gasto autorizado**.

---

## M10 — Comprovantes em imagem

### Proposta (autora, 04/10/2026)

Permitir anexar, opcionalmente, imagens de comprovantes às contas e acessá-las por um botão em Detalhes, sem exibição permanente.

### Situação atual (v6.0)

* O Sino guarda apenas dados digitados, no banco SQLite local (`database/sino.db`); não há arquivos anexados.
* Excluir uma conta apaga só registros do banco. Excluir a conta de usuário (RF43) apaga contas, séries e categorias numa transação, com `secure_delete` como medida adicional; os backups existentes não são alcançados.
* Os backups automáticos copiam só o arquivo do banco, antes de migrações.
* A Política (item 2) lista o que o Sino guarda; comprovantes não estão lá. Comprovantes podem conter dados pessoais sensíveis (nome, CPF, dados bancários, endereço) e metadados da foto (como localização GPS).
* O Flet 0.86 oferece seletor de arquivos no computador (`FilePicker`).

### Decisões técnicas do planejamento

* **Armazenamento:** cada imagem é **copiada** para uma pasta própria do app, ao lado do banco (`database/comprovantes/`), com nome aleatório (nunca o nome original do arquivo nem dados da conta no nome). O banco ganha uma tabela de comprovantes (conta, nome de arquivo interno, tipo, tamanho, resumo de integridade, data). **Isso exige migração (v9), com backup antes, como as anteriores:** é a mudança persistente que a justifica. Não se guarda a imagem dentro do banco (faria o banco e os backups crescerem muito).
* **Pasta fora do Git:** `database/comprovantes/` entra no `.gitignore`, como o banco e os backups.
* **Vínculo:** o comprovante pertence a **uma ocorrência** (a conta daquele mês), não à série nem ao modelo: não é copiado para outras ocorrências e não participa do diálogo de escopo das séries.
* **Arquivo original:** o arquivo escolhido não é alterado nem apagado; o Sino trabalha com a cópia.
* **Conferência do arquivo:** o tipo é verificado pelo conteúdo do arquivo (não só pela extensão); arquivos inválidos são recusados com mensagem amigável.
* **Exclusão em cascata:** ao excluir a ocorrência, a série (no escopo escolhido) ou a conta de usuário, os comprovantes ligados também são apagados (registro e arquivo). Os avisos de exclusão passam a citar os comprovantes; o resumo de "Excluir conta" (RF43) inclui a quantidade. Uma falha ao apagar um arquivo é registrada e tentada de novo na próxima abertura; o registro no banco não fica apontando para arquivo inexistente.
* **Limite técnico de apagamento:** apagar um arquivo do disco não garante que ele seja irrecuperável (principalmente em SSD); isso vai para a Política, como já acontece com o banco.
* **Backups:** os backups automáticos continuam copiando só o banco; os comprovantes não entram neles. Registrar na Política e nas notas.
* **Interface:** em Detalhes, um botão abre o comprovante sob demanda (sem miniatura permanente na tela); o botão tem nome acessível e funciona pelo teclado. Telas e diálogos novos entram nas verificações de legibilidade dos dois temas.
* **Documentos:** Termos e Política precisam ser atualizados antes da implementação ser liberada (o que o Sino guarda, onde, exclusão e backups) e entram na revisão jurídica (M12). ERS v7.0: requisito novo, modelo de dados, migração v9 e casos de teste.

### Perguntas apresentadas à autora (agrupadas)

* **M10-A — Tipos de arquivo:** (a) só **JPEG e PNG**; (b) JPEG, PNG e WebP; (c) também **PDF** (muitos comprovantes de banco vêm em PDF, mas a proposta fala em imagens). *Proposto: (a) nesta versão; PDF como proposta futura.*
* **M10-B — Limites:** tamanho máximo por arquivo e quantidade por conta. *Proposto: até **5 MB** por imagem e até **3 comprovantes** por conta.*
* **M10-C — Em quais contas:** (a) em **qualquer** conta (paga, pendente ou atrasada); (b) só em contas pagas. *Proposto: (a); um boleto ou uma nota também podem ser úteis antes do pagamento.*
* **M10-D — Onde se anexa e se gerencia:** (a) em **Editar conta** (anexar, trocar e remover), com "Ver comprovante" em Detalhes; (b) também direto em Detalhes. *Proposto: (a); Detalhes só mostra.*
* **M10-E — Visualização:** (a) um **diálogo** no próprio Sino com a imagem ajustada à janela e "Fechar"; (b) além disso, um botão "Abrir no visualizador do computador". *Proposto: (a); (b) cria uma cópia temporária fora do controle do app.*
* **M10-F — Metadados da foto:** (a) guardar a imagem **como veio**; (b) **remover metadados** (por exemplo, localização GPS) ao anexar, regravando a imagem, o que exige uma biblioteca nova de imagens (Pillow). *Proposto: (b), por privacidade; aceita a nova dependência.*

### Decisões da autora (04/10/2026)

* **M10-A (a):** só **JPEG e PNG** nesta versão; PDF fica como proposta futura.
* **M10-B:** até **5 MB** por imagem e até **3 comprovantes** por conta.
* **M10-C (a):** em **qualquer** conta (paga, pendente ou atrasada).
* **M10-D (a):** anexar, trocar e remover em **Editar conta**; **"Ver comprovante"** em Detalhes, só para visualizar.
* **M10-E (a):** visualização num **diálogo** do Sino, com a imagem ajustada à janela e "Fechar"; sem abrir no visualizador do computador.
* **M10-F (b):** **remover metadados** (como localização GPS) **só da cópia armazenada**, mantendo a orientação correta e a legibilidade; o arquivo original do usuário nunca é alterado. Aceita a nova dependência de imagens (Pillow).

### Detalhamento pedido pela autora (04/10/2026)

#### 1. Backup e restauração

**Problema:** os backups atuais (`database/backups/sino_pre_migracao_vN_….db`) copiam **só o banco**. Com comprovantes, uma cópia só do banco teria registros apontando para imagens que não estão no backup.

**Proposta:**

* Um **pacote de backup** novo, num arquivo único (`sino_backup_<motivo>_<data>.zip` em `database/backups/`), com:
  * uma cópia consistente do banco (pela API de backup do SQLite, como hoje);
  * as imagens referenciadas pelo banco **naquele momento** (arquivos sem referência não entram);
  * um **manifesto** (versão do schema, data, lista de arquivos com tamanho e resumo SHA-256, e a lista de comprovantes que estavam faltando, se houver).
* **Quando é criado:** ~~antes de cada migração a partir da v9 e por uma ação em Ajustes~~ — **substituído pelas decisões M10-K e M10-L**: o pacote completo só é criado pela **ferramenta de manutenção** (fora das telas), criptografado; os backups antes de migrações continuam só do banco (ver "Backups antes de migrações", abaixo).
* **Backups existentes não mudam:** os arquivos `sino_pre_migracao_*.db` já gravados ficam como estão; nada é convertido, movido ou apagado. A migração v8→v9 em si continua gerando a cópia só do banco, porque antes dela ainda não existem comprovantes.
* **Restauração:** procedimento documentado e uma conferência do pacote (o manifesto confere cada arquivo pelo resumo) antes de qualquer restauração; a restauração nunca sobrescreve o banco atual sem antes guardar um pacote do estado atual.
* **Política e notas:** explicar o que entra no pacote e que ele contém imagens com dados pessoais.

#### 2. Consistência diante de falhas

O banco e os arquivos são independentes: **não há atomicidade entre o SQLite e o disco**, e o planejamento não promete isso. A regra é a ordem das operações e a recuperação depois de falhas:

* **Regra de ouro:** o banco **nunca** passa a apontar para um arquivo que ainda não está completo no disco; um arquivo só é apagado **depois** que nenhum registro aponta para ele.
* **Anexar:**
  1. conferir e processar a imagem (seção 3) gravando num arquivo temporário da própria pasta de comprovantes;
  2. gravar no disco por completo e renomear para o nome final aleatório;
  3. só então inserir o registro no banco, numa transação;
  4. se a inserção falhar, apagar o arquivo (melhor esforço); se nem isso der, ele vira "arquivo sem referência" e é tratado pela conferência abaixo.
* **Substituir:** anexar o novo (como acima); numa transação, trocar a referência; só depois apagar o arquivo antigo. Se algo falhar no meio, ou a referência antiga continua válida, ou sobra um arquivo sem referência; nunca uma referência quebrada.
* **Remover e excluir (conta, série ou usuário):** na transação que apaga os registros, os nomes dos arquivos entram numa lista de **remoções pendentes** no banco; depois do sucesso da transação, os arquivos são apagados e saem da lista. Se a remoção do arquivo falhar, ela é tentada de novo na próxima abertura do app.
* **Conferência na abertura do app:**
  * remoções pendentes são refeitas;
  * arquivos da pasta de comprovantes **sem nenhum registro** e com mais de 1 hora (para não pegar uma anexação em andamento) são removidos (ver pergunta M10-I);
  * registros cujo arquivo sumiu (por exemplo, apagado fora do app) **não quebram a tela**: "Ver comprovante" mostra "Comprovante indisponível" e permite remover o registro.
* Os registros técnicos dessas operações contam ocorrências, sem nomes de contas nem conteúdo.

#### 3. Segurança das imagens

* **Antes de abrir:** recusar arquivos acima de **5 MB** (pelo tamanho no disco), sem ler o conteúdo.
* **Tipo pelo conteúdo:** só JPEG e PNG reconhecidos pela assinatura do arquivo e pela biblioteca de imagens; a extensão não basta.
* **Limite de dimensões:** até **10.000 px** no maior lado e até **40 megapixels** no total (bem acima de qualquer foto de celular comum, e abaixo do ponto em que imagens pequenas no disco se expandem a centenas de megabytes na memória). Acima disso, a imagem é recusada **antes** de ser decodificada por completo.
* **Animação e várias páginas:** PNG animado e imagens com mais de um quadro são recusados (ver pergunta M10-H).
* **Processamento da cópia:** aplicar a orientação indicada pela câmera, converter para o espaço de cores padrão (sRGB) para manter a aparência e regravar **sem metadados**: JPEG continua JPEG (alta qualidade) e PNG continua PNG.
* **Imagens inválidas:** arquivo corrompido, truncado, de outro tipo, grande demais ou com dimensões acima do limite é recusado com mensagem amigável ("Não foi possível usar esta imagem. Use um arquivo JPEG ou PNG de até 5 MB."); **nada é gravado**.
* O processamento roda fora da linha da interface, para a tela não travar; a biblioteca de imagens fica com versão fixada no `requirements.txt` e entra na revisão de dependências.

#### 4. Vínculo com as séries

* Cada comprovante pertence a **uma ocorrência**. Operações em séries **nunca copiam** comprovantes para outras ocorrências: "Somente este mês", "Este mês em diante", alteração do modelo da série, geração sob demanda, alterar frequência e "Transformar em recorrente" (a conta original vira a primeira ocorrência e **mantém** os seus comprovantes).
* Mudar a data de vencimento de uma ocorrência mantém os comprovantes nela.
* **Exclusão em série:** "Somente esta" apaga a ocorrência e os seus comprovantes; "Este mês em diante" apaga todas as ocorrências do trecho **e os seus comprovantes**, como hoje (sem exceção para pagas). O aviso de exclusão passa a informar quantos comprovantes serão apagados.
* **Encerrar recorrência e alterar frequência:** hoje preservam ocorrências com informação histórica (paga, com data de pagamento ou editada individualmente). Ver pergunta M10-J sobre ocorrências com comprovante.

### Perguntas do detalhamento apresentadas (agrupadas)

* **M10-G — Pacote de backup manual** *(proposta de colocar em Ajustes substituída pela M10-K)*: oferecer em Ajustes uma ação **"Criar cópia de segurança"** que gera o pacote (banco + imagens + manifesto)? *Proposto: sim; e a restauração continua manual e documentada nesta versão, sem tela de restaurar.*
* **M10-H — Limites técnicos:** confirmar **10.000 px** no maior lado, **40 megapixels** e recusa de imagens animadas ou com vários quadros. *Proposto: confirmar.*
* **M10-I — Arquivos sem referência:** (a) **apagar** automaticamente os arquivos sem registro há mais de 1 hora, só dentro da pasta de comprovantes do app; (b) mover para uma pasta de "quarentena" e apagar depois de 30 dias. *Proposto: (a); são cópias feitas pelo próprio app, nunca o original do usuário.*
* **M10-J — Comprovante protege a ocorrência?** Ao encerrar a recorrência ou alterar a frequência, uma ocorrência futura **com comprovante** deve ser **preservada** (como as pagas ou editadas)? *Proposto: sim; anexar um comprovante é informação que o usuário registrou de propósito.*

### Decisões do detalhamento (autora, 04/10/2026)

* **M10-G:** sim, **backup manual completo** (banco, imagens e manifesto), com **restauração documentada**. A ação é de **manutenção da instalação**, não um "baixar meus dados" disponível a qualquer usuário logado: o pacote contém os dados e as imagens de **todos** os usuários da instalação. Alcance e controle de acesso: ver decisão M10-K.
* **M10-H:** confirmados **10.000 px** no maior lado, **40 megapixels** e a recusa de imagens animadas ou com vários quadros. Verificar também o **tamanho da cópia final** depois do processamento.
* **M10-I (b):** **quarentena por 30 dias**, só para arquivos gerenciados pelo app. Nunca mover arquivos **referenciados**, **em processamento** ou que pertençam a **backups**.
* **M10-J:** sim. Ao encerrar a recorrência ou alterar a frequência, ocorrências **com comprovante** são **preservadas** (como as pagas ou editadas): deixam de gerar novas repetições quando aplicável, mas mantêm dados e anexos. A **exclusão explícita** continua possível, com confirmação.

### Critérios técnicos acrescentados (04/10/2026)

**Backup do mesmo estado**

* Durante a criação do pacote, as operações de anexos (anexar, substituir, remover, remoções pendentes e quarentena) **aguardam** um bloqueio de manutenção; o banco é copiado pela API de backup do SQLite e as imagens referenciadas nessa cópia são copiadas **enquanto o bloqueio está ativo**. Assim banco e arquivos do pacote correspondem ao mesmo estado.
* O manifesto registra o resumo SHA-256 de cada arquivo copiado; o pacote é conferido depois de gravado. Arquivos em quarentena e temporários não entram.
* O pacote é gravado com acesso restrito ao usuário do computador (como os arquivos da demonstração) e nunca sobrescreve um pacote existente.

**Restauração segura**

* Antes de extrair: conferir o manifesto; recusar entradas com caminho absoluto, com `..`, com letra de unidade, links simbólicos ou qualquer caminho que, resolvido, saia da pasta de destino; recusar nomes duplicados.
* Limites contra pacotes maliciosos: tamanho total extraído e quantidade de arquivos limitados pelo manifesto e por um teto fixo; cada arquivo conferido pelo resumo SHA-256 depois de extraído.
* A extração vai para uma pasta temporária; só depois de tudo conferido o estado atual é guardado num pacote e substituído. Qualquer falha deixa o estado atual intacto.

**Cópia final da imagem**

* Depois do processamento (orientação, sRGB, sem metadados), a cópia guardada também precisa ter **até 5 MB**. Se uma regravação em PNG passar disso, a imagem é recusada com a mesma mensagem amigável; nada é gravado. JPEG é regravado em alta qualidade, sem reduzir dimensões.

**Quarentena**

* Fica numa subpasta própria de `database/comprovantes/`, com a data de entrada de cada arquivo; arquivos com mais de 30 dias na quarentena são apagados na abertura do app.
* Só entra na quarentena um arquivo que esteja na pasta de comprovantes, tenha nome no formato gerado pelo app, **não** tenha registro no banco, **não** esteja na lista de remoções pendentes nem em processamento (temporários) e tenha mais de 1 hora. A pasta de backups nunca é varrida.

**Preservação por comprovante (M10-J)**

* Na prática, uma ocorrência com comprovante passa a contar como "com informação histórica", ao lado de "paga", "com data de pagamento" e "editada individualmente", nas regras de encerrar recorrência (5.8) e alterar frequência (5.5). "Excluir este mês em diante" continua sem exceção, com aviso que informa quantos comprovantes serão apagados.

### Decisões finais da M10 (autora, 04/10/2026)

* **M10-K (a):** backup e restauração por uma **ferramenta externa de manutenção** (comando no terminal), **sem** nenhuma opção nas telas dos usuários. Para simplificar a consistência, a ferramenta **exige o Sino fechado** e impede a abertura simultânea por um **bloqueio compartilhado** entre o app e a ferramenta. A proteção também depende das permissões do sistema operacional sobre a pasta da instalação.
* **M10-L (b):** pacote **criptografado com senha** definida na criação. A senha **não é guardada** nem aparece em comandos ou logs; é pedida de forma interativa, **com confirmação**, e com aviso de que **perdê-la impede a restauração**. Formato **versionado** e **criptografia autenticada**; **não** se usa só a proteção por senha tradicional do ZIP.

### Critérios técnicos das decisões finais (planejamento)

**Bloqueio entre app e ferramenta**

* Um arquivo de bloqueio na pasta do banco, com trava do sistema operacional (liberada automaticamente se o processo terminar, sem bloqueios "esquecidos"): o app abre em modo compartilhado; a ferramenta exige modo exclusivo.
* Com a ferramenta em execução, o app não abre e mostra uma mensagem de manutenção; com o app aberto, a ferramenta recusa e explica que é preciso fechá-lo.
* Diferenças de trava entre Linux e Windows ficam registradas e testadas na implementação.

**Formato do pacote**

* Cabeçalho próprio com identificador do formato e **versão** do formato; parâmetros de derivação da chave e sal aleatório no cabeçalho.
* Chave derivada da senha por uma função de derivação resistente a força bruta (scrypt, disponível na biblioteca de criptografia que o app já usa), com parâmetros registrados no cabeçalho.
* Conteúdo (banco, imagens e manifesto) cifrado com **AES-256-GCM em blocos**, cada bloco autenticado com o cabeçalho e a sua posição, e marca de bloco final, para detectar alteração, troca de ordem ou corte do arquivo.
* Senha: tamanho mínimo de 12 caracteres, recomendação de frase-senha; pedida sem eco no terminal; nunca recebida por argumento de comando nem por variável de ambiente.
* Restauração: senha errada ou pacote alterado são recusados **antes** de qualquer extração; vale também a restauração segura já definida (caminhos, limites, conferência por resumo, pasta temporária, estado atual guardado antes de substituir).

**Backups antes de migrações**

* Continuam **só do banco**, sem senha, como hoje: o app não pode pedir senha nessas horas, e uma migração altera apenas o banco, nunca os arquivos de imagem. O manifesto do pacote e a documentação deixam claro que o backup só do banco depende da pasta de comprovantes atual.
* A documentação de atualização recomenda criar um pacote completo pela ferramenta **antes** de instalar uma versão nova.

### Resumo da M10 (decidida em 04/10/2026; a implementar)

| | Regra |
|---|---|
| Tipos e limites | JPEG e PNG; até 5 MB (original e cópia final); até 10.000 px no maior lado e 40 megapixels; sem animação ou vários quadros; até 3 por conta |
| Onde | Em qualquer conta; anexar, trocar e remover em Editar conta; "Ver comprovante" em Detalhes, num diálogo |
| Privacidade | Cópia guardada sem metadados, com orientação correta e sRGB; original do usuário intacto |
| Armazenamento | Arquivos com nome aleatório em `database/comprovantes/` (fora do Git) e tabela no banco; **migração própria (v10, P31 de 06/10/2026; antes prevista na v9)** com backup do banco antes |
| Consistência | Banco nunca aponta para arquivo incompleto; arquivo só é apagado sem referências; remoções pendentes refeitas; quarentena de 30 dias para arquivos sem referência gerenciados pelo app; "Comprovante indisponível" se um arquivo sumir |
| Séries | Comprovante pertence à ocorrência; nunca é copiado; preserva a ocorrência ao encerrar ou alterar frequência; "Excluir este mês em diante" apaga com aviso |
| Backup | Pacote completo criptografado (versão própria, AES-256-GCM, scrypt) só pela ferramenta de manutenção, com o Sino fechado e bloqueio compartilhado; backups antes de migrações continuam só do banco |
| Documentos | Termos, Política e revisão jurídica (M12) antes de liberar; ERS v7.0 com requisito novo, modelo de dados, migração v9 e casos de teste |

### Esclarecimentos da autora sobre a M10 (04/10/2026)

* **O backup automático antes de migrações continua só do banco, e isso substitui a proposta anterior** de gerar o pacote completo antes das migrações. O pacote completo existe apenas pela ferramenta de manutenção.
* **Esse backup não garante a restauração completa das imagens.** Ele guarda o banco; as imagens ficam só na pasta de comprovantes.
* **As escolhas de criptografia e de formato do pacote são propostas técnicas**, sujeitas a revisão na implementação, e **não** um formato próprio já aprovado como seguro. Na implementação, comparar com formatos e ferramentas de criptografia já estabelecidos antes de criar um formato próprio, e submeter a escolha a revisão.

#### Compatibilidade e recuperação quando uma migração falha

* **Hoje:** cada migração faz um backup do banco e roda **numa única transação** (`BEGIN IMMEDIATE`, com `ROLLBACK` em qualquer falha); se falhar, o banco fica como estava e o app mostra uma tela de erro sem abrir. Essa regra continua.
* *(Plano de 04/10; com a P31 de 06/10/2026, a v9 cria só a tabela de aceites e a dos comprovantes passa para a v10. O raciocínio abaixo vale para a v10.)* **Migração v9 (cria a tabela de comprovantes e a de aceites):** antes dela ainda não existem comprovantes, então uma falha não afeta imagens; o banco volta ao estado v8 pela transação, e o backup só do banco é suficiente.
* **Migrações futuras (v10 em diante):** alteram apenas o banco; os arquivos de imagem não são tocados. Se uma falhar, a transação desfaz tudo e as imagens continuam exatamente como estavam, compatíveis com o banco anterior.
* **Restaurar mais tarde um backup só do banco** é diferente: imagens anexadas depois do backup ficam sem referência (vão para a quarentena) e imagens removidas depois dele aparecem como "Comprovante indisponível". Para reduzir essa perda: se um registro restaurado apontar para um arquivo que está na quarentena, o app o devolve à pasta de comprovantes. Ainda assim, **não há garantia**: só o pacote completo da ferramenta restaura banco e imagens do mesmo estado.
* A documentação de atualização recomenda criar um pacote completo pela ferramenta antes de instalar uma versão nova; a ERS v7.0 registra essa limitação.

---

## M11 — Nomes das contas em janelas muito estreitas

### Proposta (autora, 04/10/2026)

Corrigir a quebra dos nomes das contas em janelas muito estreitas.

### Situação atual (v6.0)

* Cada linha de conta (Tela Principal, Ver status e Contas em atraso) tem: nome e subtítulo numa coluna flexível; valor e status numa coluna fixa de 92 px; e, na Tela Principal, os botões de editar e de pagamento. A janela não tem largura mínima.
* No tamanho padrão do app (cerca de 430 px úteis) o layout está correto. Com cerca de 330 px úteis, sobra pouco para o nome e ele **quebra letra a letra** (observado em 04/10/2026, registrado na ERS v6.0, 13.6).

### Decisões técnicas do planejamento

* O nome nunca quebra no meio de uma palavra por falta de espaço: as linhas passam a reorganizar-se abaixo de uma largura a medir na implementação (ver pergunta M11-A).
* A regra vale para as três telas que usam a mesma linha de conta.
* Testes de layout em larguras estreita, padrão e larga, como os de Detalhes; conferência visual curta.
* Sem migração. Impacto: `backend/main.py` (linha de conta e, se escolhido, largura mínima da janela), testes da Tela Principal, ERS v7.0 (5.15 e casos de teste).

### Perguntas apresentadas à autora (agrupadas com a M12)

* **M11-A — Como resolver:** (a) em janela estreita, **empilhar** a linha: nome e subtítulo em cima, ocupando toda a largura; valor, status e botões numa segunda linha; (b) definir uma **largura mínima** para a janela (por exemplo, a do tamanho padrão), impedindo que ela fique estreita demais; (c) as duas coisas. *Proposto: (a); a janela continua podendo ser estreita, sem cortar nada.*
* **M11-B — Nomes longos:** nomes de até 30 caracteres sempre aparecem **inteiros**, quebrando por palavra quando necessário (sem reticências)? *Proposto: sim, inteiros.*

---

## M12 — Revisão jurídica, versionamento e novo aceite dos Termos e da Política

### Proposta (autora, 04/10/2026)

Planejar a revisão jurídica, o versionamento e o novo aceite dos Termos e da Política antes do uso por terceiros.

### Situação atual

* O Sino guarda só a **data** do aceite (`termos_aceitos_em`), feito no cadastro. Não registra qual versão do texto foi aceita e não pede novo aceite quando o texto muda (decisão P9 da v6.0, a rever antes do uso por terceiros).
* A autora aprovou o texto atual em 04/10/2026 para portfólio e demonstração local; a **revisão jurídica está pendente**.
* Pontos já anotados para a revisão jurídica (desde 30/09/2026): responsável pelos dados em cada instalação; legislação e direitos do titular (LGPD); garantias, responsabilidade, lei aplicável e foro; idade mínima.
* A v7.0 traz mudanças que afetam os textos: M8 (serviço publicado, provedores, prazos reais, restrição de destinatários, responsável e contato); M10 (comprovantes com possíveis dados pessoais, armazenamento, exclusão, quarentena, pacote de backup criptografado e backups só do banco).

### Decisões técnicas do planejamento

* **Versão dos documentos:** cada documento (Termos e Política) ganha um identificador de versão (a data da versão, por exemplo "2026-10-04"), exibido no próprio texto ("Versão de 04/10/2026").
* **Registro do aceite:** o banco passa a guardar, por usuário, **qual versão** de cada documento foi aceita e quando. Isso exige migração; ela pode ser a mesma **v9** da M10, com um único backup.
* **Usuários existentes:** a migração registra a versão conhecida na data do aceite já gravado quando for possível determiná-la; quando não for, fica como "versão anterior ao versionamento", o que leva ao novo aceite pela regra escolhida (M12-B).
* O aceite continua obrigatório no cadastro (RF15).
* Documentos: ERS v7.0 (5.37, P9 revista, RF15, modelo de dados, casos de teste), notas da versão.

### Perguntas apresentadas à autora (agrupadas com a M11)

* **M12-A — Quando a revisão jurídica acontece:** (a) **antes de abrir o serviço a terceiros** (M8-D), cobrindo os textos da v7.0 (serviço, comprovantes, backup); (b) antes de lançar a v7.0, mesmo em uso restrito. *Proposto: (a); o uso restrito aos seus endereços não envolve terceiros.*
* **M12-B — Novo aceite:** quando uma nova versão dos Termos ou da Política for publicada, o usuário (a) precisa **aceitar de novo no próximo login**, numa tela com o resumo das mudanças, "Aceitar" e "Sair" (sem aceite, não entra); (b) só recebe um **aviso** com o resumo, sem bloquear; (c) aceite novo só para mudanças **relevantes**, aviso para as demais. *Proposto: (c), com a decisão de "relevante" registrada nas notas da versão a cada mudança.*
* **M12-C — Histórico dos textos:** manter acessíveis as versões anteriores dos Termos e da Política (por exemplo, em `docs/`, com a data de cada uma)? *Proposto: sim, no repositório; no app, só a versão vigente.*
* **M12-D — Escopo da revisão jurídica:** incluir, além dos Termos e da Política, o contrato do serviço de códigos (dados enviados aos provedores) e a restrição de destinatários? A licença (M9) só entra se a autora pedir a reavaliação. *Proposto: sim.*

### Decisões da autora (04/10/2026)

**M11**

* **M11-A (a):** em janela estreita, a linha de conta se **empilha**: nome e subtítulo em cima, com toda a largura; valor, status e botões embaixo. Sem largura mínima de janela.
* **M11-B:** nomes **completos**, sem reticências, com **quebra entre palavras**. Uma palavra que não caiba na linha pode quebrar **entre caracteres percebidos**, sem nunca separar um emoji composto.

**M12**

* **M12-A (a):** revisão jurídica **antes de disponibilizar o Sino a terceiros**. O uso restrito aos endereços da autora **não** é registrado como isenção automática de obrigações legais; as obrigações aplicáveis também a esse uso são avaliadas na revisão jurídica.
* **M12-B (c):** **novo aceite** para mudanças **relevantes**; **aviso** para ajustes menores.
  * **Relevante:** muda os dados tratados, as finalidades, o compartilhamento com terceiros ou provedores, os prazos de retenção, os direitos do titular, as responsabilidades ou garantias, ou acrescenta funcionalidade que trata dados pessoais de forma nova.
  * **Ajuste menor:** redação, clareza, correções, links ou formatação, sem mudar o conteúdo.
  * **Quem classifica:** a autora, com apoio da revisão jurídica quando houver; a classificação e o motivo ficam registrados nas notas da versão; **na dúvida, a mudança é relevante**.
  * **Antes de habilitar novos anexos (M10) e o tratamento externo de dados (M8):** os textos são atualizados e o novo aceite é exigido **antes** de essas funcionalidades ficarem disponíveis.
* **M12-C:** versões anteriores dos Termos e da Política preservadas no repositório, com a data de cada uma; no app, só a vigente.
* **M12-D:** a revisão jurídica inclui o contrato do serviço de códigos e a restrição de destinatários. A licença MIT **fica fora** da reavaliação (M9 adiada). *(Em 06/10/2026 a M9 foi reaberta; a escolha da licença volta a entrar na revisão jurídica, conforme M9-C.)*

---

## M13 — Categoria especial "Faturas" (proposta candidata, 06/10/2026)

**Situação:** proposta **candidata** ao escopo da v7.0. **Nada aqui foi aprovado.** As decisões abertas abaixo continuam abertas, as decisões anteriores da v7.0 (P13–P30) não mudam e nenhuma conta existente será interpretada ou convertida.

### Proposta (autora, 06/10/2026)

Reunir várias despesas numa **fatura** (por exemplo, "Fatura Nubank de outubro"). Em Início aparece **uma única conta**, cujo total é a soma dos itens. Os gráficos continuam mostrando as **categorias reais** dos gastos, **sem duplicar valores**.

* **Estrutura:** categoria especial **Faturas**, fixa do sistema e não excluível. Uma **fatura** agrupa despesas sob um vencimento e um pagamento comuns. Cada **item** tem nome, valor, categoria própria, descrição opcional e recorrência ou parcelas. O comportamento especial depende da **identidade** da categoria no sistema, não do nome. Não pode haver fatura dentro de fatura.
* **Detalhes da fatura:** mantêm nome, ícone, status, vencimento e as ações de pagar, editar e excluir. O bloco Descrição é substituído por **"Itens da fatura"**:
  * botão "Adicionar item";
  * cada item com nome, categoria e valor, lupa (detalhes) e lápis (editar);
  * resumo dos valores por categoria.

  Ao voltar dos detalhes ou da edição de um item, o app retorna à fatura de origem. As contas comuns mantêm a Descrição.
* **Vínculo e vencimento:** cada item pertence a uma fatura específica e herda o vencimento dela, sem edição própria. Mudar o vencimento da fatura muda o dos itens. Cada ocorrência pertence à fatura do mês correspondente. Alterações futuras não mudam automaticamente faturas anteriores.
* **Visibilidade e total:** em Início aparece só a fatura, com o total calculado pela soma dos itens; os itens não aparecem como contas independentes. Adicionar, editar ou excluir um item atualiza o total e o resumo. Exemplo: Plano de saúde (Saúde, R$ 200,00) + Claude Code (Tecnologia, R$ 100,00) + Manicure (Beleza, R$ 130,00) = fatura de R$ 430,00.
* **Gráficos:**
  * o total do mês conta a fatura **uma vez**;
  * o gráfico por categoria distribui o valor da fatura pelas categorias dos itens, **sem** somar de novo em "Faturas";
  * itens sem categoria entram em "Sem categoria";
  * uma categoria soma contas comuns e itens de fatura;
  * proposta a confirmar: usar o mês de vencimento da fatura.
* **Pagamento:** a fatura é a unidade de pagamento. Marcar como paga ou reverter também se aplica aos itens (status e data). Só **pagamento integral**: pagamento parcial, juros, descontos e estornos **ficam fora**, salvo decisão própria.
* **Recorrência e parcelas:** uma fatura pode reunir assinatura recorrente, compra parcelada e compra única, cada item com as suas próprias regras (uma compra única não se repete porque a fatura se repete). Parcelas dos itens não se confundem com parcelas da fatura.
* **Decisões abertas pela autora:**
  1. personalização da categoria fixa;
  2. faturas vazias;
  3. geração das próximas faturas e vínculo de assinaturas e parcelas;
  4. itens em faturas pagas;
  5. exclusão de faturas com itens e escopos;
  6. movimentação entre faturas e transformação de conta comum em item;
  7. Ver status, atrasadas e demais consultas;
  8. exclusão da categoria de um item;
  9. relação com os comprovantes (M10);
  10. participação no limite de categorias.

### Comportamento atual (v6.0, conferido no código em 06/10/2026)

* **Modelo plano:** toda linha de `contas` é uma conta exibida e somada. Não há hierarquia entre contas. A categoria é uma linha de `categorias` do usuário (até 30, contando as 11 pré-criadas; 5.11), com cor única da paleta (5.13). Excluir uma categoria deixa as contas e as séries dela sem categoria.
* **"Cartão de crédito"** já é uma das 11 categorias pré-criadas, como categoria **comum**. Contas existentes nela **continuam comuns** (sem conversão automática).
* **Consultas que somam ou listam `contas` diretamente** (todas precisariam ser revisadas):

| Função (database/db.py) | Uso | Risco com itens de fatura |
|---|---|---|
| `listar_contas` | Início, Ver status, descoberta das séries para a geração sob demanda | Itens apareceriam como contas; total duplicado |
| `listar_contas_proximas` | Aviso de próximos vencimentos (RF17) | Itens como avisos separados; total duplicado |
| `listar_contas_atrasadas` | Contas em atraso (RF25) | Itens como atrasadas separadas |
| `resumo_do_periodo` | Total e pago do gráfico; comparação com o período anterior | Fatura + itens somados duas vezes |
| `totais_por_mes`, `totais_por_ano` | Evolução mensal e anual | Duplicação |
| `anos_com_contas` | Anos do gráfico; faixa de anos do seletor (M3) | Baixo (só anos) |
| `gastos_por_categoria` | Rosca e comparativo em colunas (M7) | Valor em "Faturas" **e** nas categorias dos itens |
| `resumo_dados_do_usuario`, `excluir_usuario` | Exclusão da conta de usuário (RF43) | Contagem e ordem de exclusão |
| `excluir_categoria`, `editar_categoria`, `criar_categoria`, `inicializar_categorias_padrao` | Categorias | Categoria especial excluída ou editada; limite de 30 |
| `marcar_conta_como_paga`, `marcar_conta_como_pendente`, `editar_data_pagamento` | Pagamento | Hoje afetam só uma ocorrência (5.9) |
| `editar_conta_ocorrencia`, `editar_conta_serie`, `alterar_frequencia_serie`, `encerrar_recorrencia`, `transformar_em_recorrente` | Edição e séries | Vencimento herdado; categoria da fatura; escopos |
| `excluir_conta`, `excluir_conta_serie` | Exclusão (5.7) | Itens órfãos |
| `gerar_ocorrencias_sob_demanda`, `obter_parcela` | Geração (5.20) e "Parcela X de Y" | Vínculo do item com a fatura do mês |
| `backend/main.py` (somas de pago e pendente na lista; total de próximas) | Interface | Duplicação, se receber itens |

**Conclusão:** **não** é seguro tratar itens como contas comuns sem revisar cada consulta acima. A proposta técnica abaixo centraliza essa separação.

### Decisões técnicas do planejamento (propostas sujeitas a revisão)

* **T15 — Identidade sem depender do nome:** a fatura é marcada na própria conta (`contas.tipo = 'fatura'`), e o item, por um vínculo com a fatura (`contas.fatura_id`, com `tipo = 'item'`). Faturas é tratada como uma **categoria do sistema** apresentada pelo app (nome e ícone fixos), **não** uma linha de `categorias` do usuário. Assim ela não pode ser excluída nem renomeada pelas funções de categoria, não consome cor da paleta e não depende do limite de 30 (ver F8). A categoria da fatura não pode ser trocada, e um item não pode ter "Faturas" como categoria (sem aninhamento).
* **T16 — Separação em dois conjuntos, num só lugar:**
  * **contas exibidas:** comuns e faturas, com o total da fatura calculado pela soma dos itens. Usado por Início, Ver status, próximas e atrasadas;
  * **lançamentos:** comuns e itens, **nunca** a linha da fatura. Usado por totais, total pago, evolução mensal e anual, rosca e comparativo.

  Proposta: duas **visões SQL** (ou duas funções únicas) por onde todas as consultas passam, em vez de filtros espalhados. O total da fatura **não é digitado** pelo usuário.
* **T17 — Status e vencimento dos itens:** copiados da fatura **na mesma transação** que muda a fatura (pagar, reverter, editar data de pagamento, mudar vencimento). Isso mantém a soma de "pago" correta nos lançamentos. A validação do schema e os testes conferem essa coerência.
* **T18 — Teste de invariante contra duplicação:** para cada período (mês e ano), estes valores precisam ser iguais:
  * total do mês;
  * soma das linhas de Início;
  * soma da rosca;
  * soma do comparativo;
  * soma de "Faturas" + comuns pelos lançamentos.

  O mesmo vale para o total pago. Valem também: fatura vazia, item sem categoria, categoria excluída, fatura paga e revertida, e séries.
* **T19 — Séries de itens:** reaproveitar o mecanismo de séries atual (posição, vagas, escopos, geração sob demanda), acrescentando à série do item o vínculo com a **série da fatura**. A ocorrência do item vai para a fatura **da mesma competência** (mês), gerada na **mesma transação** que a fatura daquele mês. A geração continua só ao navegar ou selecionar um mês (5.20, P19), nunca ao abrir o seletor.
* **T20 — Exclusão de usuário:** os itens são contas do usuário. A exclusão em uma transação continua a mesma. O vínculo da fatura (`fatura_id`) é conferido no fim do comando no SQLite, mas a ordem e os testes precisam ser verificados (CT de exclusão com faturas e itens).
* **T21 — Migração:** exige estrutura nova (`contas.tipo`, `contas.fatura_id`, vínculo entre séries, índice por fatura). Uma regra de verificação (CHECK) em tabela existente exige **reconstruir a tabela** no SQLite, ou validar no app e na verificação do schema. Nada existente muda de tipo: toda conta atual vira `comum`.
* **Fora desta proposta:** pagamento parcial, juros, descontos, estornos e importação de fatura do banco.

### Impactos por área

* **Modelo de dados:** colunas novas em `contas` e `series_recorrencia` e, se for o caso, visões. **Nenhuma tabela nova de categorias** com a T15.
* **Migrações:** com a P31 (06/10/2026), Faturas terá **migração própria**, posterior às da M12 (v9) e da M10 (v10), conforme o modelo que vier a ser aprovado.
* **Recorrências:** a série da fatura passa a comandar em quais meses existem faturas. As séries de itens dependem dela. Encerrar ou excluir a série da fatura afeta as séries de itens (G1, G4). As regras de preservação (5.5, 5.8; M10-J) valem para faturas e itens.
* **Totais e gráficos:** todos passam pelos lançamentos (T16). "Faturas" **nunca** aparece na rosca nem no comparativo. O mês é o do vencimento da fatura, herdado pelos itens.
* **Exclusão de usuário (RF43):** apaga faturas e itens. O resumo da exclusão (5.39) precisa dizer como os itens são contados (G4).
* **Comprovantes (M10):** o comprovante pertence a uma ocorrência. Falta decidir se fatura e item podem ter comprovante (G6). O limite de 3 por conta e as regras de exclusão se aplicam a quem tiver o comprovante.
* **Termos e Política:** sem dado pessoal novo de outro tipo. É ajuste **a classificar pela autora** (5.53) se a Política citar a estrutura das contas.
* **Testes:** além do invariante (T18), a regressão de séries, exclusões, pagamento, gráficos (CT110–CT118) e exclusão de usuário.

### Conflito registrado (06/10/2026): parcelas e recorrências não podem sumir em silêncio

**Requisito da autora:** parcelas e recorrências de itens **não podem desaparecer silenciosamente** quando a fatura do mês for excluída ou já estiver paga.

**Propostas acima que conflitam com esse requisito** (ficam **suspensas**, sem aprovação):

* **F4 (a):** "a ocorrência do item daquele mês não é gerada" quando a fatura do mês foi excluída;
* **F12:** "a ocorrência do item não é gerada" na fatura já paga;
* **F13 (a), escopo "Este mês em diante":** "as séries de itens deixam de gerar".

**Casos que precisam de regra explícita:**

| Caso | Situação | O que não pode acontecer |
|---|---|---|
| C1 | Fatura de um mês excluída ("Somente esta") com itens recorrentes ou parcelados ativos | A parcela daquele mês sumir sem aviso, ou a numeração "X de Y" ficar com buraco sem explicação |
| C2 | Fatura do mês já paga quando chega a ocorrência de um item recorrente ou parcelado (geração sob demanda, novo item parcelado, edição "Este mês em diante") | O valor ser somado a uma fatura paga sem aviso, ou a parcela não ser gerada sem aviso |
| C3 | Série da fatura encerrada ou excluída "Este mês em diante", ou término da fatura antes do fim das parcelas | Parcelas restantes perdidas sem aviso |
| C4 | Fatura revertida para pendente depois de C2 | Itens adiados ou retidos não voltarem, ou voltarem duplicados |

**Direções possíveis, a decidir depois em grupos menores:**

* aviso e confirmação **antes** da ação que causaria a perda, informando quantas parcelas ou ocorrências seriam afetadas;
* a ocorrência vai para a **próxima fatura pendente**, com a indicação "adiada de <mês>";
* a ocorrência fica **retida** como pendência visível na série do item, até o usuário escolher uma fatura;
* recusar a ação enquanto houver parcelas futuras vinculadas.

**Regra técnica mínima, qualquer que seja a decisão:** nenhuma operação apaga ou deixa de gerar ocorrências de itens sem que a contagem apareça para o usuário antes de confirmar. Um teste para cada caso C1–C4 confere que nenhuma parcela some sem aviso nem é contada duas vezes (invariante T18).

**Próximo passo:** quando Faturas for retomada, decidir primeiro **C1–C4**, depois G1 em blocos menores: (i) F1–F2, (ii) F3 e F5–F6, (iii) F7.

### Perguntas para a autora (agrupadas)

**G1 — Geração das faturas e dos itens recorrentes** *(abertas 2 e 3)*

* **F1 — Fatura única ou recorrente:**
  * (a) toda fatura é recorrente mensal (representa o cartão ou o agrupador);
  * (b) a fatura pode ser **única** ou **recorrente mensal**; itens recorrentes ou parcelados só em fatura recorrente.

  *Proposto: (b).*
* **F2 — Vínculo das ocorrências:**
  * item recorrente ou parcelado pertence à **série da fatura**, e cada ocorrência vai para a fatura do **mesmo mês**;
  * item anual vai para a fatura do mês da âncora;
  * compra única pertence a uma só fatura.

  *Proposto: sim.*
* **F3 — Parcelas além das faturas existentes:** ao criar um item em 10 parcelas, as faturas dos meses seguintes que ainda não existem são geradas na mesma operação, dentro do término da série da fatura, se houver. *Proposto: sim.*
* **F4 — Item sem fatura no mês:** a fatura daquele mês foi excluída ("Somente esta") ou a série da fatura termina antes do fim das parcelas.
  * (a) recusar a criação quando as parcelas passam do término da fatura; quando a fatura de um mês foi excluída, a ocorrência do item daquele mês **não** é gerada, e a numeração "X de Y" continua pela posição. **Suspensa: conflita com o requisito de 06/10 (ver C1 e C3);**
  * (b) recriar a fatura do mês automaticamente;
  * (c) gerar o item como conta comum.

  *Proposto: (a), suspenso pelo conflito registrado.*
* **F5 — Início do item:** um item criado dentro de uma fatura começa nela; as parcelas seguintes vão para as faturas seguintes. *Proposto: sim.*
* **F6 — Edição de itens recorrentes:** os mesmos escopos de hoje ("Somente este mês", "Este mês em diante"), aplicados à série do item. Nunca alteram faturas anteriores. *Proposto: sim.*
* **F7 — Faturas vazias:** permitir criar uma fatura sem itens (necessário para adicionar o primeiro item depois); ela aparece com **R$ 0,00** e "Sem itens".
  * (a) fatura vazia vencida entra em Atrasadas e Próximas como qualquer conta;
  * (b) fatura com total R$ 0,00 **não** entra em Atrasadas nem em Próximas.

  *Proposto: (b).*

**G2 — Categoria especial e limites** *(abertas 1, 8 e 10)*

* **F8 — Faturas como categoria do sistema (T15):** nome "Faturas" e ícone **fixos** nesta versão, sem cor da paleta, **fora** do limite de 30, fora dos gráficos e sem edição nem exclusão. Personalização vai para o banco de ideias. *Proposto: sim.*
* **F9 — Categoria do item:** item sem categoria ou cuja categoria for excluída vai para "Sem categoria", como as contas hoje (5.11). *Proposto: sim (sem mudança de regra).*
* **F10 — Limite de itens por fatura:** até **100 itens**, para manter Detalhes e as consultas rápidos. *Proposto: 100.*

**G3 — Pagamento e faturas pagas** *(aberta 4)*

* **F11 — Itens em fatura paga:**
  * (a) bloquear incluir, excluir e mudar valor enquanto a fatura estiver paga; nome, categoria e descrição continuam editáveis; para mudar valores, reverter o pagamento;
  * (b) permitir tudo, com aviso de que o total pago muda;
  * (c) bloquear tudo.

  *Proposto: (a).*
* **F12 — Geração em fatura paga:** um item recorrente ou parcelado nunca entra em fatura já paga. ~~Se a fatura do mês já estiver paga, a ocorrência do item **não** é gerada nela (vale F4).~~ **Suspensa: conflita com o requisito de 06/10 (ver C2 e C4).** O destino da ocorrência fica a decidir.

**G4 — Exclusão e movimentação** *(abertas 5 e 6)*

* **F13 — Excluir fatura com itens:**
  * (a) os itens daquela fatura são apagados junto, com aviso da quantidade. "Somente esta" apaga só a ocorrência e os seus itens; as séries de itens continuam nas faturas seguintes. "Este mês em diante" apaga as faturas futuras e as ocorrências futuras dos itens vinculados, e as séries de itens deixam de gerar (**esta parte está suspensa: ver C3**);
  * (b) bloquear a exclusão enquanto houver itens.

  *Proposto: (a).*
* **F14 — Mover item entre faturas, transformar conta comum em item ou item em conta comum, trocar a categoria de uma fatura:** **fora** desta versão (banco de ideias). *Proposto: fora.*
* **F15 — Resumo de "Excluir conta" (5.39):** informar faturas e itens separadamente, por exemplo "12 contas, incluindo 2 faturas com 9 itens". *Proposto: sim.*

**G5 — Consultas e gráficos** *(aberta 7 e mês dos gráficos)*

* **F16 — Mês nos gráficos:** o do vencimento da fatura, herdado pelos itens. *Proposto: confirmar.*
* **F17 — Ver status, Atrasadas, Próximas e "Suas contas estão em dia!":** só a fatura, com o total; itens só em Detalhes da fatura. *Proposto: sim.*
* **F18 — "Parcela X de Y" e frase de recorrência:** aparecem nos detalhes do item e na lista de itens da fatura. *Proposto: sim.*

**G6 — Comprovantes** *(aberta 9)*

* **F19:**
  * (a) comprovante só na **fatura**;
  * (b) também nos itens.

  *Proposto: (a); o pagamento é da fatura.*

**G7 — Escopo e ordem**

* **F20 — Onde Faturas entra:**
  * (a) no escopo da v7.0, como entrega própria **depois** da M8, das melhorias sem migração e da M10, com **migração própria** depois da(s) migração(ões) da M12 e da M10;
  * ~~(b) na mesma v9 da M12 e da M10;~~ (descartada pela P31);
  * (c) fora da v7.0 (v7.x ou v8).

  *Proposto: (a) ou (c). (b) atrasaria a M8 até o desenho de Faturas estar fechado.*

---

## M14 — Disponibilização para outras pessoas (desktop e/ou mobile) (06/10/2026)

### Proposta (autora, 06/10/2026)

Uma etapa específica para **avaliar** como disponibilizar o Sino a outras pessoas, em desktop e/ou mobile, com um **piloto restrito** antes de uma liberação mais ampla. Ter o provedor de e-mail funcionando **não** significa que o aplicativo está pronto para terceiros. **Não há compromisso de lançamento mobile.**

### Situação atual (v6.0)

* O Sino roda a partir do código-fonte (Python 3.11, `requirements.txt`, `flet run`), no computador da autora. Não há instalador nem pacote.
* O banco fica em `database/sino.db`, dentro da pasta do projeto. Os backups antes de migrações ficam em `database/backups/`.
* O empacotamento Android e iOS **não foi validado**: a biblioteca `cryptography` exige compilação em algumas plataformas (anotado no `requirements.txt`).
* Termos e Política foram aprovados pela autora para portfólio e demonstração local; revisão jurídica pendente.

### Decisões a tomar na E13 (em blocos, quando a etapa começar)

| Tema | Perguntas principais |
|---|---|
| **Público** | Quem participa do piloto (quantas pessoas, convidadas pela autora)? Quem seria o público da liberação ampla? |
| **Plataformas** | Desktop (Linux, Windows, macOS) e/ou mobile (Android, iOS)? Por qual começar? |
| **Empacotamento** | Como gerar o pacote de cada plataforma (Flet), assinatura de código, dependências nativas (`cryptography`) |
| **Instalação** | Instalador, arquivo compactado ou loja; onde ficam o programa e os dados de cada usuário (hoje dentro da pasta do projeto) |
| **Atualizações** | Como a pessoa recebe versões novas; migrações automáticas com backup; o que acontece se ela pular versões |
| **Preservação dos dados** | Garantir que atualizar ou reinstalar não apague o banco; local dos dados fora da pasta do programa |
| **Backup e recuperação** | O que a pessoa faz sozinha; papel da ferramenta de manutenção (M10, E17); orientação de recuperação |
| **Lojas** | Publicar ou não em Google Play e App Store; contas de desenvolvedor; regras de cada loja (privacidade, contrato de uso) |
| **Custos** | Contas de desenvolvedor das lojas, certificados de assinatura, domínio, provedor de e-mail acima do plano gratuito. **Nenhum gasto autorizado**; os valores serão conferidos nas fontes oficiais na etapa |
| **Segurança** | Assinatura e integridade dos pacotes, dependências fixadas e revisadas, segredos fora do app |
| **Privacidade** | O que muda na Política para outras pessoas; dados no computador ou celular de cada pessoa; serviço de códigos |
| **Revisão jurídica** | Termos, Política, licença e contrato do serviço antes do piloto (proposto) e da liberação ampla (obrigatório, 11.3) |
| **Suporte** | Canal de contato, prazo de resposta esperado, como relatar erros sem expor dados pessoais |
| **Serviço de códigos** | Ampliar a lista de destinatários só para os participantes do piloto, com registro (5.49) |
| **Avisos de terceiros** | Exibir as licenças das bibliotecas no app (Flutter, Flet e as demais) |

### Piloto restrito (E15)

* Pessoas **convidadas**, em número limitado, com as decisões da E13 tomadas e os textos revistos com novo aceite (11.3).
* Pergunta aberta (proposta: sim): exigir revisão jurídica concluída **já para o piloto**, já que o uso restrito não isenta obrigações (2.3).
* Critérios de saída do piloto (instalação, atualização sem perda de dados, recuperação, suporte) a definir na E13.

### Situação

**Planejada** como prioridade 4 (E13–E15). Nenhuma decisão tomada; nada empacotado nem publicado.

---

## Resumo geral da ERS v7.0 proposta (04/10/2026)

| ID | Melhoria | Situação no planejamento | Migração |
|---|---|---|---|
| M1 | Espaços acidentais no e-mail e nas senhas | Decidida | Não |
| M2 | Usuário sem contas × mês vazio | Decidida | Não |
| M3 | Seletor de mês e ano | Decidida | Não |
| M4 | Descrição de até 1.000 caracteres | Decidida | Não |
| M5 | Contador do nome do usuário oculto | Decidida | Não |
| M6 | Calendário em português e contraste do dia atual | Decidida | Não |
| M7 | Comparativo por categoria (colunas) | Decidida | Não |
| M8 | Envio real e publicação do serviço de códigos | Planejada com condições; domínio, remetente, responsável e contato pendentes | Não (no app) |
| M9 | Reavaliar a restrição de uso comercial | **Reaberta em 06/10/2026**; MIT continua no `LICENSE` até a decisão | — |
| M10 | Comprovantes em imagem | Decidida | **Sim (v10**, P31) |
| M11 | Nomes em janelas estreitas | Decidida | Não |
| M12 | Revisão jurídica, versionamento e novo aceite | Decidida; revisão jurídica pendente | **Sim (v9**, só aceites; P31) |
| M13 | Categoria especial "Faturas" | **Proposta candidata** (06/10/2026); decisões abertas; conflito C1–C4 registrado | Sim (migração própria, posterior) |

**Backlog futuro (fora da v7.0):** notificações; versão mobile; comprovantes em PDF; contorno nas fatias da rosca; e as ideias levantadas e deixadas fora da M1 (forma de gravação do e-mail, alfabeto internacional, ponto obrigatório no domínio).

**Decisão separada:** L1, limpeza das contas antigas de teste (resolvida na instalação principal em 06/10/2026, pela reinicialização do banco).

## Ordem de implementação proposta

*(Substituída em 06/10/2026 pela revisão aprovada abaixo; mantida como histórico.)*

Cada etapa com testes específicos, conferência visual curta só dos pontos novos, suíte completa no fechamento e commits apenas com autorização.

1. **Etapa A — Interface e regras sem migração**, em blocos independentes:
   * A1: M1 (espaços no e-mail e nas senhas);
   * A2: M2 e M3 (Tela Principal: usuário sem contas e seletor de mês e ano);
   * A3: M4 e M5 (limites: descrição e contador do nome);
   * A4: M6 (calendário: idioma e contraste);
   * A5: M11 (linhas de conta em janelas estreitas);
   * A6: M7 (comparativo por categoria).
2. **Etapa B — Versionamento e aceite (M12, parte técnica)** com a **migração v9** (tabela de aceites e tabela de comprovantes criadas juntas, com backup do banco antes). Inclui o histórico dos textos no repositório. Os textos novos de M8 e M10 só entram depois da etapa C.
3. **Etapa C — Comprovantes (M10)**, em sequência: armazenamento e consistência (remoções pendentes, quarentena); processamento seguro das imagens; telas (Editar e Detalhes); regras de séries e exclusões; ferramenta de manutenção (bloqueio compartilhado, pacote criptografado com revisão da escolha criptográfica, restauração segura). **A funcionalidade só é habilitada depois** de atualizar Termos e Política e exigir o novo aceite (M12-B).
4. **Etapa D — Serviço de códigos (M8)**, só depois de resolver domínio, remetente, responsável e contato, e de conferir planos, custos e retenção: restrição de destinatários no serviço e no contrato; ambiente de teste; uso restrito aos endereços da autora; textos atualizados e novo aceite **antes** de habilitar o envio real.
5. **Etapa E — Abertura a terceiros:** revisão jurídica concluída (M12-A, incluindo o contrato e a restrição de destinatários), reavaliação da proteção contra abuso (M8-E) e mudança explícita de configuração para abrir o serviço.

## Revisão do plano: entregas incrementais (aprovada em 06/10/2026, P31; ordem substituída pela P33)

*A divisão das migrações continua valendo. A ordem e a numeração das entregas abaixo foram substituídas no mesmo dia pela organização da P33 (ERS v7.0, seção 15). Esta seção fica como histórico; as dependências D1–D9 da M8 continuam válidas para a E4.*

**Pedido da autora (06/10/2026):** implementar **um requisito por vez**. Cada entrega concluída passa por:

* testes necessários;
* validação, quando aplicável;
* documentação;
* commit e publicação no GitHub, **sem force**.

Testes já aprovados não são repetidos sem motivo. **Prioridade inicial: envio real de e-mails (M8)**, publicado só para os endereços da autora. **Nenhum gasto autorizado** e nenhuma abertura a terceiros.

**Aprovado pela autora (06/10/2026):** dividir as migrações (v9 só para versionamento e aceites; comprovantes e Faturas em migrações posteriores) e priorizar a M8. A ordem abaixo substitui a anterior e está consolidada na ERS v7.0 (9.1 e 15).

### Nova ordem pedida pela autora (06/10/2026, depois da P31; substituída pela P33)

Primeiro a **licença** (M9 reaberta: decisão e, se houver troca, o novo `LICENSE` e os avisos); depois as **melhorias simples de UX**, **uma por entrega**; depois o **envio real de e-mails** (M12 técnica e M8). A tabela "Ordem aprovada" abaixo fica com essa sequência; as dependências da M8 continuam valendo para quando ela chegar.

### Dependências da primeira entrega (M8 em uso restrito)

A regra 5.49 da ERS v7.0 exige que, **antes de habilitar o envio real**, os Termos e a Política sejam atualizados e o **novo aceite** seja exigido (5.53). O novo aceite depende do **registro da versão aceita** (M12, parte técnica), e esse registro exige migração. Por isso, a M8 não pode ser a primeira entrega isolada sem mudar uma decisão aprovada.

| # | Dependência | Situação | Tipo |
|---|---|---|---|
| D1 | Domínio e remetente (M8-B) | Pendente. Domínio novo tem custo, e não há gasto autorizado. Alternativas sem custo: subdomínio de um domínio que a autora já tenha; ou usar a Resend sem domínio verificado, que (pela regra conhecida, **a conferir**) só entrega ao e-mail do dono da conta Resend. Isso serve ao uso restrito apenas se a autora usar **um** endereço | Decisão da autora |
| D2 | Responsável pela operação e contato para titulares (M8-C) | Pendente; precisa entrar na Política | Decisão da autora |
| D3 | Conferir planos gratuitos, limites e retenção da Cloudflare (Workers e Durable Objects com SQLite) e da Resend (M8-A, M8-F) | **Feita em 06/10/2026** (ver M8, "Conferência dos provedores"). A exigência de cartão será confirmada no cadastro; se houver cartão ou cobrança, o trabalho para e a autora decide | Conferência |
| D4 | M12 técnica: versão nos documentos, registro do aceite por versão, tela de novo aceite | Planejada (5.53); exige migração | Implementação |
| D5 | Textos dos Termos e da Política para o envio real em uso restrito (provedores, prazos reais, responsável, contato) e classificação da mudança como relevante | A redigir; a revisão jurídica não é condição do uso restrito (11.1), mas o uso restrito não isenta obrigações (2.3) | Texto + aprovação da autora |
| D6 | Restrição técnica de destinatários no serviço (T10), evolução do contrato (novo código de erro) e testes de conformidade | Planejada | Implementação |
| D7 | Mensagem do app para o novo código de erro; endereço e chave pública de produção na configuração da versão | Planejada. O app já aceita `SINO_SERVICO_URL` por ambiente; a configuração definitiva vai na versão | Implementação |
| D8 | Ambiente de teste publicado e validado, depois produção restrita; segredos por ambiente; DNS, se houver domínio | Depende de D1–D3 | Configuração (com autorização) |
| D9 | Validação: CT138, entrega real aos endereços autorizados, expiração, tentativas, reenvio, neutralidade da recuperação | Depende de D8 | Validação |

### Escolha para destravar a M8 (decidida em 06/10/2026: opção (a))

* **(a) Aprovada:** **dividir a migração**: v9 só com os **aceites** (M12); depois, uma migração própria para os comprovantes (M10) e outra para Faturas, se aprovada. Isso muda a proposta técnica T6 e a seção 9.1 ("migração v9 única"), mas mantém todas as regras de produto. Primeiras entregas: **(1) M12 técnica**, com v9 de aceites; **(2) M8 em uso restrito**, com os textos novos e o novo aceite.
* **(b)** Manter a **v9 única** (aceites + estruturas de comprovantes, sem habilitar) já na entrega (1). Risco: criar as tabelas da M10 antes de implementá-la, e ajustes no desenho viram outra migração.
* **(c)** Habilitar o envio real em uso restrito **sem** novo aceite. Muda a decisão aprovada 5.49/5.53; **não recomendado**.

### Ordem aprovada

| Entrega | Requisito | Depende de |
|---|---|---|
| 0 | **Licença (M9 reaberta):** decisão L1–L6; se houver troca, novo `LICENSE`, aviso dos documentos, registro do marco e das versões MIT, README e notas da versão; **antes do próximo push** | Decisão da autora; revisão jurídica conforme L5 |
| 1–8 | Melhorias simples de UX, **uma por entrega**: M1; M2; M3; M4; M5; M6; M11; M7 (a autora pode reordenar) | 0 |
| 9 | M12 técnica: versões, registro do aceite, tela de novo aceite, histórico dos textos; **migração v9 (aceites)** | — |
| 10 | **M8 em uso restrito:** restrição de destinatários (serviço e contrato), textos novos com novo aceite, ambiente de teste, produção restrita, validação | 9; D1–D3 |
| 11 | M10 comprovantes (sem habilitar) e ferramenta de manutenção; **migração v10** | 9; revisão de T8 |
| 12 | Habilitar comprovantes (textos e novo aceite) | 11 |
| 13 | M13 Faturas, se aprovada (F20); **migração própria**, posterior | Conflito C1–C4 e decisões G1–G7 |
| — | Liberação para terceiros | Seção 11.2 da ERS v7.0 |

* ~~A primeira publicação no GitHub levará também o commit de planejamento já existente (33b8db2).~~ Substituído pela opção B (06/10/2026): o `33b8db2` foi refeito e consolidado com a licença.
* Os critérios de conclusão (11.1), entrega parcial (11.3) e liberação para terceiros (11.2) **não mudam**.

## Pendências do planejamento

* **M8:** domínio e remetente; responsável pela operação e contato para titulares; conferência de recursos, limites e custos da Cloudflare e da Resend; prazos de retenção configuráveis e obrigatórios de cada provedor.
* **M10:** revisão da escolha criptográfica e do formato do pacote na implementação; diferenças de trava de arquivos entre Linux e Windows.
* **M12:** contratação e realização da revisão jurídica; textos novos dos Termos e da Política para M8 e M10.
* ~~**L1:** critério, backup e nova referência do banco para a limpeza das contas de teste, quando a autora decidir.~~ Resolvida em 06/10/2026 (reinicialização do banco; ref6).
* **M13 (Faturas):** decisões G1–G7 (F1–F20) abertas; entrada no escopo a confirmar (F20).
* **M9 (licença):** MIT + Commons Clause escolhida (P36); arquivos preparados, aguardando commit e publicação; pendentes: revisão jurídica e INPI (sem gasto).
* **Plano:** organização da P33 (06/10/2026) vigente: E1–E18 e F1 (ERS v7.0, seção 15).
* **M14:** decisões da avaliação de disponibilização (E13). Dependências abertas da entrega 2: D1 (domínio e remetente, ou alternativa A, B ou C), D2 (responsável e contato) e a pergunta sobre o envio real no ambiente de teste.
* **M13:** conflito C1–C4 (parcelas e recorrências não podem sumir em silêncio), a decidir em grupos menores antes de G1.
* **ERS v7.0:** consolidar estas decisões no documento da ERS v7.0 (requisitos, regras, modelo de dados, migração v9 e casos de teste) antes da implementação; a ERS v6.0 permanece como está.
