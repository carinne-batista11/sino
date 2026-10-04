# Especificação de Requisitos de Software (ERS)

## Projeto: Aplicativo de Controle de Contas — Sino

**Autora:** Carinne Batista
**Versão:** 6.0
**Data:** 23 de setembro de 2026
**Versão anterior:** 5.0 (fechada e auditada em 22/09/2026)
**Status:** **Concluída para portfólio e demonstração local (04/10/2026)**, com requisitos parciais e itens adiados para uso por terceiros separados na seção 13.6. Especificação fechada: todas as decisões de produto estão tomadas (seção 13.1).
**Atualização de estado (04/10/2026):** situação das Etapas 8, 9 e 10 em 13.3, 13.4 e 13.5; encerramento da v6.0 (Etapas 11 e 12, rastreabilidade dos testes) em 13.6. Decisões novas da Etapa 10: confirmação de senha no cadastro (P11) e Detalhes com campos fixos (P12); nenhuma outra regra foi alterada.

---

## Como ler este documento

Esta ERS descreve o Sino **como ele deve ser ao final da v6.0** e é autossuficiente: as regras herdadas da v5.0 aparecem resumidas, sem a narrativa das revisões anteriores. O histórico detalhado das decisões continua na ERS v5.0, preservada sem alterações.

Convenções:

* **[v5]**: regra herdada da v5.0 sem mudança de comportamento.
* **[v6 alterado]**: regra da v5.0 modificada nesta versão.
* **[v6 novo]**: regra criada nesta versão.
* **Pn**: decisão de produto fechada nesta versão (registro na seção 13.1).
* **Tn**: decisão técnica de implementação, sem impacto no comportamento especificado (seção 13.2).

---

# 1. Identificação

| Campo | Valor |
|---|---|
| Projeto | Sino — Aplicativo de Controle de Contas |
| Documento | Especificação de Requisitos de Software (ERS) |
| Versão | 6.0 |
| Autora | Carinne Batista |
| Data | 23/09/2026 |
| Versão anterior | 5.0 |
| Status | Especificação fechada |

---

# 2. Objetivo

O Sino é uma ferramenta pessoal para registrar e controlar contas financeiras: nome, valor, vencimento, categoria, recorrência, status e data de pagamento.

A v6.0 tem quatro objetivos:

1. **Acesso mais rápido às contas**: a Tela Principal mostra todas as contas do mês, com atalho direto para edição.
2. **Consulta mais clara**: tela Detalhes reformulada e consulta por status concentrada em "Ver status".
3. **Análise financeira**: tela Gráfico com evolução dos gastos, distribuição por categoria e comparação com o período anterior (RF21–RF23).
4. **Gestão da conta do usuário**: tela Ajustes com nome, e-mail verificado, senha, tema, documentos e sessão.

---

# 3. Escopo

## 3.1 Dentro do escopo da v6.0

* Tela Principal: Total do mês sem filtros, todas as contas do mês e atalho ✏️;
* Tela "Ver status" (substitui "Ver todas");
* Reformulação da tela Detalhes da conta;
* Descrição opcional da conta e limites de caracteres;
* Tela Gráfico: total do período, total pago, RF21, RF22, RF23 e agrupamento "Sem categoria";
* Tela Ajustes: nome, e-mail com verificação, alterar senha, tema claro/escuro, Termos de Uso, Política de Privacidade, sair e excluir conta;
* Senha mínima de 8 caracteres e recuperação de senha por código enviado por e-mail;
* Revisão geral de consistência visual;
* Atividade documental: melhoria do README.md (seção 14.3).

## 3.2 Fora do escopo da v6.0

* **Telefone**, em qualquer forma: cadastro, verificação, login, recuperação de senha, SMS, WhatsApp e notificações relacionadas ao telefone. Pode ser reconsiderado em uma evolução futura.
* **Biometria (RF16)**: só será reconsiderada se existir uma evolução mobile que a justifique.
* **"Usar tema do sistema"**: a v6.0 oferece apenas Claro e Escuro.
* **Versionamento de Termos e Política e reconsentimento**: podem ser avaliados em uma evolução futura.
* Todos os itens do Banco de Ideias (seção 14.1).
* Política completa de backup (seção 14.2), salvo aprovação explícita.

---

# 4. Visão Geral da v6.0

| Bloco | O que muda |
|---|---|
| Tela Principal | Total do mês sem filtros; todas as contas do mês com rolagem normal; atalho ✏️; acesso a "Ver status" |
| Ver status | Consulta do mês por status: Todas, Pendentes, Pagas, Atrasadas |
| Detalhes da conta | Hierarquia visual, emoji e cor da categoria, status junto do pagamento, Editar/Excluir discretos |
| Contas | Descrição opcional; limites de caracteres |
| Gráfico | Total do período, total pago, RF21, RF22, RF23, períodos vazios |
| Ajustes | Conta, segurança, aparência, documentos, sessão |
| Autenticação | E-mail verificado por código, senha mínima, alterar senha, esqueci minha senha, excluir conta |
| Aparência | Tema claro/escuro |
| Documentação | README.md do repositório |

---

# 5. Regras de Negócio

## Parte A — Recorrência, pagamento e categorias

### 5.1 Preservação do histórico [v5]

Alterações na configuração futura de uma recorrência nunca modificam ocorrências anteriores. Somente uma ação explícita do usuário sobre uma ocorrência específica pode alterá-la.

* Uma edição feita com o escopo "Somente este mês" é histórico: nenhum ajuste mecânico posterior da série (como alteração de frequência) a sobrescreve.
* Status e data de pagamento pertencem exclusivamente à ocorrência. Nenhuma ação sobre a série os altera.

### 5.2 Tipos de recorrência e âncora [v5]

Tipos: **Única**, **Mensal** e **Anual**. Em Mensal e Anual, a ocorrência inicial é a **âncora** e define o dia (e, na anual, também o mês) seguido pelas demais.

* **Mensal, sem arrasto:** se o mês não tem o dia da âncora, usa-se o último dia válido; o mês seguinte volta ao dia da âncora. Ex.: 31/01 → 28/02 (29/02 em ano bissexto) → 31/03.
* **Anual, sem arrasto:** âncora em 29/02 vira 28/02 nos anos não bissextos e volta a 29/02 nos bissextos. Ex.: 29/02/2028 → 28/02/2029 → … → 29/02/2032.

### 5.3 Horizonte de geração [v5]

* **Com data de término:** todas as ocorrências até o término são geradas na criação, sem limite de 12 meses.
* **Sem data de término:** a criação gera as ocorrências dos 12 meses seguintes à âncora; os períodos posteriores são gerados sob demanda (5.20).

### 5.4 Transformar conta avulsa em recorrente [v5]

A ocorrência única vira âncora de uma nova série. O usuário escolhe frequência e término, e não há ocorrências anteriores a incorporar.

### 5.5 Alterar frequência [v5]

* Aplica-se sempre a partir da ocorrência selecionada, que vira a nova âncora.
* Ocorrências anteriores não mudam.
* Ocorrências futuras geradas no padrão antigo são substituídas pelas da nova frequência, **exceto** as editadas individualmente, que são preservadas.

### 5.6 Escopo de edição em séries [v6 alterado]

Ao editar uma ocorrência de série, o sistema pergunta como aplicar a alteração. **[v6]** O diálogo passa a valer para **nome, valor, vencimento, categoria e descrição** (antes: apenas nome, valor e data), inclusive quando vários desses campos são alterados juntos.

* **Somente este mês** (pré-selecionado): altera só a ocorrência selecionada;
* **Este mês em diante**: altera a selecionada, as futuras já existentes e o modelo da série, para que ocorrências ainda não geradas já nasçam com os novos dados.

Ocorrências anteriores nunca mudam. Após salvar, uma mensagem em linguagem natural descreve o que mudou (ex.: "Você alterou o valor de R$ 150,00 para R$ 180,00."). O texto exato dos diálogos é decisão de UX.

* Para a descrição, "alterar" inclui adicionar e remover (P3).
* Como o Gráfico usa a categoria efetiva de cada ocorrência (5.28), uma mudança de categoria se reflete nos gráficos conforme o escopo escolhido (P7).

Uma conta Única é salva diretamente, sem diálogo de escopo.

### 5.7 Excluir ocorrência de série [v5]

Opções: **Somente este mês**, **Este mês em diante** e **Cancelar**. Funciona inclusive para a primeira ocorrência. A palavra "inativar" nunca aparece na interface. Uma conta Única é excluída diretamente.

### 5.8 Encerrar recorrência [v5]

A partir da ocorrência selecionada:

* a série deixa de gerar ocorrências;
* a ocorrência selecionada é sempre preservada;
* o corte para remoção é o **mais tardio** entre a data da ocorrência selecionada e a data atual, de modo que nada já realizado é apagado;
* ocorrências futuras pagas, com data de pagamento ou editadas individualmente são preservadas;
* as ocorrências restantes passam a ser contas avulsas.

Para voltar a ter recorrência, usa-se "Transformar em recorrente" (5.4), que cria uma série nova.

### 5.9 Status independente por ocorrência [v5]

Marcar uma ocorrência como paga nunca altera outra ocorrência da mesma série.

### 5.10 Data de pagamento [v5]

* Ao marcar como paga, a data atual é registrada;
* a data pode ser alterada por calendário, sem permitir datas futuras;
* ao voltar para pendente, a data é removida.

### 5.11 Categorias: catálogo e limite [v6 alterado]

