
# Especificação de Requisitos de Software (ERS)

## Projeto: Aplicativo de Controle de Contas

**Autora:** Carinne Batista
**Versão:** 2.0
**Data original:** 28 de julho de 2025
**Data da revisão:** 3 de agosto de 2026

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

---

## 1.2 Escopo

O sistema será um aplicativo de uso pessoal, onde cada conta cadastrada estará vinculada a um único usuário.

A primeira versão terá como foco o controle financeiro básico, com:

* Armazenamento local dos dados;
* Interface simples e intuitiva;
* Controle de contas pessoais;
* Gerenciamento de categorias.

Funcionalidades como sincronização em nuvem, notificações, exportação de arquivos e integrações externas serão consideradas para versões futuras.

---

# 2. Perfis de Usuário

## 2.1 Usuário Visitante

Usuário que ainda não possui acesso autenticado ao sistema.

### Permissões:

* Criar uma conta de acesso;
* Realizar login no sistema.

---

## 2.2 Usuário Autenticado

Usuário que realizou login no sistema.

### Permissões:

* Cadastrar contas financeiras;
* Editar contas cadastradas;
* Excluir contas;
* Marcar contas como pagas;
* Criar e gerenciar categorias;
* Filtrar e visualizar contas;
* Consultar total de gastos mensais.

---

# 3. Requisitos Funcionais

| ID   | Descrição                                                                                                                                              |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| RF01 | Permitir a criação de conta de usuário com login e senha.                                                                                              |
| RF02 | Permitir o login do usuário no sistema.                                                                                                                |
| RF03 | Associar todas as contas financeiras cadastradas ao usuário logado.                                                                                    |
| RF04 | Permitir o cadastro de novas contas informando nome, valor, data de vencimento e categoria.                                                            |
| RF05 | Listar todas as contas cadastradas pelo usuário logado.                                                                                                |
| RF06 | Permitir marcar uma conta como paga ou pendente.                                                                                                       |
| RF07 | Permitir a edição de uma conta existente.                                                                                                              |
| RF08 | Permitir a exclusão de uma conta.                                                                                                                      |
| RF09 | Permitir filtrar contas por status (pago, pendente, atrasado) e por proximidade do vencimento.                                                         |
| RF10 | Permitir marcar uma conta como fixa (recorrente), definindo mês/ano final de repetição.                                                                |
| RF11 | Exibir contas vencidas e próximas do vencimento em destaque.                                                                                           |
| RF12 | Calcular e exibir o valor total das contas de um mês específico, permitindo filtrar por status.                                                        |
| RF13 | Atualizar automaticamente o status de uma conta para "atrasada" quando a data de vencimento for anterior à data atual e o status ainda for "pendente". |
| RF14 | Permitir criar, editar, excluir e associar categorias às contas cadastradas.                                                                           |

---

# 4. Requisitos Não Funcionais

| ID    | Descrição                                                                                                                       |
| ----- | ------------------------------------------------------------------------------------------------------------------------------- |
| RNF01 | A interface deve ser simples, responsiva e utilizável em diferentes tamanhos de tela.                                           |
| RNF02 | O armazenamento dos dados deve ser local nesta primeira versão.                                                                 |
| RNF03 | O sistema deverá manter desempenho satisfatório para até 1000 contas cadastradas por usuário.                                   |
| RNF04 | A aplicação deve ser leve, de fácil instalação e acesso.                                                                        |
| RNF05 | As senhas devem ser armazenadas de forma segura utilizando hash com salt, nunca em texto puro.                                  |
| RNF06 | Operações comuns como cadastro, edição, consulta e exclusão devem ser concluídas em até 2 segundos em condições normais de uso. |
| RNF07 | O sistema deve manter cópia de segurança local dos dados, evitando perda de informações em caso de falha.                       |

---

# 5. Regras de Negócio

* Apenas usuários autenticados podem cadastrar, editar ou excluir contas.
* Cada conta cadastrada está vinculada a um único usuário.
* Contas fixas (recorrentes) são replicadas mensalmente até o mês final informado em `repetir_ate`.
* A data de vencimento deve seguir o formato `AAAA-MM-DD`.
* Contas vencidas com status "pendente" e data de vencimento anterior à data atual devem ser destacadas visualmente.
* O status "atrasado" é calculado automaticamente pelo sistema e nunca definido manualmente pelo usuário.
* Os únicos status editáveis manualmente são:

  * `pago`
  * `pendente`
* Uma conta pode pertencer a apenas uma categoria por vez.
* A exclusão de uma categoria não deve excluir as contas associadas. Essas contas permanecerão sem categoria.

