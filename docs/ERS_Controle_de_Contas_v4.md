# Especificação de Requisitos de Software (ERS)

## Projeto: Aplicativo de Controle de Contas

**Autora:** Carinne Batista
**Versão:** 4.0
**Data original:** 28 de julho de 2025
**Data desta revisão:** 21 de agosto de 2026
**Status:** Revisão baseada na implementação da Tela Nova Conta e em decisões de regra de negócio sobre o Total do Mês (RF12) e contas atrasadas

---

## Nota da Versão 4.0

Esta versão **preserva integralmente** os requisitos da v3.0 (documento `ERS_Controle_de_Contas_v3.md`, mantido sem alterações para preservar o histórico de evolução do projeto). Nenhum requisito da v3.0 foi removido ou teve seu número reaproveitado. As mudanças desta revisão são:

1. **RF12 (revisado)** — o filtro do Total do Mês passa a ter três opções explícitas: **Todas**, **Pendentes** e **Pagas**, sendo que o filtro `Pendentes` soma contas `pendente` **e** `atrasado`. O valor principal exibido muda conforme o filtro selecionado. Ver seção **5.3**.
2. **RF25 (novo)** — seção independente **"Contas atrasadas"** na Tela Principal, que não depende do mês selecionado, com mensagem de estado vazio definida. Ver seção **5.3**.
3. **RF26 (novo)** — indicação **"Parcela X de Y"** para ocorrências de contas fixas na Tela Principal, conforme protótipo.
4. **Regra de negócio nova** — contas atrasadas permanecem vinculadas ao mês original de vencimento para fins de cálculo do Total do Mês e não são somadas ao total de nenhum mês posterior. Ver seção **5.3**.
5. **Rastreabilidade** — nova seção **13** consolida o estado de implementação (implementado / decidido / não implementado) de cada requisito funcional, incluindo a **Tela Nova Conta** (RF04, RF10) e suas validações, já implementadas e testadas.

---

# 1. Introdução

## 1.1 Objetivo

O objetivo deste sistema é oferecer ao usuário uma ferramenta simples para registrar e controlar suas contas pessoais, permitindo informar nome, valor, data de vencimento, status de pagamento e categoria.

O sistema permitirá:

* Cadastro de contas financeiras;
* Controle de contas fixas (recorrentes) com prazo de encerramento definido;
* Controle de acesso por login e senha;
* Visualização do total de gastos por mês;
* Organização das contas por categorias.

## 1.2 Escopo

O sistema será um aplicativo de uso pessoal, onde cada conta cadastrada estará vinculada a um único usuário.

A primeira versão terá como foco o controle financeiro básico, com:

* Armazenamento local dos dados;
* Interface simples e intuitiva;
* Controle de contas pessoais;
* Gerenciamento de categorias.

Funcionalidades como sincronização em nuvem, notificações, exportação de arquivos e integrações externas serão consideradas para versões futuras, conforme a seção **11 - Melhorias Futuras**.

---

# 2. Perfis de Usuário

## 2.1 Usuário Visitante

Usuário que ainda não possui acesso autenticado ao sistema.

### Permissões

* Criar uma conta de acesso;
* Realizar login no sistema.

## 2.2 Usuário Autenticado

Usuário que realizou login no sistema.

### Permissões

* Cadastrar contas financeiras;
* Editar contas cadastradas;
* Excluir contas;
* Marcar contas como pagas;
* Criar e gerenciar categorias;
* Filtrar e visualizar contas;
* Consultar total de gastos mensais.

---

# 3. Requisitos Funcionais

