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

## Atualização (24/10/2026): Sino 6.9, com a medição na janela real

Medição feita na rodada de melhorias pequenas da ERS v7.0 (RNF03 e RNF06), sobre o commit `2196d98` com a mudança local das setas de mês (RNF14), que não altera as operações medidas. O registro de 04/10/2026, acima, fica preservado.

### Ambiente

Mesmo computador e mesmo software do registro de 04/10/2026 (Intel Core i7-6500U, 4 núcleos lógicos, 16 GB de RAM; Linux 6.8.0, sessão X11; Python 3.11.0, Flet 0.86.5, SQLite 3.37.2).

### Método

* **Dados:** só bancos fictícios, com os dois cenários deste documento (1.000 contas *distribuídas* e 1.000 contas *num único mês*, mesma semente). O banco real e os backups não foram abertos.
* **Camada Python:** `tests/medir_desempenho.py --repeticoes 30` (mesmo método de 04/10/2026; a ferramenta só passou a localizar a seta "Próximo mês" pelo identificador `data`, por causa da mudança das setas).
* **Janela real:** uma cópia isolada do código (fora do projeto, numa pasta temporária, com o banco fictício no lugar do banco), aberta no cliente desktop do Flet. Um roteiro externo chama o `main.main` da cópia, sem alterar o app, e aciona, dentro do laço do Flet, entrar, "Próximo mês", "Mês anterior", Gráfico e Anual, com 4 a 5 s de intervalo. O serviço de códigos apontava para um endereço local inexistente, então nenhuma chamada saiu do computador. Duas medidas:
  * **sem tecnologia assistiva:** tempo do Python até o fim de `page.update()` e tempo até a resposta de uma chamada de ida e volta ao cliente (`StoragePaths`), que só chega depois de o cliente aplicar as mensagens anteriores. Não inclui o desenho do quadro pelo Flutter;
  * **com AT-SPI:** horário dos eventos de acessibilidade da janela (`object:children-changed`), do clique até o fim da sequência de eventos. É o mais perto do tempo percebido que foi possível medir, mas o próprio ouvinte consulta o app a cada evento e pode **inflar** o resultado quando há milhares de eventos.
* **Repetição:** cada ação da janela real foi medida **uma vez** por cenário. Os números servem de referência, não de estatística.

### Validade das rodadas

As duas primeiras rodadas da camada Python (24/10/2026, 14h01 e 14h05) foram **descartadas**: um cliente do Flet aberto antes, na verificação da RNF14, continuava rodando e ocupava cerca de 44% da CPU. Os resultados abaixo são da terceira rodada, com a máquina sem esse processo.

### Camada Python (página falsa dos testes)

| Operação | Mediana | p95 | Máximo |
|---|---:|---:|---:|
| tela: entrar e montar a Tela Principal | 179,6 | 186,0 | 203,9 |
| tela: próximo mês (gera ocorrências sob demanda) | 31,5 | 35,5 | 124,9 |
| tela: Ver status + filtro Atrasadas | 38,6 | 43,8 | 157,8 |
| tela: Gráfico mensal (inclui o comparativo da E12) | 22,5 | 25,7 | 25,9 |
| tela: Gráfico anual | 16,3 | 17,8 | 18,5 |
| mês único: entrar e montar a Tela Principal (1.000 linhas) | 529,3 | 965,8 | 1.661,6 |
| mês único: Ver status + filtro Pendentes | 472,4 | 478,6 | 490,3 |
| mês único: Gráfico mensal | 110,4 | 113,2 | 116,3 |

Tempos em milissegundos. Todas as operações medidas ficaram abaixo de 2 s, como em 04/10/2026; as operações de dados também (máximo de 140,8 ms, no login).

### Janela real

**Cenário distribuído (1.000 contas)**

| Ação | Python até `update()` | Ida e volta ao cliente | Fim dos eventos do AT-SPI |
|---|---:|---:|---:|
| entrar | 259 | 269 | 544 |
| próximo mês | 79–109 | 86–114 | 210–275 |
| mês anterior | 84–95 | 91–102 | — |
| Gráfico mensal | 98 | 108 | 368 |
| Gráfico anual | 87 | 96 | 237 |

**Pior caso: 1.000 contas no mês exibido**

