# Sino 6.12 — regras de tipos de conta, parcelamentos e valores variáveis

Anexo da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (seções 5.55, 9.1 e 9.3). Registra as regras de negócio da **Sino 6.12** como foram aprovadas pela autora e implementadas na branch `integracao/sino-6.12`.

**Situação (08/11/2026):**
- A versão está **validada tecnicamente e preparada para integração**.
- **Ainda não está publicada:** não foi levada à `main` nem marcada com etiqueta.
- O banco pessoal da autora **não** foi migrado.

**Fontes:**
- Notas do ambiente experimental, que ficam fora do repositório e foram transcritas aqui sem alterar as regras:
  - `612_decisoes_consolidadas.md` (06/11/2026);
  - `612_documentacao_final.md` (07/11/2026, inclusive a seção 14 de ajustes);
  - `612_pendencias_6.13.md` (07/11/2026).
- O registro [sino-6.12-experimental.md](sino-6.12-experimental.md).
- O código e os testes da branch de integração.
- As decisões da autora durante a integração (08/11/2026).

**Divergências entre as fontes:** quando as fontes divergem, esta é a ordem de precedência:
1. as decisões posteriores da autora;
2. a seção 14 (ajustes) da documentação experimental;
3. as decisões consolidadas.

As divergências encontradas estão na seção 15.

> **Identificadores repetidos.** As decisões de projeto D1–D14 (seção 13) são as do planejamento da 6.12. A integração usa outros nomes, que coincidem em parte:
> - **D1–D6** (Etapa 2, organização da integração);
> - **D7 e D8** (Etapa 5B, 08/11/2026: R5/R3 e texto do R4-A);
> - **D6B-1 a D6B-7** (Etapa 6B).
>
> Neste anexo, as decisões da integração aparecem sempre com a etapa, por exemplo "D7 (Etapa 5B)".

---

## 1. Objetivo e escopo

A Sino 6.12 traz quatro novidades:
1. **Tipos de conta:** Única, Parcelada, Recorrente mensal e Recorrente anual.
2. **Parcelamentos** de 2 a 36 parcelas.
3. **Recorrências de valor fixo ou variável**, com conversão entre os dois comportamentos.
4. As **regras financeiras** dessas operações.

Junto vêm o **schema SQLite v11** (ERS 9.3) e o **novo limite da descrição**, de 250 caracteres (ERS 5.45).

A **interface é mínima**, feita com os componentes já existentes na 6.11 (R11). A modernização visual de Nova conta e Editar conta fica para a **Sino 6.13**. As Supercontas (F1) ficam para a **Sino 6.14**. As duas versões estão só planejadas e não foram iniciadas.

## 2. Tipos de conta

| Tipo | O que é | Identificação na tela |
|---|---|---|
| **Única** | Conta avulsa, com um vencimento | Sem "Parcela/Ocorrência X de Y" |
| **Parcelada** | Valor total dividido em 2 a 36 parcelas mensais | "Parcela X de Y" |
| **Recorrente mensal** | Repete todo mês, com ou sem término | "Ocorrência X de Y" (com término) ou "Ocorrência X" |
| **Recorrente anual** | Repete todo ano, com ou sem término | O mesmo |

- **Mensal e anual:** podem ter **Valor fixo** (o padrão, como na 6.11) ou **Valor variável**. Somando tudo, são seis combinações: Única, Parcelada, Mensal fixa, Mensal variável, Anual fixa e Anual variável.
- **Ocorrência que sobra de uma recorrência encerrada:** é tratada como Única (avulsa).
- **Rótulos (D1):** "Parcela X de Y" só aparece em parcelamentos; as recorrências usam "Ocorrência X de Y".
- **Onde se escolhe o tipo (R11):** no diálogo "Configurar recorrência" da Nova conta, entre Única, Parcelada, Mensal e Anual. A escolha "Valor fixo | Valor variável" só aparece para Mensal e Anual.

**Regra estrutural:**
- **Só a conta Única muda de tipo.** Ela pode virar Parcelada, Recorrente mensal ou Recorrente anual.
- **Parceladas, mensais e anuais não mudam de tipo**, inclusive as que nasceram de uma Única.
- **O tipo não restringe a edição:** nome, descrição, categoria, valores, vencimentos, edição individual e coletiva, pagamentos, estornos, exclusões e encerramento seguem as regras de cada modalidade.
- **Fixo ↔ Variável** muda só o comportamento do valor, dentro da mesma periodicidade. Não é uma conversão estrutural.