| ID   | Descrição                                                                                                                                                                                                                                                                                 |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RF01 | Permitir a criação de conta de usuário com login e senha.                                                                                                                                                                                                                                 |
| RF02 | Permitir o login do usuário no sistema.                                                                                                                                                                                                                                                   |
| RF03 | Associar todas as contas financeiras cadastradas ao usuário logado.                                                                                                                                                                                                                       |
| RF04 | Permitir o cadastro de novas contas, informando nome, valor, data de vencimento e categoria.                                                                                                                                                                                              |
| RF05 | Listar todas as contas cadastradas pelo usuário logado.                                                                                                                                                                                                                                   |
| RF06 | Permitir marcar uma conta como paga ou pendente.                                                                                                                                                                                                                                          |
| RF07 | Permitir a edição de uma conta existente.                                                                                                                                                                                                                                                 |
| RF08 | Permitir a exclusão de uma conta.                                                                                                                                                                                                                                                         |
| RF09 | Permitir filtrar as contas por status (`pago`, `pendente`, `atrasado`) e por proximidade do vencimento, em um número de dias definido pelo usuário.                                                                                                                                       |
| RF10 | Permitir marcar uma conta como fixa (recorrente), definindo o mês/ano final de repetição.                                                                                                                                                                                                 |
| RF11 | Exibir, destacadas, as contas vencidas e as contas próximas do vencimento.                                                                                                                                                                                                                |
| RF12 | **(revisado — v4.0)** Calcular e exibir o valor total das contas de um mês específico escolhido pelo usuário, permitindo alternar entre três filtros — **Todas**, **Pendentes** e **Pagas**. O filtro `Pendentes` deve considerar tanto contas `pendente` quanto `atrasado`. O valor principal exibido na tela deve mudar conforme o filtro selecionado. *(detalhado na seção 5.3)* |
| RF13 | Atualizar automaticamente o status de uma conta para `atrasado` quando a data de vencimento for anterior à data atual e o status ainda for `pendente`. Esse status não é definido manualmente pelo usuário.                                                                               |
| RF14 | Permitir criar, editar, excluir e associar categorias às contas cadastradas.                                                                                                                                                                                                              |
| RF15 | Exigir que o usuário aceite os Termos de Uso e a Política de Privacidade no momento do cadastro.                                                                                                                                                                                          |
| RF16 | Permitir login por biometria (impressão digital ou reconhecimento facial) quando o dispositivo suportar. A funcionalidade é opcional; o login por e-mail e senha continua disponível em qualquer caso.                                                                                    |
| RF17 | Exibir na tela principal um resumo das contas que vencem nos próximos 7 dias, com o total somado.                                                                                                                                                                                         |
| RF18 | Permitir associar um ícone a cada categoria, escolhido dentre um conjunto pré-definido.                                                                                                                                                                                                   |
| RF19 | Permitir criar uma nova conta diretamente a partir da tela de uma categoria, com o campo categoria já pré-preenchido.                                                                                                                                                                     |
| RF20 | Ao editar nome, valor ou data de uma conta fixa (recorrente), o sistema deve perguntar se a alteração se aplica apenas à ocorrência atual (`somente este mês`) ou à ocorrência atual e às futuras (`este mês em diante`). A opção `somente este mês` deve vir pré-selecionada por padrão. |
| RF21 | Exibir gráfico de evolução dos gastos totais dos últimos 6 meses.                                                                                                                                                                                                                         |
| RF22 | Exibir gráfico de distribuição dos gastos do mês por categoria, com valor e percentual de cada categoria.                                                                                                                                                                                 |
| RF23 | Exibir comparativo percentual entre o gasto do mês atual e o do mês anterior.                                                                                                                                                                                                             |
| RF24 | Permitir marcar uma conta como paga diretamente na tela de detalhe da conta, sem precisar voltar à listagem.                                                                                                                                                                              |
| RF25 | **(novo — v4.0)** Exibir na Tela Principal uma seção independente **"Contas atrasadas"**, que não depende do mês selecionado no seletor de mês e lista todas as contas do usuário com status calculado como `atrasado`. Quando não houver nenhuma conta atrasada, deve ser exibida uma mensagem de estado vazio positiva (ex.: "Todas as suas contas estão em dia!"). *(detalhado na seção 5.3)* |
| RF26 | **(novo — v4.0)** Exibir, para ocorrências de contas fixas (recorrentes) na Tela Principal, a indicação de posição na série no formato **"Parcela X de Y"**, conforme o protótipo da Tela Principal.                                                                                     |

Os requisitos **RF01 a RF14** representam funcionalidades já previstas ou incorporadas nas revisões anteriores.

Os requisitos **RF15 a RF24** foram adicionados na versão 3.0 após a análise dos protótipos de tela, que revelaram novas necessidades funcionais.

Entre eles, destaca-se o **RF20**, que define explicitamente o comportamento da edição de contas fixas e resolve a ambiguidade existente nas versões anteriores sobre alterar apenas uma ocorrência ou toda a sequência futura.

Os requisitos **RF25 e RF26** foram adicionados na versão 4.0, a partir de uma revisão de regras de negócio da Tela Principal realizada após a implementação da Tela Nova Conta. O **RF12** também foi revisado nesta versão: sua redação original já previa uma "opção de considerar apenas contas pendentes, apenas pagas ou ambas", mas não detalhava o mecanismo; a v4.0 formaliza que o filtro tem exatamente três opções (Todas, Pendentes, Pagas) e que altera um único valor principal exibido — comportamento que já era indicado, de forma menos explícita, pelo caso de teste **CT06** desde a versão 3.0.

O estado de implementação de cada requisito, incluindo os já entregues na Tela Nova Conta, está consolidado na seção **13 — Rastreabilidade e Estado de Implementação**.

---

# 4. Requisitos Não Funcionais

