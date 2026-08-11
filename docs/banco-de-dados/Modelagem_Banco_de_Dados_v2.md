# Modelagem de Banco de Dados

**Projeto: Sino — App de Controle de Contas**

*Versão 2.0 — revisada após avaliação técnica (restrições, índices, série de recorrência)*

---

# 1. Introdução

Este documento formaliza a modelagem do banco de dados do Sino, seguindo o processo clássico de projeto de banco de dados, partindo dos requisitos já definidos no ERS (v3) até chegar na implementação física em SQLite:

- **ERS** → já concluído (documento em separado, v3)
- **Modelo Conceitual** → visão de alto nível das entidades e relacionamentos, sem se preocupar com tipos de dados ou tecnologia
- **DER (Diagrama Entidade-Relacionamento)** → adiciona os atributos de cada entidade e as chaves
- **Modelo Lógico** → traduz o DER para tabelas relacionais (colunas, tipos genéricos, chaves primárias e estrangeiras)
- **Modelo Físico** → SQL específico do SGBD escolhido (SQLite), pronto para ser executado
- **Banco de Dados** → implementação real (arquivo `sino.db`, já em andamento no `database.py`)

---

# 2. Modelo Conceitual

O modelo conceitual identifica as entidades principais do sistema e como elas se relacionam entre si, sem entrar em detalhes de atributos ou implementação.

Ele responde à pergunta:

> "O que existe no sistema e como essas coisas se conectam?"

## 2.1 Entidades identificadas

- **USUÁRIO** — a pessoa que usa o aplicativo e possui login próprio.
- **CATEGORIA** — as pastas criadas pelo usuário para organizar as contas (ex.: casa, saúde, lazer).
- **CONTA** — cada conta a pagar cadastrada pelo usuário.

## 2.2 Relacionamentos identificados

- **USUÁRIO possui CATEGORIA** — um usuário pode ter zero ou várias categorias; cada categoria pertence a exatamente um usuário.
- **USUÁRIO possui CONTA** — um usuário pode ter zero ou várias contas; cada conta pertence a exatamente um usuário.
- **CATEGORIA classifica CONTA** — uma categoria pode classificar zero ou várias contas; uma conta pode ter zero ou uma categoria (é opcional, conforme a RN da seção 5 do ERS: contas sem categoria existem).

## 2.3 Cardinalidades, de forma explícita

Para não depender somente da leitura do diagrama, as cardinalidades de cada relacionamento (notação mínimo, máximo) ficam registradas aqui também:

| Relacionamento | Lado A | Lado B |
|---|---|---|
| USUÁRIO possui CATEGORIA | USUÁRIO: (0,N) | CATEGORIA: (1,1) |
| USUÁRIO possui CONTA | USUÁRIO: (0,N) | CONTA: (1,1) |
| CATEGORIA classifica CONTA | CATEGORIA: (0,N) | CONTA: (0,1) |

---

# 3. DER (Diagrama Entidade-Relacionamento)

O DER detalha o modelo conceitual, acrescentando os atributos de cada entidade e identificando as chaves primárias (PK) e estrangeiras (FK).

## 3.1 Resumo de atributos, PK e FK

| Entidade | Atributos | Chaves |
|---|---|---|
| **USUÁRIO** | `id`, `nome`, `email`, `senha_hash`, `termos_aceitos_em` | PK: `id` |
| **CATEGORIA** | `id`, `usuario_id`, `nome`, `icone` | PK: `id` · FK: `usuario_id → USUÁRIO` |
| **CONTA** | `id`, `usuario_id`, `categoria_id`, `serie_id`, `nome`, `valor`, `data_vencimento`, `status`, `conta_fixa`, `repetir_ate` | PK: `id` · FK: `usuario_id → USUÁRIO`, `categoria_id → CATEGORIA`, `serie_id → CONTA` (autorreferência) |

> **Observação:** `usuario_id` e `categoria_id` já aparecem como atributos de CONTA e CATEGORIA. Essas são as chaves estrangeiras que materializam os relacionamentos "possui" e "classifica" quando o modelo é traduzido para tabelas.
>
> O atributo `serie_id` é explicado na seção 4.5.