## 3. Contas únicas

- **Criação, edição, pagamento e exclusão:** como na 6.11, inclusive a regra da 6.10 de que "Marcar como paga" cria um registro de pagamento "integral".
- **Transformações:** a Única é o ponto de partida de todas as transformações (seção 9).

## 4. Parcelamentos

**Criação**
- **Valor total obrigatório:** o campo passa a se chamar "Valor total".
- **Quantidade:** de **2 a 36** parcelas, sempre **mensais** (D2, D4, D13). Fora dessa faixa: "Informe de 2 a 36 parcelas."
- **Divisão em centavos (D3):** parcelas iguais, com a diferença na **primeira**. Exemplo: R$ 1.000,00 em 3 dá R$ 333,34 + R$ 333,33 + R$ 333,33.
- **Vencimentos:** seguem o cálculo mensal da 6.11, sem arrasto para os dias 29, 30 e 31. Por exemplo, 31/01 vai para 28/02 ou 29/02 e volta a 31/03.
- **Prévia:** o diálogo "Confirmar parcelamento" mostra cada parcela com vencimento e valor antes de gravar. Nada é gravado antes de "Salvar conta".
- **Como é guardado (D10):** como uma série mensal com término, mais uma linha na tabela `parcelamentos`.
- **Gravação atômica (D14):** tudo ou nada, com rollback integral.

**Termos usados**
- **Protegida:** parcela ou ocorrência com registro de pagamento (ativo ou estornado) ou quitada.
- **Editada:** parcela ou ocorrência editada individualmente.
- **Livre:** nem protegida nem editada.

**Edição individual (D5, C7)**
- **Valor de uma parcela, "Somente este mês" (D5):** só é aceito em parcela sem registros de pagamento. A parcela passa a contar como editada, e o total muda sem redistribuir as outras.
- **Outros campos:** nome, categoria e descrição continuam editáveis em qualquer parcela.
- **Vencimento individual (C7):** não pode cair no mês de outra parcela. Mensagem: "Já existe outra parcela deste parcelamento nesse mês. Escolha outro mês."
- **Valor em "Este mês em diante" numa Parcelada (Etapa 7, ponto 1 = C):** é recusado com a orientação "Para mudar o valor de várias parcelas, use “Alterar parcelamento” em Editar conta, no campo Recorrência."
- **Vencimento em "Este mês em diante" (C7, P4, E6):**
  - as parcelas seguintes seguem mês a mês com o novo dia;
  - as protegidas mantêm o vencimento;
  - se uma protegida sair do próprio mês na nova sequência, a operação inteira é recusada;
  - o término é recalculado;
  - colisões nunca são resolvidas pulando meses automaticamente.

**Alterar parcelamento (D6, E5, R12)**
- **Onde fica (ajuste A):** em **Editar conta > campo Recorrência > "Alterar parcelamento"**, só em contas parceladas. Grava na hora (D3 dos ajustes). Depois de aplicar, o app volta aos Detalhes.
- **O diálogo:** abre com Valor total e Quantidade preenchidos. A prévia marca cada parcela como "· nova", "· com pagamentos (mantida)", "· editada (mantida)" ou excluída do fim.
- **Recálculo:** protegidas e editadas mantêm o valor. O novo total, menos os valores mantidos, é dividido entre todas as parcelas **livres**, inclusive as anteriores à selecionada (Etapa 7, ponto 2 = A). A diferença de centavos fica na primeira livre.
- **Aumentar a quantidade:** cria parcelas livres depois da última.
- **Reduzir a quantidade:** exclui do fim, **só parcelas livres**.
- **Recusa por inteiro, sem gravação parcial (R12):** quando a operação exigiria mexer numa protegida ou editada, ou quando as livres não comportam o valor (mínimo de 1 centavo cada). Mensagens:
  - "Para reduzir a quantidade, seria preciso excluir parcelas com pagamentos ou editadas. Nada foi alterado."
  - "Não há parcelas livres (sem pagamentos e sem edição individual) suficientes para esse valor total. Nada foi alterado."