* 11 categorias pré-criadas desde o cadastro: Casa, Automóvel, Lazer, Faculdade, Academia, Saúde, Cartão de crédito, Beleza, Streaming, Creche e Outro.
* Limite de **30 categorias** por usuário, contando as pré-criadas.
* **[v6]** Nome da categoria com no máximo **30 caracteres** (5.23).
* O seletor de categoria mostra somente as categorias existentes.
* Excluir uma categoria não exclui contas: elas ficam sem categoria.

### 5.12 Emoji da categoria [v5]

Cada categoria tem um emoji, com 5 sugestões por categoria pré-criada e acesso ao seletor completo do dispositivo. As sugestões são uma proposta de UX e podem ser ajustadas.

### 5.13 Cor da categoria [v6 alterado]

* Paleta de até 30 cores distintas; uma cor não pode ser usada por duas categorias ativas do mesmo usuário.
* A cor volta a ficar disponível quando a categoria troca de cor ou é excluída.
* Se não houver cor disponível, o sistema informa o usuário.
* **[v6]** A cor da categoria é a mesma usada nos gráficos (RF22); não existe paleta separada para gráficos.
* **[v6]** O **cinza** é reservado ao agrupamento "Sem categoria" (5.25) e não pode ser atribuído a nenhuma categoria.

### 5.14 Contas em atraso [v5]

A Tela Principal exibe um banner: "Você possui contas em atraso!" com a ação "Ver contas em atraso", ou "Suas contas estão em dia!". A tela "Contas em atraso" lista atrasadas de **qualquer mês**. Uma conta paga nunca aparece como atrasada.

### 5.15 Contas do mês na Tela Principal [v6 alterado]

* O cabeçalho é dinâmico: "Suas contas de [mês]".
* **[v6]** A lista exibe **todas** as contas do mês selecionado. O limite anterior de 5 contas deixa de existir.
* **[v6]** Com muitas contas, usa-se a **rolagem vertical normal da página**. Não há paginação, "Carregar mais" nem rolagem interna na lista.
* **[v6]** A ação "Ver status" fica ao lado do cabeçalho (5.21).
* **[v6]** Cada conta oferece três interações:
  * clique na conta → Detalhes da conta;
  * ✏️ → Editar conta diretamente;
  * controle de pagamento → marcar ou desmarcar como paga.
* O ✏️ segue o mesmo padrão visual e as mesmas dimensões do controle de pagamento.
* **[v6]** A estrutura e a ordem geral dos blocos da Tela Principal são preservadas. A v6.0 altera somente os elementos acima e o bloco Total do mês (5.16) (P10).

### 5.16 Total do mês na Tela Principal [v6 alterado]

* **[v6]** O bloco não tem mais os filtros Todas / Pendentes / Pagas.
* O valor exibido é a soma de **todas** as contas registradas no mês, independentemente do status.
* Uma conta atrasada continua contando no total do mês do seu vencimento original.

### 5.17 Mensagens de vencimento [v5]

"Vence hoje", "Vence amanhã", "Vence em X dias", "Venceu ontem" e "Venceu há X dias". O resumo dos próximos 7 dias respeita singular e plural.

### 5.18 Seletor de término [v5]

Seletor visual de mês e ano, com a opção "Sem data de término". Não permite término anterior ao vencimento inicial.

### 5.19 Posição na série [v5]

"Parcela X de Y" em séries com término; "Parcela X" em séries sem término.

### 5.20 Geração sob demanda [v5]

Ao navegar para um período futuro ainda sem ocorrências de uma série ativa e sem término, o sistema gera as ocorrências necessárias, sem duplicar e sem tocar no histórico.

> **[v6]** A navegação na tela Gráfico **não** dispara essa geração: o Gráfico representa apenas contas já registradas (5.26, P7).

## Parte B — Regras novas da v6.0

### 5.21 Ver status [v6 novo]

"Ver status" substitui "Ver todas" e é uma tela de **consulta por status**. Como todas as contas já aparecem na Tela Principal, ela não existe para compensar nenhum limite.

* Acesso ao lado de "Suas contas de [mês]";
* mês e ano de referência exibidos com clareza;
* filtros **Todas | Pendentes | Pagas | Atrasadas**, com mais destaque e botões maiores que os atuais;
* os filtros valem para o mês de referência. A tela "Contas em atraso" (5.14) continua existindo para atrasadas de qualquer mês.

### 5.22 Descrição da conta [v6 novo]

* Campo **Descrição (opcional)**, com até 500 caracteres;
* disponível em Nova Conta; pode ser adicionada, editada ou removida em Editar conta;
* aparece em Detalhes **sempre**, em linha inteira, completa e com as quebras de linha; quando vazia, o campo exibe "Sem descrição" (8.4, P12);
* em contas recorrentes, participa do diálogo de escopo (5.6) ao ser adicionada, alterada ou removida. Com "Este mês em diante", o modelo da série também recebe a descrição e as novas ocorrências nascem com ela (P3).

### 5.23 Limites de caracteres [v6 novo]

| Campo | Máximo |
|---|---|
| Nome do usuário | 70 |
| Nome da conta | 30 |
| Nome da categoria | 30 |
| Descrição da conta | 500 |

São regras de validação, aplicadas também na gravação, e não apenas características visuais dos campos. Valores acima do limite são impedidos, com mensagem amigável.

* A contagem considera o caractere percebido pelo usuário: um emoji conta como um caractere, independentemente de quantos bytes ou pontos de código ocupa internamente.
* Dados existentes nunca são cortados ou modificados automaticamente. Um registro já gravado acima do limite continua sendo exibido normalmente; ao ser editado, só pode ser salvo depois de respeitar o limite (P4).
* O nome do usuário já é obrigatório no cadastro, junto com e-mail e senha, e pode ser alterado em Ajustes → Conta (P5).

### 5.24 Totais da tela Gráfico [v6 novo]

* **Total do mês**: soma de todas as contas registradas no mês.
* **Total do ano**: soma de todas as contas registradas no ano, inclusive contas futuras que já existem nesse período.
* Pago, pendente ou atrasado **não altera** a composição dos totais nem de nenhum gráfico de gastos.
* **Total pago**: informação complementar ao total, exibida como valor pago, total e percentual com barra de progresso. Ex.: "R$ 2.000 de R$ 2.340 pagos — 85,5%". Não interfere no cálculo dos gráficos.

### 5.25 Agrupamento "Sem categoria" [v6 novo]

Contas sem categoria formam, nos gráficos, o agrupamento lógico **Sem categoria**:

* nome fixo, sem emoji, cor cinza reservada;
* não é editável nem excluível;
* não aparece na tela Categorias;
* aparece nos gráficos somente quando há contas sem categoria no período;
* ocupa sempre a última posição.

A representação interna é decisão técnica (T1).

### 5.26 Períodos da tela Gráfico [v6 novo]

* **Mensal:** navegação "‹ Setembro de 2026 ›".
* **Anual:** navegação "‹ 2026 ›", apenas entre anos com histórico. Anos completamente sem contas não aparecem.
* O Gráfico representa somente contas já registradas. Abrir ou navegar pela tela não gera ocorrências recorrentes; a geração sob demanda (5.20) não se aplica aqui (P7).

### 5.27 RF21 — Evolução dos gastos [v6 novo]

Duas perspectivas: **6 meses | Anual**.

* **6 meses:** o mês selecionado e os cinco meses anteriores. Ex.: com setembro selecionado, Abr | Mai | Jun | Jul | Ago | Set. Meses sem contas aparecem com R$ 0,00, e o mês selecionado recebe destaque.
* **Anual:** o total de cada ano com histórico (5.26), com base no total do ano definido em 5.24.

### 5.28 RF22 — Gastos por categoria [v6 novo]

* Cada categoria utilizada no período é exibida com emoji, nome, valor e percentual, na própria cor da categoria.
* Categorias sem contas no período não aparecem; "Sem categoria" segue 5.25.
* Cada conta é contada pela **categoria efetiva da ocorrência** naquele período. Se a categoria for alterada, o gráfico acompanha o escopo escolhido em 5.6 (P7).
* **Percentual** = total da categoria ÷ total do período × 100. O status de pagamento não altera o cálculo.
* **Exibição:** a casa decimal aparece só quando necessária (ex.: 42%, 24,5%, 8,3%).
* Não há ajuste artificial para que os percentuais arredondados somem exatamente 100%.

### 5.29 RF23 — Comparação com o período anterior [v6 novo]

Componente compacto, não um gráfico. Compara o mês selecionado com o mês imediatamente anterior, ou o ano selecionado com o ano imediatamente anterior, sempre pelos totais do período (5.24), e não pelos valores pagos.

* **Variação** = (total atual − total anterior) ÷ total anterior × 100, acompanhada da diferença absoluta. Ex.: "Comparado a agosto — ▲ 12% — R$ 250,00 a mais".

| Situação | Exibição |
|---|---|
| Aumento | ▲ X% e "R$ … a mais" |
| Redução | ▼ X% e "R$ … a menos" |
| Totais iguais | "0% — Sem alteração" |
| Total anterior zero e atual maior que zero | Sem percentual: "Não há base de comparação" e "R$ … a mais" |
| Ambos zero | "Sem gastos nos dois períodos." |

### 5.30 Períodos sem contas [v6 novo]

Quando o período selecionado não tem contas:

* Total: R$ 0,00 e Total pago: R$ 0,00;
* os gráficos não exibem dados artificiais;
* indicadores percentuais aparecem como 0% quando aplicável;
* a interface exibe uma mensagem de estado vazio, como "Ainda não há dados para exibir neste período." (P7).

### 5.31 E-mail e verificação [v6 novo]

