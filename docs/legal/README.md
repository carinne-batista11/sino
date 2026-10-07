# Versões dos Termos de Uso e da Política de Privacidade

Esta pasta guarda o texto de cada versão dos documentos exibidos no Sino (ERS v7.0, 5.53). Cada arquivo é identificado pelo documento e pela data da versão:

- `termos-de-uso_AAAA-MM-DD.md`
- `politica-de-privacidade_AAAA-MM-DD.md`

O aplicativo mostra só a versão vigente, com a indicação "Versão de dd/mm/aaaa". O texto vigente fica em `backend/documentos.py` e precisa ser idêntico ao arquivo da versão mais recente (os testes conferem isso). Os arquivos de versões anteriores não são alterados.

| Documento | Versão | Classificação | Observação |
|---|---|---|---|
| Termos de Uso | 04/10/2026 | Inicial | Primeira versão registrada: texto aprovado pela autora em 04/10/2026, com a mesma data e o mesmo conteúdo |
| Política de Privacidade | 04/10/2026 | Inicial | Primeira versão registrada: texto aprovado pela autora em 04/10/2026, com a mesma data e o mesmo conteúdo |
| Termos de Uso | 06/10/2026 | Relevante | Item 8: versões identificadas pela data, registro da versão aceita, novo aceite e aviso. Classificação da autora: introduz registros de dados antes não descritos |
| Política de Privacidade | 06/10/2026 | Relevante | Itens 2, 3, 8, 10 e 11: registros de aceite e de ciência, finalidade, exclusão, permanência em backups e versões. Mesma classificação |

**Como registrar uma versão nova:**

1. A autora classifica a mudança:
   - **relevante:** dados tratados, finalidades, compartilhamento, retenção, direitos do titular, responsabilidades ou garantias, ou uma funcionalidade que trate dados pessoais de forma nova. Exige novo aceite no próximo login.
   - **menor:** redação, clareza, correções, links ou formatação, sem mudar o conteúdo. Mostra só um aviso.

   Na dúvida, a mudança é relevante.
2. Atualize o texto em `backend/documentos.py`, inclusive a data de "Última atualização".
3. Acrescente a versão em `HISTORICO_VERSOES`, com o resumo das mudanças e o motivo da classificação.
4. Crie aqui o arquivo da nova versão, com o texto idêntico.
5. Registre a mudança nas notas da versão.

A revisão jurídica dos textos continua pendente e é necessária antes do uso por terceiros.