- **Botão Aplicar (ajuste B):** fica cinza e desabilitado enquanto a prévia estiver recusada.
- **Exemplo de leitura da R12:**
  - 10 parcelas de R$ 100,00, com a parcela 4 editada para R$ 150,00, dão um total de R$ 1.050,00.
  - Um novo total de R$ 1.200,00 recalcula as outras 9 parcelas, e a parcela 4 continua com R$ 150,00.

**Exclusão de parcelas (D7, C2, C3, C4, E4, P1)**
- **Parcela livre:** pode ser excluída individualmente. As demais mantêm os valores, "Parcela X de Y" é renumerada na tela, e o total diminui sem redistribuir. A identidade interna e os dados financeiros das outras parcelas ficam intactos.
- **Parcela com pagamentos ativos ou estornados:** a exclusão individual é **recusada** (C4). É uma exceção à 5.54 que vale só para Parceladas. Mensagem: "Esta parcela tem registros de pagamento (inclusive desfeitos) e não pode ser excluída."
- **"Este mês em diante" com protegida a partir da selecionada:** **recusado** (P1). Mensagem: "Há parcelas com registros de pagamento a partir desta. Exclua somente as parcelas sem pagamentos."
- **Encerrar:** uma Parcelada não é encerrada.

## 5. Recorrências mensais e anuais

- **Mecanismo:** o mesmo da 6.11, com geração sob demanda, dias 29 a 31 sem arrasto, 29/02 em ano bissexto, e opção de término ou não.
- **Frequência (R6):** Mensal ↔ Anual é **sempre bloqueado**. "Alterar frequência" saiu da tela, e a função de dados recusa a mudança com "A frequência de uma recorrência não pode ser alterada. Para usar outra frequência, encerre esta recorrência e depois transforme uma ocorrência que ficou avulsa."
- **Código mantido só para os testes:** o corpo da função da 6.11 continua no código (`_alterar_frequencia_serie_611`), só para os testes montarem dados legados (decisão D2 da integração).
- **Séries com frequência alterada na 6.11:** continuam funcionando depois da migração.

## 6. Valor fixo e valor variável

- **Fixo:** o valor da primeira ocorrência é obrigatório e se repete nas seguintes. Todas as recorrências que já existem continuam fixas depois da migração.
- **Variável:**
  - o valor da primeira ocorrência é obrigatório ("Informe o valor da primeira ocorrência.");
  - as ocorrências seguintes nascem com **"Valor pendente"**, com ou sem término, inclusive na geração sob demanda;
  - informar o valor de uma ocorrência não preenche as seguintes.
- **Alterar só o valor numa série variável (ajuste C, D2 dos ajustes):** a alteração, inclusive a de informar o valor de uma pendente, grava só aquela ocorrência e **não** abre o diálogo de abrangência. O valor-modelo e as ocorrências futuras não mudam. Se outro campo mudar junto, o diálogo aparece e vale a R5.
- **Conversão Fixo ↔ Variável (ajuste D, D1 dos ajustes):** fica em **Editar conta > Recorrência > "Alterar tipo de valor"**, e o botão dos Detalhes foi retirado. É uma ação separada de "Encerrar recorrência", não aparece quando há um encerramento pendente e grava na hora.

## 7. Ocorrências com valor pendente (R8, V5–V8, R9)

- **Pendente não é zero:** valor pendente **não é R$ 0,00**, e R$ 0,00 informado é um valor conhecido.
- **Listas (V5):** as listas e "Contas em atraso" mostram "Valor pendente" no lugar do valor. Uma pendente vencida aparece como atrasada.
- **Aviso dos próximos 7 dias (V6):** conta as pendentes ("N conta(s) com valor pendente") sem somá-las.
- **Totais e Gráfico (V7):**
  - somam só os valores conhecidos;
  - indicam as pendentes ("+N pendente(s)");
  - um mês só com pendentes mostra "Valor pendente", e não "R$ 0,00".
- **Detalhes (V8):**
  - mostram "Valor pendente" e "O valor desta ocorrência ainda não foi informado.", com saldo "—";
  - "Marcar como paga" e "Registrar pagamento parcial" ficam desativados, com o motivo;
  - o botão "Informar valor" fica disponível.