* O login continua sendo **e-mail + senha**.
* **Cadastro:** o e-mail de todo novo cadastro é verificado por código (5.32). A senha é digitada duas vezes ("Senha" e "Confirmar senha"); se as duas forem diferentes, aparece "As senhas não coincidem." e nenhum código é pedido nem nada é gravado (P11).
* **Alteração de e-mail**, em Ajustes:
  * não é permitido usar um endereço já associado a outra conta;
  * o e-mail atual continua válido enquanto o novo não for confirmado;
  * somente após a confirmação o novo endereço passa a ser usado.
* A verificação comprova acesso ao endereço; não se tenta descobrir externamente se ele "existe".
* Os envios usam um serviço externo de e-mail, com opção gratuita adequada ao projeto (P1, T4, RNF11).
* Os usuários atuais são usuários de teste, preservados para testes e regressão. Não há regra de migração para usuários legados (P2).

### 5.32 Código de verificação [v6 novo]

A mesma regra vale para verificação de e-mail (5.31) e recuperação de senha (5.35):

* código numérico de **6 dígitos**;
* validade de **10 minutos**; código expirado não pode ser utilizado;
* no máximo **5 tentativas**; esgotadas as tentativas, o código deixa de valer e é preciso solicitar um novo;
* reenvio permitido após **60 segundos**; um novo código invalida imediatamente o anterior;
* um código já utilizado fica inválido;
* validação correta conclui a operação (endereço verificado ou liberação da nova senha).

### 5.33 Senha [v6 novo]

* Mínimo de **8 caracteres** em novos cadastros, na alteração de senha e na recuperação de senha.
* Senhas definidas antes da v6.0 continuam permitindo login; a regra passa a valer sempre que uma nova senha é definida.
* O armazenamento segue RNF05 (PBKDF2-HMAC-SHA256 com salt individual).

### 5.34 Alterar senha [v6 novo]

Fluxo: Ajustes → Alterar senha → Senha atual → Nova senha → Confirmar nova senha.

* senha atual obrigatória; se estiver incorreta, nada é alterado;
* nova senha com no mínimo 8 caracteres;
* confirmação obrigatória e idêntica à nova senha;
* a nova senha deve ser diferente da atual;
* o sucesso é informado ao usuário.

### 5.35 Esqueci minha senha [v6 novo]

Fluxo: Login → Esqueci minha senha → E-mail → Código → Nova senha → Confirmação → Login.

* O código é enviado ao e-mail verificado da conta e segue 5.32.
* A nova senha segue 5.33, com confirmação obrigatória.
* A resposta ao informar o e-mail é sempre neutra, para não revelar se o endereço tem conta: "Se o e-mail informado estiver associado a uma conta, você receberá um código para redefinir sua senha."

### 5.36 Tema claro/escuro [v6 novo]

Em Ajustes → Aparência: **Claro | Escuro**.

* Claro é o padrão inicial.
* A escolha fica salva para o usuário e é aplicada sem exigir novo login.
* Login, Cadastro e recuperação de senha usam sempre o tema Claro, pois nenhum usuário está autenticado.
* Após o login, o Sino carrega a preferência do usuário; ao sair da conta, volta ao tema Claro (P8).
* A identidade visual do Sino é preservada; fundos, superfícies, cards, textos, campos e diálogos são adaptados.
* Categorias e status continuam distinguíveis entre si.
* As cores das categorias são preservadas nos gráficos.
* Contraste e legibilidade são garantidos (RNF09), incluindo uma adaptação adequada do cinza de "Sem categoria".

### 5.37 Termos e Política de Privacidade [v6 novo]

Em Ajustes → Sobre e Privacidade, o usuário pode consultar os Termos de Uso e a Política de Privacidade dentro do Sino. Isso complementa o aceite obrigatório no cadastro (RF15). Na v6.0 não há versionamento dos documentos nem reconsentimento quando o texto mudar (P9).

### 5.38 Sair da conta [v6 novo]

Encerra a sessão atual e volta à autenticação. Nenhum dado é removido.

### 5.39 Excluir conta [v6 novo]

Fluxo: Ajustes → Excluir conta → Aviso → Senha atual → Confirmação final → Exclusão.

* exige usuário autenticado e senha atual;
* exige confirmação final; nunca acontece com um único clique;
* a exclusão é permanente, sem recuperação após a confirmação;
* remove os dados associados ao usuário;
* encerra a sessão e volta ao Login;
* tem aparência de ação destrutiva, separada de "Sair da conta".

A estratégia técnica de exclusão e dos relacionamentos no banco é decisão técnica (T2).

---

# 6. Requisitos Funcionais

**Implementação:** ✅ implementado e verificado (testes automáticos; validação manual quando registrada em 13.3–13.6) · 🧪 implementado e validado localmente, com a entrega real de e-mails adiada para uso por terceiros (13.3, 13.6) · ⏸️ fora do escopo / não aplicável.

Marcadores revisados em 04/10/2026 no encerramento da v6.0, conforme as evidências da seção 13.6. A Etapa 10 não tem RF próprio: seu estado (incluindo RNF09) está em 13.5.

## 6.1 Requisitos vigentes (RF01–RF29)

| ID | Descrição | Situação | Impl. |
|---|---|---|---|
| RF01 | Criar conta de usuário com nome, e-mail verificado por código e senha de no mínimo 8 caracteres, com confirmação da senha. | v6 alterado (5.31, 5.33, P11) | 🧪 |
| RF02 | Login com e-mail e senha. | v5 | ✅ |
| RF03 | Associar as contas financeiras ao usuário logado. | v5 | ✅ |
| RF04 | Cadastrar conta com nome, valor, vencimento, categoria e, opcionalmente, descrição. | v6 alterado (5.22) | ✅ |
| RF05 | Listar **todas** as contas do mês selecionado na Tela Principal, com rolagem normal da página e título "Suas contas de [mês]". | v6 alterado (5.15) | ✅ |
| RF06 | Marcar como paga ou pendente, com data de pagamento. | v5 (5.10) | ✅ |
| RF07 | Editar conta, incluindo a descrição. | v6 alterado (5.22) | ✅ |
| RF08 | Excluir conta, com escopo em séries. | v5 (5.7) | ✅ |
| RF09 | Tela "Ver status" com filtros Todas, Pendentes, Pagas e Atrasadas para o mês de referência. | v6 alterado (5.21) | ✅ |
| RF10 | Recorrência Única/Mensal/Anual, sem arrasto e com término opcional. | v5 (5.2, 5.3, 5.18, 5.20) | ✅ |
| RF11 | Mensagens de vencimento em linguagem natural. | v5 (5.17) | ✅ |
| RF12 | Exibir o total do mês na Tela Principal, somando todas as contas do mês, sem filtros de status. | v6 alterado (5.16) | ✅ |
| RF13 | Status `atrasado` automático. | v5 | ✅ |
| RF14 | CRUD de categorias, catálogo de 11, limite de 30 e nome com até 30 caracteres. | v6 alterado (5.11) | ✅ |
| RF15 | Aceite obrigatório de Termos e Política no cadastro. | v5 | ✅ |
| RF16 | Login por biometria. | condicionado a evolução mobile | ⏸️ |
| RF17 | Resumo das contas dos próximos 7 dias. | v5 (5.17) | ✅ |
| RF18 | Emoji e cor exclusiva por categoria, com cinza reservado a "Sem categoria". | v6 alterado (5.13) | ✅ |
| RF19 | Criar conta a partir de uma categoria. | v5 | ✅ |
| RF20 | Escopo de edição em séries para nome, valor, vencimento, categoria e descrição, com mensagem de confirmação. | v6 alterado (5.6) | ✅ |
| RF21 | Evolução dos gastos nas perspectivas "6 meses" e "Anual". | v6 especificado (5.27) | ✅ |
| RF22 | Distribuição do total do período por categoria. | v6 especificado (5.28, 5.25) | ✅ |
| RF23 | Comparação compacta com o período anterior. | v6 especificado (5.29) | ✅ |
| RF24 | Marcar como paga na tela de Detalhes. | v5 | ✅ |
| RF25 | Banner de atraso e tela "Contas em atraso". | v5 (5.14) | ✅ |
| RF26 | "Parcela X de Y" / "Parcela X". | v5 (5.19) | ✅ |
| RF27 | Alterar frequência de uma série. | v5 (5.5) | ✅ |
| RF28 | Transformar conta avulsa em recorrente. | v5 (5.4) | ✅ |
| RF29 | Encerrar recorrência. | v5 (5.8) | ✅ |

## 6.2 Requisitos novos (RF30–RF43)

| ID | Descrição | Regra | Impl. |
|---|---|---|---|
| RF30 | Exibir em cada conta da Tela Principal um atalho ✏️ que abre Editar conta; o clique na conta abre Detalhes. | 5.15 | ✅ |
| RF31 | Exibir Detalhes da conta com hierarquia visual, emoji e cor da categoria, status junto da ação de pagamento e campos fixos, incluindo a descrição (P12). | 8.4 | ✅ |
| RF32 | Permitir descrição opcional da conta, com até 500 caracteres. | 5.22 | ✅ |
| RF33 | Validar os limites de caracteres de nome do usuário, nome da conta, nome da categoria e descrição. | 5.23 | ✅ |
| RF34 | Exibir a tela Gráfico com navegação mensal/anual, total do período, total pago e estado de período vazio. | 5.24, 5.26, 5.30 | ✅ |
| RF35 | Exibir e permitir alterar o nome do usuário em Ajustes. | 5.23 | ✅ |
| RF36 | Exibir e permitir alterar o e-mail, com verificação por código. | 5.31, 5.32 | 🧪 |
| RF37 | Exigir senha com no mínimo 8 caracteres sempre que uma senha for definida. | 5.33 | ✅ |
| RF38 | Permitir alterar a senha em Ajustes. | 5.34 | ✅ |
| RF39 | Permitir recuperar a senha por código enviado ao e-mail, a partir do Login. | 5.35 | 🧪 |
| RF40 | Permitir escolher tema Claro ou Escuro. | 5.36 | ✅ |
| RF41 | Permitir consultar Termos de Uso e Política de Privacidade em Ajustes. | 5.37 | ✅ |
| RF42 | Permitir sair da conta sem remover dados. | 5.38 | ✅ |
| RF43 | Permitir excluir definitivamente a conta de usuário, com senha e confirmação final. | 5.39 | ✅ |