---

# 4. Modelo Lógico

O modelo lógico traduz o DER para uma estrutura de tabelas relacionais, com tipos de dados genéricos (ainda independentes do SGBD específico) e as regras de integridade (chaves, obrigatoriedade e unicidade).

## 4.1 Tabela: USUARIO

| Coluna | Tipo | Regras |
|---|---|---|
| **id** | INTEIRO | Chave primária, autoincremento |
| `nome` | TEXTO | Obrigatório |
| `email` | TEXTO | Obrigatório, único (não pode repetir) |
| `senha_hash` | TEXTO | Obrigatório (senha nunca em texto puro) |
| `termos_aceitos_em` | DATA/HORA | Obrigatório |

## 4.2 Tabela: CATEGORIA

| Coluna | Tipo | Regras |
|---|---|---|
| **id** | INTEIRO | Chave primária, autoincremento |
| `usuario_id` | INTEIRO | Chave estrangeira → USUARIO(`id`). Obrigatório. |
| `nome` | TEXTO | Obrigatório |
| `icone` | TEXTO | Opcional |

## 4.3 Tabela: CONTA

| Coluna | Tipo | Regras |
|---|---|---|
| **id** | INTEIRO | Chave primária, autoincremento |
| `usuario_id` | INTEIRO | Chave estrangeira → USUARIO(`id`). Obrigatório. |
| `categoria_id` | INTEIRO | Chave estrangeira → CATEGORIA(`id`). Opcional (pode ser nulo). |
| `serie_id` | INTEIRO | Chave estrangeira → a própria CONTA(`id`) (autorreferência). Opcional — só existe quando `conta_fixa = 1`. Ver seção 4.5. |
| `nome` | TEXTO | Obrigatório |
| `valor` | DECIMAL | Obrigatório |
| `data_vencimento` | DATA | Obrigatório, formato AAAA-MM-DD |
| `status` | TEXTO (enum) | `"pago"` ou `"pendente"`. `"Atrasado"` é calculado, não armazenado. |
| `conta_fixa` | INTEIRO (booleano) | `1` = fixa/recorrente, `0` = não fixa |
| `repetir_ate` | TEXTO | Mês/ano final (AAAA-MM). Só se aplica quando `conta_fixa = 1`. |

## 4.4 Normalização

As três tabelas já respeitam a **Terceira Forma Normal (3FN)**:

- cada coluna depende apenas da chave primária da própria tabela;
- não há dados repetidos entre tabelas;
- a categoria de uma conta é referenciada por `categoria_id`, não duplicada como texto;
- não existem dependências transitivas.

Isso evita inconsistências — por exemplo, se o nome de uma categoria for alterado, isso é feito em um único lugar (a tabela CATEGORIA), refletindo automaticamente em todas as contas associadas.

## 4.5 Identificador de série — resolvendo a recorrência (RF20)

O ERS v3 (RF20) define que, ao editar uma conta fixa, o usuário escolhe entre:

- **"somente este mês"**
- **"este mês em diante"**

A versão anterior deste documento não tinha nenhuma forma de agrupar, no banco, quais linhas da tabela CONTA pertencem à mesma conta fixa original.

Sem isso, a opção **"este mês em diante"** não tem como ser implementada como uma consulta SQL.

A solução adotada é o campo `serie_id`: um identificador compartilhado por todas as ocorrências geradas a partir da mesma conta fixa.

### Funcionamento

- Quando uma conta comum (não fixa) é criada: `serie_id` fica nulo.
- Quando uma conta fixa é criada: a primeira ocorrência é inserida, e o próprio `id` dessa primeira linha passa a ser usado como `serie_id` — nela mesma e em todas as ocorrências seguintes geradas para os meses futuros (até `repetir_ate`).
- Editar **"somente este mês"**:

```sql
UPDATE contas
SET ...
WHERE id = <id da ocorrência editada>;
