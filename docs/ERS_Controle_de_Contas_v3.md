# Especificação de Requisitos de Software (ERS)

## Projeto: Aplicativo de Controle de Contas

**Autora:** Carinne Batista
**Versão:** 3.0
**Data original:** 28 de julho de 2025
**Data desta revisão:** 9 de agosto de 2026
**Status:** Revisada com base nos protótipos de tela

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
| RF12 | Calcular e exibir o valor total das contas de um mês específico escolhido pelo usuário, com opção de considerar apenas contas pendentes, apenas pagas ou ambas.                                                                                                                           |
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

Os requisitos **RF01 a RF14** representam funcionalidades já previstas ou incorporadas nas revisões anteriores.

Os requisitos **RF15 a RF24** foram adicionados na versão 3.0 após a análise dos protótipos de tela, que revelaram novas necessidades funcionais.

Entre eles, destaca-se o **RF20**, que define explicitamente o comportamento da edição de contas fixas e resolve a ambiguidade existente nas versões anteriores sobre alterar apenas uma ocorrência ou toda a sequência futura.

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

### Alterações em relação às versões anteriores

Em relação à versão anterior do modelo:

* O campo `status_pagamento` foi substituído por `status`, permitindo os valores `pago` e `pendente`.
* O estado `atrasado` deixou de ser armazenado diretamente e passou a ser calculado pelo sistema.
* Foi adicionado o campo `usuario_id`, para vincular cada conta ao usuário responsável.
* Foi adicionado o campo `categoria_id`, para permitir a organização das contas por categoria.
* Foi adicionado o campo `termos_aceitos_em` à entidade Usuário para registrar o aceite dos Termos de Uso e da Política de Privacidade.
* Foi adicionado o campo `icone` à entidade Categoria para permitir a identificação visual das categorias.

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
* Visualizar detalhes de uma conta;
* Criar uma conta a partir de uma categoria;
* Visualizar gráficos financeiros.

---

# 8. Interface (Protótipo)

Os wireframes das telas principais já foram desenhados e validados. Todas seguem a mesma identidade visual do projeto **$ino**, com paleta verde/escura e componentes reutilizados entre as telas.

As principais telas previstas são:

### Login

* Acesso por e-mail e senha;
* Opção de login por biometria quando disponível.

### Criar Conta de Usuário

* Cadastro do usuário;
* E-mail;
* Senha;
* Aceite dos Termos de Uso e da Política de Privacidade.

### Tela Principal

* Saudação ao usuário;
* Total de gastos do mês;
* Resumo de contas pagas e pendentes;
* Resumo das contas com vencimento nos próximos 7 dias;
* Lista de contas;
* Navegação inferior.

### Nova Conta

* Nome da conta;
* Valor;
* Data de vencimento;
* Categoria;
* Status;
* Opção de conta fixa;
* Data final da recorrência;
* Configuração de lembrete.

### Categorias

* Lista de categorias;
* Ícone da categoria;
* Quantidade de contas por categoria;
* Total gasto por categoria.

### Categoria — Detalhe/Edição

* Edição do nome;
* Edição do ícone;
* Exclusão da categoria;
* Lista de contas associadas;
* Atalho para criação de nova conta com a categoria pré-preenchida.

### Detalhe/Edição de Conta

* Visualização dos dados da conta;
* Edição dos campos;
* Marcação da conta como paga;
* Exclusão da conta;
* Confirmação do escopo de alteração para contas fixas.

### Gráficos de Gastos

* Evolução dos gastos totais dos últimos 6 meses;
* Distribuição dos gastos do mês por categoria;
* Valor e percentual de cada categoria;
* Comparativo percentual entre o mês atual e o mês anterior.

### Pendente

Tela de **Ajustes**, contemplando:

* Perfil;
* Notificações padrão;
* Preferências;
* Informações sobre o aplicativo.

---

# 9. Plano de Desenvolvimento

| Etapa                               | Status       | Observações                                                                                |
| ----------------------------------- | ------------ | ------------------------------------------------------------------------------------------ |
| Análise de requisitos               | Concluída    | ERS elaborada e revisada.                                                                  |
| Modelagem de dados                  | Concluída    | Modelo revisado com `usuario_id`, `categoria_id`, `status`, `termos_aceitos_em` e `icone`. |
| Protótipo da interface              | Em andamento | Desenvolvimento e validação das telas e do fluxo de navegação.                             |
| Codificação CRUD                    | A fazer      | Implementação das operações de cadastro, consulta, edição e exclusão.                      |
| Implementação das regras de negócio | A fazer      | Recorrência, escopo de edição, cálculo de status e demais regras.                          |
| Implementação dos gráficos          | A fazer      | Evolução mensal, distribuição por categoria e comparativo mensal.                          |
| Testes                              | A fazer      | Testes das funcionalidades, regras de negócio e requisitos.                                |
| Empacotamento/Distribuição          | A fazer      | Criação da versão final da aplicação.                                                      |

---

# 10. Casos de Teste

| ID   | Descrição                                                                 | Resultado Esperado                                                                                                       |
| ---- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| CT01 | Cadastrar nova conta                                                      | Conta salva com sucesso e vinculada ao usuário logado.                                                                   |
| CT02 | Marcar conta como paga                                                    | Status atualizado para `pago`.                                                                                           |
| CT03 | Excluir conta                                                             | Conta removida da listagem.                                                                                              |
| CT04 | Deixar uma conta pendente vencer sem marcar como paga                     | O sistema exibe o status `atrasado` automaticamente, sem ação manual do usuário.                                         |
| CT05 | Cadastrar conta fixa com `repetir_ate` definido                           | O sistema gera uma ocorrência para cada mês até o mês limite, permitindo edição individual.                              |
| CT06 | Consultar total do mês filtrando apenas contas pendentes                  | O valor total exibido soma apenas as contas com status `pendente` ou `atrasado` daquele mês.                             |
| CT07 | Editar o valor de uma conta fixa escolhendo o escopo `este mês em diante` | A ocorrência editada e todas as futuras da mesma série são atualizadas; as ocorrências passadas mantêm o valor anterior. |
| CT08 | Editar o valor de uma conta fixa escolhendo o escopo `somente este mês`   | Apenas a ocorrência editada é alterada; ocorrências passadas e futuras da mesma série permanecem inalteradas.            |

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

# Histórico de Versões

| Versão | Data       | Alterações                                                                                                                                                                                                                                                                                                    |
| ------ | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0    | 28/07/2025 | Primeira versão da especificação.                                                                                                                                                                                                                                                                             |
| 2.0    | 03/08/2026 | Revisão geral dos requisitos, inclusão de categorias, controle de usuário, status automático de atraso, backup e melhorias estruturais.                                                                                                                                                                       |
| 3.0    | 09/08/2026 | Revisão baseada nos protótipos de tela. Inclusão de aceite dos Termos de Uso e Política de Privacidade, biometria opcional, resumo semanal, ícones de categorias, criação de contas a partir de categorias, definição do escopo de edição de contas recorrentes, gráficos financeiros e novos casos de teste. |