- **Informar o valor de uma pendente:** grava o valor e retira a pendência na mesma transação. Só nesse caso R$ 0,00 é aceito; fora dele continua a regra da 6.11 de valor maior que zero.
- **Como é guardado (R9):** numa tabela complementar (`ocorrencias_valor_pendente`). O `contas.valor = 0` serve só de marcador interno e nunca é exibido.
- **Pendente não vira outro tipo:**
  - "Esta conta está com valor pendente: informe o valor antes de transformá-la."
  - "Esta conta está com valor pendente: informe o valor antes de parcelá-la."

## 8. Pagamentos, estornos e preservação financeira

- **Continua como na 6.10 e na 6.11:**
  - pagamentos integrais e parciais em centavos;
  - estornos rastreáveis, sem apagar o histórico;
  - proteção por registros de pagamento ativos ou estornados;
  - H2 e I1–I4 nas recorrências;
  - exclusões pela 5.54, salvo a exceção C4/P1 nas Parceladas;
  - totais e gráficos sem duplicidade.
- **Pendente não recebe pagamento (R8):** a recusa está nas telas e também na camada de dados. Mensagem: "Esta conta está com valor pendente. Informe o valor antes de registrar um pagamento."
- **Ocorrência com pagamento não fica pendente:** o gatilho `trg_valor_pendente_sem_pagamentos` (v11) impede que uma ocorrência com registros de pagamento, inclusive só estornados, seja marcada como pendente. Mensagem: "Uma ocorrência com registros de pagamento não pode ficar com valor pendente."
- **Sem gatilho em `pp_pagamentos`:** a validação v10 exige essa tabela exata. A recusa de pagar uma pendente depende do código e é conferida pela validação v11.
- **Pagamentos não ultrapassam o valor:** um pagamento nunca fica acima do valor da conta.

## 9. Transformações e matriz de conversões

**Matriz definitiva** (decisões consolidadas, seção 3):

| De \ Para | Única | Parcelada | Mensal | Anual |
|---|---|---|---|---|
| **Única sem registros de pagamento** | — | ✅ (P6) | ✅ fixa ou variável | ✅ fixa ou variável |
| **Única com pagamentos ativos ou estornados, ou quitada** | — | ❌ (R1) | ✅ (R2) | ✅ (R2) |
| **Parcelada** | ❌ | — | ❌ | ❌ |
| **Mensal** | ❌ | ❌ | Fixo ↔ Variável ✅ (R3/R4) | ❌ (R6) |
| **Anual** | ❌ | ❌ | ❌ (R6) | Fixo ↔ Variável ✅ (R3/R4) |

- **Única → Parcelada ("Parcelar esta conta", P6):**
  - a própria conta vira a parcela 1, no mesmo vencimento;
  - é recusada quando o valor em centavos é menor que a quantidade de parcelas ("O valor total é pequeno demais para essa quantidade de parcelas.");
  - com qualquer registro de pagamento, mesmo estornado, aparece o diálogo "Não é possível parcelar" (R1): "Esta conta tem registros de pagamento (inclusive desfeitos) e não pode ser parcelada."
- **Única → Recorrente com pagamentos (R2):** a Única vira a primeira ocorrência, com status, data de pagamento e pagamentos (ativos e estornados) intactos. Numa recorrência variável, só as ocorrências criadas ficam pendentes.
- **"Transformar em recorrente" (X1):** só aparece para a Única ou para a avulsa de uma série encerrada, e não para uma avulsa com valor pendente. Para os outros casos, a mensagem é "Só uma conta Única ou uma ocorrência de recorrência encerrada pode ser transformada."
- **Encerrar e depois transformar (X2):** são duas ações explícitas, sem reorganização automática.
- **Parcelada:** não muda de tipo ("Uma conta parcelada não pode mudar de tipo.").
- **"Encerrar recorrência" (R7)** não é uma conversão; ver a seção 11.

## 10. Conversão Fixo ↔ Variável (R3, R4, R4-A, R5, X3)

- **Mudar para valor variável (R3, X3):**
  - a ocorrência selecionada **mantém** o valor;
  - as **livres seguintes** ficam pendentes;
  - protegidas e editadas são preservadas.
- **Mudar para valor fixo (R4, X3):**
  - exige um valor e sugere o último informado;
  - a selecionada, se estiver pendente, recebe o valor, e depois as pendentes elegíveis seguintes também;
  - valores já informados, protegidas e editadas são mantidos;
  - a primeira ocorrência nunca fica sem valor.
