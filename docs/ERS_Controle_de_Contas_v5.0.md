# Especificação de Requisitos de Software (ERS)

## Projeto: Aplicativo de Controle de Contas — Sino

**Autora:** Carinne Batista
**Versão:** 5.0
**Data original:** 28 de julho de 2025
**Data desta revisão:** 1 de setembro de 2026 (última alteração pontual: 5 de setembro de 2026, decisão D7; fechamento documental pós-implementação: 22 de setembro de 2026 — ver seção 14)
**Status:** Implementação concluída e auditada. Auditoria final de rastreabilidade realizada em 22/09/2026, confrontando cada requisito com o código e o banco de dados reais — ver seção 14 ("Fechamento da v5.0 — Auditoria Final").

---

## Nota da Versão 5.0

Esta versão representa uma **revisão estrutural completa** da ERS, motivada principalmente pela necessidade de:

1. Suportar recorrência **mensal e anual**, além da recorrência única, incluindo séries **sem data de término**;
2. Corrigir uma limitação de modelagem de dados (`contas.serie_id` autorreferenciado) que impede excluir a primeira ocorrência de uma série, alterar a frequência de uma série ou representar séries sem término;
3. Introduzir a **data efetiva de pagamento**, distinta da data de vencimento;
4. Formalizar a identidade visual das categorias (emoji e cor), a lista de categorias pré-criadas e o limite de 30 categorias;
5. Corrigir a redação do RF05, resolvendo a pendência registrada na v4.1 — **nota de fechamento (22/09/2026):** ao contrário do que se presumia nesta revisão original, o título dinâmico da Tela Principal não estava implementado antes desta ERS; a auditoria final identificou a lacuna e o comportamento foi efetivamente construído no fechamento desta versão (ver seções 5.15, 12 e 14);
6. Substituir textos técnicos/artificiais da interface (contagem de dias, lista de atrasadas ocupando a Tela Principal) por linguagem natural e por um fluxo dedicado.

Esta versão **não copia a v4.1 e acrescenta texto**: os requisitos foram reorganizados, redundâncias entre RF12/RF25 (Total do Mês / Contas atrasadas) e RF17 (resumo de 7 dias) foram eliminadas, e nenhum novo RF foi criado para funcionalidades que um RF existente já cobria (por exemplo, sugestões de emoji continuam sob o RF18, que já previa ícone pré-definido).

Os documentos `ERS_Controle_de_Contas_v4.md` e `ERS_Controle_de_Contas_v4.1.md` são preservados sem alterações, como histórico.

**Importante:** esta ERS descreve o que deve ser construído. A tabela da seção 12 (Rastreabilidade) indica, requisito a requisito, o que já está implementado hoje e o que ainda depende da nova arquitetura de séries descrita na seção 9.

Esta revisão (**consolidação final**, 01/09/2026) fecha as decisões de produto que haviam ficado pendentes após a auditoria da v5.0: RF26 (posição na série adaptada ao tipo de recorrência), o horizonte de geração de séries com data de término (sem cap de 12 meses), a redação do RF28, o tratamento das ocorrências futuras ao alterar a frequência de uma série (RF27), a preservação de ocorrências editadas individualmente diante de uma alteração de frequência, a geração sob demanda ao navegar para períodos futuros de séries sem término, a disponibilidade das categorias no seletor de conta, o papel de `conta_fixa`/`repetir_ate` na nova arquitetura, e o não tratamento especial de `data_pagamento` histórico (o aplicativo ainda está em desenvolvimento, sem dados de produção). **Não há mais nenhuma decisão de produto pendente nesta ERS.** A seção 14 lista apenas pontos de implementação, sem impacto no comportamento já decidido.

**Alteração pontual (decisão D7, 05/09/2026):** a validação manual do fluxo de edição de recorrência revelou que a redação original de RF29/§5.8 ("Remover recorrência") não correspondia à expectativa de uso do encerramento de uma recorrência. RF29 e §5.8 foram revisados — a ação passa a se chamar "Encerrar recorrência" e passa a remover ocorrências futuras ainda não realizadas a partir da ocorrência selecionada, preservando sempre o histórico já ocorrido e a própria ocorrência selecionada, com proteção defensiva para ocorrências futuras com informação histórica relevante (pagas, com data de pagamento, ou editadas individualmente). Ver seção 14, Decisão D7, para o registro completo. Nenhuma outra seção ou decisão anterior (D1–D6 inclusive) foi reaberta por esta alteração.

---

# 1. Identificação e Versionamento

| Campo | Valor |
|---|---|
| Projeto | Sino — Aplicativo de Controle de Contas |
| Documento | Especificação de Requisitos de Software (ERS) |
| Versão | 5.0 |
| Autora | Carinne Batista |
| Data desta revisão | 01/09/2026 (última alteração pontual: 05/09/2026, decisão D7; fechamento documental: 22/09/2026) |
| Versão anterior | 4.1 (27/08/2026) |
| Status desta versão | Implementação concluída e auditada — ver seção 14 ("Fechamento da v5.0 — Auditoria Final") |

O histórico completo de versões está na seção final deste documento.

---

# 2. Objetivo

O Sino é uma ferramenta pessoal para registro e controle de contas financeiras, permitindo informar nome, valor, data de vencimento, categoria, status de pagamento e data efetiva de pagamento.

A partir da v5.0, o sistema passa a oferecer:

* Recorrência única, mensal ou anual, com ou sem data de término;
* Preservação rigorosa do histórico: alterações futuras de uma série nunca reescrevem ocorrências passadas;
* Controle independente de status e data de pagamento por ocorrência;
* Identidade visual própria por categoria (emoji e cor);
* Uma Tela Principal mais enxuta, com alertas em linguagem natural em vez de listas técnicas.

---

# 3. Escopo

Mantido em relação à v4.1: aplicativo de uso pessoal, uma conta financeira vinculada a um único usuário, armazenamento local, interface simples.

Escopo desta revisão especificamente:

* **Dentro do escopo:** recorrência mensal/anual sem arrasto de data, séries sem término, transformação de conta avulsa em recorrente, alteração de frequência, exclusão granular de ocorrências (incluindo a primeira da série), encerramento de recorrência preservando o histórico já ocorrido, data efetiva de pagamento, categorias pré-criadas com limite de 30, emoji e cor por categoria, banner de contas em atraso com tela dedicada, mensagens de vencimento em linguagem natural, seletor visual de "repetir até".
* **Fora do escopo desta etapa:** implementação de código, alteração de schema, migração de banco, novas telas construídas, gráficos financeiros (RF21–RF23, permanecem não implementados), notificações, sincronização em nuvem, exportação de dados — ver seção 13 (Melhorias Futuras, mantida da v4.1) implícita nesta seção.

---

# 4. Visão Geral do Sistema

O sistema já implementado hoje (base para esta revisão) cobre: login/cadastro, CRUD de contas com recorrência mensal com término obrigatório, edição com escopo "somente este mês" / "este mês em diante", exclusão de conta com tratamento parcial de série, filtro de status na tela "Ver todas", total do mês com três filtros, seção de contas atrasadas na Tela Principal, indicação "Parcela X de Y", CRUD de categorias com ícone em texto livre.

A v5.0 estende esse sistema em quatro frentes principais:

1. **Modelo de recorrência** — de "sempre mensal, sempre com fim obrigatório, série gerada por autorreferência" para "única/mensal/anual, fim opcional, série representada por uma entidade própria" (seção 9).
2. **Granularidade de ações sobre a série** — exclusão, alteração de frequência e remoção de recorrência passam a agir corretamente sobre qualquer ocorrência, incluindo a primeira.
3. **Pagamento** — a data efetiva de pagamento passa a existir como dado da ocorrência.
4. **Categorias** — ganham identidade visual completa (emoji + cor) e um catálogo inicial padronizado.

---

# 5. Regras de Negócio

## 5.1 Princípio geral — preservação do histórico

> Alterações feitas na configuração futura de uma recorrência não modificam automaticamente ocorrências anteriores. Somente uma ação explícita do usuário sobre uma ocorrência específica pode alterar aquela ocorrência.

Este princípio se aplica, sem exceção, a:

* alteração de valor, nome ou data de vencimento (RF20);
* alteração de frequência (RF27);
* transformação de conta avulsa em recorrente (RF28);
* encerramento da recorrência (RF29);
* exclusão de ocorrências (RF08);
* qualquer outra alteração futura da série que venha a ser criada.

**Edição individual prevalece sobre alteração futura da série — decisão final.** Se uma ocorrência já foi alterada individualmente pelo usuário (escopo "Somente este mês", seção 5.6), essa alteração é histórico e permanece intacta: um ajuste mecânico posterior da série — como a alteração de frequência (RF27, seção 5.5) — nunca a sobrescreve. Isso não muda o funcionamento de "Este mês em diante" (seções 5.6 e 5.7): quando o usuário escolhe esse escopo deliberadamente, a alteração ou exclusão continua se aplicando à ocorrência selecionada e às futuras, exatamente como já definido. O princípio aqui é que apenas uma ação explícita do usuário sobre a série, no escopo que ele escolheu, pode afetar ocorrências futuras — nunca um efeito colateral de outra operação.

Consequência direta: **status de pagamento e data de pagamento pertencem exclusivamente à ocorrência.** Nenhuma ação sobre a série (edição, mudança de frequência, remoção da recorrência) pode alterar o status ou a data de pagamento de qualquer ocorrência, passada ou futura. Marcar agosto como paga não afeta setembro, outubro ou qualquer outra ocorrência da mesma série.

## 5.2 Tipos de recorrência e âncora (RF10)

A recorrência suporta três tipos: **Única**, **Mensal**, **Anual**.

Para Mensal e Anual, a **ocorrência inicial** (a primeira criada) é a **âncora** da série: sua data de vencimento define o dia (e, na recorrência anual, também o mês) que as demais ocorrências devem seguir.

### 5.2.1 Recorrência mensal — sem arrasto

Cada ocorrência mensal usa como referência o **dia da data-âncora**, não o dia da ocorrência anterior. Quando o mês de destino não possui esse dia, o sistema usa o último dia válido daquele mês — mas o mês seguinte volta a tentar o dia original da âncora.

Exemplo (âncora em 31/01):

```
31/01 → 28/02 (ajuste: fevereiro não tem dia 31) → 31/03 (volta ao dia 31 da âncora)
```

Não existe "arrasto": fevereiro ter sido ajustado para 28 não faz março herdar o dia 28. O cálculo deve considerar corretamente anos bissextos (ex.: 31/01 → 29/02 em ano bissexto → 31/03).