| ID    | Descrição                                                                                                                        |
| ----- | -------------------------------------------------------------------------------------------------------------------------------- |
| RNF01 | A interface deve ser simples, responsiva e utilizável em telas de diferentes tamanhos.                                           |
| RNF02 | O armazenamento dos dados deve ser local nesta primeira versão.                                                                  |
| RNF03 | O sistema deverá manter desempenho satisfatório para até 1000 contas cadastradas por usuário.                                    |
| RNF04 | A aplicação deve ser leve, de fácil instalação e acesso.                                                                         |
| RNF05 | As senhas devem ser armazenadas de forma segura utilizando hash com salt, nunca em texto puro.                                   |
| RNF06 | Operações comuns como cadastro, edição, consulta e exclusão devem ser concluídas em até 2 segundos em condições normais de uso.  |
| RNF07 | O sistema deve manter cópia de segurança (backup) local dos dados, evitando perda de informações em caso de falha do aplicativo. |

---

# 5. Regras de Negócio

* Apenas usuários autenticados podem cadastrar, editar ou excluir contas.
* Cada conta cadastrada está vinculada a um único usuário.
* Contas fixas (recorrentes) são replicadas mensalmente até o mês final informado em `repetir_ate`.
* A data de vencimento deve seguir o formato `AAAA-MM-DD`.
* Contas vencidas, com status `pendente` e data de vencimento anterior à data atual, devem ser destacadas visualmente na listagem.
* O status `atrasado` é sempre calculado pelo sistema e nunca definido manualmente pelo usuário.
* Os únicos status editáveis manualmente são `pago` e `pendente`.
* Uma conta só pode pertencer a uma categoria por vez.
* A exclusão de uma categoria não deve excluir as contas associadas. Essas contas permanecerão sem categoria.

## 5.1 Sobre a Recorrência de Contas Fixas

Ao marcar uma conta como fixa, o sistema deverá gerar automaticamente uma ocorrência para cada mês, desde o mês de cadastro até o mês definido no campo `repetir_ate`.

Cada ocorrência será armazenada como um registro independente.

Isso permite que cada mês possa ser alterado individualmente sem afetar as demais ocorrências.

### Exemplo

Uma conta de aluguel cadastrada como fixa:

* Janeiro: R$ 1.000,00
* Fevereiro: R$ 1.000,00
* Março: R$ 1.200,00

Caso o valor do aluguel aumente em março, somente a ocorrência daquele mês será alterada.

As ocorrências permanecem como registros independentes mesmo quando uma alteração é aplicada à ocorrência atual e às ocorrências futuras da mesma série.

Essa abordagem permite controlar cada ocorrência individualmente e, ao mesmo tempo, possibilita a aplicação de alterações futuras conforme definido na seção **5.2**.

## 5.2 Escopo de Edição de uma Conta Fixa

Sempre que o usuário alterar nome, valor ou data de vencimento de uma ocorrência pertencente a uma conta fixa, o sistema deverá exibir uma confirmação perguntando o escopo da alteração.

Serão apresentadas duas opções:

### Somente este mês

Apenas a ocorrência em edição será alterada.

As demais ocorrências, passadas e futuras, permanecerão com seus valores anteriores.

Esta será a opção padrão, pré-selecionada pelo sistema.

### Este mês em diante

A ocorrência em edição e todas as ocorrências futuras da mesma série serão atualizadas.

Serão consideradas futuras as ocorrências cuja `data_vencimento` seja igual ou posterior à ocorrência atual.

Ocorrências passadas não serão alteradas.

Essa confirmação será exibida somente para contas em que `conta_fixa = 1`.

Para contas não recorrentes, a alteração será salva diretamente, sem essa etapa adicional.

## 5.3 Total do Mês e Contas Atrasadas (decisões v4.0)

Esta seção formaliza as decisões de regra de negócio tomadas em revisão da Tela Principal realizada em agosto de 2026, complementando o **RF12** e introduzindo o **RF25**.

### Filtro do Total do Mês (RF12)

O "Total do Mês" exibido na Tela Principal possui três opções de filtro, mutuamente exclusivas:

* **Todas** — soma o valor de todas as contas com vencimento no mês selecionado, independentemente do status.
* **Pendentes** — soma apenas as contas com status `pendente` **ou** `atrasado` cujo vencimento seja no mês selecionado.
* **Pagas** — soma apenas as contas com status `pago` cujo vencimento seja no mês selecionado.

Ao trocar o filtro, **o valor principal exibido no card de total muda** de acordo com a opção escolhida. Não se trata de três valores fixos exibidos simultaneamente, e sim de um único valor que responde à seleção do usuário.

### Vínculo de Contas Atrasadas ao Mês Original

Uma conta vencida e ainda não paga (status calculado como `atrasado`) permanece vinculada ao mês do seu `data_vencimento` original para fins do Total do Mês. Seu valor **não** é somado ao total de nenhum mês posterior ao seu vencimento, mesmo enquanto ela continuar em aberto.