- **Bloqueio R4-A:** "Mudar para valor fixo" é recusado enquanto houver ocorrências **anteriores** à selecionada com valor pendente. Mensagem: "Há ocorrências anteriores a esta com valor pendente. Informe esses valores ou faça a mudança a partir da primeira ocorrência pendente. Nada foi alterado."
  - Quando essa condição já é conhecida ao abrir o diálogo, o botão "Mudar para fixo" fica **cinza e desabilitado**, com o motivo visível.
  - Mesmo que o botão seja acionado à força, nada é gravado, e o banco também recusa.
  - Depois que as pendentes anteriores são informadas, o botão volta a ficar habilitado ao reabrir o diálogo.
- **Prévia e frequência:** os dois diálogos mostram uma prévia e **não mudam a frequência** (R6).
- **Quando a conversão não é aceita:**
  - "Só uma recorrência ativa pode ter o valor fixo ou variável alterado."
  - "Esta recorrência já tem valor variável."
  - "Esta recorrência já tem valor fixo."
- **"Este mês em diante" numa série variável (R5):** muda só a selecionada e o valor-modelo. **Não** preenche pendências futuras e **não** altera valores futuros já informados. É uma exceção à 5.1, restrita às séries variáveis, e o diálogo de escopo mostra esse aviso.
  - Com o ajuste C, essa escolha só aparece quando o valor muda junto com outro campo.
  - **D7 (Etapa 5B):** um valor gravado por "Este mês em diante" **não** marca a ocorrência como editada. Por isso, uma conversão R3 posterior a torna pendente outra vez. Isso segue a R3 como foi escrita e é **mantido na 6.12**. Fica registrado como possível melhoria (seção 14).

## 11. Encerramento de recorrências (R7, X2)

- **Corte:** o comportamento é o da 6.11 (RF29 revisado). A série deixa de gerar ocorrências, e o corte é o maior entre o vencimento da selecionada e hoje.
- **O que sai e o que fica:**
  - as ocorrências posteriores ao corte são removidas;
  - **ficam** as pagas, as que têm data de pagamento e as editadas;
  - a selecionada nunca é removida.
- **As que ficam:** viram avulsas, e as pendentes continuam pendentes (o valor pode ser informado depois).
- **Encerrar com Salvar (X2):** com um encerramento pendente em Editar, o menu só oferece "Desfazer esta alteração". O Salvar nunca encerra uma série e cria outra de uma vez.
- **Alterações não salvas (D3 dos ajustes):** "Alterar parcelamento" e "Alterar tipo de valor" gravam na hora. Se houver alteração não salva no formulário, o app mostra "Há alterações não salvas" e não abre nem descarta nada.

## 12. Descrição de até 250 caracteres

- **Novo limite:** **250 caracteres percebidos**, antes 1.000 (Sino 6.5). Vale na criação e na edição, em todos os escopos, no modelo da série e nas parceladas.
- **Na tela:** contador "x/250" e dica "Até 250 caracteres". A descrição continua opcional.
- **O que não muda:** contagem, normalização, recusa sem corte, "Limite atingido", o som e a exibição completa em Detalhes (ERS 5.45).
- **Dados existentes (P4):** descrições já gravadas com mais de 250 caracteres não são migradas nem cortadas. Aparecem inteiras e só podem ser salvas depois de reduzidas.

## 13. Decisões consolidadas aplicáveis