---

# 7. Requisitos Não Funcionais

| ID | Descrição | Situação |
|---|---|---|
| RNF01 | Interface simples, responsiva e utilizável em diferentes tamanhos de tela. | v5 |
| RNF02 | Armazenamento local dos dados do aplicativo. | v5 (exceção: o envio de e-mails usa um serviço externo, 5.31) |
| RNF03 | Desempenho satisfatório com até 1000 contas por usuário. | v5 (inclui a Tela Principal sem limite de contas); medido em 04/10/2026, atendido na camada medida ([desempenho-v6.md](desempenho-v6.md), 13.6) |
| RNF04 | Aplicação leve e de fácil instalação. | v5 |
| RNF05 | Senhas com PBKDF2-HMAC-SHA256 e salt individual, nunca em texto puro; hashes legados são atualizados no primeiro login. | v5 |
| RNF06 | Operações comuns em até 2 segundos. | v5; medido em 04/10/2026, atendido na camada medida, sem a renderização da janela ([desempenho-v6.md](desempenho-v6.md), 13.6) |
| RNF07 | Backup local dos dados (hoje: backup antes de migrações). | v5; política completa fora do escopo (14.2) |
| RNF08 | Migrações de schema preservam integralmente os dados existentes. | v5; vale para as migrações da v6.0 |
| RNF09 | Nos dois temas, textos, status, categorias, gráficos e "Sem categoria" permanecem legíveis, distinguíveis e com contraste adequado. | v6 novo; verificado nos testes, com os limites de 13.6 |
| RNF10 | Códigos de verificação têm validade, limite de tentativas e uso único (5.32), e nunca são exibidos em registros ou mensagens de erro. | v6 novo |
| RNF11 | Credenciais, chaves e segredos do serviço de e-mail ficam fora do código-fonte e do repositório GitHub. | v6 novo |

---

# 8. Interface e UX

## 8.0 Diretrizes gerais [v6 novo]

A v6.0 inclui uma revisão de consistência visual entre Tela Principal, Detalhes, Gráfico e Ajustes. Os pontos observados são: identidade verde do Sino, harmonia de cores, legibilidade, tamanho e hierarquia de botões, mensagens e diálogos, tema escuro e gráficos. A paleta de categorias da v5.0 deve ser preservada, e não reconstruída sem necessidade.

## 8.1 Tela Principal

* Bloco **Total do mês**: apenas o valor total, sem filtros;
* banner de atraso e resumo dos próximos 7 dias;
* cabeçalho **"Suas contas de [mês]"**, com **Ver status** ao lado;
* lista com **todas** as contas do mês, usando a rolagem normal da página;
* em cada conta, o controle de pagamento e o ✏️, com o mesmo tamanho e a mesma identidade visual;
* a estrutura e a ordem geral dos blocos permanecem como estão hoje.

## 8.2 Ver status

Mês e ano de referência visíveis; filtros Todas | Pendentes | Pagas | Atrasadas em destaque, com botões maiores.

## 8.3 Contas em atraso

Mantida da v5.0: lista de atrasadas de qualquer mês, aberta pelo banner.

## 8.4 Detalhes da conta

Exemplo conceitual:

```
🌐 Internet Claro
Internet

Valor          | Vencimento
R$ 190,42      | 05/09/2026

Categoria      | Parcela
Internet       | Parcela 1 de 49

Recorrência
Esta conta se repete mensalmente até setembro de 2030.

Descrição
(texto completo, em linha inteira; vazia: "Sem descrição")

🔴 Atrasado  | ✓ Marcar como paga

        [ Editar ]  [ Excluir ]
```

* A identificação usa **emoji e cor da categoria**; não existe sistema separado de ícones por conta.
* Status e ação de pagamento ficam lado a lado:
  * 🔴 Atrasado | ✓ Marcar como paga
  * Pendente | ✓ Marcar como paga
  * 🟢 Pago | Desmarcar como paga
* **Editar** e **Excluir** ficam no rodapé: menores que os atuais, do mesmo tamanho e centralizados. Excluir mantém a aparência destrutiva.
* **Conta Única:** mantém o comportamento atual, com a informação "Esta conta não é recorrente", sem nova representação.
* **Conta sem categoria:** exibe "Sem categoria" no padrão cinza, sem emoji e sem emoji genérico ou substituto, no mesmo conceito dos gráficos (5.25).
* **Campos fixos (P12, 04/10/2026, Etapa 10):** Detalhes exibe sempre, nesta ordem, Valor, Vencimento, Categoria, Parcela, Recorrência e Descrição. Em janela larga, Valor e Vencimento ficam lado a lado, assim como Categoria e Parcela; em janela estreita, os campos se empilham. Recorrência e Descrição ocupam sempre a linha inteira, com quebra de texto e altura automática; a Descrição usa o mesmo tamanho de fonte da Recorrência, sem negrito. Ícones e rótulos ficam centralizados na altura de cada campo. Cada campo tem ícone no mesmo verde, com fundo suave, e o rótulo fica à esquerda do conteúdo; quando não há espaço para isso sem apertar o valor, o rótulo passa para cima do conteúdo. Sem informação, o campo continua na tela, no cinza secundário:

  | Campo | Sem informação | Observação |
  |---|---|---|
  | Categoria | "Sem categoria" | 5.25 |
  | Parcela | "Não há parcelas" | conta Única e série encerrada (5.8); série ativa sem término mostra "Parcela X" (5.19) |
  | Recorrência | "Esta conta não é recorrente." | conta Única e série encerrada (5.8, P6) |
  | Descrição | "Sem descrição" | 5.22 |

  Só a apresentação muda: regras e dados de categoria, parcela, recorrência e descrição continuam os mesmos.

## 8.5 Nova Conta / Editar conta

* Campo **Descrição (opcional)**, com indicação do limite;
* validação de limites com mensagem amigável;
* seção "Recorrência" mantida da v5.0.

## 8.6 Gráfico

A tela é dedicada à análise de gastos e não tem filtros Todas / Pendentes / Pagas.

```
Gráfico
  Mensal | Anual        ‹ Setembro de 2026 ›
  Total do período  +  Total pago
  Evolução dos gastos     (6 meses | Anual)
  Gastos por categoria
  Comparação com período anterior
```

Em período sem contas: totais zerados, indicadores em 0% quando aplicável e a mensagem de estado vazio, sem dados artificiais (5.30). A navegação não gera ocorrências recorrentes (5.26).

## 8.7 Ajustes

```
CONTA
  👤 Nome
  ✉️ E-mail

SEGURANÇA
  🔒 Alterar senha

APARÊNCIA
  🌙 Tema — Claro / Escuro

SOBRE E PRIVACIDADE
  📄 Termos de Uso
  🛡️ Política de Privacidade

CONTA E SESSÃO
  🚪 Sair da conta
  🗑️ Excluir conta
```

## 8.8 Login e Cadastro

* Login: e-mail + senha, com o link **Esqueci minha senha**;
* Cadastro: nome, e-mail, senha mínima de 8 caracteres com confirmação ("Confirmar senha", P11), aceite de Termos e Política (RF15) e verificação do e-mail por código;
* todas as telas de autenticação usam o tema Claro.

---

# 9. Modelo de Dados

## 9.1 Base herdada da v5.0

* `series_recorrencia`: configuração da série (frequência, âncora, término, `ativa`, modelo de nome/valor/categoria, `horizonte_gerado_ate`);
* `contas`: ocorrências, com `serie_id` referenciando `series_recorrencia`, além de `data_pagamento` e `editado_individualmente`;
* `categorias`: inclui `cor`.

## 9.2 Alterações previstas na v6.0

Os nomes são proposta de referência. Ajustes que não mudem o comportamento especificado não são decisão de produto.

| Tabela | Alteração | Origem |
|---|---|---|
| `contas` | `descricao` (texto, nulo, até 500) | 5.22 |
| `series_recorrencia` | `descricao` no modelo da série | 5.6, 5.22 |
| `usuarios` | limite de 70 caracteres em `nome` (campo já existente e obrigatório) | 5.23 |
| `usuarios` | indicador de e-mail verificado | 5.31 |
| `usuarios` | preferência de tema (padrão: claro) | 5.36 |
| nova (ex.: `codigos_verificacao`) | usuário, finalidade (verificação de e-mail / recuperação de senha), código armazenado de forma segura (ex.: hash), e-mail de destino, expiração, tentativas, utilizado | 5.32 — implementado de outra forma: os códigos ficam no serviço; localmente, `autorizacoes_usadas` (schema v8). Ver 13.3 |
| a definir | representação de "Sem categoria" | T1 |

Toda migração segue RNF08, com backup prévio.

---

# 10. Casos de Teste

## 10.1 Regressão

Os casos CT01–CT48 da ERS v5.0 continuam válidos como suíte de regressão.

## 10.2 Casos novos da v6.0

