# Política de Privacidade do Sino

Última atualização: 04/10/2026

O Sino é um projeto pessoal de portfólio desenvolvido por Carinne Batista. Esta política descreve como a **versão desktop atual** do Sino trata as informações registradas nele. As afirmações sobre o que o Sino guarda, usa e envia se referem ao próprio aplicativo; bibliotecas de terceiros são tratadas no item 7.

## 1. Funcionamento local

O Sino é instalado e usado no computador. As informações de cada instalação ficam nesse computador, e o aplicativo não as envia à desenvolvedora nem a terceiros. A desenvolvedora não recebe, por meio do Sino, os dados registrados em instalações de outras pessoas.

A única função que conversa com um serviço fora do aplicativo é a **confirmação por código** (criar conta, alterar o e-mail e recuperar a senha). Com o serviço de códigos publicado, o endereço de e-mail e alguns dados técnicos seriam enviados a ele pela internet; no modo de demonstração, o serviço roda no próprio computador e os dados do fluxo de códigos são tratados localmente, sem envio ao provedor de e-mail (item 7). Nome, senha e informações financeiras não são enviados em nenhum dos dois casos.

## 2. Quais informações o Sino guarda

*Dados da sua conta de usuário:* nome, e-mail, se o e-mail foi confirmado por código, senha (guardada de forma protegida, veja o item 5), a data em que você aceitou os Termos de Uso e esta Política, e sua preferência de tema (Claro ou Escuro).

*Registro técnico das confirmações por código:* para que a mesma confirmação não seja usada duas vezes, o Sino guarda um identificador aleatório de cada confirmação usada, a finalidade (cadastro, alteração de e-mail ou recuperação de senha) e até quando ela valeria. Esse registro não contém e-mail, nome nem senha, e os itens vencidos são apagados nas confirmações seguintes. Como não está ligado a nenhum usuário, ele não é apagado na exclusão da conta de usuário (item 8).

*Informações financeiras que você registra:* nome, valor, data de vencimento, situação (paga ou pendente), data de pagamento, categoria, descrição (opcional) e recorrência de cada conta; nome, emoji e cor de cada categoria.

Além dessas, o Sino não coleta outras informações, como localização, contatos, dados bancários ou dados do seu computador. A exceção é a confirmação por código: ao usá-la, o serviço de códigos recebe dados técnicos do pedido, como o endereço IP de onde ele parte e identificadores gerados na hora. O que é enviado, o que o serviço guarda e por quanto tempo estão descritos no item 7.

## 3. Para que essas informações são usadas

Somente para o funcionamento do aplicativo: permitir que você entre na sua conta, confirmar o e-mail por código (cadastro, alteração de e-mail e recuperação de senha), mostrar e organizar suas contas, calcular totais, indicar vencimentos e atrasos, exibir gráficos e aplicar o tema escolhido. O Sino não usa suas informações para publicidade.

## 4. Onde as informações ficam

As informações descritas no item 2 ficam no computador da instalação, em um arquivo de banco de dados (`database/sino.db`) dentro da pasta do Sino. O Sino não envia esse arquivo para servidores ou nuvem e não sincroniza dados entre dispositivos. O que é enviado ao serviço de códigos está descrito no item 7.

Se mais de uma pessoa usar a mesma instalação do Sino, os dados de todas ficam no mesmo arquivo. Dentro do aplicativo, cada usuário vê apenas as próprias informações.

## 5. Como as informações são protegidas

A senha não é guardada como texto: o Sino guarda apenas um resumo protegido dela (PBKDF2-HMAC-SHA256, com um valor aleatório diferente para cada usuário). Senhas cadastradas em um formato antigo são atualizadas para esse formato quando a pessoa entra no aplicativo.

As **demais informações não são criptografadas** no arquivo. Qualquer pessoa ou programa com acesso a esse arquivo pode conseguir lê-las. Por isso, proteja o acesso ao computador e à pasta do Sino.

Nenhum sistema é totalmente seguro, e o Sino não promete proteção absoluta.

## 6. Cópias de segurança (backups)