| Ação | Python até `update()` | Ida e volta ao cliente | Fim dos eventos do AT-SPI |
|---|---:|---:|---:|
| entrar (1.000 linhas em Início) | **2.289** | **2.475** | cerca de 6.500 |
| próximo mês (sai do mês cheio) | 119 | 128 | 1.275 |
| mês anterior (volta ao mês cheio) | **2.134** | **2.348** | cerca de 5.000 |
| Gráfico mensal | 142 | 150 | 817 |
| Gráfico anual | 79 | 88 | 206 |

Tempos em milissegundos; "—" = não medido nessa rodada. As duas primeiras colunas vêm da rodada sem tecnologia assistiva, e a última, da rodada com o ouvinte do AT-SPI (mesmo banco e mesmo roteiro).

### Leitura

* **Cenário distribuído:** todas as ações ficaram abaixo de 0,6 s na janela real, inclusive com o AT-SPI. Para esse uso, o RNF06 está atendido também na janela.
* **Pior caso (1.000 contas num único mês):** **o RNF06 não é atendido na janela real** quando Início mostra as 1.000 contas (entrar e voltar ao mês cheio). Só o lado Python, com a página real, já passa de 2 s (2,1 a 2,3 s), antes de o Flutter desenhar a tela; com o AT-SPI, o fim dos eventos ficou entre 5 e 6,5 s, valor possivelmente inflado pelo ouvinte.
* **Diagnóstico (hipótese, não comprovada por perfil):** na página falsa, a mesma entrada leva de 0,5 a 1,7 s; na página real, cerca de 2,3 s. A diferença indica que o custo extra está em `page.update()`, ou seja, em transformar os cerca de 1.000 conjuntos de controles das linhas em mensagens para o cliente, além da montagem das linhas no Python. Gráficos e telas sem as 1.000 linhas não têm esse problema.
* **Soluções possíveis (não implementadas; dependem de decisão):** mostrar as contas de Início em partes ou com "Mostrar mais" (muda o RF05, que pede todas as contas do mês com rolagem normal); usar uma lista que só monta as linhas visíveis (exige avaliar o suporte do Flet 0.86.5 e o efeito na rolagem, no teclado e na acessibilidade); simplificar os controles de cada linha. Nenhuma é uma correção pequena.

### Limites

* Uma máquina, uma medida por ação na janela real, sem controle de carga concorrente (o navegador estava aberto).
* A ida e volta ao cliente não inclui o desenho do quadro; o tempo com AT-SPI inclui o custo do próprio ouvinte. O tempo percebido fica entre os dois.
* Não foram medidos: Ver status e Detalhes na janela real, nem o tema Escuro. Não houve cronometragem visual pela autora.
* Por isso: **RNF03 e RNF06 atendidos na camada Python e, na janela real, no cenário distribuído; não atendidos na janela real no pior caso de 1.000 contas num único mês.**

## Atualização (30/10/2026): Sino 6.10, com pagamentos parciais

Medição da Etapa 7B da Sino 6.10 (ainda não publicada), sobre o código da branch `integracao/sino-6.10` no commit `7b074f7`. Os registros de 04/10 e 24/10/2026, acima, ficam preservados.

### Ambiente

Mesmo computador e mesmo software (Intel Core i7-6500U, 4 núcleos lógicos, 16 GB de RAM; Linux 6.8.0, X11, disco ext4; Python 3.11.0, Flet 0.86.5, SQLite 3.37.2). Navegador aberto durante parte das rodadas; carga média entre 0,7 e 1,8; nenhum cliente do Flet esquecido em execução.

### Método

* **Ferramenta:** `tests/medir_desempenho.py` **não funciona com a v10**: a operação "marcar/desmarcar como paga" falha, porque marcar como paga passa a registrar um pagamento e desmarcar uma quitação registrada vira estorno (ERS v7.0, 5.54). O arquivo não foi alterado; as medições usaram um script **externo** ao projeto, que reaproveita a mesma classe de medição e as guardas dos testes (banco descartável; banco real e backups nunca abertos; "hoje" = 15/09/2026).
* **Perfil A (referência):** as mesmas 1.000 contas e a mesma semente de 04/10 e 24/10; as cerca de 30% pagas ficam pagas **sem** registro de pagamento, como um banco v9 migrado. Mesmo conteúdo das medições anteriores; a operação "marcar/desmarcar" foi trocada por "marcar como paga + desfazer (estorno)", que não é equivalente.
* **Perfil B (pagamentos parciais):** o perfil A mais 200 contas (20%), sorteadas entre as não pagas, com 1 a 3 pagamentos parciais cada (396 registros no cenário distribuído); **dentro** dessas 200, 50 contas (5% do total) com o último pagamento estornado.
* **Camada Python:** 1 aquecimento e 30 medições por operação, duas rodadas por perfil, e a ferramenta original da Sino 6.9.1 na mesma máquina e na mesma hora, como linha de base.
* **Janela real:** cópia isolada com banco fictício do perfil B, cliente desktop do Flet, roteiro externo; 3 repetições por ação; tempo do Python até o fim de `page.update()` e ida e volta ao cliente, como em 24/10 (sem AT-SPI).