| Id | Decisão |
|---|---|
| R1 | Única → Parcelada bloqueada com qualquer registro de pagamento, inclusive estornado ou quitação |
| R2 | Única → Mensal/Anual permitida com pagamentos, histórico intacto; numa variável, as seguintes nascem pendentes |
| R3 | Fixo → Variável: as livres a partir da selecionada ficam pendentes (alcance X3) |
| R4 | Variável → Fixo: valor obrigatório, sugere o último; preenche as pendentes elegíveis (alcance X3) |
| R4-A | R4 recusado enquanto houver pendentes anteriores à selecionada (07/11/2026) |
| R5 | "Este mês em diante" numa variável: só a selecionada e o modelo |
| R6 | Mensal ↔ Anual bloqueado; "Alterar frequência" retirado |
| R7 | Encerrar como na 6.11 |
| R8 | Pendente não é R$ 0,00 (V5–V8); pagamentos bloqueados até informar o valor |
| R9 | Pendentes em tabela complementar |
| R10 | Migrações numeradas na ordem de implementação (v11 = 6.12). *Atualização (08/11/2026):* a parte "sem reservar a v12" foi revista pela autora; a v12 fica reservada a Comprovantes e Remoções pendentes (seção 15) |
| R11 | Interface mínima na 6.12; modernização na 6.13 |
| R12 | Recálculo de parcelas recusado se exigir mexer em protegida ou editada, ou se as livres não comportarem o valor |
| X1 | "Transformar" só para Única ou avulsa de série encerrada |
| X2 | Encerrar → Transformar em duas ações explícitas |
| X3 | R3: a selecionada mantém o valor; R4: a selecionada, se pendente, recebe o valor; a 1ª ocorrência nunca fica sem valor |
| Etapa 7, ponto 1 = C | Valor "Este mês em diante" numa Parcelada continua bloqueado (orientação para "Alterar parcelamento") |
| Etapa 7, ponto 2 = A | "Alterar parcelamento" recalcula todas as parcelas livres, inclusive as anteriores à selecionada |
| Ajustes A–D, D1–D3 dos ajustes | Seções 4, 6, 10 e 11 deste anexo |

**Situação das decisões anteriores do planejamento:**
- **Mantidas:** D1–D7, D10, D13, D14; E4–E6; C2–C4, C7; P1, P4, P6, P7; e V5–V8, por meio da R8.
- **Adiada para a 6.14:** a V12.
- **Revisadas, substituídas e desnecessárias:** ver a seção 7 de `612_decisoes_consolidadas.md`.
- **Correspondência com esta numeração:** D8 e D9 foram revisadas (a conversão só parte da Única). D11 foi revisada pela R10 e, depois, pela decisão de 08/11/2026 sobre a v12. D12 e "tipos visíveis no formulário" passaram para a 6.13.
- **Decisões da integração (08/11/2026):**
  - D7 (Etapa 5B): manter R5 seguido de R3;
  - D8 (Etapa 5B): manter o texto do R4-A;
  - D6B-1 a D6B-7: sequência 6B/6C/6D, migração por chamada explícita, ensaio com pagamentos, este anexo, numeração v11/v12, etiqueta experimental fora do repositório oficial e pendências registradas.

## 14. Pendências conhecidas (abertas; nenhuma resolvida nesta versão)

**Melhorias planejadas para a 6.13** (escopo indicado pela autora, sem obrigação de implementar cada item):
1. **D7 (Etapa 5B):** preservar o valor informado por abrangência coletiva diante de conversões posteriores (interação R5 → R3).
2. **D8 (Etapa 5B):** corrigir a frase "receberão este valor", que continua visível no diálogo "Mudar para valor fixo" quando a conversão está bloqueada pelo R4-A.
3. **"Valor pendente" em Início:** quebra em duas linhas e fica desalinhado, inclusive a 1000 px.
4. **Responsividade em 320 px:**
   - Ajustes mostra Nome e E-mail quebrados letra a letra;
   - "Cancela r";
   - os botões de tipo da Nova conta ("Úni ca", "Parcela da") e os filtros de status quebram;
   - os rótulos do Gráfico se sobrepõem;
   - textos e cartões de Início ficam cortados (itens F, G e H; parte disso já existia na 6.11).
5. **Diretriz aprovada:** um botão indisponível por condição conhecida fica cinza e desabilitado. Na 6.12 isso foi aplicado só em Aplicar (ajuste B) e em "Mudar para fixo" (R4-A); a padronização geral fica para a 6.13.
6. **P1:** a sessão cai se os dois "Cancelar" (o do diálogo "Configurar recorrência" e o da Nova conta) disparam no mesmo instante. Só acontece por roteiro automatizado. A proposta é rever o foco devolvido ao fechar o diálogo.
7. **P2:** "Registrar pagamento parcial" mostra "Valor da conta R$ 0,00" numa pendente, mas só quando a ação desativada é chamada por roteiro. O banco recusa o pagamento.