### 5.2.2 Recorrência anual — sem arrasto

Cada ocorrência anual mantém o **mês e o dia da data-âncora**. Quando o ano de destino não possuir esse dia (âncora em 29/02, em anos não bissextos), o sistema ajusta para 28/02 **daquele ano**, mas o próximo ano com fevereiro bissexto volta a usar 29/02 — a âncora nunca muda.

Exemplo (âncora em 29/02/2028):

```
29/02/2028 → 28/02/2029 → 28/02/2030 → 28/02/2031 → 29/02/2032
```

29/02 continua sendo a data-âncora da série; 28/02 é apenas o ajuste pontual dos anos não bissextos.

## 5.3 Horizonte de geração de ocorrências (RF10)

A regra de geração inicial depende de a série ter ou não data de término — **decisão final:**

* **Com data de término:** a geração inicial cria as ocorrências até a data de término definida pelo usuário, integralmente, no momento da criação da série — **sem limite de 12 meses**. Se o término for daqui a 3 anos, as ocorrências dos 3 anos são geradas de uma vez, como já acontece hoje.
* **Sem data de término:** o sistema gera, no momento da criação, as ocorrências correspondentes aos **12 meses seguintes** a partir da ocorrência-âncora, para que o usuário já visualize suas contas futuras.

**Para séries sem término, o horizonte de 12 meses é o horizonte inicial da criação da recorrência — não uma exigência de que o sistema mantenha continuamente 12 meses à frente, e não uma rotina obrigatória de regeneração contínua.** A forma como o sistema garante que o usuário não veja um mês futuro vazio ao navegar além desse horizonte inicial é a geração sob demanda, descrita na seção 5.20 e detalhada tecnicamente na seção 9.4 — acionada pela necessidade real (o usuário navegando até um período ainda não gerado), não por um job periódico obrigatório.

## 5.4 Transformar conta avulsa em recorrente (RF28)

Uma conta avulsa (Única) possui uma única ocorrência. O usuário pode transformá-la em recorrente:

* essa ocorrência passa a ser a **âncora** de uma nova série;
* o usuário escolhe a frequência (mensal ou anual) e a configuração de término;
* não existem ocorrências anteriores a incorporar — a série começa exatamente a partir daquela ocorrência.

## 5.5 Alterar frequência de uma série (RF27)

O usuário pode alterar a frequência de uma série existente (ex.: Mensal → Anual).

* A nova frequência é aplicada **a partir da ocorrência selecionada**, que passa a ser a nova âncora da configuração;
* Ocorrências anteriores à selecionada permanecem exatamente como estavam, incluindo sua frequência original — nunca são modificadas por esta ação;
* Diferente da edição de valor/nome/data (seção 5.6), a alteração de frequência tem um único modo de aplicação — sempre "a partir desta ocorrência em diante" — porque não há como reinterpretar retroativamente uma frequência diferente sobre ocorrências já existentes.

### Ocorrências futuras já geradas sob a frequência anterior — decisão final

Como a série pode já ter ocorrências futuras geradas sob a frequência antiga (ver horizonte de geração, seção 5.3), a mudança de frequência precisa tratar essas ocorrências explicitamente:

> As ocorrências futuras à ocorrência selecionada que tenham sido geradas sob a frequência anterior e que não se encaixem na nova frequência devem ser **ajustadas à nova frequência a partir do ponto de alteração**. Ocorrências anteriores à ocorrência selecionada nunca são modificadas.

Na prática, isso significa que as ocorrências futuras geradas sob o padrão antigo (por exemplo, as ocorrências mensais restantes dentro do horizonte já gerado) são substituídas pelas ocorrências que resultariam da nova frequência a partir da ocorrência selecionada, preservando integralmente tudo o que é anterior a ela. O objetivo é que, depois da alteração, a série futura siga exclusivamente a nova frequência definida pelo usuário — sem ocorrências remanescentes do padrão antigo além do que já está no histórico.

**Exceção — ocorrências já editadas individualmente (decisão final):** se, entre essas ocorrências futuras, houver alguma que o usuário já tenha alterado individualmente (escopo "Somente este mês", seção 5.6), essa ocorrência **não** é substituída pelo ajuste de frequência — a edição individual é histórico e prevalece, conforme o princípio geral da seção 5.1. Apenas as ocorrências futuras que ainda refletem o modelo padrão da série (nunca editadas individualmente) são ajustadas/substituídas para seguir a nova frequência.

Esta regra está fechada e não deve ser reaberta durante a implementação. A forma técnica de representá-la internamente (por exemplo, se a mesma linha de `series_recorrencia` é atualizada in-place ou substituída) é um ponto de implementação, não uma decisão de produto — ver seção 9.3.

## 5.6 Escopo de edição de valor, nome ou data (RF20)

Ao editar nome, valor ou data de vencimento de uma ocorrência que pertence a uma série, o sistema pergunta ao usuário como aplicar a alteração — por exemplo, com a pergunta **"Aplicar alteração a:"** (o texto exato da interface é uma decisão de UX, não uma exigência literal deste requisito, desde que a intenção fique clara para o usuário) — oferecendo duas opções:

* **Somente este mês** — altera apenas a ocorrência selecionada. Continua sendo a opção pré-selecionada por padrão.
* **Este mês em diante** — altera a ocorrência selecionada e as ocorrências futuras da série (`data_vencimento >= ocorrência selecionada`).

Ocorrências anteriores à selecionada nunca são alteradas, em nenhum dos dois modos.

Uma edição feita com o escopo "Somente este mês" é considerada uma alteração individual da ocorrência: ela passa a fazer parte do histórico e fica protegida de ajustes mecânicos futuros da série, como a alteração de frequência (RF27, seção 5.5) — ver o princípio geral na seção 5.1.

### Mensagem de confirmação

Sempre que fizer sentido, o sistema deve informar de forma natural e explícita o que foi alterado, por exemplo:

> "Você alterou o valor de R$ 150,00 para R$ 180,00 e o vencimento de 10/09 para 15/09."

A mensagem deve refletir os campos realmente alterados (pode ser só valor, só data, ou ambos) e evitar linguagem técnica (não expor nomes de campos do banco, IDs de série, etc.). O mesmo princípio de mensagem natural se aplica à alteração de frequência (RF27) — por exemplo: *"Você alterou a frequência de mensal para anual a partir de outubro/2026."*

## 5.7 Excluir ocorrência de uma série (RF08)

Ao excluir uma conta que pertence a uma série, o sistema pergunta ao usuário o que excluir — por exemplo, com a pergunta **"O que você deseja excluir?"** (o texto exato da interface é uma decisão de UX, não uma exigência literal deste requisito, desde que a intenção fique clara para o usuário) — oferecendo três opções:

* **Somente este mês** — exclui apenas a ocorrência selecionada.
* **Este mês em diante** — exclui a ocorrência selecionada e as ocorrências futuras da série. Ocorrências anteriores permanecem no histórico.
* **Cancelar** — nenhuma alteração.

Este comportamento deve funcionar **inclusive quando a ocorrência selecionada é a primeira da série** — hoje isso não é possível porque o modelo de dados usa a própria primeira ocorrência como identificador da série (ver seção 9.1 sobre a limitação atual e a proposta de correção).

O termo "inativar" não deve aparecer em nenhum texto de interface relacionado a esta ação; é usado apenas nesta documentação para descrever o conceito interno.

Para uma conta que não pertence a nenhuma série (Única), a exclusão ocorre diretamente, sem esse diálogo.

## 5.8 Encerrar recorrência (RF29) — decisão final (revisão D7)

**Redação revisada nesta revisão (D7, ver seção 14).** A versão anterior deste requisito ("Remover recorrência") definia uma ação que nunca excluía nenhuma ocorrência, passada ou futura. A validação manual do fluxo de edição mostrou que essa regra confundia o usuário: ele esperava que "encerrar" uma recorrência também parasse de exibir as parcelas futuras que ainda não aconteceram, não apenas as impedisse de serem geradas. Esta seção substitui a regra anterior — a decisão abaixo é final e não deve ser reaberta.

"Encerrar recorrência" é uma ação diferente de "excluir contas" (RF08), mas — diferentemente da redação anterior — passa a remover ocorrências futuras ainda não realizadas, preservando integralmente o que já aconteceu.

A ação é **contextual à ocorrência que o usuário está editando** (não à data atual do sistema): o mês/ano dessa ocorrência é o ponto de encerramento comunicado ao usuário e usado para decidir o que é preservado.

Ao encerrar a recorrência a partir da ocorrência selecionada:

* a série deixa de gerar novas ocorrências (equivalente a `ativa = 0`, seção 9.2);
* a ocorrência selecionada é sempre preservada;
* **nenhuma ocorrência já realizada é excluída** — o corte usado para decidir o que remover é sempre o **mais tardio** entre a data da ocorrência selecionada e a data atual, nunca apenas a ocorrência selecionada isoladamente. Na prática:
  * se a ocorrência selecionada é passada (ex.: hoje é setembro/2026 e o usuário está editando a ocorrência de março/2026), tudo o que já aconteceu — de março a setembro de 2026, inclusive — é preservado; só as ocorrências futuras a partir de outubro/2026 são removidas;
  * se a ocorrência selecionada ainda não aconteceu, ela e tudo antes dela são preservados; só as ocorrências estritamente posteriores a ela são removidas;
* ocorrências futuras que, mesmo estando no intervalo que seria removido, carreguem informação histórica relevante — já estiverem marcadas como pagas, já tiverem uma data de pagamento registrada, ou já tiverem sido editadas individualmente ("Somente este mês", seção 5.6) — **não são apagadas silenciosamente**; permanecem no sistema como conta individual, sem exigir nenhuma decisão adicional do usuário;
* as ocorrências que permanecem (a selecionada e as anteriores) passam a se comportar como contas individuais (podem ser editadas e excluídas isoladamente, sem diálogo de escopo, pois deixam de pertencer a uma série ativa);
* o histórico já ocorrido nunca é apagado, em nenhuma circunstância.

**Encerrar recorrência ≠ Excluir contas futuras (RF08).** A diferença está na base de comparação e na proteção de histórico: "Excluir esta mês em diante" (RF08) age a partir da própria ocorrência escolhida pelo usuário, sem nenhuma proteção especial para ocorrências pagas ou editadas individualmente dentro do intervalo excluído. "Encerrar recorrência" (RF29) nunca exclui a ocorrência selecionada nem nada anterior a ela (mesmo quando isso significa preservar mais do que apenas a ocorrência escolhida, por causa da data atual), e protege explicitamente ocorrências futuras com informação histórica relevante.

