# Sino 6.13 — modernização visual, Nova conta e logotipo

Anexo da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (seção 5.56). Registra o que a Sino 6.13 muda, as regras que ela preserva, os testes e as pendências. Fica fora das melhorias M1–M14 e das entregas E1–E18, como as Sinos 6.10 a 6.12.

**Situação:** aprovada integralmente pela autora em 12/11/2026, depois da validação visual. Integrada à `main` e publicada no GitHub em 12/11/2026, com a etiqueta anotada `sino-6.13`. Os detalhes da publicação estão na seção 15.2 da ERS e nas [notas da versão](notas-da-versao.md).

## 1. Origem

- Desenvolvida entre 10 e 12/11/2026 num protótipo isolado: um clone sem remoto, a partir da etiqueta `sino-6.12` (`ca1ea13`), com banco fictício e sandbox sem rede.
- Os 16 commits do protótipo foram trazidos para a branch `integracao/sino-6.13` por cherry-pick com `-x`, sobre a `main` de então (`ad6fbcd`). Cada commit integrado registra o hash original. O histórico da 6.12 não muda.
- Cada etapa foi aprovada pela autora depois de testes e capturas em 320, 380 e 1000 px, nos temas Claro e Escuro:
  - Nova conta (11/11);
  - Editar conta e Detalhes (11/11);
  - quantidade de parcelas e "Alterar término da recorrência" (11/11);
  - correções finais de Editar (11/11);
  - categorias predefinidas, E1 (11/11);
  - modernização das telas, E2–E4 (12/11);
  - logotipo (12/11).

## 2. O que muda para quem usa

### 2.1 Nova conta

- **Cartões "Conta comum" e "Superconta":**
  - Em Conta comum, os quatro tipos (Única, Parcelada, Recorrente mensal e Recorrente anual) ficam no próprio formulário, em cartões compactos. Antes, eram escolhidos no diálogo "Configurar recorrência".
  - Cada tipo tem uma faixa com uma explicação curta.
- **Superconta só visual:**
  - O cartão e a apresentação aparecem, mas nada nele grava e nenhuma regra da F1 é chamada.
  - Ele mostra o aviso "Supercontas em desenvolvimento". Ver a pendência 7(e).
- **Campos:**
  - organização Nome | Categoria e Valor | Data;
  - contadores dentro dos campos Nome e Descrição;
  - "Valor por parcela (estimado)" como campo informativo, com "i";
  - Tipo de valor (Fixo ou Variável) como campo, cada opção com seu "i".
- **Quantidade de parcelas:** um só controle, de 2 a 36, digitável ou pelas setas. É o mesmo em Nova conta, "Parcelar esta conta" e "Alterar parcelamento".
- **Término:**
  - Uma recorrência nova começa "Sem data de término". Mês e Ano ficam visíveis, mas desabilitados, enquanto essa opção está marcada.
  - Em telas estreitas, Mês e Ano ficam empilhados.

### 2.2 Editar conta e Detalhes

- **Recorrência em Editar:** um resumo curto ("Única · Sem repetição", "Parcelada · 11 parcelas", "Mensal · Variável · Sem término", "Anual · Fixo · Até nov/2029"). Os Detalhes mantêm a frase longa.
- **"Transformar em recorrente":** começa "Sem data de término".
- **"Parcelar esta conta":**
  - saiu dos Detalhes e virou um item do menu da Recorrência em Editar;
  - o diálogo, a prévia e as regras são os da 6.12;
  - a prévia fica mais alta em janelas estreitas.
- **Contadores:** 30 e 250, dentro dos campos Nome e Descrição.
- **"Alterar término da recorrência"** (novo; regras em 3.2):
  - fica no menu da Recorrência das séries mensais e anuais ativas;
  - o novo término é um rascunho, gravado só no Salvar;
  - os avisos explicam o que é preservado e o que volta a ser gerado.
- **Rodapé:** em 320 px, Cancelar cabe em uma linha.

### 2.3 Categorias predefinidas (E1)

- **Catálogo de 16, para usuários novos:**
  - Moradia, Transporte, Lazer, Estudos, Esportes, Saúde, Cartão de crédito, Beleza, Assinaturas, Crianças e Outros (7 nomes atualizados e ícones revistos);
  - mais Mercado, Lanches, Animais, Compras e Finanças, que são novas.
- **Cores:** cada uma tem uma cor distinta da paleta de 30, sem o cinza reservado a "Sem categoria".
- **Usuários já cadastrados:** mantêm as categorias que têm. Não há migração, e as sugestões de emoji dos nomes antigos continuam valendo.
- **Regras:** o limite de 30 categorias por usuário e as demais regras não mudam.

### 2.4 Início, Ver status e Contas em atraso (E2)