Quando uma nova versão do Sino precisa atualizar a estrutura do banco de dados, o aplicativo cria **automaticamente** uma cópia completa do arquivo antes da atualização, na pasta `database/backups/`. Cada cópia contém as informações de **todos os usuários** daquela instalação no momento em que foi feita.

As cópias são **arquivos separados** do banco principal e **não são apagadas pelo aplicativo**. Por isso, uma informação que você alterou ou excluiu no Sino pode continuar existindo em uma cópia anterior.

## 7. Serviço de códigos, bibliotecas de terceiros e comunicações externas

*Serviço de códigos por e-mail.* Quando você cria uma conta, altera o e-mail ou pede a recuperação da senha, o Sino envia ao serviço de códigos o endereço de e-mail informado, a finalidade do pedido e identificadores técnicos gerados na hora; para conferir o código, envia também o código que você digitou. Fora do próprio computador, a conexão com o serviço usa HTTPS. Como em qualquer conexão pela internet, o serviço recebe o endereço IP de onde o pedido veio. O Sino não envia nome, senha, informações financeiras nem o arquivo do banco.

O serviço gera o código e o envia ao endereço informado por meio de um provedor de envio de e-mails (na implementação atual, a Resend). O provedor recebe o endereço e a mensagem com o código de forma legível, porque precisa entregá-la. O serviço não conhece as contas do Sino: na recuperação de senha, quando não há uma conta com e-mail confirmado naquele endereço, o pedido é enviado do mesmo jeito, mas nenhum e-mail é mandado.

O que o serviço guarda, pela implementação atual:

* **e-mail, endereço IP e código:** não são guardados como texto. O serviço guarda resumos de mão única (HMAC-SHA256) calculados com uma chave secreta dele, que permitem comparar valores sem guardá-los. Isso não é criptografia reversível: o serviço não recupera o texto a partir do resumo. Do IP, entra no resumo o endereço IPv4 completo ou o início (/64) do endereço IPv6;
* **identificadores técnicos:** o segredo e as chaves de cada pedido também ficam só como resumo; o identificador de vínculo enviado pelo aplicativo já chega como resumo (SHA-256) e é guardado como recebido; o identificador da confirmação emitida fica legível. Nenhum deles contém o e-mail em texto;
* **legíveis:** a finalidade do pedido, horários, número de tentativas, situação do envio, resultado de cada tentativa e contadores usados para limitar abusos;
* **prazos:** os pedidos encerrados são apagados 24 horas depois do encerramento, os contadores por hora em 2 horas, os contadores diários por e-mail e por conexão em 48 horas, e os totais diários gerais (sem e-mail nem IP) em 35 dias;
* **registros de funcionamento:** o serviço não registra códigos, e-mails nem o conteúdo das mensagens.

**Nesta versão, o serviço de códigos ainda não foi publicado para uso por outras pessoas.** A empresa de hospedagem, o domínio de envio, quem será responsável pela operação do serviço publicado e o tratamento dado aos dados pelos provedores de hospedagem e de envio (inclusive por quanto tempo eles guardam essas informações) ainda não foram definidos. Esta política será atualizada antes da publicação.

*Modo de demonstração (desenvolvimento).* Nele, o serviço de códigos e uma caixa de mensagens rodam no próprio computador, e os dados do fluxo de códigos são tratados localmente, sem envio ao provedor de e-mail. Cada mensagem (endereço, assunto e código) é gravada como **texto legível** em um arquivo com acesso restrito ao usuário do computador que executa a demonstração, em uma pasta própria fora do aplicativo; as chaves da demonstração ficam na mesma pasta, também com acesso restrito. Esses arquivos ficam lá até serem apagados manualmente. Informar o código gravado localmente apenas conclui o fluxo demonstrativo: a conta aparece como verificada no banco da demonstração, mas isso não comprova acesso ao endereço informado.

*Outras comunicações.* Fora o serviço de códigos, o Sino não envia suas informações a terceiros e não inclui telemetria nem coleta de estatísticas de uso.