Ao encerrar uma recorrência, a conta deixa de possuir recorrência e passa a ser tratada como conta avulsa. Se o usuário quiser novamente uma recorrência, deverá utilizar "Transformar em recorrente" (RF28, seção 5.4), seguindo o mesmo fluxo de uma conta avulsa — não existe uma ação separada de "reativação". Essa nova série é uma série nova, começando naquela ocorrência como âncora; a série antiga (encerrada) não é reaproveitada nem precisa ser removida do banco — ela permanece apenas para preservar o histórico das ocorrências anteriores que ainda a referenciam (seção 9.1).

## 5.9 Status de pagamento independente por ocorrência

O status (`pago`/`pendente`, com `atrasado` calculado) pertence exclusivamente à ocorrência. Marcar uma ocorrência como paga não altera o status de nenhuma outra ocorrência da mesma série, passada ou futura.

## 5.10 Data efetiva de pagamento (RF06/RF24)

Cada ocorrência possui, além da data de vencimento, uma **data de pagamento**, independente da recorrência.

* Ao marcar uma ocorrência como paga, a data atual é registrada automaticamente como data de pagamento;
* O usuário pode alterar essa data posteriormente, usando um seletor de calendário;
* Não é permitido informar uma data de pagamento futura (posterior à data atual);
* Ao voltar o status de uma ocorrência para Pendente, a data de pagamento é removida (fica nula).

## 5.11 Categorias — catálogo inicial e limite (RF14)

Todo usuário possui, desde o cadastro, as seguintes categorias pré-criadas:

1. Casa
2. Automóvel
3. Lazer
4. Faculdade
5. Academia
6. Saúde
7. Cartão de crédito
8. Beleza
9. Streaming
10. Creche
11. Outro

O usuário pode criar, editar e excluir categorias livremente, respeitando um **limite de 30 categorias por usuário**, contando as pré-criadas. A exclusão de uma categoria não exclui as contas associadas — elas passam a ficar sem categoria (`categoria_id = NULL`), regra já vigente desde versões anteriores.

As categorias pré-criadas ficam disponíveis desde o primeiro acesso, na área de categorias e em qualquer seletor de categoria, para que o usuário já possa utilizá-las ao cadastrar a primeira conta — não é necessário criá-las manualmente.

### Categorias disponíveis no seletor de conta (RF04/RF07)

Ao criar ou editar uma conta, o seletor de categoria exibe somente as categorias **atualmente existentes** para aquele usuário:

* as categorias pré-criadas aparecem desde o início;
* uma categoria excluída deixa de aparecer no seletor;
* uma categoria recém-criada passa a aparecer no seletor imediatamente.

**Contas são independentes de categorias.** Excluir uma categoria nunca exclui as contas que a utilizavam — elas permanecem no sistema, apenas passam a ficar sem categoria (`categoria_id = NULL`), como já registrado acima.

## 5.12 Emoji da categoria (RF18)

Cada categoria possui um emoji. Ao criar ou editar uma categoria, o sistema sugere 5 emojis relacionados ao nome/tipo da categoria:

| Categoria | Sugestões |
|---|---|
| Casa | 🏡 🏘️ 🏚️ 🏢 |
| Automóvel | 🚗 🚕 🏍️ ✈️ 🚃 |
| Lazer | 🎡 🏟️ 🏖️ 🎮 🎳 |
| Faculdade | 📚 📋 📝 👩‍💻 📖 |
| Academia | 🏋🏻‍♀️ ⛹🏻‍♂️ 🛹 🏊🏻‍♂️ 🚴🏻‍♂️ |
| Saúde | 🏥 💊 🩺 🩻 💉 |
| Cartão de crédito | 💳 💵 🪙 💰 🪪 |
| Beleza | 💄 💅🏻 👗 👟 👜 |
| Streaming | 📽️ 🎥 📺 🍿 🎬 |
| Creche | 👶 👧 🧒 🧸 🚼 |
| Outro | 💕 🔨 🐾 🧳 🛒 |

Essas sugestões são uma proposta inicial de UX, **não valores imutáveis da ERS** — nomes, emojis e combinações das categorias pré-criadas podem ser ajustados durante a implementação e os testes de UX, sem que isso represente uma mudança de requisito. O usuário sempre pode escolher qualquer outro emoji disponível no seletor do dispositivo, inclusive para categorias criadas por ele mesmo (sem sugestões pré-definidas específicas).

## 5.13 Cor da categoria (RF18)

Cada categoria possui uma cor própria — a cor pertence à **categoria**, não à conta.

* O sistema mantém uma paleta de até **30 cores**, harmoniosas e visualmente distintas entre si, pensada tanto para a interface quanto para uso futuro nos gráficos financeiros (RF21/RF22);
* Uma mesma cor não pode ser usada simultaneamente por duas categorias ativas do mesmo usuário;
* Ao criar uma categoria, o sistema pode atribuir automaticamente uma cor disponível; o usuário pode escolher/trocar manualmente por outra cor disponível;
* Ao trocar a cor de uma categoria, a cor anterior volta a ficar disponível;
* Ao excluir uma categoria, sua cor volta a ficar disponível;
* Se não houver nenhuma cor disponível no momento (ex.: usuário no limite de 30 categorias, todas as cores em uso), o sistema deve informar o usuário adequadamente, em vez de falhar silenciosamente ou atribuir uma cor duplicada.

Os valores exatos (códigos hex/RGB) da paleta não são fixados nesta ERS como decisão definitiva — podem ser ajustados durante a implementação e os testes de UX, alinhados à paleta verde/escura já usada no aplicativo. O objetivo é garantir boa diferenciação visual, especialmente para os futuros gráficos financeiros.

## 5.14 Contas atrasadas — banner e tela dedicada (RF25)

A Tela Principal não mantém mais uma lista de contas atrasadas ocupando espaço permanente. Em vez disso, exibe um banner/status:

* Havendo contas atrasadas: mensagem do tipo **"Você possui contas em atraso!"**, com ação **"Ver contas em atraso"**, que abre uma tela dedicada listando essas contas;
* Não havendo contas atrasadas: mensagem positiva, do tipo **"Suas contas estão em dia!"**.

Mantém-se o princípio já estabelecido na v4.0/v4.1: contas atrasadas são independentes do mês selecionado no seletor de mês da Tela Principal (mesmo princípio do resumo de 7 dias, RF17) e uma conta paga nunca aparece como atrasada, mesmo com vencimento já passado.

## 5.15 Contas do mês selecionado (RF05)

Na Tela Principal e na tela "Ver todas as contas", quando um mês está selecionado, a listagem exibe as contas com vencimento naquele mês.

Na Tela Principal, o cabeçalho da lista de contas é dinâmico e reflete o mês selecionado — **"Suas contas de setembro"**. Este comportamento foi implementado no fechamento desta versão (22/09/2026): antes, o cabeçalho era um texto estático ("Suas contas"), independente do mês selecionado no seletor logo acima. Na tela "Ver todas as contas", o título permanece no formato "{Mês} {Ano}" (ex.: "Setembro 2026"), já dinâmico desde antes desta correção e mantido sem alteração — por decisão de produto, a mudança desta versão ficou restrita ao cabeçalho da Tela Principal.

Isso corrige a redação do RF05 da v4.1 (que dizia "listar todas as contas do usuário logado"), alinhando o texto do requisito ao comportamento agora efetivamente implementado.

## 5.16 Total do mês (RF12) — mantido sem alteração

Regra herdada integralmente da v4.0/v4.1, sem mudanças nesta versão: o "Total do Mês" tem três filtros mutuamente exclusivos (Todas / Pendentes — inclui `atrasado` / Pagas), e uma conta atrasada permanece vinculada ao mês do seu vencimento original, nunca sendo somada ao total de um mês posterior.

## 5.17 Mensagens de vencimento (RF11/RF17)

Mensagens relacionadas a vencimento usam linguagem natural, nunca a forma "X dia(s)":

| Situação | Texto |
|---|---|
| Vence hoje | **Vence hoje** |
| Vence amanhã | **Vence amanhã** |
| Vence em mais de 1 dia | **Vence em X dias** |
| Venceu ontem | **Venceu ontem** |
| Venceu há mais de 1 dia | **Venceu há X dias** |

O resumo de contas que vencem nos próximos 7 dias (RF17) também deve respeitar singular/plural na contagem de contas (ex.: "1 conta vence nos próximos 7 dias" vs. "3 contas vencem nos próximos 7 dias").

## 5.18 Seletor de término da recorrência (RF10)

O campo de data de término deixa de ser um campo textual e passa a ser um seletor visual de mês e ano (ex.: navegação entre Janeiro–Dezembro e uma faixa de anos, como 2026 a 2036), com a opção **"Sem data de término"**. Não é permitido selecionar uma data de término anterior à data de vencimento da ocorrência inicial.

## 5.19 Indicação de posição na série (RF26) — decisão final

A indicação de posição da ocorrência dentro da série é adaptada ao tipo de recorrência:

* **Séries com data de término definida:** exibir **"Parcela X de Y"**, em que X é a posição da ocorrência e Y é o total de ocorrências da série (calculado sobre a geração integral até o término, ver seção 5.3).
* **Séries sem data de término:** exibir apenas **"Parcela X"**, sem o total. A ausência do "Y" é intencional — não existe um total definitivo de ocorrências em uma série sem término, e exibir um número que representasse apenas "quantas ocorrências já foram geradas até agora" seria enganoso.

Esta decisão está fechada e não deve ser reaberta durante a implementação.

## 5.20 Navegação para meses futuros em séries sem término (geração sob demanda)

Como a recorrência sem término tem apenas um horizonte inicial de geração (seção 5.3), é preciso garantir que o usuário não veja um mês vazio ao navegar para além desse horizonte. Regra de produto:

* Se o usuário navegar para um período futuro que ainda não possui ocorrências de uma série ativa e sem data de término, o sistema gera as ocorrências necessárias para cobrir aquele período;
* essa geração nunca altera o histórico (ocorrências passadas ou já existentes não são tocadas);
* essa geração nunca cria duplicidades — antes de gerar, o sistema verifica quais ocorrências já existem para aquela série no período solicitado;
* trata-se de geração **sob demanda**, motivada pela necessidade real de exibir aquele período — não uma rotina contínua e automática de regeneração (ver seção 9.4).

