# Política de Privacidade do Sino

Última atualização: 13/10/2026

O Sino é um projeto pessoal de portfólio desenvolvido por Carinne Batista. Esta política descreve como a **versão desktop atual** do Sino trata as informações registradas nele. As afirmações sobre o que o Sino guarda, usa e envia se referem ao próprio aplicativo; o serviço de códigos, os provedores que ele usa e as bibliotecas de terceiros são tratados no item 7.

## 1. Funcionamento local

O Sino é instalado e usado no computador. As informações de cada instalação ficam nesse computador, e o aplicativo não as envia à desenvolvedora nem a terceiros. A desenvolvedora não recebe, por meio do Sino, os dados registrados em instalações de outras pessoas, exceto o que passa pelo serviço de códigos (item 7).

A única função que conversa com um serviço fora do aplicativo é a **confirmação por código** (criar conta, alterar o e-mail e recuperar a senha). Quando o serviço real estiver em uso, o endereço de e-mail e alguns dados técnicos serão enviados pela internet ao serviço de códigos, operado pela desenvolvedora, e o endereço e a mensagem com o código chegarão ao provedor que entrega o e-mail (item 7). No modo de demonstração, o serviço roda no próprio computador e os dados do fluxo de códigos são tratados localmente, sem envio ao provedor de e-mail. Nome, senha e informações financeiras não são enviados em nenhum dos casos.

## 2. Quais informações o Sino guarda

*Dados da sua conta de usuário:* nome, e-mail, se o e-mail foi confirmado por código, senha (guardada de forma protegida, veja o item 5), a data em que você aceitou os Termos de Uso e esta Política, e sua preferência de tema (Claro ou Escuro).

*Registros de aceite e de ciência dos documentos:* nas contas criadas a partir da versão de 06/10/2026, o Sino guarda qual versão dos Termos de Uso e desta Política foi aceita no cadastro, com a data e a hora. Quando um desses documentos receber uma mudança relevante e você aceitar a nova versão, o Sino guarda a versão aceita, com a data e a hora. Quando um documento receber um ajuste menor e você clicar em "Entendi" no aviso, o Sino guarda a versão avisada, com a data e a hora, como **registro de ciência**: esse registro mostra que o aviso foi visto e **não** equivale a um aceite. Nas contas criadas antes da versão de 06/10/2026, o aceite original permanece registrado apenas pela data, sem versão identificada. Novos aceites e registros de ciência passam a ser guardados conforme as regras descritas acima.

*Registro técnico das confirmações por código:* para que a mesma confirmação não seja usada duas vezes, o Sino guarda um identificador aleatório de cada confirmação usada, a finalidade (cadastro, alteração de e-mail ou recuperação de senha) e até quando ela valeria. Esse registro não contém e-mail, nome nem senha, e os itens vencidos são apagados nas confirmações seguintes. Como não está ligado a nenhum usuário, ele não é apagado na exclusão da conta de usuário (item 8).

*Informações financeiras que você registra:* nome, valor, data de vencimento, situação (paga ou pendente), data de pagamento, categoria, descrição (opcional) e recorrência de cada conta; nome, emoji e cor de cada categoria.

Além dessas, o Sino não coleta outras informações: não pede a localização do dispositivo nem coleta contatos, dados bancários ou dados do seu computador. A exceção é a confirmação por código: ao usá-la, o serviço de códigos recebe dados técnicos do pedido, como o endereço IP de onde ele parte e identificadores gerados na hora. O endereço IP pode permitir inferir uma localização geográfica aproximada, como a cidade ou a região. O serviço usa o endereço IP apenas para limitar abusos: guarda um resumo calculado a partir dele, não guarda o IP completo em texto no armazenamento do serviço de códigos e não o usa para determinar a localização geográfica. O que é enviado, o que o serviço guarda e por quanto tempo estão descritos no item 7.

## 3. Para que essas informações são usadas