- **Cartão do resumo:** em degradê verde, com Total do mês, Pago e Pendente.
  - Os valores vêm do mesmo cálculo de antes. O aviso das contas com valor pendente fora do total é mantido.
  - O cartão fica em três colunas em janela larga, duas a 380 px e uma a 320 px.
- **Mês e alertas:**
  - seletor de mês em pílula;
  - os alertas "vencem nos próximos 7 dias" e "contas em atraso" ficam lado a lado em janela larga;
  - em janela estreita, "Ver essas contas" desce para baixo do texto.
- **Linhas de conta:** mais compactas, também em Ver status e Contas em atraso.
  - O ícone da categoria aparece quando o nome ainda tem pelo menos 160 px. Conta sem categoria mostra um círculo neutro, sem emoji.
  - O nome da categoria continua no subtítulo.
  - Há um divisor antes dos botões.
- **Teclado:** o "+", "Ver status", "Ver essas contas" e as quatro abas da barra inferior viraram botões com foco visível.
- **Abas:** a aba ativa aparece em pílula verde nas quatro telas.
- **Sino:** o ícone do sino continua só decorativo.

### 2.5 Categorias (E3)

- **Banner:** em degradê, com o botão "Nova categoria". A ação e o limite são os mesmos.
- **Ícone:** passa a ter 44 px, com o centro clareado. Emojis e cores são os aprovados; os de Animais, Mercado, Lanches e Lazer ficam mais legíveis.
- **Janela estreita:** a 320 e a 380 px, os três botões (nova conta, editar e excluir) descem para baixo do nome, inteiros e com os mesmos nomes acessíveis. Antes, ficavam cortados.

### 2.6 Gráfico (E4)

- **Cabeçalho:** com Mensal/Anual e o período. Os alternadores são botões com foco visível.
- **Resumo:** em degradê, com Total, Total pago, Pendente e a barra de progresso.
  - Pendente = total − pago, a mesma definição de Início.
  - Quando só há valores pendentes, o total aparece como "Valor pendente".
- **Topo:** Evolução e Gastos por categoria lado a lado em janela larga.
- **Legenda compacta:**
  - mostra as 6 maiores categorias e "Outras (N)";
  - "Sem categoria" fica sempre à parte;
  - "Outras" é só apresentação: os cálculos e o agrupamento por categoria não mudam;
  - "Ver todas as categorias" abre a lista completa, só para consulta.
- **Comparativo por categoria:** largura total, com todas as categorias.
- **Comparação com o mês anterior:** numa faixa compacta.
- **Janela estreita:** a legenda fica em duas linhas.

### 2.7 Logotipo

- **Imagem:** o logotipo aprovado pela autora ("$ino" sobre fundo verde-escuro, com ondas verdes), incluído sem alteração em `backend/assets/logo_sino.png` (1254 × 1254 px).
- **Onde aparece:**
  - com 104 px, no login, na recuperação de senha e na confirmação do código do cadastro;
  - com 46 px, ao lado da saudação em Início.
- **Enquadramento:**
  - recorte do quadrado arredondado da imagem, com cantos arredondados;
  - proporção 1:1, sem cortar o texto e sem bordas pretas;
  - se o arquivo faltar, volta a marca em texto anterior.
- **O que não muda:** os formulários, a autenticação, o serviço de códigos, o ícone da janela e o lançador do sistema.

## 3. Regras

### 3.1 Preservadas

- **Banco de dados:** continua na **versão 11**, sem migração.
  - As funções de preparação, conexão e migração (`preparar_banco`, `criar_tabelas`, `conectar` e `migrar_schema_v5` a `migrar_schema_v11`) são idênticas às da 6.12.
  - Abrir a 6.13 não altera os dados existentes.
- **Regras da 6.12:** seguem o anexo [sino-6.12-regras.md](sino-6.12-regras.md):
  - os quatro tipos de conta e a mudança de tipo só a partir da Única (R1, R2);
  - o bloqueio Mensal ↔ Anual (R6);
  - os valores variáveis e o "Valor pendente";
  - os pagamentos parciais e os estornos;
  - o limite de 250 caracteres.
- **Valores e cálculos:** os totais, os valores pagos e pendentes, o agrupamento por categoria e o status das contas não mudam.
- **Autenticação e e-mails:**
  - a autenticação, a recuperação de senha, os códigos (validação, expiração, tentativas e reenvio) e o serviço de e-mails não mudam;
  - os Termos de Uso e a Política de Privacidade também não.

### 3.2 Nova: "Alterar término da recorrência" (decisões B1–B7 da autora, 11/11/2026)

