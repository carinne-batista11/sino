# Sino 6.12 — encerramento da versão experimental (07/11/2026)

> *Atualização (08/11/2026):* este registro do encerramento experimental fica preservado como estava. As regras vigentes da 6.12 estão no anexo [sino-6.12-regras.md](sino-6.12-regras.md), com a situação da integração e da validação. Alguns itens abaixo foram superados depois, entre eles "Notas da versão sem seção da 6.12", a validação manual pendente e as regras "nas notas do ambiente experimental".

**Situação:** etapa funcional experimental **concluída**. Commit local e etiqueta `sino-6.12-experimental` existem
**só no clone experimental** (`/var/tmp/sino-612-20261106/app`, branch `experimental-6.12`, sem remoto).
**Não publicada** e **não integrada** à `main`. O banco pessoal **não** foi migrado. Este encerramento **não**
libera a versão para uso pessoal. A versão oficial continua sendo a **Sino 6.11**.

## Escopo da 6.12
- Tipos de conta: Única, Parcelada (2 a 36 parcelas), Recorrente mensal e anual.
- Parcelamentos: prévia, edição individual de parcelas e "Alterar parcelamento" (novo total e/ou quantidade).
  Só as parcelas livres são recalculadas; as que têm pagamento (inclusive estornado) e as editadas ficam como
  estão.
- Recorrências de **valor fixo** e de **valor variável**: ocorrências com "Valor pendente", pagamento bloqueado
  enquanto o valor estiver pendente, informar o valor da pendente.
- Conversão Fixo ↔ Variável (R3/R4, X3) com o bloqueio R4-A; Mensal ↔ Anual bloqueado (R6).
- Só a conta Única muda de tipo; encerrar e transformar são duas ações separadas (X1/X2).
- Schema **v11**, aditivo: `parcelamentos`, `series_valor_variavel`, `ocorrencias_valor_pendente`.
- Limite da descrição: **250 caracteres** (antes 1.000; ERS v7.0, 5.45, atualização de 07/11/2026).

## Ajustes depois da validação manual
| Item | Mudança |
|---|---|
| A | "Alterar parcelamento" saiu dos Detalhes e foi para **Editar conta → Recorrência** (só em parceladas); depois de aplicar, volta aos Detalhes |
| B | "Aplicar" fica cinza e desabilitado enquanto o recálculo é recusado |
| C / D2 | Série variável: alterar **só o valor** grava só a ocorrência, sem o diálogo de abrangência; com outros campos, o diálogo e a R5 continuam |
| D / D1 | Conversão Fixo ↔ Variável só em **Editar conta → Recorrência → "Alterar tipo de valor"**; botão dos Detalhes retirado |
| D3 | Aviso "Há alterações não salvas" antes das ações que gravam na hora |
| R4-A | "Mudar para fixo" cinza e desabilitado quando há ocorrência anterior pendente; o banco continua recusando |
| Texto | Mensagem do valor coletivo numa parcelada: "use “Alterar parcelamento” em Editar conta, no campo Recorrência" |
| Limite | Descrição de até 250 caracteres na criação e na edição, em todos os tipos e escopos; dado antigo acima do limite segue a P4. Nenhum registro excluído |

## Testes automatizados (bancos temporários, sem rede)
| Rodada | Resultado |
|---|---|
| Referência E0 / Etapa 12 | 1.615 / 1.849 |
| Ajustes A–D (2ª execução) | 1.872/1.872 |
| D1 | 1.872/1.872 |
| R4-A + limite 250 (2ª execução) | 1.882/1.882 |
| **Validação automatizada final** | **1.894/1.894**; regressão 990/990 (36 módulos) |

Isolamento do ambiente: 53/53. Itens protegidos (Sino 6.11 oficial, bancos pessoais, backups, ambientes F1):
63/63 idênticos em todas as rodadas.

## Validação manual da autora (banco fictício)
- **1ª rodada (parcial):** parcelamentos, recorrências fixas e variáveis.
- **2ª rodada:** ajustes A–D, conversões nos cenários principais, R4-A funcional, encerramento de recorrência e
  aviso D3, aprovados nos cenários executados.
- **3ª rodada:** limite de 250 (aprovado), mensagem de "Alterar parcelamento" (aprovada) e bloqueio visual R4-A
  (aprovado na conferência visual; a proteção contra gravação foi aprovada nos testes automáticos).
- **Não executados ou parciais no roteiro (não aprovados):** conta Única (1); recorrências **anuais** fixas e
  variáveis (5 e 6); pagamento integral (8); estornos (9); transformação de contas (12); totais, listas e
  gráficos (13); outras mensagens e bloqueios (14); navegação geral (15); casos especiais de conversão.
  Esses itens só têm cobertura de testes automáticos.

## Pendências para a Sino 6.13
- Interface, organização visual, responsividade, acessibilidade e padronização dos botões. Diretriz aprovada:
  uma ação indisponível por condição já conhecida fica **cinza e desabilitada**.
- Alinhamento de "Valor pendente" em Início; cortes de textos e cartões em Início (320/360 px); rótulos do
  Gráfico sobrepostos em 320 px; quebra dos botões de tipo em Nova conta.
- Técnicas: foco ao fechar "Configurar recorrência" (P1); diálogo de pagamento parcial com valor pendente (P2);
  Editar de recorrências grava campos e estrutura em duas transações; consulta extra por linha em Início
  (`obter_identificacao`); código legado mantido só para testes; sem gatilho em `pp_pagamentos`.

## Sino 6.14 / F1 — Supercontas
Supercontas e contas descendentes, com faturas mensais, parcelamentos, recorrências e detalhamento de gastos,
sobre as regras estabilizadas da 6.12. Descrição prevista de até **250** caracteres, a confirmar. **Não
iniciada**; os ambientes F1 não foram alterados.

## Ressalvas para a futura integração oficial
- A integração precisa de autorização própria e traz a **migração v11** do banco pessoal (hoje v10). É
  obrigatória uma cópia de recuperação verificada antes, e o `db.py` da 6.11 recusa abrir um banco v11.
- Fazer a validação manual dos cenários pendentes listados acima, ou registrar a dispensa de cada um pela autora.
- As regras e decisões detalhadas da 6.12 estão nas notas do ambiente experimental (`notas/`, fora do
  repositório) e precisam ser incorporadas à ERS na integração.
- Notas da versão (`notas-da-versao.md`) sem seção da 6.12, de propósito: a versão não foi publicada.
- Descrições antigas acima de 250 caracteres no banco pessoal, se houver, ficam intactas e só são exigidas
  reduzidas quando editadas (P4). Contar quantas existem antes de integrar.
- Os testes de interface simulam a página. A aparência final em cada largura e tema deve ser conferida na 6.13.