Esta regra vale apenas para séries ativas (não removidas — seção 5.8) e sem data de término. Séries com término não precisam desse mecanismo, pois já são geradas integralmente até a data definida (seção 5.3).

---

# 6. Requisitos Funcionais

**Legenda de mudança em relação à v4.1:** *inalterado* · *alterado* · *estendido* · *substituído* · *novo*.

| ID | Descrição | Mudança |
|---|---|---|
| RF01 | Permitir a criação de conta de usuário com login e senha. | inalterado |
| RF02 | Permitir o login do usuário no sistema. | inalterado |
| RF03 | Associar todas as contas financeiras cadastradas ao usuário logado. | inalterado |
| RF04 | Permitir o cadastro de novas contas, informando nome, valor, data de vencimento e categoria. | inalterado |
| RF05 | Listar as contas do usuário logado com vencimento no mês selecionado, com título dinâmico refletindo o mês (ex.: "Suas contas de setembro"). *(seção 5.15)* | alterado (redação) |
| RF06 | Permitir marcar uma conta como paga ou pendente, registrando automaticamente a data efetiva de pagamento ao marcar como paga, permitindo edição posterior dessa data (sem datas futuras) e removendo-a ao reverter para pendente. *(seção 5.10)* | estendido |
| RF07 | Permitir a edição de uma conta existente. | inalterado |
| RF08 | Permitir a exclusão de uma conta, com as opções "Somente este mês", "Este mês em diante" e "Cancelar" quando a conta pertencer a uma série — inclusive quando for a primeira ocorrência da série. *(seção 5.7)* | alterado — depende da nova arquitetura de séries (seção 9) |
| RF09 | Permitir filtrar as contas do mês selecionado, na tela "Ver todas as contas", por status (Todas, Pendentes, Pagas, Atrasadas). | inalterado (mantido da v4.1) |
| RF10 | Permitir configurar uma conta como Única, Mensal ou Anual. Para Mensal/Anual, a ocorrência inicial é a âncora da série (sem arrasto de data); o término é opcional, escolhido por um seletor visual de mês/ano ou por "Sem data de término". Séries com término são geradas integralmente até a data definida; séries sem término geram inicialmente 12 meses a partir da âncora e passam a gerar ocorrências adicionais sob demanda conforme o usuário navega para períodos futuros. *(seções 5.2, 5.3, 5.18, 5.20)* | substituído — depende da nova arquitetura de séries (seção 9) |
| RF11 | Exibir, destacadas, as contas vencidas e as contas próximas do vencimento, com mensagens em linguagem natural ("Vence hoje", "Vence amanhã", "Vence em X dias", "Venceu ontem", "Venceu há X dias"). *(seção 5.17)* | alterado (linguagem) |
| RF12 | Calcular e exibir o valor total das contas de um mês, com os filtros Todas/Pendentes/Pagas. *(seção 5.16)* | inalterado |
| RF13 | Atualizar automaticamente o status de uma conta para `atrasado` quando vencida e ainda `pendente`. | inalterado |
| RF14 | Permitir criar, editar, excluir e associar categorias às contas, com um catálogo de 11 categorias pré-criadas e limite de 30 categorias por usuário. *(seção 5.11)* | estendido |
| RF15 | Exigir aceite dos Termos de Uso e da Política de Privacidade no cadastro. | inalterado |
| RF16 | Permitir login por biometria quando o dispositivo suportar (opcional). | inalterado |
| RF17 | Exibir na Tela Principal um resumo, em linguagem natural e com singular/plural corretos, das contas que vencem nos próximos 7 dias, com o total somado. *(seção 5.17)* | alterado (linguagem) |
| RF18 | Permitir associar a cada categoria um emoji — escolhido entre 5 sugestões pré-definidas por categoria ou livremente pelo seletor do dispositivo — e uma cor exclusiva, escolhida em uma paleta de até 30 cores. *(seções 5.12, 5.13)* | estendido |
| RF19 | Permitir criar uma nova conta a partir da tela de uma categoria, com a categoria pré-preenchida. | inalterado |
| RF20 | Ao editar nome, valor ou data de uma ocorrência pertencente a uma série, perguntar o escopo ("Somente este mês" ou "Este mês em diante"), com "Somente este mês" pré-selecionado, e exibir uma mensagem de confirmação em linguagem natural descrevendo o que foi alterado. *(seção 5.6)* | alterado |
| RF21 | Exibir gráfico de evolução dos gastos totais dos últimos 6 meses. | inalterado (não implementado) |
| RF22 | Exibir gráfico de distribuição dos gastos do mês por categoria, com valor e percentual. | inalterado (não implementado) |
| RF23 | Exibir comparativo percentual entre o gasto do mês atual e o do mês anterior. | inalterado (não implementado) |
| RF24 | Permitir marcar uma conta como paga diretamente na tela de detalhe, usando o comportamento estendido do RF06. | inalterado |
| RF25 | Exibir na Tela Principal um banner de status sobre contas em atraso ("Você possui contas em atraso!" / "Suas contas estão em dia!"), com ação "Ver contas em atraso" abrindo uma tela dedicada, no lugar da lista embutida. *(seção 5.14)* | substituído (UX) |
| RF26 | Exibir, para ocorrências de séries, a indicação de posição: "Parcela X de Y" quando a série tem data de término definida, ou apenas "Parcela X" quando a série não tem término. *(seção 5.19)* | alterado — decisão final registrada; depende da nova arquitetura de séries |
| RF27 | Permitir alterar a frequência de uma série existente (ex.: mensal → anual) a partir de uma ocorrência selecionada, que passa a ser a nova âncora; ocorrências anteriores permanecem inalteradas; ocorrências futuras já geradas sob a frequência anterior são ajustadas para seguir a nova frequência a partir da ocorrência selecionada, exceto as que já haviam sido editadas individualmente, que são preservadas. *(seção 5.5)* | **novo** — depende da nova arquitetura de séries |
| RF28 | Permitir transformar uma conta avulsa (Única) em recorrente a partir da ocorrência existente, que passa a ser a âncora de uma nova série. *(seção 5.4)* | **novo** — depende da nova arquitetura de séries |
| RF29 | Permitir encerrar a recorrência de uma série a partir da ocorrência selecionada: a série deixa de gerar novas ocorrências, o histórico já realizado (incluindo a ocorrência selecionada) é sempre preservado, e as ocorrências futuras ainda não realizadas são removidas, exceto as que já tenham informação histórica relevante (pagas, com data de pagamento, ou editadas individualmente). *(seção 5.8)* | **novo** — revisado na consolidação D7; depende da nova arquitetura de séries |

---

# 7. Requisitos Não Funcionais

| ID | Descrição |
|---|---|
| RNF01 | A interface deve ser simples, responsiva e utilizável em telas de diferentes tamanhos. |
| RNF02 | O armazenamento dos dados deve ser local nesta primeira versão. |
| RNF03 | O sistema deve manter desempenho satisfatório para até 1000 contas cadastradas por usuário. |
| RNF04 | A aplicação deve ser leve, de fácil instalação e acesso. |
| RNF05 | As senhas devem ser armazenadas de forma segura, com hash e salt, nunca em texto puro. |
| RNF06 | Operações comuns (cadastro, edição, consulta, exclusão) devem concluir em até 2 segundos em condições normais. |
| RNF07 | O sistema deve manter cópia de segurança (backup) local dos dados. |
| RNF08 | **(novo)** Qualquer migração de schema decorrente desta ERS (ver seção 9.5) deve preservar integralmente os dados hoje existentes — nenhuma conta, categoria ou usuário pode ser perdido ou ter seu histórico de pagamento alterado pela migração. |

---

# 8. Requisitos de Interface/UX

Esta seção descreve o impacto de UX das decisões acima, sem redefinir o padrão visual já validado (paleta verde/escura, componentes reutilizados) descrito na v4.1.

### Tela Principal
* Título de contas do mês dinâmico (RF05: "Suas contas de setembro");
* Banner de contas em atraso (RF25) no lugar da lista embutida, com ação "Ver contas em atraso";
* Mensagens de vencimento em linguagem natural nos itens da lista (RF11) e no resumo de 7 dias (RF17), com plural correto.

### Tela "Contas em Atraso" (nova)
* Lista dedicada de contas com status `atrasado`, de qualquer mês, aberta a partir do banner da Tela Principal (RF25). Não substitui a tela "Ver todas as contas" (RF05/RF09), que continua escopada ao mês selecionado.

### Nova Conta / Configuração de Recorrência
* Seletor de tipo: Única, Mensal, Anual (RF10);
* Para Mensal/Anual: seletor visual de mês/ano para o término, com opção "Sem data de término" (RF10, seção 5.18), substituindo o campo textual de "Repetir até" existente hoje;
* Validação de que a data de término não é anterior à data de vencimento inicial.

### Detalhe/Edição de Conta
* Campo de data de pagamento, editável por calendário quando a conta está paga, sem permitir datas futuras (RF06);
* Diálogo de escopo de edição ("Somente este mês" / "Este mês em diante") com mensagem de confirmação em linguagem natural (RF20);
* Diálogo de exclusão ("O que você deseja excluir?" com "Somente este mês" / "Este mês em diante" / "Cancelar"), funcional inclusive para a primeira ocorrência da série (RF08). O texto da interface não usa a palavra "inativar" em nenhum momento;
* Ações "Transformar em recorrente" (RF28), "Alterar frequência" (RF27, quando aplicável) e "Encerrar recorrência" (RF29, revisão D7), distintas visualmente da ação de excluir, agrupadas numa seção própria "Recorrência" junto aos demais dados da conta — não como ações soltas próximas de "Salvar alterações". Essa seção exibe também uma frase contextual sobre a recorrência (ex.: "Esta conta se repete mensalmente até dezembro de 2030."), no lugar de um rótulo genérico como "Recorrente: Sim". Uma conta sem recorrência exibe "Esta conta não possui recorrência." e a ação "Transformar em recorrente" — não existe um terceiro estado visual para "recorrência encerrada": depois de RF29, a conta é tratada como avulsa (seção 5.8).

### Categorias
* Catálogo pré-criado de 11 categorias no primeiro acesso (RF14);
* Seletor de emoji com 5 sugestões por categoria + acesso ao seletor completo do dispositivo (RF18);
* Seletor de cor com paleta de até 30 cores, indicando visualmente quais já estão em uso por outra categoria do usuário (RF18);
* Aviso ao atingir o limite de 30 categorias, impedindo a criação de uma nova até que alguma seja excluída.