| ID | Descrição | Resultado esperado | Ref. |
|---|---|---|---|
| CT49 | Tela Principal com contas pagas, pendentes e atrasadas no mês | Total do mês soma todas; o bloco não tem filtros | RF12 |
| CT50 | Mês com 12 contas | As 12 aparecem, com rolagem normal da página, sem paginação nem rolagem interna | RF05 |
| CT51 | Abrir "Ver status" | Mês e ano de referência visíveis; quatro filtros | RF09 |
| CT52 | Filtro Atrasadas em "Ver status" | Somente as atrasadas do mês de referência | RF09 |
| CT53 | Tocar no ✏️ | Abre Editar conta diretamente | RF30 |
| CT54 | Tocar na conta | Abre Detalhes | RF30 |
| CT55 | Detalhes de conta com categoria | Emoji e cor da categoria na identificação | RF31 |
| CT56 | Detalhes de conta pendente, atrasada e paga | "Marcar como paga" nas duas primeiras; "Desmarcar como paga" na paga | RF31 |
| CT57 | Detalhes de conta sem descrição | Campo Descrição em linha inteira com "Sem descrição" (P12) | RF31, 8.4 |
| CT58 | Adicionar, editar e remover descrição | Cada operação é refletida em Detalhes | RF32 |
| CT59 | Descrição com 501 caracteres | Bloqueada, com mensagem amigável | RF33 |
| CT60 | Nome da conta com 31 caracteres | Bloqueado, com mensagem amigável | RF33 |
| CT61 | Nome da categoria com 31 caracteres | Bloqueado, com mensagem amigável | RF33 |
| CT62 | Nome do usuário com 71 caracteres | Bloqueado, com mensagem amigável | RF33, RF35 |
| CT63 | Total do mês no Gráfico com contas em todos os status | Soma todas | RF34 |
| CT64 | Total do ano com contas futuras já existentes no ano | Contas futuras entram no total | RF34 |
| CT65 | Marcar uma conta como paga e voltar ao Gráfico | Total e gráficos inalterados; só o Total pago muda | 5.24 |
| CT66 | R$ 2.000 pagos de R$ 2.340 | "R$ 2.000 de R$ 2.340 pagos — 85,5%" | RF34 |
| CT67 | Período sem contas | Total e Total pago em R$ 0,00; mensagem de estado vazio; nenhum dado artificial | 5.30 |
| CT68 | RF21 "6 meses" com setembro selecionado | Abr a Set; meses sem contas com R$ 0,00; setembro destacado | RF21 |
| CT69 | RF21 "Anual" com contas em 2024 e 2026, sem contas em 2025 | 2025 não aparece | RF21 |
| CT70 | RF22 com categoria sem contas no período | A categoria não aparece | RF22 |
| CT71 | RF22 com contas sem categoria | "Sem categoria" em cinza, sem emoji, na última posição | 5.25 |
| CT72 | RF22 sem contas sem categoria | "Sem categoria" não aparece | 5.25 |
| CT73 | RF22 com categoria de R$ 490 em total de R$ 2.000 | 24,5% | 5.28 |
| CT74 | RF22 com categoria de R$ 840 em total de R$ 2.000 | 42% (sem casa decimal) | 5.28 |
| CT75 | Tela Categorias | "Sem categoria" não é listada | 5.25 |
| CT76 | Escolher a cor de uma categoria | O cinza reservado não está disponível | 5.13 |
| CT77 | RF23 com R$ 2.090 → R$ 2.340 | ▲ 12% e R$ 250,00 a mais | RF23 |
| CT78 | RF23 com totais iguais | "0% — Sem alteração" | RF23 |
| CT79 | RF23 com anterior R$ 0 e atual R$ 500 | "Não há base de comparação" e "R$ 500,00 a mais", sem percentual | RF23 |
| CT80 | RF23 com os dois períodos zerados | "Sem gastos nos dois períodos." | RF23 |
| CT81 | Senha de 7 caracteres no cadastro, na alteração e na recuperação | Recusada nos três fluxos | RF37 |
| CT82 | Login de usuário com senha anterior à v6.0 e menor que 8 caracteres | Login funciona normalmente | 5.33 |
| CT83 | Alterar senha com a senha atual incorreta | Nada é alterado | RF38 |
| CT84 | Alterar senha com confirmação diferente | Recusado | RF38 |
| CT85 | Alterar senha para a mesma senha atual | Recusado | RF38 |
| CT86 | Alterar senha com dados válidos | Senha alterada e sucesso informado | RF38 |
| CT87 | Alterar e-mail sem validar o código | O novo endereço não é considerado válido | RF36 |
| CT88 | Validar o código correto em até 10 minutos | Endereço verificado | RF36 |
| CT89 | Usar um código após 10 minutos | Recusado | 5.32 |
| CT90 | Errar o código 5 vezes | O código deixa de valer; é preciso solicitar outro | 5.32 |
| CT91 | Reenviar o código e usar o anterior | O anterior é recusado | 5.32 |
| CT92 | Reutilizar um código já validado | Recusado | 5.32 |
| CT93 | Esqueci minha senha com e-mail cadastrado e com e-mail não cadastrado | Mesma mensagem neutra nos dois casos | RF39 |
| CT94 | Recuperação completa com código válido | Nova senha definida e aceita no Login | RF39 |
| CT95 | Trocar para tema Escuro | Aplicado imediatamente, sem novo login, com legibilidade | RF40 |
| CT96 | Sair e entrar novamente após trocar o tema | O tema escolhido é mantido | RF40 |
| CT97 | Primeiro acesso de um usuário | Tema Claro | RF40 |
| CT98 | Abrir Termos de Uso e Política em Ajustes | Documentos exibidos dentro do Sino | RF41 |
| CT99 | Sair da conta e entrar novamente | Volta à autenticação; os dados continuam lá | RF42 |
| CT100 | Excluir conta e cancelar em qualquer etapa | Nada é excluído | RF43 |
| CT101 | Excluir conta com a senha atual incorreta | Exclusão não ocorre | RF43 |
| CT102 | Excluir conta com senha correta e confirmação final | Dados do usuário removidos, sessão encerrada, retorno ao Login; o login antigo não funciona mais | RF43 |
| CT103 | Alterar a categoria de uma ocorrência de série com "Somente este mês" | Só a ocorrência muda; o Gráfico daquele mês reflete a nova categoria; outros meses inalterados | 5.6, 5.28 |
| CT104 | Alterar a categoria com "Este mês em diante" | Selecionada, futuras e modelo mudam; meses anteriores preservados; o Gráfico acompanha | 5.6 |
| CT105 | Adicionar descrição com "Este mês em diante" e navegar até um mês ainda não gerado de série sem término | A ocorrência gerada nasce com a descrição | 5.6, 5.22 |
| CT106 | Remover a descrição com "Somente este mês" | Só a ocorrência selecionada perde a descrição | 5.6 |
| CT107 | Alterar nome, valor, categoria e descrição de uma vez | Um único diálogo de escopo, aplicado a todos os campos; a mensagem descreve as alterações | 5.6 |
| CT108 | Nome de conta com 30 caracteres, incluindo um emoji composto (ex.: 👩‍💻) | O emoji conta como um caractere; nome aceito | 5.23 |
| CT109 | Editar um registro já gravado acima do limite | Exibido sem corte; só é salvo depois de respeitar o limite | 5.23 |
| CT110 | Novo cadastro | Exige verificação do e-mail por código | RF01 |
| CT111 | Alterar o e-mail para um endereço de outra conta | Recusado | RF36 |
| CT112 | Alterar o e-mail e entrar antes de confirmar o novo | Login com o e-mail atual continua funcionando | RF36 |
| CT113 | Pedir reenvio de código antes de 60 segundos | Reenvio indisponível até completar 60 segundos | 5.32 |
| CT114 | Navegar no Gráfico até um mês futuro sem ocorrências de uma série sem término | Nenhuma ocorrência é gerada | 5.26 |
| CT115 | Detalhes de uma conta Única | Exibe os seis campos, com "Não há parcelas" e "Esta conta não é recorrente" (P12) | 8.4 |
| CT116 | Detalhes de uma conta sem categoria | "Sem categoria" em cinza, sem emoji | 8.4 |
| CT117 | Usuário com tema Escuro sai da conta | Login em tema Claro; ao entrar de novo, o Escuro é carregado | 5.36 |
| CT118 | Cadastro com "Confirmar senha" diferente da senha | "As senhas não coincidem."; nenhum código é pedido e nada é gravado | 5.31, P11 |

---

# 11. Critérios de Aceitação

A v6.0 está atendida quando:

* **Tela Principal:** total sem filtros; todas as contas do mês com rolagem normal; ✏️ abre Editar e o clique abre Detalhes (CT49–CT50, CT53–CT54).
* **Ver status:** mês de referência visível e os quatro filtros funcionando (CT51–CT52).
* **Detalhes:** hierarquia visual, emoji e cor da categoria, status junto do pagamento, campos fixos com textos de ausência (CT55–CT57, P12).
* **Campos:** descrição gerenciável e todos os limites validados com mensagem amigável (CT58–CT62).
* **Gráfico:** totais independentes de status; total pago complementar; RF21, RF22 e RF23 com todos os casos de borda; período vazio sem dados artificiais; "Sem categoria" conforme 5.25 (CT63–CT80).
* **Senha e e-mail:** senha mínima, alterar senha, verificação de e-mail e recuperação conforme 5.31–5.35 (CT81–CT94).
* **Tema, documentos e sessão:** tema persistido e legível, Termos e Política acessíveis, sair e excluir conta conforme 5.36–5.39 (CT95–CT102).
* **Escopo de edição:** categoria e descrição seguem o diálogo de escopo das séries, e o Gráfico acompanha a categoria efetiva (CT103–CT107).
* **Complementos:** contagem por caractere percebido, dados existentes preservados, verificação no cadastro, regras de alteração de e-mail, reenvio após 60 segundos, Gráfico sem geração de ocorrências, Detalhes de conta Única e sem categoria, tema Claro na autenticação (CT108–CT117) e confirmação de senha no cadastro (CT118).
* **Regressão:** CT01–CT48 da v5.0 continuam passando.
* **Migração:** nenhum dado perdido (RNF08).