#### Exemplo

Uma conta de R$ 200,00 venceu em julho/2026 e não foi paga. Ao navegar até agosto/2026 no seletor de mês, essa conta:

* **não** aparece na lista de contas de agosto/2026;
* **não** é somada ao Total do Mês de agosto/2026, em nenhum dos três filtros;
* continua aparecendo, com valor de R$ 200,00, na lista e no Total do Mês de julho/2026 (filtro Pendentes ou Todas), e também na seção independente **"Contas atrasadas"** (RF25), até ser marcada como paga.

### Seção "Contas atrasadas" (RF25)

A seção **"Contas atrasadas"** é independente do mês selecionado no seletor de mês da Tela Principal, seguindo o mesmo princípio de independência já usado pelo resumo de contas que vencem em 7 dias (RF17). Ela lista todas as contas do usuário cujo status calculado seja `atrasado`, de qualquer mês.

Regras específicas dessa seção:

* Contas com status `pago` **nunca** aparecem nessa seção, mesmo que sua data de vencimento já tenha passado — por definição, uma conta paga não é uma conta atrasada.
* Quando não houver nenhuma conta atrasada, a seção exibe uma mensagem de estado vazio positiva, como **"Todas as suas contas estão em dia!"**, em vez de ficar oculta ou em branco.

---

# 6. Modelagem de Dados

## 6.1 Entidade: Usuário

| Campo               | Tipo      | Descrição                                                                                         |
| ------------------- | --------- | ------------------------------------------------------------------------------------------------- |
| `id`                | Inteiro   | Identificador único do usuário.                                                                   |
| `nome`              | Texto     | Nome do usuário.                                                                                  |
| `email`             | Texto     | E-mail utilizado para login. Deve ser único.                                                      |
| `senha_hash`        | Texto     | Hash da senha do usuário, nunca armazenando a senha em texto puro.                                |
| `termos_aceitos_em` | Data/Hora | Data e hora em que o usuário aceitou os Termos de Uso e a Política de Privacidade, conforme RF15. |

## 6.2 Entidade: Categoria

| Campo        | Tipo    | Descrição                                                                                |
| ------------ | ------- | ---------------------------------------------------------------------------------------- |
| `id`         | Inteiro | Identificador único da categoria.                                                        |
| `usuario_id` | Inteiro | Referência ao usuário dono da categoria.                                                 |
| `nome`       | Texto   | Nome da categoria (ex.: casa, saúde, lazer).                                             |
| `icone`      | Texto   | Identificador do ícone associado à categoria, escolhido dentre um conjunto pré-definido. |

## 6.3 Entidade: Conta

| Campo             | Tipo         | Descrição                                                                                     |
| ----------------- | ------------ | --------------------------------------------------------------------------------------------- |
| `id`              | Inteiro      | Identificador único da conta.                                                                 |
| `usuario_id`      | Inteiro      | Referência ao usuário dono da conta.                                                          |
| `categoria_id`    | Inteiro      | Referência à categoria da conta. Campo opcional.                                              |
| `nome`            | Texto        | Nome ou descrição da conta.                                                                   |
| `valor`           | Decimal      | Valor da conta em reais.                                                                      |
| `data_vencimento` | Data         | Data de vencimento da conta no formato `AAAA-MM-DD`.                                          |
| `status`          | Texto (enum) | Valores permitidos: `pago` ou `pendente`. O status `atrasado` é calculado pelo sistema.       |
| `conta_fixa`      | Inteiro      | `1` para conta fixa/recorrente e `0` para conta comum.                                        |
| `repetir_ate`     | Texto        | Mês e ano limite da repetição no formato `AAAA-MM`. Aplicável apenas quando `conta_fixa = 1`. |

A implementação atual acrescenta ainda o campo `serie_id` (auto-referência a `Conta`), usado para agrupar as ocorrências de uma mesma conta fixa — ver seção **13** para detalhes de rastreabilidade com o código.

### Alterações em relação às versões anteriores

Em relação à versão anterior do modelo:

* O campo `status_pagamento` foi substituído por `status`, permitindo os valores `pago` e `pendente`.
* O estado `atrasado` deixou de ser armazenado diretamente e passou a ser calculado pelo sistema.
* Foi adicionado o campo `usuario_id`, para vincular cada conta ao usuário responsável.
* Foi adicionado o campo `categoria_id`, para permitir a organização das contas por categoria.
* Foi adicionado o campo `termos_aceitos_em` à entidade Usuário para registrar o aceite dos Termos de Uso e da Política de Privacidade.
* Foi adicionado o campo `icone` à entidade Categoria para permitir a identificação visual das categorias.

### Notas de Implementação — v4.0

As decisões desta versão **não exigem alterações no schema do banco de dados**:

* O filtro do Total do Mês (RF12) e a seção "Contas atrasadas" (RF25) usam o `status` já calculado dinamicamente a partir de `data_vencimento` (ver RF13) — não é necessário nenhum campo novo.
* A indicação "Parcela X de Y" (RF26) pode ser calculada a partir da posição da ocorrência dentro de `serie_id` (ordenada por `data_vencimento`) e do total de ocorrências geradas para aquela série — também sem necessidade de campo novo.

---

# 7. Casos de Uso

## 7.1 Usuário Visitante

* Criar conta de acesso;
* Fazer login.

## 7.2 Usuário Autenticado

* Cadastrar conta;
* Visualizar lista de contas;
* Editar conta;
* Excluir conta;
* Marcar conta como paga;
* Filtrar contas por status e por proximidade do vencimento;
* Criar, editar e excluir categorias;
* Visualizar o total de gastos do mês;
* Selecionar o filtro do Total do Mês (Todas, Pendentes ou Pagas); *(novo — v4.0)*
* Consultar a seção de contas atrasadas; *(novo — v4.0)*
* Visualizar detalhes de uma conta;
* Criar uma conta a partir de uma categoria;
* Visualizar gráficos financeiros.

---

# 8. Interface (Protótipo)

Os wireframes das telas principais já foram desenhados e validados. Todas seguem a mesma identidade visual do projeto **$ino**, com paleta verde/escura e componentes reutilizados entre as telas.

Cada subseção abaixo indica também o **status de implementação** atual, para rastreabilidade (ver detalhamento por requisito na seção 13).

### Login

**Status: Implementado** (`backend/main.py`, `mostrar_tela_login`)

* Acesso por e-mail e senha;
* Opção de login por biometria quando disponível — **não implementado** (RF16, opcional).

### Criar Conta de Usuário

**Status: Implementado parcialmente** (mesmo fluxo de `mostrar_tela_login`, alternância cadastro/login)

* Cadastro do usuário;
* E-mail;
* Senha;
* Aceite dos Termos de Uso e da Política de Privacidade — o campo `termos_aceitos_em` é gravado automaticamente no momento do cadastro, mas a tela ainda não possui um checkbox de aceite explícito para o usuário.

### Tela Principal

**Status: Implementado parcialmente** (`backend/main.py`, `mostrar_tela_principal`)

* Saudação ao usuário — implementado;
* Total de gastos do mês — implementado; **filtro Todas/Pendentes/Pagas (RF12 revisado) ainda não implementado**;
* Resumo de contas pagas e pendentes — implementado;
* Resumo das contas com vencimento nos próximos 7 dias — implementado (RF17);
* Seção independente **"Contas atrasadas"**, com estado vazio — **não implementado** (RF25, novo na v4.0);
* Indicação **"Parcela X de Y"** para contas fixas — **não implementado** (RF26, novo na v4.0);
* Lista de contas — implementado (limitada às 5 mais urgentes do mês selecionado; link "Ver todas" ainda sem ação);
* Navegação inferior — implementado (abas "Gráfico" e "Ajustes" ainda sem destino).

### Nova Conta

**Status: Implementado** (`backend/main.py`, `mostrar_tela_nova_conta`, ligada ao FAB da Tela Principal)

* Nome da conta — implementado;
* Valor — implementado, com interpretação do padrão brasileiro de milhar/decimal (ex.: `1.234` → R$ 1.234,00);
* Data de vencimento — implementado (seletor de data);
* Categoria — implementado;
* Status — não é um campo do formulário: toda conta nova é criada com status `pendente`, conforme regra de negócio (seção 5);
* Opção de conta fixa — implementado;
* Data final da recorrência — implementado, com validação de que não seja anterior ao mês de vencimento;
* Configuração de lembrete — **não implementado** (fora do escopo desta etapa; não há campo correspondente no modelo de dados).

### Categorias

**Status: Implementado parcialmente** (`backend/main.py`, `mostrar_tela_categorias`)

* Lista de categorias — implementado;
* Ícone da categoria — implementado (RF18);
* Quantidade de contas por categoria — **não implementado**;
* Total gasto por categoria — **não implementado**.

### Categoria — Detalhe/Edição

**Status: Implementado parcialmente** (via diálogos na própria tela de Categorias, sem uma tela de detalhe dedicada)

* Edição do nome — implementado;
* Edição do ícone — implementado;
* Exclusão da categoria — implementado;
* Lista de contas associadas — **não implementado**;
* Atalho para criação de nova conta com a categoria pré-preenchida — **não implementado** (RF19).

### Detalhe/Edição de Conta

**Status: Não implementado** (próxima etapa planejada)

* Visualização dos dados da conta;
* Edição dos campos;
* Marcação da conta como paga;
* Exclusão da conta;
* Confirmação do escopo de alteração para contas fixas.