### Camada Python (página falsa dos testes)

| Operação | Perfil A (mediana / máx.) | Perfil B (mediana / máx.) | 6.9.1 (mediana / máx.) |
|---|---:|---:|---:|
| tela: entrar e montar a Tela Principal | 204 / 282 | 204 / 274 | 172 / 215 |
| tela: Início (voltar) | 72 / 219 | 73 / 213 | 40 / 106 |
| tela: próximo mês | 42 / 205 | 43 / 199 | 31 / 34 |
| tela: Ver status + Atrasadas | 60 / 77 | 60 / 65 | 38 / 39 |
| tela: abrir Detalhes (conta com pagamentos no B) | 11 / 812 | 12 / 779 | — |
| tela: Detalhes → Editar | 5 / 8 | 5 / 6 | 3 / 3 |
| tela: prévia do saldo em Editar | 0,3 / 0,6 | 0,3 / 0,4 | — |
| tela: Gráfico mensal | 26 / 27 | 25 / 27 | 21 / 22 |
| dados: registrar pagamento parcial | 11 / 201 | 11 / 126 | — |
| dados: estornar pagamento | 10 / 190 | 88 / 178 | — |
| mês único: entrar (1.000 linhas), isolado | 536 / 1.049 | 544 / 1.053 | 502 / 946 |
| mês único: Ver status + Pendentes, isolado | 471 / 1.613 | 475 / 1.619 | 448 / 1.450 |

Tempos em milissegundos; menor mediana entre as rodadas e maior máximo observado. Na coluna da 6.9.1, os valores do mês único vêm da rodada completa da ferramenta original (não isolada). Na linha "Detalhes → Editar", a 6.9.1 mediu uma ocorrência de série. Todas as operações abaixo de 2 s.

* **Pico de 3,4 s descartado como artefato:** nas rodadas completas, "mês único: entrar" teve um máximo de cerca de 3,4 s (e "Ver status + Pendentes" de 2,3 s no perfil B). O diagnóstico mostrou que os picos coincidem com coletas completas do coletor de lixo do Python sobre objetos acumulados **pelo processo de medição**, que repete o login dezenas de vezes depois das outras operações; sem o coletor, nenhuma repetição passou de 0,55 s, e o padrão é o mesmo na 6.9.1. Medido num processo novo (linhas "isolado"), o máximo ficou em 1,05 s.
* Início, Ver status e próximo mês ficaram de 10 a 30 ms mais lentos na mediana que na 6.9.1 (hipótese, não confirmada por perfil: o cálculo do pago com os pagamentos parciais), dentro do limite.

### Janela real (perfil B)

| Ação | Distribuído (ida e volta, 3 medidas) | Mês único (ida e volta) |
|---|---:|---:|
| entrar | 274 | **2.150** |
| próximo mês | 88–108 | 25–127 |
| mês anterior (volta ao mês cheio no mês único) | 90–94 | **2.159** |
| abrir Detalhes (conta com pagamentos) | 24–31 | — |
| Detalhes → Editar | 23–32 | — |
| Gráfico mensal | 73–81 | 123–681 |
| Gráfico anual | 68–80 | 64–65 |

### Leitura

* **Cenário distribuído, com e sem pagamentos parciais:** RNF06 atendido na camada Python e na janela real (todas as ações abaixo de 0,3 s na janela).
* **Pior caso (1.000 contas num único mês):** continua **não atendido na janela real** (cerca de 2,15 s para entrar e para voltar ao mês cheio, contra 2,35–2,48 s em 24/10), a mesma limitação já registrada; tratamento pendente de decisão.
* **Limites:** uma máquina; 3 medidas por ação na janela real; o desenho do quadro pelo Flutter e o tema Escuro não foram medidos; comparações com 04/10 e 24/10 só como referência.