---

# 12. Rastreabilidade v5.0 → v6.0

| Requisito | Situação na v6.0 |
|---|---|
| RF02, RF03, RF06, RF08, RF10, RF11, RF13, RF15, RF17, RF19, RF24–RF29 | Inalterados |
| RF01 | Alterado: e-mail verificado por código e senha mínima de 8 caracteres |
| RF20 | Alterado: escopo de edição inclui categoria e descrição |
| RF04, RF07 | Alterados: descrição opcional |
| RF05 | Alterado: todas as contas do mês, com rolagem normal |
| RF09 | Alterado: "Ver todas" vira "Ver status" |
| RF12 | Alterado: sem filtros de status |
| RF14 | Alterado: limite de 30 caracteres no nome |
| RF16 | Continua condicionado a uma evolução mobile |
| RF18 | Alterado: cinza reservado; cor reutilizada nos gráficos |
| RF21–RF23 | Especificados e dentro do escopo (estavam fora na v5.0) |
| RF30–RF43 | Novos |
| RNF01–RNF08 | Mantidos |
| RNF09–RNF11 | Novos |

---

# 13. Decisões

## 13.1 Decisões de produto fechadas nesta versão

Nenhuma decisão de produto está pendente. As pendências P1–P10 foram fechadas e incorporadas às regras; P11 e P12 foram decididas na Etapa 10:

| ID | Tema | Decisão | Onde |
|---|---|---|---|
| P1 | Envio de e-mail | Serviço externo com opção gratuita adequada; segredos fora do código e do GitHub | 5.31, RNF11, T4 |
| P2 | E-mail verificado | Cadastro verificado por código; e-mail de outra conta recusado; e-mail atual vale até a confirmação do novo; reenvio após 60 segundos; usuários atuais são de teste, sem migração | 5.31, 5.32 |
| P3 | Descrição em séries | Participa do diálogo de escopo; "Este mês em diante" atualiza o modelo da série | 5.6, 5.22 |
| P4 | Limites e dados existentes | Nada é cortado automaticamente; a edição exige respeitar o limite; contagem por caractere percebido | 5.23 |
| P5 | Nome do usuário | Já obrigatório no cadastro; máximo de 70; editável em Ajustes; sem migração | 5.23, RF35 |
| P6 | Detalhes | Conta Única mantém "Esta conta não é recorrente"; conta sem categoria em cinza, sem emoji | 8.4 |
| P7 | Gráfico | Não gera ocorrências; estado vazio sem dados artificiais; usa a categoria efetiva; categoria segue o diálogo de escopo | 5.6, 5.26, 5.28, 5.30 |
| P8 | Tema antes do login | Autenticação sempre em Claro; preferência carregada após o login; volta a Claro ao sair | 5.36 |
| P9 | Termos e Política | Consulta em Ajustes; sem versionamento nem reconsentimento na v6.0 | 5.37, 3.2 |
| P10 | Tela Principal | Estrutura e ordem dos blocos preservadas | 5.15 |
| P11 | Confirmação de senha no cadastro (03/10/2026, Etapa 10) | Campo "Confirmar senha" no mesmo padrão do campo de senha; comparação exata, depois das regras de 5.33; senhas diferentes mostram "As senhas não coincidem." sem pedir código nem gravar; o campo fica bloqueado durante o envio do código, como os demais | 5.31, 8.8, RF01, CT118 |
| P12 | Detalhes com campos fixos (04/10/2026, Etapa 10) | Sempre Valor, Vencimento, Categoria, Parcela, Recorrência e Descrição, nesta ordem; ausência mostrada como "Sem categoria", "Não há parcelas", "Esta conta não é recorrente." e "Sem descrição"; Descrição em linha inteira; ícones no mesmo verde; rótulo à esquerda do conteúdo, ou acima em janela estreita. Substitui "descrição só quando preenchida" (5.22) | 5.22, 8.4, CT57, CT115 |

## 13.2 Decisões técnicas

Ficam a critério da implementação, desde que o comportamento especificado seja respeitado:

* **T1** Representação interna de "Sem categoria" (NULL ou outra solução). Antes da implementação, confirmar que nenhuma categoria existente usa um cinza da paleta atual.
* **T2** Estratégia de exclusão da conta de usuário e dos relacionamentos no banco (contas, séries, categorias, códigos de verificação). Situação em 03/10/2026: exclusão explícita em uma única transação, sem `ON DELETE CASCADE` nem migração; `autorizacoes_usadas` preservada (13.4).
* **T3** Paleta definitiva do tema escuro, respeitando 5.36 e RNF09.
* **T4** Serviço de envio de e-mail: escolha entre SMTP e API e do provedor, desde que haja opção gratuita adequada ao projeto e que os segredos sigam RNF11. Situação em 02/10/2026: serviço próprio de códigos com envio pela API da Resend, implementado e ainda não publicado (13.3).
* **T5** Forma de contar o caractere percebido (por exemplo, por agrupamentos de grafemas), aplicada igualmente na interface e na gravação.

## 13.3 Estado da Etapa 8 (02/10/2026)

Registro de situação, sem mudança de regra. Detalhes técnicos no [contrato do serviço](contrato-servico-codigos.md); validações em [validacao-etapa8.md](validacao-etapa8.md).

**Resumo:** a **entrega local de códigos** (serviço no próprio computador, caixa de desenvolvimento e modo de demonstração) está **concluída e validada**. A **publicação para outras pessoas** (serviço publicado, entrega real de e-mails, hospedagem e revisões) está **pendente**. A Etapa 8, como um todo, **não está concluída**.

**Implementado**

* Serviço próprio de códigos (`servidor/`, TypeScript em Cloudflare Workers com Durable Objects): gera, envia e confere os códigos com as regras de 5.32 e limites contra abuso; envio pela API da Resend. Não conhece contas, senhas nem dados financeiros.
* O app recebe uma autorização assinada (Ed25519), conferida localmente, e registra o uso único em `autorizacoes_usadas` (schema v8), na mesma transação da operação.
* Cadastro com verificação (RF01), alteração de e-mail com senha atual e código (RF36) e recuperação de senha em três passos, com resposta neutra (RF39). O login continua local (e-mail e senha conferidos no computador).
* Textos dos e-mails definidos em `servidor/src/envio/mensagens.ts`; limites e retenção do serviço definidos no contrato v1.
* Sem o serviço configurado, cadastro, alteração de e-mail e recuperação mostram "A confirmação por e-mail não está disponível nesta instalação." e não são concluídos; o login funciona. Nesta versão não há endereço nem chave de produção configurados no app.
* Correção: fechar a janela durante uma gravação local não deixa mais o processo preso; a gravação termina de forma atômica. Não há fechamento seguro da janela (`prevent_close`), previsto na Etapa 10.
* Ferramentas de desenvolvimento: caixa local de mensagens e modo de demonstração (`servidor/README.md`). Na demonstração, a conta fica com o e-mail verificado no banco demonstrativo, mas isso **não comprova** acesso ao endereço.

**Entrega local de códigos — concluída e validada**

* Testes automáticos do app e do serviço.
* Validação manual com o serviço local e a caixa de desenvolvimento (cadastro, recuperação, alteração de e-mail, código errado, tentativas esgotadas, reenvio, expiração recusada pelo app, neutralidade, rolagem, carregamento e cancelamento), fechamento durante gravação e demonstração local, com as ressalvas registradas em [validacao-etapa8.md](validacao-etapa8.md).
* Casos de teste: CT90, CT91, CT93, CT94, CT110 e CT113 também validados manualmente; CT92, CT111 e CT112 cobertos pelos testes automáticos.

**Publicação para outras pessoas — pendente**

* Entrega real de e-mails pela Resend, hospedagem e publicação do serviço.
* Decisões: empresa de hospedagem e responsável pela operação do serviço publicado; domínio e remetente de envio; tratamento e retenção dos dados pelos provedores de hospedagem e de envio; limites adicionais contra abuso.
* Termos de Uso e Política de Privacidade atualizados em 02/10/2026, aguardando revisão da autora e revisão jurídica. *(04/10/2026: revisão da autora concluída; revisão jurídica pendente — ver 13.6.)*
* P9 (sem versionamento dos documentos nem novo aceite) continua valendo; precisa ser revista **antes do uso por outras pessoas**, porque o texto mudou de forma relevante na Etapa 8.
* O cadastro continua dependente do serviço de códigos; em desenvolvimento, o caminho documentado é o modo de demonstração. Não há cadastro sem verificação.
* Etapa 10: fechamento seguro da janela, pendências de UX da Etapa 8 (falha transitória na gravação exige novo código, formulário editável durante o envio, contador do reenvio, confirmação de senha no cadastro) e RNF09.

## 13.4 Estado da Etapa 9 (03/10/2026)

Registro de situação, sem mudança de regra. **Excluir conta (RF43) implementado e validado**; a revisão dos textos dos Termos e da Política continua pendente.

**Implementado**