### Gráficos de Gastos

**Status: Não implementado**

* Evolução dos gastos totais dos últimos 6 meses;
* Distribuição dos gastos do mês por categoria;
* Valor e percentual de cada categoria;
* Comparativo percentual entre o mês atual e o mês anterior.

### Pendente

**Status: Não implementado**

Tela de **Ajustes**, contemplando:

* Perfil;
* Notificações padrão;
* Preferências;
* Informações sobre o aplicativo.

---

# 9. Plano de Desenvolvimento

| Etapa                               | Status       | Observações                                                                                                                                                                                             |
| ----------------------------------- | ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Análise de requisitos               | Concluída    | ERS elaborada e revisada.                                                                                                                                                                               |
| Modelagem de dados                  | Concluída    | Modelo revisado com `usuario_id`, `categoria_id`, `status`, `termos_aceitos_em` e `icone`. Nenhuma alteração de schema foi necessária para as decisões da v4.0.                                        |
| Protótipo da interface              | Em andamento | Desenvolvimento e validação das telas e do fluxo de navegação. Telas de Detalhe/Edição de Conta, Gráficos e Ajustes ainda pendentes.                                                                   |
| Codificação CRUD                    | Em andamento | Login/cadastro, CRUD de categorias e cadastro de contas (create) implementados e commitados. Edição e exclusão de contas via UI ainda a fazer (lógica de banco já existe).                             |
| Implementação das regras de negócio | Em andamento | Recorrência na criação de contas fixas, cálculo automático de status `atrasado` e validações da Tela Nova Conta implementados. Escopo de edição (RF20), filtro do Total do Mês (RF12) e seção de contas atrasadas (RF25) decididos, mas ainda não implementados. |
| Implementação dos gráficos          | A fazer      | Evolução mensal, distribuição por categoria e comparativo mensal.                                                                                                                                       |
| Testes                              | A fazer      | Testes automatizados ad hoc foram executados durante o desenvolvimento da Tela Nova Conta (parser de valor, validação de recorrência), mas ainda não há uma suíte de testes formal no repositório.     |
| Empacotamento/Distribuição          | A fazer      | Criação da versão final da aplicação.                                                                                                                                                                   |

---

# 10. Casos de Teste

| ID   | Descrição                                                                                                        | Resultado Esperado                                                                                                       | Status                                                              |
| ---- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| CT01 | Cadastrar nova conta                                                                                                | Conta salva com sucesso e vinculada ao usuário logado.                                                                   | Implementado e verificado (Tela Nova Conta)                          |
| CT02 | Marcar conta como paga                                                                                              | Status atualizado para `pago`.                                                                                           | Lógica de banco implementada; UI pendente (Detalhe/Edição de Conta)  |
| CT03 | Excluir conta                                                                                                       | Conta removida da listagem.                                                                                              | Lógica de banco implementada; UI pendente (Detalhe/Edição de Conta)  |
| CT04 | Deixar uma conta pendente vencer sem marcar como paga                                                               | O sistema exibe o status `atrasado` automaticamente, sem ação manual do usuário.                                         | Implementado e verificado                                            |
| CT05 | Cadastrar conta fixa com `repetir_ate` definido                                                                     | O sistema gera uma ocorrência para cada mês até o mês limite, permitindo edição individual.                              | Implementado e verificado (Tela Nova Conta)                          |
| CT06 | Consultar total do mês filtrando apenas contas pendentes                                                            | O valor total exibido soma apenas as contas com status `pendente` ou `atrasado` daquele mês.                             | Regra decidida (v4.0, ver 5.3); UI pendente                          |
| CT07 | Editar o valor de uma conta fixa escolhendo o escopo `este mês em diante`                                           | A ocorrência editada e todas as futuras da mesma série são atualizadas; as ocorrências passadas mantêm o valor anterior. | Lógica de banco implementada; UI pendente (Detalhe/Edição de Conta)  |
| CT08 | Editar o valor de uma conta fixa escolhendo o escopo `somente este mês`                                             | Apenas a ocorrência editada é alterada; ocorrências passadas e futuras da mesma série permanecem inalteradas.            | Lógica de banco implementada; UI pendente (Detalhe/Edição de Conta)  |
| CT09 | Consultar total do mês com o filtro "Todas" selecionado                                                             | O valor total exibido soma todas as contas do mês, independentemente do status.                                         | Regra decidida (v4.0, ver 5.3); UI pendente                          |
| CT10 | Consultar total do mês com o filtro "Pagas" selecionado                                                             | O valor total exibido soma apenas as contas com status `pago` daquele mês.                                              | Regra decidida (v4.0, ver 5.3); UI pendente                          |
| CT11 | Consultar o Total do Mês de um mês posterior ao vencimento de uma conta atrasada ainda em aberto                    | O valor da conta atrasada não é somado ao Total do Mês do mês posterior, em nenhum dos três filtros.                     | Regra decidida (v4.0, ver 5.3); UI pendente                          |
| CT12 | Consultar a seção "Contas atrasadas" com uma conta vencida e não paga de um mês anterior ao mês selecionado         | A conta aparece na seção "Contas atrasadas", independentemente do mês selecionado no seletor.                            | Regra decidida (v4.0, ver 5.3); UI pendente (RF25)                   |
| CT13 | Consultar a seção "Contas atrasadas" sem nenhuma conta atrasada cadastrada                                          | O sistema exibe a mensagem "Todas as suas contas estão em dia!" em vez de uma lista vazia.                               | Regra decidida (v4.0, ver 5.3); UI pendente (RF25)                   |
| CT14 | Consultar a seção "Contas atrasadas" com uma conta paga cuja data de vencimento já passou                          | A conta não aparece na seção "Contas atrasadas".                                                                         | Regra decidida (v4.0, ver 5.3); UI pendente (RF25)                   |
| CT15 | Visualizar na Tela Principal uma ocorrência de conta fixa gerada a partir de uma série                              | O sistema exibe "Parcela X de Y", em que X é a posição da ocorrência na série e Y é o total de ocorrências da série.     | Decidido (v4.0); UI pendente (RF26)                                   |
| CT16 | Cadastrar uma conta pela Tela Nova Conta informando o valor `1.234`                                                 | A conta é salva com valor R$ 1.234,00 (ponto interpretado como separador de milhar, não decimal).                       | Implementado e verificado (testes automatizados + manual)            |
| CT17 | Marcar "conta fixa" na Tela Nova Conta e informar em "Repetir até" um mês/ano anterior ao mês da data de vencimento | O sistema exibe mensagem de erro e não salva a conta.                                                                    | Implementado e verificado (testes automatizados + manual)            |

