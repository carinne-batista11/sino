# Desempenho da v6.0 — RNF03 e RNF06

Medição de 04/10/2026, no encerramento da v6.0 para portfólio. Situação geral na
[ERS v6.0, seção 13.6](ERS_Controle_de_Contas_v6.0.md#136-encerramento-da-v60-para-portfólio-04102026).

## Critérios da ERS

| Requisito | Texto | Critério usado aqui |
|---|---|---|
| RNF03 | Desempenho satisfatório com até 1000 contas por usuário (inclui a Tela Principal sem limite de contas). | A ERS não define "satisfatório"; foi usado o limite do RNF06 com 1.000 contas. |
| RNF06 | Operações comuns em até 2 segundos. | Cada operação medida abaixo de 2 s, inclusive no tempo máximo observado. |

## Ambiente

| Item | Valor |
|---|---|
| Computador | Intel Core i7-6500U (2,50 GHz), 4 núcleos lógicos, 16 GB de RAM |
| Sistema | Linux 6.8.0 (x86_64), disco ext4 |
| Software | Python 3.11.0, Flet 0.86.5, SQLite 3.37.2 |
| Código | commit `98a936f` (a correção posterior da inicial das categorias, RNF09, não altera as operações medidas) |

## Método

Script reprodutível [`tests/medir_desempenho.py`](../tests/medir_desempenho.py), fora da suíte de testes:

```bash
.venv/bin/python tests/medir_desempenho.py --repeticoes 30 --json resultado.json
```

* **Banco descartável:** pasta temporária, com as mesmas guardas dos testes; o banco real e os backups nunca são abertos.
* **Dados (semente fixa, "hoje" = 15/09/2026):**
  * *distribuído*: 1 usuário e exatamente 1.000 contas: 10 séries mensais com término (36 ocorrências cada), 2 séries mensais sem término e contas únicas de jan/2025 a dez/2027, com ~30% pagas, ~25% com descrição e ~10% sem categoria;
  * *mês único* (pior caso da Tela Principal, que mostra todas as contas do mês, sem paginação): as 1.000 contas em setembro de 2026.
* **Medida:** `time.perf_counter`, 1 execução de aquecimento e 30 medidas por operação. Tempos em milissegundos; "p95" é o 28º de 30 valores ordenados.
* **Duas camadas:**
  * *dados*: funções de `database/db.py` usadas pelas telas;
  * *tela*: o fluxo real de `backend/main.py` com a página falsa dos testes, ou seja, consulta ao banco e montagem dos controles da tela, sem a janela.

## Resultados

**Cenário distribuído (1.000 contas)**

| Operação | Mediana | p95 | Máximo |
|---|---:|---:|---:|
| dados: login (PBKDF2) | 148,3 | 154,3 | 157,7 |
| dados: contas do mês | 0,7 | 0,8 | 1,0 |
| dados: contas atrasadas | 1,7 | 2,9 | 3,5 |
| dados: próximos 7 dias | 0,6 | 0,9 | 1,1 |
| dados: gastos por categoria (ano) | 0,8 | 0,9 | 1,1 |
| dados: totais por ano | 0,8 | 1,0 | 1,4 |
| dados: criar conta única | 13,5 | 14,6 | 56,4 |
| dados: marcar e desmarcar como paga | 17,3 | 18,0 | 52,8 |
| dados: editar série (este mês em diante) | 9,9 | 10,3 | 25,2 |
| dados: excluir conta única | 12,8 | 13,6 | 14,0 |
| tela: entrar e montar a Tela Principal | 192,9 | 223,1 | 349,9 |
| tela: voltar ao Início | 45,8 | 51,1 | 127,7 |
| tela: próximo mês (gera ocorrências sob demanda) | 33,9 | 37,7 | 130,1 |
| tela: Ver status + filtro Atrasadas | 42,4 | 47,2 | 162,1 |
| tela: abrir Detalhes (série) | 7,9 | 9,1 | 10,4 |
| tela: Detalhes → Editar | 3,7 | 5,2 | 6,0 |
| tela: Gráfico mensal | 18,5 | 20,5 | 22,1 |
| tela: Gráfico anual | 11,9 | 14,1 | 21,6 |
| tela: Categorias | 10,6 | 11,7 | 12,4 |

**Pior caso: 1.000 contas no mesmo mês**

| Operação | Mediana | p95 | Máximo |
|---|---:|---:|---:|
| tela: entrar e montar a Tela Principal (1.000 linhas) | 598,0 | 1.122,9 | 1.271,7 |
| tela: Ver status + filtro Pendentes | 506,9 | 535,9 | 1.697,3 |
| tela: Gráfico mensal | 102,8 | 109,9 | 114,0 |

## Leitura

* Na camada medida (banco + montagem da tela no Python), **todas as operações ficaram abaixo de 2 s**, inclusive no tempo máximo.
* No cenário distribuído, o maior tempo foi o da entrada (máximo de 0,35 s), dominado pela verificação da senha (PBKDF2, ~0,15 s, intencional).
* No pior caso extremo (1.000 contas num único mês), a margem é pequena: máximo de **1,70 s** em Ver status e 1,27 s na Tela Principal.

## Limites da medição

* **Não medido:** a renderização da janela pelo Flutter e a troca de mensagens entre o Python e a janela do Flet. O tempo percebido na janela real pode ser maior que o da tabela.
* Uma única máquina, sem carga concorrente controlada; os números servem de referência, não de garantia.
* Por isso, RNF03 e RNF06 estão **atendidos na camada medida**, sem declaração de atendimento integral.

## Observação visual (não substitui a medição)

Em 04/10/2026, a autora navegou numa cópia isolada do app com um banco descartável de 1.000 contas (cenário distribuído), passando por Início, mês seguinte, Ver status e Gráfico (Mensal e Anual). Não houve demora perceptível nem travamento. É uma impressão qualitativa, sem cronometragem.