* Ajustes → Conta e sessão → **Excluir conta**, com aparência destrutiva e separado de "Sair da conta". Três passos: aviso com as quantidades de contas, séries e categorias (informativas; incluem as ocorrências futuras já geradas das séries), senha atual e confirmação final com botão destrutivo. Cancelar em qualquer passo não altera nada.
* T2: a senha é conferida no segundo passo, e a pendência guarda só a impressão do hash. Na confirmação, uma única transação (`BEGIN IMMEDIATE`) relê o usuário, confere de novo a impressão e apaga contas → séries → categorias → usuário, sempre pelo `usuario_id`. As chaves estrangeiras ficam como rede de segurança; qualquer falha desfaz tudo. Sem `ON DELETE CASCADE` nem migração.
* `autorizacoes_usadas` é preservada (não identifica usuários). A exclusão não alcança backups existentes, o serviço de códigos, o provedor de envio nem cópias externas.
* `PRAGMA secure_delete = ON` na transação, como medida adicional; não é garantia de apagamento em backups, journals, snapshots ou no dispositivo.
* Ao concluir, a sessão é encerrada e o Login mostra "Sua conta foi excluída.". Operações assíncronas da sessão antiga não atualizam a interface depois da exclusão.
* Termos (itens 4 e 6) e Política (itens 2, 8 e 10) atualizados em 03/10/2026; P9 mantida.

**Validação**

* Testes automáticos: exclusão completa; outros usuários preservados (registros e relações); senha incorreta; senha alterada entre os passos; usuário inexistente; falha no meio; referência cruzada; banco ocupado; interface (CT100–CT102); legibilidade nos dois temas; gravação assíncrona pendente da sessão antiga.
* Validação visual em cópia isolada do banco: item nos dois temas, cancelamento nos três passos (CT100), senha errada (CT101), exclusão com retorno ao Login e recusa do login antigo (CT102), conferência dos dados dos demais usuários e de outra conta. Banco real e backups inalterados.
* Ressalva: o texto da mensagem "Sua conta foi excluída." no Login tem cobertura automática, sem confirmação visual.

**Pendente**

* Revisão da autora e revisão jurídica dos Termos e da Política (03/10/2026); P9 deve ser revista antes do uso por outras pessoas. *(04/10/2026: revisão da autora concluída; revisão jurídica pendente — ver 13.6.)*

## 13.5 Estado da Etapa 10 (04/10/2026)

Registro de situação. **Revisão de UX e legibilidade implementada e validada**; duas decisões de produto novas (P11 e P12, em 13.1). RNF09 **parcialmente verificado**.

**Implementado**

* **Fechamento seguro da janela:** sem gravação em andamento, fecha na hora; com gravação rastreada de um fluxo com código, bloqueia, avisa "Salvando… a janela será fechada quando terminar." e fecha ao terminar, sem tempo limite.
* **Nova tentativa após falha transitória** (`sqlite3.OperationalError`) depois de confirmar o código: repete a mesma gravação com a mesma autorização, sem validar o código de novo; a autorização é descartada ao cancelar, sair ou encerrar.
* **Campos bloqueados** durante envio, confirmação e gravação nos fluxos com código; Voltar/Cancelar continuam ativos. **Contador** "Reenviar código em N s", baseado no tempo informado pelo serviço.
* **Confirmação de senha no cadastro** (P11, CT118).
* **Detalhes com campos fixos** (P12, 8.4, 5.22, CT57, CT115): ícones informativos no mesmo verde; rótulo à esquerda do conteúdo a partir de 520 px de largura da página, acima em janela estreita.
* **Paleta Clara (RNF09):** verde de texto e botões #16795A e cinza secundário #6C6B66; texto próprio nas pílulas de status (fundo mantido); ícones de Detalhes e do Gráfico com contraste mínimo de 3:1 sobre o fundo efetivo. Cores das categorias no banco inalteradas; o círculo da categoria em Detalhes mantém o fundo translúcido.
* Aviso de Excluir conta: "As contas incluem os meses futuros já gerados das recorrências."

**Validação**

* Testes automáticos específicos por bloco, com mutações detectadas, e suíte completa no fechamento da etapa.
* Validação visual em cópias isoladas do banco: fechamento sem gravação e durante gravação; campos bloqueados e contador; "As senhas não coincidem."; paleta Clara em Início, Detalhes, Gráfico, Ajustes e aviso de exclusão (cancelado); campos fixos de Detalhes nas duas larguras. Banco real e backups inalterados.
* A nova tentativa após falha transitória foi verificada só nos testes automáticos (não há como provocar a falha pela interface de forma confiável).

**RNF09 — situação**

* Verificado: pares de cores mapeados nos dois temas e telas e diálogos autenticados percorridos nos testes, com contraste medido sobre o fundo efetivo (4,5:1 para texto, 3:1 para ícones e elementos gráficos).
* Fora da verificação: estados raros, telas de autenticação na varredura de contraste e gráficos em detalhe. Por isso RNF09 **não** é declarado integralmente atendido.

**Limitações conhecidas**

* O fechamento seguro aguarda só as gravações rastreadas dos fluxos com código; as demais gravações são transações curtas e atômicas. Sem tempo limite nem segundo aviso; o evento de fechamento depende do gerenciador de janelas (validado no Linux).
* Só a falha transitória oferece nova tentativa; outros erros recomeçam o fluxo. Uma falha `OperationalError` permanente continua oferecendo nova tentativa até a autorização expirar, sem gravação indevida. Caso extremo: se a tentativa anterior gravou e o registro de uso foi apagado após o vencimento, a nova tentativa informa código expirado embora a operação esteja gravada.
* O contador do reenvio atualiza a tela a cada segundo enquanto há contagem.
* No Linux, o Flutter/GTK pode registrar avisos técnicos ao fechar a janela; o processo encerra normalmente.

## 13.6 Encerramento da v6.0 para portfólio (04/10/2026)

A v6.0 está **concluída como entrega de portfólio e demonstração local**: todas as funcionalidades especificadas estão implementadas e verificadas no computador da autora. O uso por outras pessoas depende dos itens adiados abaixo, que **não** fazem parte desta entrega.

**Concluído**

* Etapas 1–10 (seção 15), uma por commit ou grupo de commits, com testes automáticos e as validações manuais registradas em 13.3–13.5 e em [validacao-etapa8.md](validacao-etapa8.md). Etapas 2–5 e 7 têm verificação por testes automáticos; a Etapa 6 teve validação manual aprovada pela autora (30/09/2026).
* Etapa 11 (testes): suíte do aplicativo com **879 testes aprovados** (04/10/2026, depois da ampliação de RNF09) e serviço de códigos com **151 testes aprovados** e verificação de tipos (02/10/2026; `servidor/` sem mudanças desde então). Rastreabilidade abaixo.
* Termos de Uso e Política de Privacidade (texto de 04/10/2026, com os ajustes do item 4 dos Termos e do item 2 da Política): **revisados e aprovados pela autora em 04/10/2026** para a versão de portfólio e demonstração local, com apoio de revisão técnica e de clareza. A revisão jurídica continua pendente (ver "Adiado para uso por terceiros").
* Etapa 12 (README): apresentação do projeto, funcionalidades da v6.0, como executar, demonstração local, testes e limitações.
* RF02–RF15, RF17–RF35, RF37, RF38 e RF40–RF43: ✅ (seção 6).
* RNF01, RNF02 (com a exceção do serviço de códigos), RNF04, RNF05, RNF07, RNF08, RNF10 e RNF11 atendidos: telas responsivas nas larguras testadas; dados locais; instalação por `requirements.txt`; PBKDF2 (`test_senha`, `test_usuarios_categorias`); backup e migrações sem perda (`test_migracao_v6`, `v7`, `v8`); regras dos códigos (`servidor/test/nucleo`); segredos fora do repositório (`.gitignore`, só o modelo `.dev.vars.example` é versionado).

**Rastreabilidade dos casos de teste (Etapa 11)**

| Casos | Tema | Evidência automática | Validação manual |
|---|---|---|---|
| CT01–CT48 | Regressão da v5.0 | `test_recorrencia`, `test_posicao_serie`, `test_edicao_exclusao`, `test_bug_este_mes_em_diante`, `test_pagamento_listagens`, `test_usuarios_categorias`, `test_interface_edicao` | Auditoria final da v5.0 (22/09/2026) |
| CT49–CT54 | Tela Principal e Ver status | `test_tela_principal` | — |
| CT55–CT58 | Detalhes e descrição | `test_detalhes`, `test_descricao_escopo` | Etapa 10 (Detalhes, P12) |
| CT59–CT62 | Limites de caracteres | `test_limites_caracteres` | — |
| CT63–CT80 | Gráfico | `test_grafico` | Etapa 10 (paleta) |
| CT81–CT94 | Senha, e-mail e recuperação | `test_senha`, `test_cadastro_senha`, `test_alterar_senha_interface`, `test_cadastro_codigo_interface`, `test_alterar_email_interface`, `test_recuperacao_interface`, `test_autorizacoes_locais`, `test_fluxos_codigo`, `servidor/test` | Etapa 8 (serviço local; CT90, CT91, CT93, CT94) |
| CT95–CT102 | Tema, documentos, sair e excluir conta | `test_sessao_tema`, `test_tela_ajustes`, `test_ajustes_usuario`, `test_documentos`, `test_legibilidade_temas`, `test_legibilidade_rnf09`, `test_excluir_usuario` | Etapas 6 e 9 |
| CT103–CT107 | Escopo de categoria e descrição | `test_descricao_escopo`, `test_grafico` | — |
| CT108–CT117 | Complementos | `test_limites_caracteres`, `test_cadastro_codigo_interface`, `test_alterar_email_interface`, `test_autorizacoes_locais`, `test_recuperacao_interface`, `test_contador_reenvio`, `test_grafico`, `test_detalhes`, `test_sessao_tema`, `test_tela_ajustes` | Etapas 8 (CT110, CT113) e 10 |
| CT118 | Confirmação de senha no cadastro | `test_cadastro_senha` (`TestConfirmacaoDaSenha`) | Etapa 10 |
| — | Etapa 10 (nova tentativa, fechamento, campos e contador) | `test_nova_tentativa`, `test_fechamento`, `test_contador_reenvio` | Etapa 10 (fechamento, contador) |