---

## 5.1 Sobre a Recorrência de Contas Fixas

Ao marcar uma conta como fixa, o sistema deverá gerar automaticamente uma ocorrência para cada mês, desde o mês de cadastro até o mês definido no campo `repetir_ate`.

Cada ocorrência será armazenada como um registro independente.

Isso permite que cada mês possa ser alterado individualmente sem afetar as demais ocorrências.

### Exemplo:

Uma conta de aluguel cadastrada como fixa:

* Janeiro: R$ 1.000,00
* Fevereiro: R$ 1.000,00
* Março: R$ 1.200,00

Caso o valor do aluguel aumente em março, somente a ocorrência daquele mês será alterada.

Essa abordagem evita dúvidas sobre edição de séries recorrentes, tratando cada mês como um registro próprio.

---

# 6. Modelagem de Dados

## 6.1 Entidade: Usuário

| Campo      | Tipo    | Descrição                                                        |
| ---------- | ------- | ---------------------------------------------------------------- |
| id         | Inteiro | Identificador único do usuário.                                  |
| nome       | Texto   | Nome do usuário.                                                 |
| email      | Texto   | E-mail utilizado para login (único).                             |
| senha_hash | Texto   | Hash da senha do usuário, nunca armazenando senha em texto puro. |

---

## 6.2 Entidade: Categoria

| Campo      | Tipo    | Descrição                                    |
| ---------- | ------- | -------------------------------------------- |
| id         | Inteiro | Identificador único da categoria.            |
| usuario_id | Inteiro | Referência ao usuário dono da categoria.     |
| nome       | Texto   | Nome da categoria (ex.: casa, saúde, lazer). |

---

## 6.3 Entidade: Conta

| Campo           | Tipo         | Descrição                                                                                   |
| --------------- | ------------ | ------------------------------------------------------------------------------------------- |
| id              | Inteiro      | Identificador único da conta.                                                               |
| usuario_id      | Inteiro      | Referência ao usuário dono da conta.                                                        |
| categoria_id    | Inteiro      | Referência à categoria da conta (opcional).                                                 |
| nome            | Texto        | Nome ou descrição da conta.                                                                 |
| valor           | Decimal      | Valor da conta em reais.                                                                    |
| data_vencimento | Data         | Data de vencimento no formato AAAA-MM-DD.                                                   |
| status          | Texto (enum) | Valores permitidos: `pago` ou `pendente`. O status `atrasado` é calculado pelo sistema.     |
| conta_fixa      | Inteiro      | `1` para conta fixa/recorrente e `0` para conta comum.                                      |
| repetir_ate     | Texto        | Mês e ano limite da repetição no formato AAAA-MM. Aplicável apenas quando `conta_fixa = 1`. |

---

## Alterações importantes do modelo

Em relação à versão anterior:

* O campo `status_pagamento` foi substituído por `status`, permitindo os valores:

  * `pago`
  * `pendente`

* O estado `atrasado` deixou de ser armazenado diretamente e passou a ser calculado pelo sistema.

* Foram adicionados:

  * `usuario_id`, para vincular contas ao usuário responsável;
  * `categoria_id`, para organização financeira por categorias.

---

# 7. Casos de Uso

## 7.1 Usuário Visitante

| Caso de Uso | Descrição                 |
| ----------- | ------------------------- |
| UC01        | Criar conta de acesso     |
| UC02        | Realizar login no sistema |

---

## 7.2 Usuário Autenticado

| Caso de Uso | Descrição                                             |
| ----------- | ----------------------------------------------------- |
| UC03        | Cadastrar conta financeira                            |
| UC04        | Visualizar lista de contas                            |
| UC05        | Editar conta existente                                |
| UC06        | Excluir conta                                         |
| UC07        | Marcar conta como paga                                |
| UC08        | Filtrar contas por status e proximidade do vencimento |
| UC09        | Criar, editar e excluir categorias                    |
| UC10        | Visualizar total de gastos do mês                     |

---

# 8. Interface (Protótipo)

A interface do sistema será desenvolvida com foco em simplicidade e facilidade de uso.

As principais telas previstas são:

## Tela de Login

Funcionalidades:

* Entrada de e-mail;
* Entrada de senha;
* Botão para acessar o sistema;
* Opção para criação de nova conta.

---

## Tela de Cadastro de Conta

Campos:

* Nome da conta;
* Valor;
* Data de vencimento;
* Categoria;
* Status;
* Opção de conta fixa;
* Data final da recorrência.

A tela deverá possuir botão para salvar o cadastro.

