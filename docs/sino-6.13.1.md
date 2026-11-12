# Sino 6.13.1 — manutenção da suíte de testes e cores explícitas

Anexo da [ERS v7.0](ERS_Controle_de_Contas_v7.0.md) (seção 5.56, atualização da 6.13.1). Versão de **correção**, sem funcionalidade nova. Registra a origem das 52 ocorrências da suíte deixadas pela 6.13, a recuperação dos testes, a restauração da verificação de legibilidade e as duas correções de cor aprovadas pela autora.

**Situação:** aprovada pela autora em 12/11/2026, em três etapas: diagnóstico D1, implementação M1 num ambiente isolado e decisão B1. Integrada à `main` e publicada no GitHub em 12/11/2026, com a etiqueta anotada `sino-6.13.1`.

## 1. Origem das 52 ocorrências

A Sino 6.13 foi publicada com a suíte em `failures=6` e `errors=46`. O diagnóstico D1 investigou as 52 ocorrências uma a uma, só com leitura, a partir de cópias do código extraídas por `git archive`, em sandbox sem rede e com bancos temporários.

- Na 6.12 (`ca1ea13`), os 154 testes dos 10 módulos envolvidos passavam.
- 48 ocorrências surgiram no primeiro commit da 6.13 (`c158e6a`, nova Nova conta). As 5 dos contadores mudaram de forma em `ac2a816`, quando os contadores passaram para dentro dos campos. De `ac2a816` até `dce57ee`, o conjunto ficou idêntico.
- **As 52 eram testes desatualizados.** Nenhuma indicava defeito funcional, de ambiente ou causa indeterminada. Os testes procuravam estruturas que a 6.13 substituiu de propósito.

| Causa-raiz | Ocorrências | O que a 6.13 mudou |
|---|---:|---|
| R1 | 39 | O campo "Recorrência" e o diálogo "Configurar recorrência" deram lugar aos cartões de tipo no formulário e ao campo e diálogo "Término da recorrência" |
| R2 | 5 | O contador passou para dentro do campo, e o contador de baixo ficou desligado |
| R3 | 2 | O "Voltar" da Nova conta passou a ser um botão com o texto "Voltar" |
| R4 | 1 | A Superconta (só visual) tem um calendário próprio |
| R5 | 5 | O percurso de legibilidade parava em "Recorrência" e, desde `05bfd54`, no "+" de Início |

**Correção do registro da 6.13.** O registro da publicação da 6.13 diz que as 52 falhas tinham "a mesma causa" da referência do protótipo. Isso só vale para o nome do teste e o tipo da exceção. Nos 5 testes de legibilidade, o ponto de interrupção mudou no commit `05bfd54` (E2–E4): de "Recorrência" (linha 255) para o "+" de Início (linha 250), que virou um botão de ícone com nome. A comparação da época olhou só a última linha do erro. Consequência: as telas Nova conta, Categorias, Gráfico, Ajustes e os documentos **não tiveram o contraste verificado automaticamente na 6.13**. Os registros originais foram mantidos, com a correção indicada ao lado.

## 2. Recuperação dos testes

- **Reescritos:** os 42 métodos de teste das 52 ocorrências (10 delas são subtestes), com os mesmos nomes e as mesmas verificações de comportamento, sobre a estrutura da 6.13. Nenhum teste foi excluído, desabilitado ou aposentado.
- **Auxiliares comuns da Nova conta da 6.13** em `tests/test_612_parcelada_telas.py`: cartões de tipo, valor, término e preenchimento.
- **Contadores:** `contador_de` (`tests/test_descricao_250.py`) lê o contador interno e exige que o contador de baixo esteja desligado.
- **Verificações sem equivalente direto, substituídas:**
  - a comparação dos chips de tipo do diálogo com os de Editar virou a comparação da parte comum do término com "Transformar em recorrente";
  - os resumos "Mensal até…" do campo Recorrência viraram a faixa do tipo e o texto do término;
  - a lista de 2 a 36 parcelas virou a validação do número digitado (1 e 37 recusados; 2 e 36 aceitos);
  - a ajuda do valor variável virou as dicas "i" de cada opção (`TEXTOS_TIPO_DE_VALOR`).