---

# 9. Modelo e Arquitetura de Dados Proposta

## 9.1 Limitação do modelo atual

Hoje, `contas.serie_id` referencia a própria ocorrência-âncora da série (`FOREIGN KEY (serie_id) REFERENCES contas(id)`, com `serie_id = id` na ocorrência inicial). O código atual (`database/db.py`, funções `excluir_conta`, `editar_conta_serie`, `excluir_conta_serie`) já reflete essa limitação diretamente: `excluir_conta` **recusa explicitamente** excluir a ocorrência-âncora enquanto existirem outras ocorrências apontando para ela via `serie_id`, pois isso quebraria a chave estrangeira dessas ocorrências.

Essa limitação impede, ou torna artificialmente complexo:

* excluir somente a primeira ocorrência de uma série (RF08);
* alterar a frequência de uma série (RF27), já que a série não tem identidade própria além da primeira ocorrência;
* encerrar a recorrência (RF29) preservando o histórico já realizado, sem um lugar próprio para registrar "esta série não gera mais ocorrências";
* representar uma série sem data de término, já que `contas.repetir_ate` é obrigatório quando `conta_fixa = 1` e é interpretado por ocorrência, não por série;
* gerar apenas mensal (o código de geração em `criar_conta` não suporta frequência anual).

## 9.2 Arquitetura aprovada: entidade própria para a série

A direção arquitetural está aprovada: separar **configuração da série** de **ocorrências**, com uma nova entidade `series_recorrencia`, no lugar da autorreferência atual de `contas.serie_id`. Os nomes de campos e detalhes finos abaixo são a proposta técnica de referência para a implementação — ajustes de implementação que não mudem o comportamento decidido nesta ERS não representam uma nova decisão de produto.

### `series_recorrencia` (nova)

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | Inteiro | Identificador único da série. |
| `usuario_id` | Inteiro | Dono da série. |
| `nome` | Texto | Nome-modelo usado ao gerar novas ocorrências. |
| `valor` | Decimal | Valor-modelo usado ao gerar novas ocorrências. |
| `categoria_id` | Inteiro | Categoria-modelo usada ao gerar novas ocorrências (opcional). |
| `frequencia` | Texto (enum) | `mensal` ou `anual`. |
| `dia_ancora` | Inteiro | Dia do mês da data-âncora atual da série. |
| `mes_ancora` | Inteiro | Mês da data-âncora (apenas para `frequencia = anual`). |
| `data_inicio` | Data | Data da ocorrência-âncora vigente (pode ser atualizada por RF27/RF28 — ver 9.3). |
| `data_termino` | Data (nulo) | Fim da recorrência; `NULL` significa "sem data de término". |
| `ativa` | Booleano | `0` quando a recorrência foi encerrada (RF29, revisão D7) — a série para de gerar novas ocorrências, mas o registro é preservado para as ocorrências existentes continuarem referenciando seu histórico. |
| `horizonte_gerado_ate` | Data | Até que data as ocorrências já foram geradas (ver 9.4). |

### `contas` (ocorrência — campos alterados)

| Campo | Alteração proposta |
|---|---|
| `serie_id` | Passa a referenciar `series_recorrencia(id)` em vez de `contas(id)`. Continua nulo para contas Únicas. |
| `data_pagamento` | **Novo campo**, Data (nulo). Preenchido automaticamente ao marcar como paga; removido ao voltar para pendente (RF06). |
| `conta_fixa` | **Removido de `contas`** (decisão fechada). A identificação de recorrência passa a ser responsabilidade exclusiva da série: uma ocorrência é considerada parte de uma recorrência quando `serie_id IS NOT NULL`. |
| `repetir_ate` | **Removido de `contas`** (decisão fechada). O término da recorrência passa a pertencer exclusivamente à série (`series_recorrencia.data_termino`); a ausência de valor (`NULL`) representa uma recorrência sem término. |

O restante dos campos de `contas` (nome, valor, data_vencimento, status, categoria_id) permanece como hoje, pertencendo à ocorrência individual — cada ocorrência mantém sua própria cópia, mesmo quando gerada a partir do modelo da série.

### `categorias` (campo novo)

| Campo | Descrição |
|---|---|
| `cor` | **Novo campo**, identificador da cor atribuída à categoria (ver seção 5.13). |

## 9.3 O que pertence à série vs. o que pertence à ocorrência

* **Pertence à série:** frequência, âncora (dia/mês), data de término, se a série está ativa (ainda gerando ocorrências), e o "modelo" (nome/valor/categoria) usado para gerar as próximas ocorrências.
* **Pertence à ocorrência:** data de vencimento efetiva, valor efetivo, nome efetivo, categoria efetiva, status, data de pagamento.

Quando uma ocorrência é editada com o escopo "Este mês em diante" (RF20), tanto as ocorrências futuras quanto o **modelo da série** (`series_recorrencia.nome`/`valor`) devem ser atualizados, para que ocorrências ainda não geradas nasçam já com o novo valor. Ocorrências passadas nunca são tocadas.

Quando a frequência é alterada (RF27) ou uma conta avulsa é transformada em recorrente (RF28), `series_recorrencia.data_inicio` (e `dia_ancora`/`mes_ancora`/`frequencia`) é atualizada para refletir a nova âncora e a nova frequência, e as ocorrências futuras já geradas sob a configuração anterior são ajustadas para seguir a nova frequência a partir da ocorrência selecionada (regra de produto fechada — seção 5.5). A forma exata de representar isso internamente — atualizar o mesmo registro de `series_recorrencia` ou criar um novo registro vinculado ao anterior para preservar um histórico de configurações — é um **ponto de implementação**, a critério do desenvolvedor, e não uma decisão de produto em aberto.

## 9.4 Geração para séries sem término: horizonte inicial + geração sob demanda

Como uma série sem término não pode ter todas as ocorrências geradas antecipadamente (não há fim), a geração ocorre em dois momentos, ambos fechados como decisão de produto:

1. **Geração inicial (seção 5.3):** ao criar a série, geram-se as ocorrências dos 12 meses seguintes à âncora. Isso não exige nenhuma rotina contínua — é uma geração única, no momento da criação.
2. **Geração sob demanda (navegação futura, seção 5.20):** quando o usuário navega para (ou o sistema precisa consultar) um período futuro de uma série ativa e sem término que ainda não possui ocorrências geradas, o sistema gera as ocorrências necessárias para cobrir aquele período, a partir de `horizonte_gerado_ate`, e atualiza `horizonte_gerado_ate` de acordo. Antes de gerar, o sistema verifica se já existem ocorrências daquela série no período solicitado, para não criar duplicidades. Ocorrências passadas nunca são tocadas por esta geração.

**Não existe, nesta ERS, uma exigência de rotina periódica ou de job em background que mantenha um número fixo de meses sempre gerados à frente.** A geração sob demanda descrita no item 2 é suficiente para que o usuário nunca veja um mês vazio ao navegar para o futuro, sem exigir manutenção contínua de um horizonte fixo.

O ponto técnico ainda em aberto — de implementação, não de produto — é o gatilho exato da geração sob demanda: por exemplo, gerar de forma síncrona no momento da consulta que descobre a lacuna, ou gerar um bloco maior de uma vez para reduzir consultas futuras. Qualquer uma dessas abordagens deve resultar no mesmo comportamento observável descrito acima.

## 9.5 Impacto da migração dos dados existentes

A migração deve preservar integralmente os dados atuais (RNF08). Proposta:

1. Para cada valor distinto de `contas.serie_id` hoje existente (que corresponde ao `id` de uma ocorrência-âncora), criar um registro em `series_recorrencia` com: `nome`/`valor`/`categoria_id` copiados da ocorrência-âncora; `frequencia = 'mensal'` (única frequência existente hoje); `dia_ancora` extraído da `data_vencimento` da âncora; `data_inicio` = `data_vencimento` da âncora; `data_termino` = `repetir_ate` da âncora; `ativa = 1`; `horizonte_gerado_ate` = maior `data_vencimento` entre as ocorrências daquela série.
2. Atualizar todas as ocorrências que tinham aquele `serie_id` para apontar para o novo `series_recorrencia.id`.
3. `data_pagamento` nasce nula para ocorrências que já estejam marcadas como `pago` antes da migração. Não é necessário nenhum tratamento especial para esse caso: o aplicativo ainda está em desenvolvimento e não possui dados de produção com contas previamente pagas. A partir da implementação da v5.0, toda conta marcada como paga passa a registrar `data_pagamento` normalmente, seguindo a regra da seção 5.10.
4. Remover a restrição de chave estrangeira autorreferenciada em `contas.serie_id` e recriá-la apontando para `series_recorrencia(id)`.
5. Remover as colunas `contas.conta_fixa` e `contas.repetir_ate` após a migração (decisão fechada — seção 9.2): toda a informação de recorrência passa a residir em `series_recorrencia`, e uma ocorrência é identificada como parte de uma série por `serie_id IS NOT NULL`.

**Nota de fechamento (22/09/2026):** esta migração foi executada (backup pré-migração registrado em `database/backups/`); a auditoria final de rastreabilidade confirmou, contra o banco real, ausência de `contas.conta_fixa`/`contas.repetir_ate`, presença de `data_pagamento`/`editado_individualmente`/`categorias.cor`, e zero órfãos/violações de chave estrangeira (RNF08 atendido). Os passos acima permanecem registrados como o desenho de referência efetivamente seguido, não como uma migração ainda pendente.

---

# 10. Casos de Teste

Todos os casos abaixo foram **especificados nesta revisão e confirmados como implementados e validados na auditoria final de fechamento (22/09/2026, ver seção 14)**, exceto os que dependem de funcionalidades explicitamente fora do escopo da v5.0 (gráficos financeiros, RF21–RF23 — nenhum caso desta tabela depende deles). Casos marcados como "preservado"/equivalentes a versões anteriores já existiam e apenas foram confirmados como mantidos.