---

## Tela Principal

Funcionalidades:

* Listagem das contas cadastradas;
* Destaque para contas vencidas;
* Destaque para contas próximas do vencimento;
* Filtros por status;
* Consulta do total de gastos mensal.

---

# 9. Plano de Desenvolvimento

| Etapa                      | Status       | Observações                                                           |
| -------------------------- | ------------ | --------------------------------------------------------------------- |
| Análise de requisitos      | Concluída    | ERS elaborada e revisada.                                             |
| Modelagem de dados         | Concluída    | Definição das entidades Usuário, Conta e Categoria.                   |
| Protótipo da interface     | Em andamento | Desenvolvimento das telas e fluxo de navegação.                       |
| Codificação CRUD           | A fazer      | Implementação das operações de cadastro, consulta, edição e exclusão. |
| Testes                     | A fazer      | Testes das funcionalidades e regras de negócio.                       |
| Empacotamento/Distribuição | A fazer      | Criação da versão final da aplicação.                                 |

---

# 10. Casos de Teste

| ID   | Descrição                                                | Resultado Esperado                                                                     |
| ---- | -------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| CT01 | Cadastrar nova conta                                     | Conta salva com sucesso e vinculada ao usuário logado.                                 |
| CT02 | Marcar conta como paga                                   | Status atualizado para `pago`.                                                         |
| CT03 | Excluir conta                                            | Conta removida da listagem.                                                            |
| CT04 | Deixar uma conta pendente vencer sem marcar como paga    | Sistema exibe o status `atrasado` automaticamente, sem ação manual do usuário.         |
| CT05 | Cadastrar conta fixa com data final definida             | Sistema gera ocorrências mensais até o limite informado, permitindo edição individual. |
| CT06 | Consultar total do mês filtrando apenas contas pendentes | Sistema soma somente contas com status `pendente` ou `atrasado` daquele período.       |

---

# 11. Restrições do Projeto

Nesta primeira versão, o sistema seguirá as seguintes restrições:

| Item                         | Definição     |
| ---------------------------- | ------------- |
| Linguagem de desenvolvimento | Python        |
| Banco de dados               | SQLite        |
| Interface gráfica            | CustomTkinter |
| Tipo de aplicação            | Desktop       |
| Sistema de armazenamento     | Local         |
| Ambiente inicial             | Windows       |

---

# 12. Validações do Sistema

O sistema deverá aplicar as seguintes validações:

* O nome da conta é obrigatório.
* O valor da conta deve ser maior que zero.
* A data de vencimento deve ser informada obrigatoriamente.
* O formato da data deve seguir `AAAA-MM-DD`.
* O e-mail do usuário deve ser único.
* A senha deve ser armazenada utilizando hash com salt.
* O campo `repetir_ate` deve ser informado somente quando a conta for marcada como fixa.
* O período de repetição deve ser igual ou posterior ao mês de criação da conta.
* A categoria da conta é opcional.

---

# 13. Requisitos de Segurança

| ID    | Descrição                                                                              |
| ----- | -------------------------------------------------------------------------------------- |
| RNF08 | O sistema deve impedir que um usuário acesse informações pertencentes a outro usuário. |
| RNF09 | O sistema deve validar a autenticação antes de permitir operações financeiras.         |
| RNF10 | O sistema deve encerrar a sessão do usuário ao fechar a aplicação.                     |
| RNF11 | As informações financeiras devem permanecer protegidas contra acesso não autorizado.   |

---

# 14. Melhorias Futuras

Funcionalidades previstas para versões futuras:

* Notificações de contas próximas do vencimento;
* Configuração personalizada de alertas;
* Sincronização com armazenamento em nuvem;
* Exportação de dados em PDF ou Excel;
* Tema escuro;
* Gráficos de gastos mensais por categoria;
* Dashboard financeiro;
* Pesquisa por nome da conta;
* Ordenação por data de vencimento;
* Backup automático;
* Importação de dados;
* Sincronização entre dispositivos.

---

# 15. Anexos

Documentos complementares previstos:

* Diagrama Entidade-Relacionamento (DER);
* Diagrama de Casos de Uso (UML);
* Protótipos das telas;
* Capturas de tela da aplicação;
* Link do repositório GitHub.

---

# Histórico de Versões

| Versão | Data       | Alterações                                                                                                                              |
| ------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0    | 28/07/2025 | Primeira versão da especificação.                                                                                                       |
| 2.0    | 03/08/2026 | Revisão geral dos requisitos, inclusão de categorias, controle de usuário, status automático de atraso, backup e melhorias estruturais. |

---