Somente para o funcionamento do aplicativo: permitir que você entre na sua conta, confirmar o e-mail por código (cadastro, alteração de e-mail e recuperação de senha), mostrar e organizar suas contas, calcular totais, indicar vencimentos e atrasos, exibir gráficos e aplicar o tema escolhido. O Sino não usa suas informações para publicidade. Os registros de aceite e de ciência dos documentos servem para saber quais versões dos Termos de Uso e desta Política cada usuário aceitou ou viu, e assim decidir quando pedir um novo aceite ou mostrar um aviso.

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

No envio real, o serviço gera o código e o envia ao endereço informado por meio de um provedor de envio de e-mails, a **Resend**. O pedido de envio à Resend parte do serviço, não diretamente do seu computador. O provedor recebe o endereço e a mensagem com o código de forma legível, porque precisa entregá-la. O serviço não conhece as contas do Sino: na recuperação de senha, quando não há uma conta com e-mail confirmado naquele endereço, o pedido é enviado do mesmo jeito, mas nenhum e-mail é mandado.

O que o serviço guarda, pela implementação atual:

* **e-mail, endereço IP e código:** não são guardados como texto. O serviço guarda resumos de mão única (HMAC-SHA256) calculados com uma chave secreta dele, que permitem comparar valores sem guardá-los. Isso não é criptografia reversível: o serviço não recupera o texto a partir do resumo. Do IP, entra no resumo o endereço IPv4 completo ou o início (/64) do endereço IPv6;
* **identificadores técnicos:** o segredo e as chaves de cada pedido também ficam só como resumo; o identificador de vínculo enviado pelo aplicativo já chega como resumo (SHA-256) e é guardado como recebido; o identificador da confirmação emitida fica legível. Nenhum deles contém o e-mail em texto;
* **legíveis:** a finalidade do pedido, horários, número de tentativas, situação do envio, resultado de cada tentativa e contadores usados para limitar abusos;
* **prazos:** os pedidos encerrados são apagados 24 horas depois do encerramento, os contadores por hora em 2 horas, os contadores diários por e-mail e por conexão em 48 horas, e os totais diários gerais (sem e-mail nem IP) em 35 dias. Veja abaixo o que a plataforma de hospedagem pode manter depois disso;
* **registros de funcionamento:** o serviço não registra códigos, e-mails nem o conteúdo das mensagens.

**O que se segue descreve o funcionamento do serviço real de códigos, planejado para a fase restrita de testes, e vale quando ele estiver em uso.**

*Quem opera o serviço.* O serviço de códigos é operado por Carinne Batista, desenvolvedora do Sino, que define como ele funciona e quais dados ele trata. Dúvidas e pedidos sobre esses dados podem ser enviados ao contato do item 12.

*Fase restrita de testes.* Nesta fase, o serviço real é destinado apenas a testes restritos da desenvolvedora: só poderão receber códigos os endereços de e-mail autorizados por ela (item 4 dos Termos de Uso). A lista de endereços autorizados também é guardada só como resumo (HMAC-SHA256), sem os endereços em texto. Pedidos para outros endereços são recusados ou respondidos de forma neutra, sem envio de e-mail, mas o serviço e a hospedagem recebem e tratam os dados desses pedidos como descrito neste item.

*Hospedagem: Cloudflare.* O serviço roda na plataforma Cloudflare Workers, da empresa norte-americana Cloudflare, e guarda os dados descritos acima no armazenamento da própria plataforma (Durable Objects). Segundo a documentação da Cloudflare, esse armazenamento fica em um centro de dados escolhido pela plataforma, sem garantia de país; por isso, esses dados podem ficar fora do Brasil. A plataforma também oferece um recurso que permite restaurar esse armazenamento a um momento dos últimos 30 dias; por isso, dados que o serviço já apagou nos prazos acima podem continuar recuperáveis pela plataforma dentro dessa janela. Na configuração prevista para o serviço, os registros de funcionamento e de rastreamento da plataforma (Workers Logs e Traces) ficam desligados. Isso não impede que a Cloudflare, como em qualquer conexão que passa pela sua rede, receba o endereço IP e dados técnicos de cada pedido e os trate conforme a própria política de privacidade. Essa política não informa um prazo específico para esses dados e diz que a Cloudflare guarda informações principalmente nos Estados Unidos e na Europa e pode acessá-las de qualquer parte do mundo.