| ID | Descrição | Resultado Esperado | Equivalente v4.1 |
|---|---|---|---|
| CT01 | Marcar uma ocorrência como paga | `status = pago` e `data_pagamento` preenchida automaticamente com a data atual | CT02 (estendido) |
| CT02 | Alterar a data de pagamento de uma ocorrência já paga, via calendário | Nova data de pagamento salva; não é possível escolher uma data futura | novo |
| CT03 | Reverter uma ocorrência paga para pendente | `status = pendente` e `data_pagamento` removida (nula) | novo |
| CT04 | Marcar agosto como paga em uma série mensal | Setembro, outubro e demais ocorrências da série permanecem `pendente` | novo |
| CT05 | Criar recorrência mensal com âncora em 31/01, sem data de término | Ocorrências geradas em 31/01, 28/02 (ou 29/02 em ano bissexto), 31/03 — sem arrasto do ajuste de fevereiro | novo |
| CT06 | Criar recorrência anual com âncora em 29/02/2028 | Ocorrências em 29/02/2028, 28/02/2029, 28/02/2030, 28/02/2031, 29/02/2032 | novo |
| CT07 | Criar recorrência sem data de término | Sistema gera as ocorrências dos 12 meses seguintes à âncora no momento da criação | novo |
| CT08 | Navegar para um mês futuro além do horizonte já gerado de uma série sem término ativa | O sistema gera sob demanda as ocorrências necessárias para aquele período, sem duplicar ocorrências existentes e sem alterar ocorrências passadas | novo — cobre §5.20 |
| CT09 | Transformar uma conta avulsa em recorrente a partir da sua ocorrência única | Uma nova série é criada com a ocorrência selecionada como âncora; ocorrências futuras passam a ser geradas a partir dela | novo |
| CT10 | Alterar a frequência de uma série de mensal para anual, a partir de uma ocorrência no meio da série que já possui ocorrências futuras mensais geradas além dela, sendo que uma dessas ocorrências futuras já havia sido editada individualmente ("Somente este mês") | Ocorrências anteriores à selecionada permanecem mensais e inalteradas; as ocorrências futuras mensais ainda no padrão da série são ajustadas/substituídas pelas ocorrências da nova frequência anual; a ocorrência editada individualmente é preservada, não sobrescrita | novo — cobre §5.5 |
| CT11 | Editar valor de uma ocorrência de série com escopo "Este mês em diante" | Ocorrência selecionada e futuras atualizadas; ocorrências passadas mantêm o valor anterior; mensagem de confirmação descreve a alteração | CT07 (alterado — mensagem) |
| CT12 | Editar valor de uma ocorrência de série com escopo "Somente este mês" | Apenas a ocorrência selecionada é alterada | CT08 |
| CT13 | Excluir "somente este mês" de uma ocorrência no meio de uma série | Apenas a ocorrência selecionada é removida; anteriores e futuras permanecem | novo |
| CT14 | Excluir "este mês em diante" a partir de uma ocorrência no meio de uma série | Ocorrência selecionada e futuras são removidas; anteriores permanecem no histórico | novo |
| CT15 | Excluir "este mês em diante" a partir da **primeira** ocorrência de uma série | A série inteira é removida sem erro de integridade referencial | novo — cobre a limitação da seção 9.1 |
| CT16 | Encerrar a recorrência de uma série a partir de uma ocorrência futura ainda não realizada, com outras ocorrências futuras já geradas além dela | A ocorrência selecionada e tudo anterior a ela são preservados; as ocorrências estritamente posteriores são removidas; a série para de gerar novas ocorrências; as ocorrências que restam continuam editáveis/excluíveis individualmente | alterado (D7) — anteriormente "Remover recorrência", que não excluía nenhuma ocorrência |
| CT17 | Criar a 30ª categoria de um usuário (contando as pré-criadas) | Categoria criada normalmente | novo |
| CT18 | Tentar criar a 31ª categoria de um usuário | Sistema impede a criação e informa o limite atingido | novo |
| CT19 | Atribuir a uma categoria uma cor já usada por outra categoria ativa do mesmo usuário | Sistema impede a seleção dessa cor para a nova categoria | novo |
| CT20 | Trocar a cor de uma categoria | Cor anterior volta a ficar disponível para outras categorias | novo |
| CT21 | Excluir uma categoria | Cor da categoria volta a ficar disponível; contas associadas ficam sem categoria (`categoria_id = NULL`) | CT existente (comportamento de categoria_id preservado) |
| CT22 | Selecionar emoji de uma categoria pré-criada (ex.: Saúde) | As 5 sugestões definidas para "Saúde" são exibidas; usuário pode escolher outra via seletor do dispositivo | novo |
| CT23 | Selecionar data de término de uma recorrência usando o seletor visual de mês/ano | Data aplicada corretamente; opção "Sem data de término" disponível | CT17 (substitui validação de campo textual) |
| CT24 | Tentar selecionar data de término anterior à data de vencimento inicial | Sistema impede a seleção/exibe erro | CT17 |
| CT25 | Consultar mensagem de vencimento de uma conta que vence hoje/amanhã/em 5 dias | Textos exibidos: "Vence hoje", "Vence amanhã", "Vence em 5 dias" | novo (linguagem) |
| CT26 | Consultar mensagem de uma conta vencida ontem / há 5 dias | Textos exibidos: "Venceu ontem", "Venceu há 5 dias" | novo (linguagem) |
| CT27 | Resumo de 7 dias com exatamente 1 conta a vencer | Texto no singular (ex.: "1 conta vence nos próximos 7 dias") | novo (plural/singular) |
| CT28 | Consultar a Tela Principal com contas em atraso existentes | Banner "Você possui contas em atraso!" exibido, com ação "Ver contas em atraso" | substitui CT12 |
| CT29 | Acessar "Ver contas em atraso" a partir do banner | Tela dedicada lista todas as contas com status `atrasado`, de qualquer mês | substitui CT12 |
| CT30 | Consultar a Tela Principal sem contas em atraso | Banner "Suas contas estão em dia!" exibido | substitui CT13 |
| CT31 | Visualizar título da tela "Suas contas" com setembro selecionado no seletor de mês | Título exibido: "Suas contas de setembro" | novo (RF05) |
| CT32 | Cadastrar nova conta (Única) | Conta salva com sucesso, vinculada ao usuário logado | CT01 (preservado) |
| CT33 | Deixar uma conta pendente vencer sem marcar como paga | Status `atrasado` exibido automaticamente | CT04 (preservado) |
| CT34 | Criar recorrência mensal com data de término definida para 24 meses à frente | Todas as 24 ocorrências são geradas imediatamente na criação, sem limite de 12 meses | novo — corrige §5.3 |
| CT35 | Consultar a indicação de posição em uma ocorrência de série **com** data de término | Exibe "Parcela X de Y", com X e Y corretos | novo — RF26 |
| CT36 | Consultar a indicação de posição em uma ocorrência de série **sem** data de término | Exibe apenas "Parcela X", sem total | novo — RF26 |
| CT37 | Editar "este mês em diante" uma ocorrência de série e, em seguida, navegar até um mês futuro ainda não gerado | A ocorrência recém-gerada para esse mês futuro já nasce com o valor/dado atualizado pelo modelo da série, não com o valor antigo | novo — cobre §9.3 |
| CT38 | Excluir uma categoria e abrir o seletor de categoria em Nova Conta/Edição de Conta | A categoria excluída não aparece mais no seletor; contas que a utilizavam permanecem sem categoria | novo — §5.11 |
| CT39 | Criar uma categoria quando todas as cores da paleta já estão em uso pelo próprio usuário | O sistema informa que não há cor disponível, em vez de duplicar uma cor ou falhar silenciosamente | novo — §5.13 |
| CT40 | Editar uma ocorrência de conta Única (sem série) | A conta é salva diretamente, sem exibir diálogo de escopo | novo — baseline RF10/RF20 |
| CT41 | Encerrar a recorrência a partir de uma ocorrência **passada** (ex.: hoje é setembro/2026, ocorrência selecionada é março/2026) | Todas as ocorrências entre março e setembro de 2026, inclusive, são preservadas (já aconteceram); só as ocorrências de outubro/2026 em diante são removidas; a série para de gerar novas ocorrências | novo — cobre §5.8 (D7) |
| CT42 | Encerrar a recorrência a partir da ocorrência do **mês atual** | A ocorrência do mês atual é preservada; ocorrências futuras são removidas; a série para de gerar novas ocorrências | novo — cobre §5.8 (D7) |
| CT43 | Encerrar a recorrência a partir de uma ocorrência **futura** ainda não realizada | A ocorrência selecionada e tudo anterior a ela (incluindo ocorrências já realizadas) são preservados; só as ocorrências estritamente posteriores à selecionada são removidas | novo — cobre §5.8 (D7) |
| CT44 | Encerrar uma recorrência quando uma das ocorrências futuras que seria removida já está marcada como paga | Essa ocorrência não é excluída, mesmo estando no intervalo que seria removido; permanece no sistema como conta individual | novo — cobre a proteção defensiva de §5.8 (D7) |
| CT45 | Encerrar uma recorrência quando uma das ocorrências futuras que seria removida já tem `data_pagamento` registrada | Essa ocorrência não é excluída | novo — cobre a proteção defensiva de §5.8 (D7) |
| CT46 | Encerrar uma recorrência quando uma das ocorrências futuras que seria removida já foi editada individualmente ("Somente este mês") | Essa ocorrência não é excluída | novo — cobre a proteção defensiva de §5.8 (D7) |
| CT47 | Consultar a seção "Recorrência" em Editar após um encerramento | Exibe "Esta conta não possui recorrência." e a ação "Transformar em recorrente" — a conta é tratada como avulsa; não oferece "Alterar frequência" nem "Encerrar recorrência" | novo — cobre §5.8/§8 |
| CT48 | Usar "Transformar em recorrente" numa conta cuja recorrência já foi encerrada | Uma nova série é criada a partir dessa ocorrência como âncora, com a frequência e término escolhidos pelo usuário; a série antiga (encerrada) permanece intacta no banco, sem ser reaproveitada | novo — cobre §5.8/§5.4 |

---

# 11. Critérios de Aceitação

A v5.0 é considerada atendida quando, para cada frente:

* **Recorrência:** é possível criar séries Única/Mensal/Anual; séries mensais e anuais não apresentam arrasto de data (CT05, CT06); séries com término são geradas integralmente até a data definida, sem cap de 12 meses (CT34); séries sem término geram 12 meses inicialmente e passam a gerar ocorrências adicionais sob demanda quando o usuário navega além do horizonte gerado, sem exigir uma rotina contínua (CT07, CT08).
* **Indicação de posição (RF26):** séries com término mostram "Parcela X de Y"; séries sem término mostram apenas "Parcela X" (CT35, CT36).
* **Granularidade de ações sobre a série:** excluir, alterar frequência e encerrar recorrência funcionam corretamente para qualquer ocorrência da série, incluindo a primeira (CT15); encerrar recorrência nunca apaga histórico já realizado, seja qual for a posição da ocorrência selecionada em relação à data atual, e protege ocorrências futuras com informação histórica relevante (CT41–CT46).
* **Alteração de frequência:** ocorrências futuras já geradas sob a frequência antiga são ajustadas para seguir a nova frequência a partir do ponto de alteração; ocorrências anteriores nunca são tocadas (CT10).
* **Histórico:** nenhuma ação sobre a configuração futura de uma série altera ocorrências passadas, em nenhum dos fluxos acima (CT11, CT13, CT14, CT16, CT37).
* **Pagamento:** toda ocorrência paga possui data de pagamento; reverter para pendente remove essa data; datas futuras são recusadas (CT01–CT03).
* **Status independente:** marcar uma ocorrência como paga nunca altera outras ocorrências da mesma série (CT04).
* **Categorias:** o catálogo de 11 categorias pré-criadas existe desde o primeiro acesso; o limite de 30 é respeitado; cores nunca colidem entre categorias ativas do mesmo usuário; emoji e cor liberados são reutilizáveis; o seletor de categoria em Nova Conta/Edição reflete somente categorias existentes; o sistema informa quando não há cor disponível (CT17–CT22, CT38, CT39).
* **UX de vencimento e atraso:** nenhuma mensagem de vencimento usa a forma "X dia(s)"; a Tela Principal usa banner + tela dedicada para atrasadas (CT25–CT30).
* **RF05:** o título da lista de contas reflete o mês selecionado (CT31).
* **RF15:** o cadastro exige aceite explícito dos Termos de Uso e da Política de Privacidade (checkbox obrigatório, exibido somente no modo Cadastro); sem esse aceite, a conta não é criada; o aceite só é registrado quando efetivamente fornecido pelo usuário.
* **Segurança de senhas (RNF05):** senhas são armazenadas com PBKDF2-HMAC-SHA256 e salt aleatório individual por usuário, nunca em texto puro; hashes no formato legado (anteriores a esta correção) continuam autenticando normalmente e são automaticamente atualizados para o novo formato logo após o primeiro login correto, sem exigir ação do usuário. Validado tanto por testes dedicados quanto pela coexistência real dos dois formatos no banco em uso.
* **Migração:** nenhuma conta, categoria ou usuário existente é perdido ao migrar para a nova arquitetura de séries (RNF08).

---

# 12. Rastreabilidade

Para cada RF da v4.1, o que ocorre nesta versão:

| RF (v4.1) | Situação na v5.0 |
|---|---|
| RF01–RF04 | Permanecem inalterados. |
| RF05 | Alterado (redação) — resolve a pendência registrada na v4.1. **Atendido.** O título dinâmico da Tela Principal ("Suas contas de {mês}") não existia antes desta versão (o cabeçalho era estático) e foi implementado no fechamento desta ERS; a tela "Ver todas as contas" manteve seu título já dinâmico ("{Mês} {Ano}"), sem alteração (ver seção 5.15). |
| RF06 | Estendido — ganha data efetiva de pagamento. Depende de novo campo `data_pagamento` (não depende da nova arquitetura de séries). |
| RF07 | Permanece inalterado. |
| RF08 | Alterado — ganha a terceira opção "Cancelar" (já existente na prática como fechar o diálogo) formalizada, e passa a funcionar para a primeira ocorrência da série. **Depende da nova arquitetura de séries (seção 9).** |
| RF09 | Permanece inalterado (mantido da própria v4.1). |
| RF10 | Substituído — de "sempre mensal, término obrigatório" para "única/mensal/anual, término opcional, sem arrasto, geração incremental". **Depende da nova arquitetura de séries.** |
| RF11 | Alterado (linguagem das mensagens). |
| RF12 | Permanece inalterado. |
| RF13 | Permanece inalterado. |
| RF14 | Estendido — catálogo pré-criado e limite de 30. |
| RF15 | **Atendido** — implementado no fechamento desta versão. Apesar do rótulo "inalterado" herdado da v4.1, o requisito nunca teve interface de consentimento: `termos_aceitos_em` era preenchido automaticamente em todo cadastro, sem checkbox nem bloqueio. Agora o cadastro exige aceite explícito (checkbox obrigatório, cadastro bloqueado sem aceite, registro só quando efetivamente fornecido) — ver critério de aceitação correspondente em §11. Conteúdo jurídico, tela dedicada, versionamento e reconsentimento permanecem fora do escopo desta versão (observação para v6.0). |
| RF16 | **Não aplicável à versão atual — condicionado à versão mobile.** O login por biometria é uma funcionalidade opcional e condicionada à execução do Sino em dispositivo móvel compatível. A versão atual do projeto não contempla distribuição mobile. Portanto, o RF16 não constitui pendência da ERS v5.0 e deverá ser reavaliado caso uma versão mobile do aplicativo seja desenvolvida. |
| RF17 | Alterado (linguagem e plural/singular). |
| RF18 | Estendido — formaliza sugestões de emoji (já previstas conceitualmente) e adiciona cor. |
| RF19 | Permanece inalterado. |
| RF20 | Alterado — mensagem de confirmação em linguagem natural passa a ser exigida. |
| RF21–RF23 | Permanecem inalterados (não implementados); RF21/RF22 passam a depender da paleta de cores definida em RF18 quando forem implementados. |
| RF24 | Permanece inalterado, mas usa o RF06 estendido. |
| RF25 | Substituído (UX) — banner + tela dedicada no lugar da lista embutida. |
| RF26 | Alterado — decisão final registrada nesta consolidação (seção 5.19): "Parcela X de Y" para séries com término, "Parcela X" para séries sem término. **Depende da nova arquitetura de séries.** |
| — | RF27, RF28, RF29 são novas necessidades, decorrentes diretamente das decisões de produto desta revisão (seções 6, 4 e 8 da consolidação de decisões). Todas dependem da nova arquitetura de séries. |

**Requisitos que dependem da nova arquitetura de séries (seção 9):** RF08, RF10, RF26, RF27, RF28, RF29.
**Requisitos que não dependem da nova arquitetura:** RF06 (data de pagamento é campo isolado em `contas`), RF14/RF18 (categorias), RF05/RF11/RF17/RF25 (mudanças de leitura/UX sobre dados já existentes).

---

# 13. Plano de Desenvolvimento

| Etapa | Depende de | Observação |
|---|---|---|
| 1. Revisão e aprovação desta ERS | — | Concluída. |
| 2. Migração de arquitetura (`series_recorrencia`, `data_pagamento`, `categorias.cor`) | Etapa 1 | Pré-requisito de RF08, RF10, RF27, RF28, RF29. Deve seguir o plano da seção 9.5 e respeitar RNF08. |
| 3. Recorrência mensal/anual sem arrasto e sem término obrigatório (RF10) | Etapa 2 | Inclui geração incremental (seção 9.4). |
| 4. Ações granulares sobre séries: exclusão (RF08), alteração de frequência (RF27), transformar em recorrente (RF28), encerrar recorrência (RF29, revisão D7) | Etapa 2 | Depende da nova arquitetura já estar disponível. |
| 5. Data efetiva de pagamento (RF06/RF24) | Etapa 2 (apenas o campo) | Pode ser desenvolvida em paralelo à etapa 3/4. |
| 6. Categorias: catálogo pré-criado, limite de 30, emoji sugerido, cor (RF14/RF18) | Etapa 2 (apenas o campo `cor`) | Catálogo e limite não dependem de schema novo além da coluna `cor`. |
| 7. UX: banner de atrasadas + tela dedicada (RF25), mensagens naturais (RF11/RF17), título dinâmico (RF05), seletor visual de término (RF10), indicação de posição adaptada ao tipo de série (RF26) | Etapas 3–6 | Majoritariamente mudanças de interface sobre dados já existentes ou já migrados. |
| 8. Testes | Etapas 2–7 | Cobrir a tabela da seção 10. |

**Nota de fechamento (22/09/2026):** todas as etapas acima (1–8) estão concluídas. A auditoria final de rastreabilidade (seção 14) confirmou, requisito a requisito, que o código e o banco de dados reais correspondem ao planejado nesta tabela.

Itens já entregues antes desta ERS (RF01–04, RF07, RF09, RF12, RF13, RF19, CRUD básico de categorias) permanecem como estão e não fazem parte deste plano.

RF05 e RF15, apesar de rotulados como "inalterado"/"já entregue" em revisões anteriores desta ERS, exigiram implementação real no fechamento desta versão: o comportamento descrito no texto do requisito não correspondia ao código até a auditoria final de rastreabilidade (22/09/2026, ver seção 14). Essa divergência entre rótulo histórico e comportamento real foi identificada e corrigida nesse fechamento — ver seção 12 para o estado final de cada um.

---

# 14. Pendências e Decisões Técnicas

Esta seção foi atualizada na consolidação final (01/09/2026) e revisada novamente na decisão D7 (05/09/2026, ver abaixo). **Não há nenhuma decisão de produto pendente.** As duas questões que permaneciam em aberto após a auditoria da v5.0 foram fechadas na consolidação final:

* A preservação de ocorrências editadas individualmente diante de uma alteração de frequência (RF27) — decisão final registrada nas seções 5.1 e 5.5: a edição individual sempre prevalece sobre um ajuste mecânico posterior da série.
* O tratamento de `data_pagamento` para contas já pagas antes da migração — deixou de ser uma questão em aberto: o aplicativo ainda está em desenvolvimento, não há dados de produção com contas previamente pagas, e a regra de preenchimento de `data_pagamento` (seção 5.10) já cobre integralmente o comportamento a partir da implementação da v5.0 (ver seção 9.5, item 3).

## Decisão D7 (05/09/2026) — revisão de RF29/§5.8, "Remover recorrência" → "Encerrar recorrência"

Registrada após a validação manual do fluxo de edição de recorrência ter revelado que a redação original de RF29 ("nenhuma ocorrência já existente é excluída — passadas ou futuras") não correspondia à expectativa de uso: o usuário esperava que encerrar uma recorrência também deixasse de exibir as parcelas futuras ainda não realizadas, não apenas impedisse a geração de novas.

**Decisão final, registrada objetivamente:**