---

# 11. Melhorias Futuras

Funcionalidades previstas para versões futuras:

* Notificações de contas próximas do vencimento;
* Configuração personalizada de alertas;
* Sincronização com armazenamento em nuvem;
* Exportação de dados em PDF ou Excel;
* Tema escuro;
* Dashboard financeiro;
* Pesquisa por nome da conta;
* Ordenação por data de vencimento;
* Backup automático;
* Importação de dados;
* Sincronização entre dispositivos.

---

# 12. Anexos

Documentos complementares:

* Capturas de tela;
* Protótipos das telas;
* Diagrama Entidade-Relacionamento (DER);
* Diagrama de Casos de Uso (UML);
* Link do repositório GitHub.

---

# 13. Rastreabilidade e Estado de Implementação (v4.0)

Esta seção consolida, para cada requisito funcional, seu status atual de implementação, a evidência no código (quando aplicável), o protótipo relacionado e os casos de teste associados. O objetivo é evitar que qualquer funcionalidade já implementada seja tratada como futura, e vice-versa.

**Legenda de status:** Implementado · Implementado (parcial) · Suporte de banco implementado — UI pendente · Decidido (v4.0) — não implementado · Não implementado.

| RF   | Descrição resumida                                    | Status                                            | Evidência no código                                                                 | Protótipo relacionado             | CTs relacionados     |
| ---- | ------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------- | ---------------------- |
| RF01 | Criar conta de usuário                                   | Implementado                                       | `mostrar_tela_login` (modo cadastro); `database.criar_usuario`                       | Criar Conta de Usuário             | —                       |
| RF02 | Login do usuário                                         | Implementado                                       | `mostrar_tela_login`; `database.verificar_login`                                     | Login                              | —                       |
| RF03 | Associar contas ao usuário logado                        | Implementado                                       | `usuario_id` em todas as consultas de `database/db.py`                               | —                                   | CT01                    |
| RF04 | Cadastro de novas contas                                 | Implementado                                       | `mostrar_tela_nova_conta`; `database.criar_conta`                                    | Nova Conta                         | CT01, CT16              |
| RF05 | Listar todas as contas do usuário                        | Implementado (parcial)                             | `mostrar_tela_principal` (`atualizar_dados`) — só as 5 mais urgentes do mês           | Tela Principal                     | —                       |
| RF06 | Marcar conta como paga/pendente                          | Suporte de banco implementado — UI pendente        | `database.marcar_conta_como_paga`                                                    | Detalhe/Edição de Conta            | CT02                    |
| RF07 | Editar conta existente                                   | Suporte de banco implementado — UI pendente        | `database.editar_conta_ocorrencia`, `database.editar_conta_serie`                    | Detalhe/Edição de Conta            | CT07, CT08              |
| RF08 | Excluir conta                                             | Suporte de banco implementado — UI pendente        | `database.excluir_conta`, `database.excluir_conta_serie`                             | Detalhe/Edição de Conta            | CT03                    |
| RF09 | Filtrar por status e proximidade configurável             | Não implementado                                   | —                                                                                     | —                                   | —                       |
| RF10 | Conta fixa/recorrente com mês/ano final                   | Implementado                                       | `mostrar_tela_nova_conta` (switch + "Repetir até", validado); `database.criar_conta` | Nova Conta                         | CT05, CT17              |
| RF11 | Destacar contas vencidas e próximas do vencimento          | Implementado (parcial)                             | `linha_conta`, `banner_semana` em `mostrar_tela_principal`                            | Tela Principal                     | CT04                    |
| RF12 | Total do mês com filtro Todas/Pendentes/Pagas              | Decidido (v4.0) — não implementado                 | hoje exibe total, pago e pendente simultaneamente, sem filtro seletivo               | Tela Principal                     | CT06, CT09, CT10, CT11  |
| RF13 | Status `atrasado` calculado automaticamente               | Implementado                                       | `database.listar_contas`, `database.listar_contas_proximas`                          | —                                   | CT04                    |
| RF14 | CRUD de categorias                                        | Implementado                                       | `mostrar_tela_categorias`; `database.criar_categoria/editar_categoria/excluir_categoria` | Categorias                       | —                       |
| RF15 | Aceite dos Termos de Uso no cadastro                       | Implementado (parcial)                             | `database.criar_usuario` grava `termos_aceitos_em`; sem checkbox de aceite na UI      | Criar Conta de Usuário             | —                       |
| RF16 | Login por biometria (opcional)                             | Não implementado                                   | —                                                                                     | Login                              | —                       |
| RF17 | Resumo de contas que vencem em 7 dias                      | Implementado                                       | `database.listar_contas_proximas`; `banner_semana`                                   | Tela Principal                     | —                       |
| RF18 | Ícone por categoria                                        | Implementado                                       | campo `icone` em `categorias`; `mostrar_tela_categorias`                             | Categorias                         | —                       |
| RF19 | Criar conta a partir de uma categoria (pré-preenchida)      | Não implementado                                   | —                                                                                     | Categoria — Detalhe/Edição         | —                       |
| RF20 | Escopo de edição de conta fixa                             | Suporte de banco implementado — UI pendente        | `database.editar_conta_ocorrencia/editar_conta_serie`, campo `serie_id`              | Detalhe/Edição de Conta            | CT07, CT08              |
| RF21 | Gráfico de evolução dos últimos 6 meses                    | Não implementado                                   | —                                                                                     | Gráficos de Gastos                 | —                       |
| RF22 | Gráfico de distribuição por categoria                      | Não implementado                                   | —                                                                                     | Gráficos de Gastos                 | —                       |
| RF23 | Comparativo percentual mês atual x anterior                | Não implementado                                   | —                                                                                     | Gráficos de Gastos                 | —                       |
| RF24 | Marcar conta como paga na tela de detalhe                  | Não implementado                                   | —                                                                                     | Detalhe/Edição de Conta            | —                       |
| RF25 | Seção "Contas atrasadas" independente do mês (novo)         | Decidido (v4.0) — não implementado                 | —                                                                                     | Tela Principal                     | CT12, CT13, CT14        |
| RF26 | "Parcela X de Y" em contas fixas na Tela Principal (novo)   | Decidido (v4.0) — não implementado                 | —                                                                                     | Tela Principal                     | CT15                    |