*Envio: Resend.* Os e-mails são enviados pela Resend, empresa norte-americana, a partir do domínio `envios.appsino.com.br`, pelo remetente `nao-responda@envios.appsino.com.br`; as respostas a eles chegam ao contato do item 12. O serviço deve operar sem rastreamento de abertura e de cliques: cada e-mail é só texto, sem links nem imagens, e o rastreamento fica desativado na configuração do domínio de envio, que é conferida novamente antes do primeiro envio real. Os e-mails saem pela região de envio de São Paulo, mas essa escolha define apenas de onde as mensagens partem: segundo a Resend, os dados da conta, inclusive o conteúdo das mensagens e os registros de entrega, ficam guardados nos **Estados Unidos**, qualquer que seja a região de envio. A Resend informa que guarda os dados de cada e-mail enviado (endereço, conteúdo com o código, situação da entrega e registros) por **30 dias** no plano usado e que mantém cópias de segurança por **7 dias**; ela não detalha como esses dois prazos se combinam. A remoção de uma mensagem antes do fim do prazo depende de pedido feito à Resend. Durante esse período, pessoas com acesso autorizado à conta da desenvolvedora na Resend podem ver no painel o endereço, o assunto e o conteúdo dos e-mails enviados, inclusive os códigos. A Resend também informa que uma pequena amostra de e-mails pode ser analisada para segurança e prevenção de abuso. Para prestar o serviço, ela usa outras empresas (suboperadores), cujos nomes, finalidades e localizações constam da lista oficial publicada pela Resend em https://resend.com/legal/subprocessors. O código perde a validade em 10 minutos, bem antes desses prazos.

*Transferência internacional.* Por causa desses provedores, o endereço de e-mail, a mensagem com o código, o endereço IP e os dados técnicos dos pedidos são tratados fora do Brasil, inclusive nos Estados Unidos.

*Modo de demonstração (desenvolvimento).* Nele, o serviço de códigos e uma caixa de mensagens rodam no próprio computador, e os dados do fluxo de códigos são tratados localmente, sem envio ao provedor de e-mail. Cada mensagem (endereço, assunto e código) é gravada como **texto legível** em um arquivo com acesso restrito ao usuário do computador que executa a demonstração, em uma pasta própria fora do aplicativo; as chaves da demonstração ficam na mesma pasta, também com acesso restrito. Esses arquivos ficam lá até serem apagados manualmente. Informar o código gravado localmente apenas conclui o fluxo demonstrativo: a conta aparece como verificada no banco da demonstração, mas isso não comprova acesso ao endereço informado.

*Outras comunicações.* Fora o serviço de códigos, o Sino não envia suas informações a terceiros e não inclui telemetria nem coleta de estatísticas de uso.

Para exibir as telas, o Sino usa a biblioteca Flet. Na primeira execução em um computador, se o componente de interface da Flet ainda não estiver disponível, a própria biblioteca pode baixá-lo da internet, a partir do GitHub, onde a Flet publica suas versões. Esse download é feito pela biblioteca, não pelo Sino.

A verificação técnica feita para esta política abrangeu o código do Sino e esse comportamento da Flet. As demais partes das bibliotecas de terceiros usadas pelo Sino não foram examinadas por completo.

O aviso sonoro de "limite atingido" usa programas de som do próprio computador. Em caso de erro, detalhes técnicos podem aparecer no terminal do computador; o Sino não os envia para fora.

## 8. O que você pode fazer com suas informações

No aplicativo, você pode ver, editar e excluir suas contas financeiras e categorias, alterar seu nome e sua senha e escolher o tema.

Com o serviço de códigos disponível (item 7), você também pode alterar o e-mail e recuperar uma senha esquecida.