- **Foco do diálogo de término**, agora verificado: ao abrir, o foco vai para a chave "Sem data de término"; ao Cancelar ou Confirmar, volta para a seta "Escolher término da recorrência". O campo não recebe foco e o diálogo é modal.

## 3. Legibilidade

- **Percurso restaurado:**
  - o "+" de Início;
  - Nova conta (Única) e o erro de validação;
  - Recorrente mensal;
  - o diálogo do término com "Sem data de término" ligado e desligado;
  - Parcelada e Superconta;
  - as demais telas, como antes.

  Vale para os temas Claro e Escuro e também depois de trocar o tema.
- **Método:** o verificador guarda a tela viva e a confere no fim do percurso. Por isso cada estado da Nova conta e do diálogo é registrado numa abertura própria. Antes, só o último estado da tela era de fato verificado.
- **Resultado:** contraste aprovado em todas as vistas. O percurso encontrou duas inconsistências com a regra de cor explícita (RNF09), sem defeito visível. As duas foram corrigidas (seção 4).

## 4. Correções de cor (RNF09)

- **A, cartões de tipo da Nova conta** (Única, Parcelada, Recorrente mensal e Recorrente anual): cor de texto explícita no próprio botão, igual à do nome visível (`chip_ativo_texto` no ativo, `texto_principal` nos demais). Segue o padrão dos cartões Conta comum | Superconta.
- **B1, campo "Valor por parcela (estimado)"** (Parcelada): `color=cores.texto_sucesso`, a mesma cor que o estilo do texto já usava. Contraste: 4,91:1 no tema Claro e 6,67:1 no Escuro.
- **Aparência:** comparada por capturas reais, antes e depois, em 1000 e 320 px, nos temas Claro e Escuro.
  - Os cartões com cada tipo escolhido, a Parcelada preenchida e vazia e os estados de hover e foco ficaram idênticos pixel a pixel.
  - No pressionamento, a onda do toque é animada e varia até entre duas execuções da mesma versão. A cor da onda é a mesma.
  - Em 320 px, o campo estimado fica abaixo da área capturada.
- Cada correção tem um teste próprio e uma prova negativa: sem a correção, o teste falha.

## 5. Testes

- **Suíte completa no estado integrado:** **2.052 testes, sem failures nem errors**, num sandbox sem rede, com bancos temporários e sem acesso ao banco pessoal.
- **Em relação à 6.13:** 2.050 testes com `failures=6` e `errors=46`. As 52 ocorrências foram recuperadas, e há 2 testes novos (A e B1).

## 6. O que não muda

- Banco de dados na **v11**, sem migração.
- Regras de negócio, cálculos, autenticação, serviço de e-mails, Termos de Uso e Política de Privacidade.
- Telas: as únicas mudanças são as duas propriedades de cor, sem efeito visual.

## 7. Limitações e pendências

- **Pendências da 6.13:** continuam abertas, sem correção nesta versão. São as seis do anexo [sino-6.13.md](sino-6.13.md), seção 7: margem de 24 px, rótulos da Evolução em 320 px, filtros de Ver status sem foco, emoji de Animais, texto da Superconta e comentários "Protótipo 6.13".
- **Pendências da 6.12:** continuam abertas, inclusive D7 e D8.
- **Acessibilidade:** leitor de tela (Orca), AT-SPI e foco pelo teclado real não testados.
- **Ajuda do valor variável na Nova conta:** desde a 6.13, não menciona "Valor pendente". O texto foi aprovado assim na 6.13; em "Transformar em recorrente", a menção continua.
- **F1 (Supercontas):** continua futura.