---

# Histórico de Versões

| Versão | Data       | Alterações                                                                                                                                                                                                                                                                                                    |
| ------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0    | 28/07/2025 | Primeira versão da especificação.                                                                                                                                                                                                                                                                             |
| 2.0    | 03/08/2026 | Revisão geral dos requisitos, inclusão de categorias, controle de usuário, status automático de atraso, backup e melhorias estruturais.                                                                                                                                                                       |
| 3.0    | 09/08/2026 | Revisão baseada nos protótipos de tela. Inclusão de aceite dos Termos de Uso e Política de Privacidade, biometria opcional, resumo semanal, ícones de categorias, criação de contas a partir de categorias, definição do escopo de edição de contas recorrentes, gráficos financeiros e novos casos de teste. |
| 4.0    | 21/08/2026 | Revisão baseada na implementação da Tela Nova Conta (RF04, RF10) e em decisões de regra de negócio sobre o Total do Mês e contas atrasadas: RF12 revisado com filtro Todas/Pendentes/Pagas; vínculo de contas atrasadas ao mês original de vencimento (sem migrar para totais posteriores); nova seção independente "Contas atrasadas" (RF25) com estado vazio definido; indicação de parcela em contas recorrentes na Tela Principal (RF26). Adiciona seção de rastreabilidade e estado de implementação (seção 13) e os casos de teste CT09–CT17. |