**Observações que ainda exigem análise ou decisão:**
8. **Duas contas no mesmo mês:** encerrar uma série que tem uma ocorrência futura editada (preservada) e depois transformar a avulsa em nova série pode deixar duas contas no mesmo mês. Isso também acontece na 6.11.
9. **Validação de nome e valor:** a camada de dados aceita nome vazio e valor negativo em `criar_conta_unica`; só o formulário recusa. É igual na 6.11.
10. **Enter no login:** o Enter não envia o login. Nenhum campo de texto tem envio pelo Enter, e é igual na 6.11.
11. **Categoria "Cartão de crédito":** aparece em Categorias sem o ícone de lixeira. Também está assim nas capturas da validação; sem diagnóstico conclusivo.
12. **Leitor de tela:** Orca e AT-SPI não foram testados.
13. **Comentário desatualizado:** a documentação interna de `preparar_banco` (`database/db.py`) ainda diz "schema atual (v10)". O código usa a v11; é só texto.

**Pendências técnicas, sem impacto funcional conhecido:**
- A tela Editar de recorrências grava campos e estrutura em duas transações, como na 6.11.
- `obter_identificacao` faz uma consulta a mais por linha de série em Início, com impacto no pior caso de desempenho (RNF06) não medido.
- Código legado mantido só para os testes: `_alterar_frequencia_serie_611`, `ocorrencias_futuras_com_pagamentos` e `MENSAGEM_VARIAVEL_NAO_MUDA_FREQUENCIA`.
- Não há gatilho em `pp_pagamentos` (seção 8).

**Reservado para a 6.14 (Supercontas, F1):** integração das Supercontas sobre estas regras, com descrição prevista de até 250 caracteres, a confirmar, e a decisão V12 (se as compras recorrentes podem ser variáveis). **Não iniciada.**

## 15. Divergências entre as fontes e como foram resolvidas

| Divergência | Resolução |
|---|---|
| R10 (06/11/2026) diz "sem reservar a v12 para comprovantes"; as decisões da autora de 08/11/2026 (D4 da Etapa 2 e D6B-5) reservam a v12 para Comprovantes e Remoções pendentes | Vale a decisão posterior. O texto original da R10 fica como histórico (seção 13). A v12 segue o princípio de 9.1: a numeração acompanha a ordem real de implementação |
| As pendências experimentais (seção 7) deixavam em aberto se "Mudar para valor fixo/variável" ficaria também nos Detalhes | Resolvido pelo ajuste D (D1 dos ajustes): o botão dos Detalhes foi retirado. O código confirma |
| As pendências experimentais (seção 8) registravam a mensagem `MENSAGEM_VALOR_COLETIVO_PARCELADA` como desatualizada ("nos detalhes da conta") | Corrigida na finalização experimental ("em Editar conta, no campo Recorrência"). O código e a validação da Etapa 5 confirmam |
| A documentação experimental (seção 7) situava "Alterar parcelamento" nos Detalhes | Substituído pelo ajuste A (Editar conta > Recorrência), como na seção 4 deste anexo |
| A documentação experimental (seção 13) dizia "validação manual não realizada" | Superado: três rodadas experimentais e a validação manual da integração (Etapa 5B, 24/24, aprovada pela autora em 08/11/2026) |

## 16. Validação (08/11/2026; não equivale a publicação)

**Testes técnicos (automatizados, só com bancos temporários ou fictícios):**
- suíte completa **1.894/1.894** (Etapa 3; repetida na Etapa 6B depois da documentação);
- ensaio da migração v10 → v11 numa cópia do banco pessoal, **38/38** (Etapa 4);
- ensaio da migração com pagamentos integrais, parciais, de saldo e estornados num banco v10 inteiramente fictício, criado pela 6.11: **27/27** (Etapa 6B);
- Etapa 5:
  - camada de dados, **87/87**;
  - roteiros gráficos, **185/185**, com 195 capturas em claro e escuro, de 320 a 1000 px;
  - módulos de acessibilidade e legibilidade, **119/119**.

**Aprovação manual da autora:** **24/24** verificações aprovadas em 08/11/2026, na sessão manual com banco fictício (Etapa 5B), com mouse e teclado reais.

**Não realizado até esta data:**
- integração na `main`;
- migração do banco pessoal (prevista por chamada explícita a `migrar_schema_v11`, D6B-2);
- publicação no GitHub;
- etiqueta de versão.