*Excluir a conta de usuário.* Em Ajustes > Excluir conta, depois de informar a senha atual e confirmar, você pode excluir sua conta de usuário. A exclusão apaga do banco de dados atual (`database/sino.db`), em uma única operação, os dados da sua conta de usuário (nome, e-mail e sua confirmação, senha protegida, data do aceite, registros de aceite e de ciência dos documentos e tema), suas contas financeiras, séries recorrentes e categorias. Se algo falhar no meio, nada é apagado. Os dados dos outros usuários da mesma instalação não são alterados.

A exclusão da conta de usuário **não alcança**:

* as cópias de segurança já existentes em `database/backups/` (item 6), que continuam contendo seus dados até serem apagadas manualmente;
* o registro técnico das confirmações por código (item 2), que não identifica usuários;
* o que o serviço de códigos e o provedor de envio já receberam ou guardaram (item 7), que segue os prazos e o tratamento de cada um; o Sino não pede a esses serviços que apaguem nada;
* cópias feitas fora do aplicativo, como cópias da pasta do Sino, backups do computador ou arquivos do modo de demonstração.

*Dados do serviço de códigos.* Dúvidas e pedidos sobre os dados tratados pelo serviço de códigos e pelos provedores (item 7) podem ser enviados ao contato do item 12.

*Vestígios técnicos.* Ao excluir um item ou a conta de usuário, os dados deixam de aparecer no aplicativo. Na exclusão da conta de usuário, o Sino pede ao banco de dados que sobrescreva o espaço liberado no arquivo. Essa é uma medida adicional: não garante que a informação não possa ser recuperada por outros meios, como cópias, arquivos temporários do banco de dados ou recursos do sistema e do dispositivo de armazenamento. Nas demais exclusões, o próprio arquivo do banco pode manter vestígios técnicos da informação apagada até que esse espaço seja reutilizado.

## 9. Sair da conta não apaga dados

"Sair da conta" apenas encerra a sessão. Nenhuma informação é removida, e ao entrar novamente tudo continua lá, inclusive o tema escolhido.

## 10. Por quanto tempo as informações ficam guardadas

As informações permanecem no banco de dados enquanto o arquivo `database/sino.db` for mantido, até serem excluídas no aplicativo (item 8). Os registros de aceite e de ciência dos documentos ficam guardados enquanto a sua conta de usuário existir e são apagados na exclusão da conta. Eles podem continuar existindo nas cópias de segurança já feitas antes da exclusão (item 6), que o aplicativo não apaga. As cópias de segurança permanecem enquanto os seus próprios arquivos em `database/backups/` forem mantidos. Excluir itens ou a conta de usuário no aplicativo não apaga essas cópias. Os prazos do serviço de códigos e dos provedores estão no item 7.

Desinstalar ou apagar apenas o programa não garante que o banco e os backups sejam removidos. **Atenção:** apagar manualmente `database/sino.db` remove os dados de todos os usuários daquela instalação, não apenas os seus. Os backups são arquivos separados em `database/backups/` e permanecem até serem apagados também. O aplicativo não oferece uma função para desfazer essa remoção.

## 11. Alterações desta política

Esta política pode mudar em versões futuras do Sino. Cada versão é identificada pela data, que aparece no aplicativo ("Versão de dd/mm/aaaa"), e as alterações são mencionadas nas notas da versão. Quando uma mudança for relevante, o Sino pede um novo aceite no próximo login, e sem ele não é possível entrar. Ajustes menores são informados por um aviso, sem bloquear o acesso. Os registros guardados são os do item 2.

## 12. Contato

Dúvidas, sugestões, relatos de problemas e pedidos sobre dados pessoais podem ser enviados para sino.lembrete.contas@gmail.com, endereço acompanhado pela desenvolvedora, que opera o serviço de códigos (item 7). Quando houver envio real, as respostas aos e-mails de código também chegarão a esse endereço. Esse endereço é uma conta do Gmail: as mensagens enviadas a ele são tratadas pelo Google, conforme as políticas do Google. Não envie senhas, códigos, arquivos do banco de dados ou informações financeiras pessoais.