- **B1:** o novo término nunca é anterior ao mês mais recente entre o da ocorrência em edição e o mês atual. Nada que já venceu é excluído.
- **B2/B3:** depois do novo término, só são excluídas as ocorrências sem histórico protegido. A proteção é a mesma de "Encerrar recorrência": pagamentos ativos ou estornados, contas pagas antes da 6.10 e ocorrências editadas individualmente. As protegidas continuam registradas além do término.
- **B4:** prorrogar ou remover o término volta a gerar a grade da série, inclusive meses antes excluídos, pelas mesmas funções da geração sob demanda.
- **B5:** é uma só transação, desfeita por inteiro em qualquer falha. Um novo vencimento com "Este mês em diante" não pode ser combinado com uma alteração de término; essa combinação é recusada antes de gravar.
- **B6:** vale só para séries ativas, mensais ou anuais, fixas ou variáveis. Não vale para contas parceladas.
- **B7:** o mês do término é o limite inclusivo, como na criação.
- **Salvamento atômico de Editar:** quando há um término pendente, o Salvar grava os campos e o término numa única transação (`salvar_edicao_com_termino`). Uma recusa ou um erro inesperado em qualquer etapa desfaz tudo.

## 4. Testes

- **Suíte completa no estado integrado:** 2.050 testes, executados num sandbox sem rede, com bancos temporários. Resultado `failures=6` e `errors=46`.
  - As 52 falhas são **preexistentes**: as mesmas, comparadas pelo nome do teste, nas execuções de referência do protótipo.
  - Elas vêm de testes antigos acoplados a estruturas de tela substituídas desde as primeiras rodadas do protótipo.
  - Nenhuma regressão nova e nenhuma falha a menos. Nenhum teste foi removido ou alterado para esconder falhas.
- **Testes novos da 6.13** (todos aprovados):

  | Arquivo | Testes |
  |---|---|
  | `test_613_nova_conta_prototipo` | 35 |
  | `test_613_editar_detalhes_prototipo` | 18 |
  | `test_613_termino_parcelas_prototipo` | 41 |
  | `test_613_atomicidade_prototipo` | 19, com falhas reais simuladas por gatilhos SQLite |
  | `test_613_categorias_e1_prototipo` | 12 |
  | `test_613_telas_e2_e4_prototipo` | 23 |
  | `test_613_logotipo_prototipo` | 8 |

  O conjunto `test_613_*` soma 156 testes.
- **Testes antigos adaptados:** alguns foram adaptados às estruturas de tela substituídas, por trocas declaradas e contadas. As trocas mudam como o teste encontra o controle, nunca o que ele verifica.
- **Validação visual:** capturas reais em 320, 380 e 1000 px, nos temas Claro e Escuro, em cópias descartáveis do banco fictício. As telas de código foram capturadas com o cliente real sobre um servidor falso, sem rede e sem envio.

## 5. Ressalvas

- **Leitor de tela:** Orca e AT-SPI não foram testados. Foram verificados só a estrutura de semântica e a ordem do Tab.
- **Fonte de emoji:** as cores dos emojis dependem da fonte do sistema.
- **Telas de autenticação:** abrem sempre no tema Claro (regra 5.36, P8), também quando o tema escolhido é Escuro.
- **Capturas de referência do README:** as de `docs/capturas/` são anteriores à 6.13 e não foram atualizadas.

## 6. Fora do escopo

- **F1 — Supercontas e contas descendentes:** continua **futura** e não foi implementada. Na 6.13, a Superconta aparece só como apresentação visual na Nova conta, sem gravar nada, conforme a orientação da autora de 10/11/2026 (preparar a interface sem ativar a funcionalidade). As regras da F1 continuam sem aprovação e precisam ser revistas diante da 6.12 (ERS, 15.3).
- **Melhorias D7 e D8 da 6.12:** não foram tratadas e continuam pendentes (ERS, 13.4).

## 7. Pendências (registradas, sem correção nesta versão)

- **(a) Margem de 24 px depois do login:** no Flet 0.86, `page.padding = 0` não chega ao cliente depois que o login usa 24 px, e a margem fica em todas as telas. Os layouts novos a descontam (`MARGEM_DA_PAGINA`). Corrigi-la muda todas as telas.
- **(b) Gráfico de Evolução em 320 px:** os rótulos "R$ 0,00" dos meses vazios se sobrepõem. O problema é anterior à 6.13; resolvê-lo exige abreviar ou omitir valores.
- **(c) Filtros de Ver status:** não recebem foco pelo teclado.
- **(d) Contraste do emoji de Animais (🐾 sobre `#FBC02D`):** a legibilidade melhorou com o centro clareado do ícone, mas o contraste depende da fonte de emoji local. Reavaliar se ainda for pertinente.
- **(e) Texto da Superconta na Nova conta:** diz "As supercontas estarão disponíveis na próxima versão do Sino". Isso não corresponde à situação da F1 (item 6), e o texto foi mantido como aprovado visualmente. Revisá-lo depende de decisão da autora.
- **(f) Comentários "protótipo" no código:** os comentários e as docstrings do código citam "Protótipo 6.13", por terem sido escritos no protótipo. Não afetam o funcionamento.
