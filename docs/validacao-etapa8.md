# Validação da Etapa 8 — resumo

Resumo das validações manuais da Etapa 8 (e-mail com código), feitas em
01–02/10/2026. Não inclui endereços, senhas, códigos nem identificadores reais;
as evidências completas (logs, linhas do tempo e referências de hash) ficam
fora do repositório.

**Situação:** entrega local de códigos **concluída e validada**; publicação
para outras pessoas (serviço publicado, entrega real de e-mails, hospedagem)
**pendente**. A Etapa 8 não está concluída.

## Como foi feito

- Cada rodada usou uma **cópia isolada** do aplicativo, com título de janela
  próprio e banco copiado pela API de backup do SQLite (ou, na demonstração,
  um banco novo e vazio). Os caminhos do banco e dos backups foram conferidos
  antes de abrir cada janela.
- Nenhum e-mail real foi enviado: na Parte A o serviço estava ausente ou
  inacessível; na Parte B, o serviço rodou localmente (`wrangler dev`) com a
  caixa de desenvolvimento, em `127.0.0.1`.
- O banco real de desenvolvimento e seus backups foram comparados por SHA-256
  antes e depois de cada rodada. Ressalva: em 01/10 o banco real foi migrado
  para o schema v8 fora do roteiro (origem não comprovada) e teve uma troca de
  senha confirmada pela autora; os dois eventos foram preservados, e as
  comparações seguintes usaram novas referências.

## Resultados

| Cenário | Resultado | Ressalvas |
|---|---|---|
| Migração v7 → v8 de uma cópia, com backup | Aprovado | — |
| Sem serviço configurado: login, inclusive sem internet | Aprovado | — |
| Serviço inacessível: tratamento da falha no cadastro, na recuperação e na alteração de e-mail | Aprovado | — |
| Rolagem das telas de entrada, cadastro, código e recuperação (janela de 760 px e reduzida) | Aprovado | Corrigido durante a validação |
| Cadastro com verificação | Aprovado | — |
| Código errado ("restam 4 tentativas") | Aprovado | — |
| Tentativas esgotadas | Aprovado | Uma série observada na tela; outra só confirmada no serviço |
| Reenvio antes de 60 s ("Aguarde…") | Aprovado | — |
| Reenvio depois de 60 s: código antigo recusado, novo aceito | Aprovado | — |
| Expiração | Aprovado como **recusa pelo próprio app** | A recusa pelo serviço (prazo do servidor) só é coberta pelos testes automáticos: o app encerra o pedido antes |
| Cancelamento durante o envio | Aprovado | Houve três pedidos para o endereço de teste; a sequência exata não foi esclarecida |
| Carregamento ("Enviando código…", botão desativado) | Aprovado | Três pedidos para o endereço de teste, sem duplicidade dentro da mesma espera; o estado dos campos durante o envio não foi observado (pendência de UX) |
| Recuperação completa e entrada com a nova senha | Aprovado | — |
| Nova senha igual à atual recusada | Aprovado | A senha curta nesse passo ficou coberta só pelos testes automáticos |
| Neutralidade da recuperação (conta não verificada e endereço inexistente) | Aprovado na tela e no funcionamento | Neutralidade de tempo não medida; um pedido recusado por intervalo (429) sem endereço identificado |
| Alteração de e-mail, entrada pelo novo endereço e selo "Verificado" | Aprovado | — |
| Interrupção brusca do processo em três pontos da gravação (automático, 9 casos) | Aprovado | Atomicidade e integridade em todos os casos |
| Fechar a janela durante uma gravação | Aprovado após correção | Antes: gravação atômica, mas processo preso consumindo CPU. Depois: gravação concluída e processo encerrado sozinho. Sem fechamento seguro da janela |
| Modo de demonstração (título, aviso, abertura automática da mensagem, cadastro, entrada, encerramento, reabertura com a conta preservada) | Aprovado | Dois defeitos do comando corrigidos (falso bloqueio de porta e mensagens retidas no terminal) |

## Conferências técnicas

- Bancos das cópias: integridade e chaves estrangeiras corretas ao fim de cada
  rodada; contas e autorizações gravadas sempre juntas.
- Estado salvo do serviço local e logs: nenhum código em texto encontrado.
- O pacote de produção do serviço não contém nada de desenvolvimento.

## Não validado

- Entrega real de e-mails pela Resend, hospedagem e publicação do serviço.
- Fechamento seguro da janela (Etapa 10).

## Observações abertas

- Avisos do Flutter no terminal ao fechar a janela (sem efeito observado).
- Origem de um aviso de subprocesso em uma execução da suíte de testes.
- Nada impede tecnicamente publicar a configuração de desenvolvimento do
  serviço; ela não deve ser publicada.