1. A ação passa a se chamar "Encerrar recorrência" em toda a interface e na documentação — "Remover recorrência" não é mais usada.
2. A ação passa a excluir ocorrências futuras ainda não realizadas, o que a versão anterior do RF29 proibia explicitamente. Esta é uma reversão deliberada e final dessa proibição, não uma reinterpretação de texto.
3. Histórico já realizado nunca é apagado: o ponto de corte usado é sempre o mais tardio entre a data da ocorrência selecionada e a data atual — nunca apenas a ocorrência selecionada isoladamente. Isso é o que impede que encerrar uma recorrência a partir de uma ocorrência passada apague ocorrências que já aconteceram entre aquele mês e hoje.
4. A ocorrência selecionada pelo usuário é sempre preservada, nunca excluída por esta ação.
5. Ocorrências futuras que, mesmo estando no intervalo removido, tenham informação histórica relevante (pagas, com `data_pagamento`, ou editadas individualmente) são preservadas em vez de apagadas — proteção técnica, sem exigir decisão adicional do usuário.
6. A representação técnica reaproveita `series_recorrencia.ativa = 0` (já existente, seção 9.2) para "a série não gera mais ocorrências" — nenhum campo novo foi introduzido.
7. Esta decisão altera o texto de §5.8 e a linha de RF29 na seção 6 diretamente (diferente de decisões técnicas anteriores como D1–D6, que não exigiram reabrir o texto da ERS). As demais seções desta ERS, incluindo D1–D6, permanecem como estavam — esta revisão não as reabre.

Esta decisão está fechada e não deve ser reaberta durante a implementação.

Os pontos abaixo são **decisões de implementação** (não de produto) e não bloqueiam a aprovação desta ERS — ficam a critério do desenvolvedor, desde que o comportamento observável descrito nas seções 5 e 9 seja respeitado:

* Nomes exatos de campos e se o mesmo registro de `series_recorrencia` é atualizado in-place ou substituído ao alterar a frequência de uma série (seção 9.3);
* Gatilho técnico exato da geração sob demanda (seção 9.4) — síncrono na consulta, ou geração antecipada de um bloco maior;
* Paleta definitiva de cores (códigos hex/RGB) e ajustes finos de nomes/emojis das categorias pré-criadas (seções 5.12, 5.13) — explicitamente deferidos para a etapa de implementação/UX por decisão já tomada, não é um ponto pendente de aprovação de produto.

## Fechamento da v5.0 — Auditoria Final (22/09/2026)

Após a implementação, foi realizada uma auditoria final confrontando cada requisito da v5.0 (Regras de Negócio §5.1–§5.20, Requisitos Funcionais RF01–RF29, Requisitos Não Funcionais RNF01–RNF08) diretamente com o código (`backend/main.py`, `database/db.py`) e com o schema/dados reais de `database/sino.db` — não apenas com os rótulos históricos de rastreabilidade desta ERS, que em alguns pontos não refletiam o estado real do código. As divergências encontradas foram corrigidas nesta revisão documental. Resumo do fechamento:

* **RF05** — implementado (título dinâmico da Tela Principal). Ver seção 5.15 e rastreabilidade (seção 12).
* **RF15** — implementado (aceite obrigatório dos Termos de Uso/Política de Privacidade no cadastro). Ver rastreabilidade (seção 12) e critério de aceitação (seção 11). Conteúdo jurídico completo, tela dedicada, versionamento do texto aceito e reconsentimento **não fazem parte desta versão** — permanecem como observação para uma futura ERS v6.0.
* **RF16** — **não aplicável à versão atual, condicionado à versão mobile.** O login por biometria é uma funcionalidade opcional e condicionada à execução do Sino em dispositivo móvel compatível. A versão atual do projeto não contempla distribuição mobile. Portanto, o RF16 não constitui pendência da ERS v5.0 e deverá ser reavaliado caso uma versão mobile do aplicativo seja desenvolvida — sem presumir, desde já, que ele fará parte de uma eventual ERS v6.0.
* **RF21–RF23** (gráficos financeiros) — confirmados como não implementados, permanecendo **explicitamente fora do escopo da v5.0** (ver seção 3, Escopo). Esta ausência não impede o fechamento desta versão.
* **RNF05** — **atendido.** Senhas passaram a ser armazenadas com PBKDF2-HMAC-SHA256 e salt aleatório individual por usuário (nunca em texto puro), com compatibilidade para hashes no formato legado (anteriores a esta correção) e rehash automático para o formato novo logo após o primeiro login correto de cada conta, sem exigir nenhuma ação do usuário nem migração manual dos dados existentes. Ver critério de aceitação correspondente em seção 11, dada a relevância deste ponto para a segurança do sistema.
* **RNF06** (operações comuns em até 2 segundos) — mantido como requisito, sem alteração de texto. Nenhuma evidência de violação foi encontrada na auditoria, mas **não foi realizado um benchmark formal** desta versão contra o critério de 2 segundos; a ausência de medição é registrada aqui como uma limitação da validação realizada, não como uma falha funcional comprovada.
* **RNF07** (cópia de segurança local) — **atendido dentro do escopo restrito já existente.** O requisito, com redação genérica ("manter cópia de segurança local dos dados"), não define frequência, gatilho ou política de retenção. A implementação atual mantém um mecanismo de backup local acionado antes de migrações de schema (proteção da migração para a arquitetura de séries desta ERS). Uma rotina de backup periódico/automático, com política formal de frequência e retenção, não é exigida por este requisito na redação atual e fica registrada como observação para especificação futura (ERS v6.0), não como pendência desta versão.
* **RF08/RF20** — os textos de diálogo citados nas seções 5.6/5.7 (por exemplo, "Aplicar alteração a:" e "O que você deseja excluir?") foram ajustados nesta revisão para deixar explícito que descrevem a intenção do diálogo, não uma exigência literal de texto de interface — mesmo tratamento já dado a emoji/cor de categorias (seções 5.12/5.13). O comportamento funcional (opções, escopo, proteção de histórico) já estava correto e não foi alterado.

**Nenhum requisito novo foi criado nesta auditoria.** As correções acima são exclusivamente de rastreabilidade/redação, refletindo comportamento já implementado e validado manualmente antes desta revisão documental.

---

# Histórico de Versões

| Versão | Data | Alterações |
|---|---|---|
| 1.0 | 28/07/2025 | Primeira versão da especificação. |
| 2.0 | 03/08/2026 | Revisão geral: categorias, controle de usuário, status automático de atraso, backup. |
| 3.0 | 09/08/2026 | Revisão baseada nos protótipos de tela: termos de uso, biometria, resumo semanal, ícones, criação a partir de categoria, escopo de edição de contas fixas, gráficos financeiros. |
| 4.0 | 21/08/2026 | Revisão baseada na implementação da Tela Nova Conta: filtro do Total do Mês, contas atrasadas vinculadas ao mês original, seção "Contas atrasadas", indicação de parcela. Seção de rastreabilidade introduzida. |
| 4.1 | 27/08/2026 | Revisão documental: RF09 simplificado (remoção do filtro de proximidade), alinhamento textual do RF17, atualização da rastreabilidade, registro da pendência do RF05. |
| 5.0 | 01/09/2026 | Revisão estrutural completa: recorrência única/mensal/anual sem arrasto, com término opcional (RF10); arquitetura de séries aprovada (`series_recorrencia`) para corrigir a limitação do `serie_id` autorreferenciado, habilitando exclusão da primeira ocorrência, alteração de frequência (RF27, novo) e remoção de recorrência (RF29, novo) sem excluir ocorrências; transformação de conta avulsa em recorrente (RF28, novo); data efetiva de pagamento (RF06 estendido); catálogo de 11 categorias pré-criadas e limite de 30 (RF14 estendido); emoji sugerido e cor exclusiva por categoria (RF18 estendido); banner de contas em atraso com tela dedicada substituindo a lista embutida (RF25); mensagens de vencimento em linguagem natural com singular/plural corretos (RF11/RF17); correção da redação do RF05, resolvendo a pendência da v4.1. **Consolidação final (mesma data):** fechadas as decisões de RF26 (Parcela X de Y para séries com término, Parcela X para séries sem término — seção 5.19), geração integral de séries com término sem cap de 12 meses (seção 5.3, corrige inconsistência C1 da auditoria), ajuste das ocorrências futuras ao alterar a frequência de uma série (RF27, seção 5.5), geração sob demanda ao navegar para períodos futuros de séries sem término (seção 5.20, substitui a ideia de rotina periódica), disponibilidade das categorias no seletor de conta (seção 5.11), e remoção de `conta_fixa`/`repetir_ate` de `contas` em favor da entidade de série (seção 9.2). **Segunda rodada da consolidação final (mesma data):** registrada a decisão de que edição individual de uma ocorrência ("Somente este mês") prevalece sobre ajuste mecânico futuro da série, incluindo alteração de frequência (RF27, seções 5.1 e 5.5); removida a falsa pendência sobre `data_pagamento` histórico pré-migração — não há dados de produção a tratar (seção 9.5). Seção 14 não lista mais nenhuma decisão de produto em aberto, apenas pontos de implementação. Nenhuma alteração de código, banco de dados ou interface foi realizada nesta etapa — esta versão é somente especificação. **Decisão D7 (05/09/2026):** revisão de RF29/§5.8 após validação manual — "Remover recorrência" passa a se chamar "Encerrar recorrência" e passa a remover ocorrências futuras ainda não realizadas a partir da ocorrência selecionada (o que a redação anterior proibia), preservando sempre o histórico já ocorrido, a ocorrência selecionada, e ocorrências futuras com informação histórica relevante (pagas, com data de pagamento, ou editadas individualmente). Ver seção 14 para o registro completo da decisão; nenhuma outra decisão (D1–D6) foi reaberta. |
| 5.0 | 22/09/2026 | **Fechamento documental pós-implementação.** Auditoria final de rastreabilidade confrontando toda a ERS (Regras de Negócio, RFs, RNFs) com o código e o banco de dados reais. RF05 e RF15 corrigidos de "inalterado"/"já entregue" para "atendido", com a implementação real registrada (título dinâmico da Tela Principal e aceite obrigatório dos Termos de Uso/Política de Privacidade, respectivamente); RF16 registrado como "não aplicável à versão atual — condicionado à versão mobile"; RF21–RF23 confirmados fora do escopo da v5.0; RNF05 registrado como atendido (PBKDF2-HMAC-SHA256 com salt individual e migração automática de hashes legados); RNF07 documentado dentro do escopo restrito já existente (backup de proteção da migração, sem rotina periódica); RNF06 registrado sem benchmark formal, sem falha comprovada; textos de diálogo das seções 5.6/5.7 ajustados para não exigir frase literal. Ver seção 14 ("Fechamento da v5.0 — Auditoria Final") para o registro completo. Nenhum requisito novo foi criado nesta revisão. |