Para exibir as telas, o Sino usa a biblioteca Flet. Na primeira execução em um computador, se o componente de interface da Flet ainda não estiver disponível, a própria biblioteca pode baixá-lo da internet, a partir do GitHub, onde a Flet publica suas versões. Esse download é feito pela biblioteca, não pelo Sino.

A verificação técnica feita para esta política abrangeu o código do Sino e esse comportamento da Flet. As demais partes das bibliotecas de terceiros usadas pelo Sino não foram examinadas por completo.

O aviso sonoro de "limite atingido" usa programas de som do próprio computador. Em caso de erro, detalhes técnicos podem aparecer no terminal do computador; o Sino não os envia para fora.

## 8. O que você pode fazer com suas informações

No aplicativo, você pode ver, editar e excluir suas contas financeiras e categorias, alterar seu nome e sua senha e escolher o tema.

Com o serviço de códigos disponível (item 7), você também pode alterar o e-mail e recuperar uma senha esquecida.

*Excluir a conta de usuário.* Em Ajustes > Excluir conta, depois de informar a senha atual e confirmar, você pode excluir sua conta de usuário. A exclusão apaga do banco de dados atual (`database/sino.db`), em uma única operação, os dados da sua conta de usuário (nome, e-mail e sua confirmação, senha protegida, data do aceite e tema), suas contas financeiras, séries recorrentes e categorias. Se algo falhar no meio, nada é apagado. Os dados dos outros usuários da mesma instalação não são alterados.

A exclusão da conta de usuário **não alcança**:

* as cópias de segurança já existentes em `database/backups/` (item 6), que continuam contendo seus dados até serem apagadas manualmente;
* o registro técnico das confirmações por código (item 2), que não identifica usuários;
* o que o serviço de códigos e o provedor de envio já receberam ou guardaram (item 7), que segue os prazos e o tratamento de cada um; o Sino não pede a esses serviços que apaguem nada;
* cópias feitas fora do aplicativo, como cópias da pasta do Sino, backups do computador ou arquivos do modo de demonstração.

*Vestígios técnicos.* Ao excluir um item ou a conta de usuário, os dados deixam de aparecer no aplicativo. Na exclusão da conta de usuário, o Sino pede ao banco de dados que sobrescreva o espaço liberado no arquivo. Essa é uma medida adicional: não garante que a informação não possa ser recuperada por outros meios, como cópias, arquivos temporários do banco de dados ou recursos do sistema e do dispositivo de armazenamento. Nas demais exclusões, o próprio arquivo do banco pode manter vestígios técnicos da informação apagada até que esse espaço seja reutilizado.

## 9. Sair da conta não apaga dados

"Sair da conta" apenas encerra a sessão. Nenhuma informação é removida, e ao entrar novamente tudo continua lá, inclusive o tema escolhido.

## 10. Por quanto tempo as informações ficam guardadas

As informações permanecem no banco de dados enquanto o arquivo `database/sino.db` for mantido, até serem excluídas no aplicativo (item 8). As cópias de segurança permanecem enquanto os seus próprios arquivos em `database/backups/` forem mantidos. Excluir itens ou a conta de usuário no aplicativo não apaga essas cópias. Os prazos do serviço de códigos estão no item 7.

Desinstalar ou apagar apenas o programa não garante que o banco e os backups sejam removidos. **Atenção:** apagar manualmente `database/sino.db` remove os dados de todos os usuários daquela instalação, não apenas os seus. Os backups são arquivos separados em `database/backups/` e permanecem até serem apagados também. O aplicativo não oferece uma função para desfazer essa remoção.

## 11. Alterações desta política

Esta política pode mudar em versões futuras do Sino. Quando isso acontecer, o texto atualizado ficará disponível dentro do aplicativo e as alterações serão mencionadas nas notas da versão. Nesta versão, não há controle de versões do texto nem novo pedido de aceite.

## 12. Contato

Dúvidas, sugestões e relatos de problemas podem ser enviados para sino.lembrete.contas@gmail.com. Não envie senhas, arquivos do banco de dados ou informações financeiras pessoais.