**Parcial**

* **RF01, RF36 e RF39** (🧪): cadastro, alteração de e-mail e recuperação de senha por código funcionam e foram validados com o serviço de códigos no próprio computador (caixa local e modo de demonstração). A entrega real de e-mails não foi validada; a confirmação na demonstração **não comprova** acesso ao endereço.
* **RNF09** (ampliado em 04/10/2026, depois do registro de 13.5): contraste medido nos dois temas sobre o fundo efetivo, em todas as telas e diálogos autenticados e também em:
  * telas de autenticação (Claro, P8): login e erro, cadastro e recusas, código (mensagens, erro, contagem do reenvio, faixa da demonstração), serviço indisponível e os três passos da recuperação;
  * campos: texto, rótulo, dica e erro (4,5:1) e borda (3:1);
  * gráficos: rótulos dos eixos, valores e cores das barras;
  * estados: categoria sem emoji, categoria sem cor e conta que vence hoje.

  Encontrado e corrigido: a inicial de categoria sem emoji na tela Categorias (branco sobre cores claras, 2,21–3,39:1) passa a usar branco ou preto, o de maior contraste (≥ 4,6:1 nas 30 cores da paleta). Testes: `test_legibilidade_temas` e `test_legibilidade_rnf09`; iniciais conferidas visualmente pela autora.
  **Fora da verificação:** fatias da rosca nas cores das categorias (pastéis, da paleta oficial; a legenda identifica cada fatia por nome, valor e percentual em texto, o que é verificado); controles desativados (isentos pela WCAG 1.4.3); o que o Flutter desenha por conta própria (calendário, dicas flutuantes, foco e destaque ao passar o mouse ou clicar); a imagem final em pixels. Por isso RNF09 não é declarado integralmente atendido.
* **RNF03 e RNF06** (medidos em 04/10/2026, [desempenho-v6.md](desempenho-v6.md)): com 1.000 contas, todas as operações medidas ficaram abaixo de 2 s na camada medida (consulta ao banco + montagem da tela no Python); máximo de 0,35 s no cenário distribuído e de 1,70 s no pior caso (1.000 contas num único mês). **Não medidos:** a renderização da janela pelo Flutter e a comunicação com ela. Observação visual da autora com 1.000 contas: sem demora perceptível nem travamento (qualitativa, não substitui a medição). Por isso ficam como atendidos na camada medida, sem declaração de atendimento integral.

**Adiado para uso por terceiros**

* Publicação do serviço de códigos e entrega real de e-mails pela Resend: hospedagem, domínio e remetente, responsável pela operação, retenção pelos provedores e limites adicionais contra abuso (13.3).
* Revisão jurídica dos Termos e da Política e revisão da P9 (versionamento e novo aceite), antes do uso por outras pessoas.
* RF16 (biometria): fora do escopo da v6.0 (3.2).

**Para depois, sem bloquear a entrega**

* ~~Capturas reais das telas no README~~ — feitas em 04/10/2026 no modo de demonstração, com dados fictícios ([`docs/capturas/`](capturas/README.md)); os protótipos ficam como histórico.
* Calendário de escolha de datas (Nova/Editar conta) exibido em inglês ("Select date", "Cancel", nomes de meses e dias), padrão do Flutter; tradução pendente (registrado em 04/10/2026).
* Em janelas mais estreitas que o tamanho padrão do app (cerca de 330 px úteis), o nome da conta nas linhas da Tela Principal quebra letra a letra; no tamanho padrão o layout está correto (observado em 04/10/2026).

Correção de 04/10/2026, depois deste registro: na Tela Principal, o botão "+" (nova conta) passou a ocupar uma faixa própria acima da barra de navegação, com o mesmo estilo, e não cobre mais "Ver status" nem as ações das linhas (`test_tela_principal`).

---

# 14. Fora dos Requisitos Funcionais

## 14.1 Banco de ideias (não aprovado para a v6.0)

* Notificações configuráveis de vencimento e outros eventos;
* Pesquisa de contas;
* Ordenação de contas por vencimento, nome, valor ou categoria;
* Exportação para PDF ou Excel;
* Importação de dados;
* Sincronização entre dispositivos;
* Armazenamento/sincronização em nuvem;
* Dashboard financeiro ampliado, a avaliar depois que RF21–RF23 estiverem em uso.

## 14.2 Melhorias técnicas a avaliar

* **Dependências:** formalizar com `requirements.txt` ou `pyproject.toml`.
* **Backup:** política completa (frequência, retenção, localização, restauração, automático/manual). Não aprovada automaticamente para a v6.0.
* **Bancos `sino.db` antigos:** o banco em uso é `/home/carinne/Projetos/sino/database/sino.db`. Os demais arquivos `sino.db` devem ser investigados antes de qualquer exclusão.
* **Benchmark de RNF06:** feito em 04/10/2026 na camada do Python ([desempenho-v6.md](desempenho-v6.md)); falta medir a renderização na janela.

## 14.3 Documentação

Melhoria do **README.md** do repositório, associada à v6.0 e separada dos RFs: o que é o Sino, objetivo do projeto, principais funcionalidades, tecnologias e apresentação como portfólio. **Feita em 04/10/2026 (Etapa 12, ver 13.6)**, com capturas reais da demonstração (dados fictícios) em `docs/capturas/`; os protótipos ficam como histórico.

---

# 15. Plano de Desenvolvimento

| Etapa | Conteúdo | Depende de |
|---|---|---|
| 1 | Migração de schema (9.2), com backup | T1 |
| 2 | Descrição, limites e escopo de edição de categoria e descrição (RF04, RF07, RF14, RF20, RF32, RF33) | Etapa 1, T5 |
| 3 | Tela Principal e Ver status (RF05, RF09, RF12, RF30) | — |
| 4 | Detalhes da conta (RF31) | Etapa 2 |
| 5 | Gráfico (RF21–RF23, RF34), "Sem categoria" e cinza reservado (RF18) | Etapa 1, T1 |
| 6 | Ajustes sem e-mail: nome, tema, documentos, sair (RF35, RF40, RF41, RF42) | T3 |
| 7 | Senha mínima e alterar senha (RF37, RF38) | — |
| 8 | Serviço de e-mail, verificação no cadastro e na alteração, recuperação de senha (RF01, RF36, RF39) | T4 |
| 9 | Excluir conta (RF43) | T2 |
| 10 | Revisão geral de UX e tema escuro em todas as telas (RNF09) | Etapas 3–9 |
| 11 | Testes: regressão CT01–CT48 e novos CT49–CT118 | Etapas 1–10 |
| 12 | README.md | Pode ocorrer em paralelo |

Situação em 04/10/2026: Etapas 1–12 concluídas para portfólio e demonstração local; requisitos parciais e itens adiados em 13.6.

---

# Histórico de Versões

| Versão | Data | Resumo |
|---|---|---|
| 1.0 | 28/07/2025 | Primeira versão. |
| 2.0 | 03/08/2026 | Categorias, controle de usuário, atraso automático, backup. |
| 3.0 | 09/08/2026 | Revisão por protótipos: termos, biometria, resumo semanal, ícones, escopo de edição, gráficos. |
| 4.0 | 21/08/2026 | Filtros do Total do Mês, contas atrasadas, indicação de parcela, rastreabilidade. |
| 4.1 | 27/08/2026 | Revisão documental (RF09, RF17, pendência do RF05). |
| 5.0 | 01/09/2026 – 22/09/2026 | Nova arquitetura de séries, recorrência mensal/anual sem arrasto, data de pagamento, categorias com emoji e cor, banner de atraso, decisão D7 (Encerrar recorrência) e auditoria final pós-implementação. |
| 6.0 | 23/09/2026 | Tela Principal com todas as contas e atalho de edição, Ver status, Detalhes reformulada, descrição e limites de campos, tela Gráfico (RF21–RF23), Ajustes, verificação de e-mail por código, senha mínima, alterar e recuperar senha, excluir conta, tema claro/escuro. Escopo de edição das séries estendido a categoria e descrição. Decisões de produto P1–P10 fechadas. |
| 6.0 (estado) | 02/10/2026 | Registro do estado da Etapa 8 (13.3), marcadores de RF01, RF36 e RF39 e nota sobre `codigos_verificacao` em 9.2 e T4; nenhuma regra alterada. |
| 6.0 (estado) | 03/10/2026 | Registro do estado da Etapa 9 (13.4), marcador de RF43 e nota em T2; nenhuma regra alterada. |
| 6.0 (P11) | 03/10/2026 | Decisão P11: confirmação de senha no cadastro (Etapa 10); RF01, 5.31, 8.8 e CT118. |
| 6.0 (P12) | 04/10/2026 | Decisão P12: Detalhes com campos fixos e textos de ausência (Etapa 10); 5.22, 8.4, CT57 e CT115. |
| 6.0 (estado) | 04/10/2026 | Registro do estado da Etapa 10 (13.5), incluindo a situação parcial de RNF09. |
| 6.0 (encerramento) | 04/10/2026 | v6.0 concluída para portfólio e demonstração local (13.6): marcadores dos RFs revisados, rastreabilidade dos testes, Etapas 11 e 12; parciais e adiados separados. |
| 6.0 (RNF) | 04/10/2026 | RNF09 ampliado (autenticação, campos, gráficos e estados; inicial de categoria corrigida) e medição de RNF03/RNF06 ([desempenho-v6.md](desempenho-v6.md)); limites registrados em 13.6. |
| 6.0 (Termos) | 04/10/2026 | Termos e Política: ajustes do item 4 dos Termos e do item 2 da Política; revisão pela autora concluída para portfólio e demonstração local; revisão jurídica pendente (13.6). |
